#!/usr/bin/env python3
"""
修复零字节HTML文件：从数据库元数据中提取html_content并重新写入文件
"""
import sys
import os
import json
import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = "filebot.db"

def fix_zero_size_html():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查找文件大小为0的HTML文档
    cursor.execute("""
        SELECT d.id, d.title, d.original_filename, d.file_type, d.file_size, 
               d.folder_id, d.stored_filename, d.document_metadata,
               f.path as folder_path
        FROM documents d
        LEFT JOIN folders f ON d.folder_id = f.id
        WHERE d.file_type IN ('html', 'htm', 'HTML', 'HTM')
          AND d.file_size = 0
        ORDER BY d.created_at DESC
    """)
    
    zero_size_docs = cursor.fetchall()
    
    print(f"找到 {len(zero_size_docs)} 个零字节HTML文档")
    
    fixed_count = 0
    error_count = 0
    
    for doc in zero_size_docs:
        doc_id = doc['id']
        title = doc['title']
        filename = doc['original_filename']
        folder_id = doc['folder_id']
        stored_filename = doc['stored_filename']
        metadata = doc['document_metadata']
        
        print(f"\n处理: {title} (ID: {doc_id})")
        print(f"  文件名: {filename}, 文件夹: {folder_id}")
        
        # 解析元数据
        html_content = None
        if metadata:
            try:
                meta_dict = json.loads(metadata)
                if 'html_content' in meta_dict:
                    html_content = meta_dict['html_content']
                    print(f"  从元数据找到html_content, 长度: {len(html_content)} 字符")
                else:
                    print(f"  元数据中无html_content字段")
            except json.JSONDecodeError:
                print(f"  无法解析元数据JSON")
                error_count += 1
                continue
        else:
            print(f"  无元数据")
            error_count += 1
            continue
        
        if not html_content:
            print(f"  html_content为空")
            error_count += 1
            continue
        
        # 构建文件路径
        # 尝试多个可能的路径
        possible_paths = []
        
        # 1. 默认存储路径
        if stored_filename:
            possible_paths.append(Path("data/files/original") / stored_filename)
        
        # 2. 爬虫存储路径
        possible_paths.append(Path("data/documents") / folder_id / (filename or f"{doc_id}.html"))
        
        # 3. 直接路径（如果stored_filename是绝对路径）
        if stored_filename and os.path.isabs(stored_filename):
            possible_paths.append(Path(stored_filename))
        
        target_path = None
        for path in possible_paths:
            if path.exists():
                target_path = path
                print(f"  找到文件: {target_path}")
                break
        
        if not target_path:
            # 文件不存在，创建它
            target_path = Path("data/documents") / folder_id / (filename or f"{doc_id}.html")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"  文件不存在，将创建: {target_path}")
        
        # 写入内容
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 验证写入
            if target_path.exists():
                actual_size = target_path.stat().st_size
                expected_size = len(html_content.encode('utf-8'))
                
                if actual_size == expected_size:
                    # 更新数据库中的file_size
                    cursor.execute(
                        "UPDATE documents SET file_size = ? WHERE id = ?",
                        (actual_size, doc_id)
                    )
                    print(f"  ✓ 修复成功: 文件大小 {actual_size} 字节")
                    fixed_count += 1
                else:
                    print(f"  ✗ 文件大小不匹配: 预期 {expected_size}, 实际 {actual_size}")
                    error_count += 1
            else:
                print(f"  ✗ 文件写入后不存在")
                error_count += 1
                
        except Exception as e:
            print(f"  ✗ 写入文件失败: {e}")
            error_count += 1
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print(f"\n=== 修复完成 ===")
    print(f"修复: {fixed_count} 个文件")
    print(f"错误: {error_count} 个文件")
    print(f"总计: {len(zero_size_docs)} 个零字节文档")
    
    return fixed_count

if __name__ == "__main__":
    fix_zero_size_html()