#!/usr/bin/env python3
import sqlite3
import os
import json
import sys

DB_PATH = 'filebot.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 统计所有HTML文件
    cursor.execute("""
        SELECT 
            COUNT(*) as total_html,
            SUM(CASE WHEN file_size = 0 THEN 1 ELSE 0 END) as empty_html,
            SUM(CASE WHEN file_size > 0 THEN 1 ELSE 0 END) as non_empty_html,
            AVG(file_size) as avg_size,
            MIN(file_size) as min_size,
            MAX(file_size) as max_size
        FROM documents 
        WHERE LOWER(file_type) IN ('html', 'htm')
    """)
    stats = cursor.fetchone()
    
    print("📊 HTML文件统计报告")
    print("=" * 50)
    print(f"HTML文件总数: {stats['total_html'] or 0}")
    print(f"空文件(0字节): {stats['empty_html'] or 0}")
    print(f"非空文件: {stats['non_empty_html'] or 0}")
    print(f"平均大小: {stats['avg_size'] or 0:.1f} 字节")
    print(f"最小大小: {stats['min_size'] or 0} 字节")
    print(f"最大大小: {stats['max_size'] or 0} 字节")
    
    if stats['empty_html'] and stats['empty_html'] > 0:
        empty_percent = (stats['empty_html'] / stats['total_html']) * 100
        print(f"\n⚠️  警告: {empty_percent:.1f}% 的HTML文件为空!")
    
    # 列出所有空HTML文件的详细信息
    print("\n📋 空HTML文件列表:")
    cursor.execute("""
        SELECT id, original_filename, stored_filename, file_size, folder_id, document_metadata
        FROM documents 
        WHERE LOWER(file_type) IN ('html', 'htm') AND file_size = 0
        LIMIT 20
    """)
    empty_files = cursor.fetchall()
    
    for i, doc in enumerate(empty_files):
        print(f"\n{i+1}. {doc['original_filename']}")
        print(f"   文档ID: {doc['id']}")
        print(f"   存储文件: {doc['stored_filename']}")
        print(f"   文件夹ID: {doc['folder_id']}")
        
        # 检查元数据中是否有html_content
        metadata_str = doc['document_metadata']
        has_html_content = False
        if metadata_str:
            try:
                metadata = json.loads(metadata_str)
                if 'html_content' in metadata and metadata['html_content']:
                    content_len = len(metadata['html_content'])
                    print(f"   元数据中html_content长度: {content_len} 字符")
                    has_html_content = True
                else:
                    print(f"   元数据中无html_content或为空")
            except json.JSONDecodeError:
                print(f"   元数据JSON解析失败")
        else:
            print(f"   无元数据")
        
        # 检查文件系统
        possible_paths = [
            os.path.join("data/documents", doc['stored_filename']),
            os.path.join("data/files/original", doc['stored_filename']),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                actual_size = os.path.getsize(path)
                print(f"   文件路径: {path}")
                print(f"   实际文件大小: {actual_size} 字节")
                if actual_size > 0:
                    print(f"   ✅ 文件系统已有内容!")
                elif has_html_content:
                    print(f"   ⚠️  文件为空但元数据有内容（可修复）")
                break
        else:
            print(f"   ❌ 文件未找到")
    
    # 检查非空HTML文件示例
    print("\n📋 非空HTML文件示例:")
    cursor.execute("""
        SELECT original_filename, file_size, folder_id
        FROM documents 
        WHERE LOWER(file_type) IN ('html', 'htm') AND file_size > 0
        LIMIT 5
    """)
    non_empty_files = cursor.fetchall()
    
    for i, doc in enumerate(non_empty_files):
        print(f"{i+1}. {doc['original_filename']} - {doc['file_size']} 字节")
    
    # 按文件夹统计
    print("\n📊 按文件夹统计空HTML文件:")
    cursor.execute("""
        SELECT folder_id, COUNT(*) as empty_count
        FROM documents 
        WHERE LOWER(file_type) IN ('html', 'htm') AND file_size = 0
        GROUP BY folder_id
        ORDER BY empty_count DESC
    """)
    folder_stats = cursor.fetchall()
    
    for stat in folder_stats:
        print(f"文件夹 {stat['folder_id']}: {stat['empty_count']} 个空文件")
    
    conn.close()
    
    # 提供修复建议
    if stats['empty_html'] and stats['empty_html'] > 0:
        print(f"\n🚀 修复建议:")
        print(f"1. 运行修复脚本: python3 fix_empty_html.py")
        print(f"2. 总共需要修复 {stats['empty_html']} 个文件")
        print(f"3. 修复前提: 元数据中必须有html_content字段")

if __name__ == "__main__":
    main()