#!/usr/bin/env python3
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = "filebot.db"

def check_recent_crawl():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查找最近24小时内创建的HTML文档
    one_day_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    
    print("=== 最近24小时内创建的HTML文档 ===")
    cursor.execute("""
        SELECT d.id, d.title, d.original_filename, d.file_type, d.file_size, 
               d.created_at, d.folder_id, d.stored_filename, d.document_metadata,
               f.name as folder_name, f.path as folder_path
        FROM documents d
        LEFT JOIN folders f ON d.folder_id = f.id
        WHERE d.file_type IN ('html', 'htm', 'HTML', 'HTM')
          AND d.created_at > ?
        ORDER BY d.created_at DESC
        LIMIT 20
    """, (one_day_ago,))
    
    recent_docs = cursor.fetchall()
    
    if not recent_docs:
        print("没有找到最近24小时内创建的HTML文档")
        # 检查所有HTML文档，按创建时间排序
        cursor.execute("""
            SELECT d.id, d.title, d.original_filename, d.file_type, d.file_size, 
                   d.created_at, d.folder_id, d.stored_filename, d.document_metadata,
                   f.name as folder_name, f.path as folder_path
            FROM documents d
            LEFT JOIN folders f ON d.folder_id = f.id
            WHERE d.file_type IN ('html', 'htm', 'HTML', 'HTM')
            ORDER BY d.created_at DESC
            LIMIT 20
        """)
        recent_docs = cursor.fetchall()
    
    for i, doc in enumerate(recent_docs):
        print(f"\n[{i+1}] {doc['title']}")
        print(f"    文件名: {doc['original_filename']}")
        print(f"    文件类型: {doc['file_type']}")
        print(f"    数据库大小: {doc['file_size']} 字节")
        print(f"    创建时间: {doc['created_at']}")
        print(f"    文件夹: {doc['folder_name']} ({doc['folder_path']})")
        
        # 检查文件系统中是否存在
        if doc['stored_filename']:
            # 尝试多个可能的路径
            possible_paths = []
            
            # 1. 默认存储路径
            possible_paths.append(Path("data/files/original") / doc['stored_filename'])
            
            # 2. 爬虫存储路径 (website_crawler.py使用的路径)
            if doc['folder_id']:
                possible_paths.append(Path("data/documents") / doc['folder_id'] / (doc['original_filename'] or f"{doc['id']}.{doc['file_type']}"))
            
            # 3. 直接路径
            if os.path.isabs(doc['stored_filename']):
                possible_paths.append(Path(doc['stored_filename']))
            
            file_found = False
            for path in possible_paths:
                if path.exists():
                    actual_size = path.stat().st_size
                    print(f"    文件系统路径: {path}")
                    print(f"    实际文件大小: {actual_size} 字节")
                    
                    if doc['file_size'] == 0 and actual_size > 0:
                        print(f"    ⚠️ 警告: 数据库记录为0字节，但实际文件大小为{actual_size}字节")
                    elif doc['file_size'] > 0 and actual_size == 0:
                        print(f"    ⚠️ 警告: 数据库记录为{doc['file_size']}字节，但实际文件为0字节")
                    elif doc['file_size'] == 0 and actual_size == 0:
                        print(f"    ❌ 严重: 文件和数据库都显示为0字节")
                    else:
                        print(f"    ✓ 大小匹配")
                    
                    file_found = True
                    break
            
            if not file_found:
                print(f"    ❌ 文件未找到 (存储路径: {doc['stored_filename']})")
                
                # 尝试更广泛的搜索
                print(f"    搜索可能的文件位置...")
                search_pattern = f"**/*{doc['original_filename']}" if doc['original_filename'] else f"**/*{doc['id']}*"
                for search_path in [Path("data/documents"), Path("data/files")]:
                    if search_path.exists():
                        for file in search_path.rglob(search_pattern):
                            if file.is_file():
                                print(f"    找到可能文件: {file}, 大小: {file.stat().st_size} 字节")
        else:
            print(f"    ❌ 无存储文件名记录")
        
        # 检查元数据中是否有html_content
        if doc['document_metadata']:
            try:
                import json
                metadata = json.loads(doc['document_metadata'])
                if 'html_content' in metadata:
                    html_len = len(metadata['html_content'])
                    print(f"    元数据html_content长度: {html_len} 字符")
                    if html_len == 0:
                        print(f"    ⚠️ 元数据中html_content为空")
                else:
                    print(f"    元数据中无html_content字段")
            except:
                print(f"    无法解析元数据: {doc['document_metadata'][:100]}...")
    
    # 检查最近的ConversionTask记录
    print("\n=== 最近的爬虫任务 ===")
    cursor.execute("""
        SELECT id, task_type, status, parameters, created_at, updated_at, result
        FROM conversion_tasks
        WHERE task_type = 'website_crawl' OR task_type LIKE '%crawl%'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    tasks = cursor.fetchall()
    for task in tasks:
        print(f"\n任务ID: {task['id']}")
        print(f"任务类型: {task['task_type']}")
        print(f"状态: {task['status']}")
        print(f"创建时间: {task['created_at']}")
        print(f"更新时间: {task['updated_at']}")
        if task['parameters']:
            print(f"参数: {task['parameters'][:100]}...")
    
    conn.close()
    
    print("\n=== 文件系统检查 ===")
    # 统计零字节HTML文件
    zero_count = 0
    total_html = 0
    for html_file in Path("data/documents").rglob("*.html"):
        total_html += 1
        if html_file.stat().st_size == 0:
            zero_count += 1
            print(f"零字节文件: {html_file}")
    
    for html_file in Path("data/documents").rglob("*.htm"):
        total_html += 1
        if html_file.stat().st_size == 0:
            zero_count += 1
            print(f"零字节文件: {html_file}")
    
    print(f"\n总计HTML文件: {total_html}")
    print(f"零字节HTML文件: {zero_count}")
    
    if zero_count > 0:
        print(f"\n⚠️ 发现{zero_count}个零字节HTML文件")

if __name__ == "__main__":
    check_recent_crawl()