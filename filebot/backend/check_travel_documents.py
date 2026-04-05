#!/usr/bin/env python3
"""
检查旅行和旅游文件夹中的零字节HTML文件
"""
import sqlite3
import json
import os
from pathlib import Path

def main():
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 1. 查找应用名为"Travel and tourism"或包含"travel"的应用
    cursor.execute('''
        SELECT id, name, slug FROM apps WHERE name LIKE '%travel%' OR name LIKE '%tourism%'
    ''')
    apps = cursor.fetchall()
    print("📋 找到的应用:")
    for app_id, app_name, app_slug in apps:
        print(f"  - {app_name} (ID: {app_id}, Slug: {app_slug})")
    
    # 2. 查找这些应用下的文件夹
    for app_id, app_name, app_slug in apps:
        cursor.execute('''
            SELECT id, name, path FROM folders WHERE app_id = ? OR app_id LIKE ? 
        ''', (app_id, f'%{app_id}%'))
        
        folders = cursor.fetchall()
        print(f"\n📁 应用 '{app_name}' 下的文件夹:")
        for folder_id, folder_name, folder_path in folders:
            print(f"  - {folder_name} (ID: {folder_id}, 路径: {folder_path})")
            
            # 3. 查找这个文件夹中的文档
            cursor.execute('''
                SELECT id, original_filename, file_type, file_size, stored_filename, document_metadata
                FROM documents WHERE folder_id = ?
            ''', (folder_id,))
            
            documents = cursor.fetchall()
            if documents:
                print(f"    📄 文档列表 ({len(documents)} 个):")
                for doc_id, filename, file_type, file_size, stored_filename, metadata_json in documents:
                    metadata = json.loads(metadata_json) if metadata_json else {}
                    html_content = metadata.get('html_content', '')
                    html_len = len(html_content) if html_content else 0
                    
                    # 检查文件是否存在
                    file_exists = False
                    actual_size = 0
                    if stored_filename:
                        file_path = Path('data/documents') / stored_filename
                        file_exists = file_path.exists()
                        if file_exists:
                            actual_size = file_path.stat().st_size
                    
                    print(f"      - {filename}")
                    print(f"        类型: {file_type}, 数据库大小: {file_size} 字节")
                    print(f"        存储路径: {stored_filename}")
                    print(f"        元数据html_content长度: {html_len} 字符")
                    print(f"        文件存在: {file_exists}")
                    print(f"        实际文件大小: {actual_size} 字节")
                    
                    # 特别关注零字节文件
                    if file_size == 0 or actual_size == 0:
                        print(f"        ⚠️  ⚠️  ⚠️ 零字节文件警告!")
                        print(f"        🔧 修复建议:")
                        print(f"          1. 检查html_content: {html_len > 0}")
                        print(f"          2. 文件路径: {file_path if stored_filename else '无'}")
                        print(f"          3. 是否存在: {file_exists}")
                    
                    print()
            else:
                print("    📭 无文档")
    
    # 4. 全局搜索"Travel.gc.ca"相关的文档
    print("\n🔍 全局搜索 'Travel.gc.ca' 相关文档:")
    cursor.execute('''
        SELECT d.id, d.original_filename, d.file_type, d.file_size, d.stored_filename, 
               d.folder_id, d.document_metadata, f.name as folder_name
        FROM documents d
        LEFT JOIN folders f ON d.folder_id = f.id
        WHERE d.original_filename LIKE '%Travel.gc.ca%' OR d.original_filename LIKE '%travel%'
    ''')
    
    travel_docs = cursor.fetchall()
    for doc_id, filename, file_type, file_size, stored_filename, folder_id, metadata_json, folder_name in travel_docs:
        metadata = json.loads(metadata_json) if metadata_json else {}
        html_content = metadata.get('html_content', '')
        html_len = len(html_content) if html_content else 0
        
        # 检查文件
        actual_size = 0
        if stored_filename:
            file_path = Path('data/documents') / stored_filename
            if file_path.exists():
                actual_size = file_path.stat().st_size
        
        print(f"  - {filename}")
        print(f"    文件夹: {folder_name} (ID: {folder_id})")
        print(f"    类型: {file_type}, 数据库大小: {file_size} 字节")
        print(f"    实际文件大小: {actual_size} 字节")
        print(f"    html_content长度: {html_len} 字符")
        print(f"    存储路径: {stored_filename}")
        
        if file_size == 0 or actual_size == 0:
            print(f"    ⚠️  零字节文件!")
    
    # 5. 统计所有零字节HTML文件
    print("\n📊 零字节HTML文件统计:")
    cursor.execute('''
        SELECT COUNT(*) FROM documents 
        WHERE file_type IN ('html', 'htm', 'HTML', 'HTM') AND file_size = 0
    ''')
    zero_count = cursor.fetchone()[0]
    print(f"  数据库记录为零的文件: {zero_count}")
    
    cursor.execute('''
        SELECT COUNT(*) FROM documents 
        WHERE file_type IN ('html', 'htm', 'HTML', 'HTM')
    ''')
    total_html = cursor.fetchone()[0]
    print(f"  总HTML文件数: {total_html}")
    
    # 6. 检查文件系统
    zero_files = list(Path('data/documents').rglob('*.html'))
    zero_files = [f for f in zero_files if f.stat().st_size == 0]
    print(f"  文件系统零字节HTML文件: {len(zero_files)} 个")
    
    if zero_files:
        print("  具体文件:")
        for f in zero_files[:10]:  # 只显示前10个
            print(f"    - {f}")
    
    conn.close()
    
    return 0

if __name__ == '__main__':
    exit(main())