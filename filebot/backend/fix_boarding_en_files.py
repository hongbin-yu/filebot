#!/usr/bin/env python3
"""
修复Boarding应用中/en文件夹的零字节HTML文件
从元数据中提取html_content并重新写入文件
"""

import sqlite3
import json
import os
from pathlib import Path
import sys

def fix_zero_byte_html_files():
    """修复零字节HTML文件"""
    db_path = "filebot.db"
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查找Boarding应用中路径为/boarding/canada-site/en的文件夹
    cursor.execute('''
        SELECT f.id, f.name, f.path, f.app_id
        FROM folders f
        JOIN apps a ON f.app_id = a.id
        WHERE a.slug = 'boarding' AND f.path = '/boarding/canada-site/en'
    ''')
    folders = cursor.fetchall()
    
    if not folders:
        print("未找到/boarding/canada-site/en文件夹")
        return
    
    folder_id = folders[0][0]
    print(f"找到文件夹: ID={folder_id}, 名称={folders[0][1]}, 路径={folders[0][2]}")
    
    # 查找这个文件夹中的零字节HTML文档
    cursor.execute('''
        SELECT d.id, d.original_filename, d.file_type, d.file_size, d.stored_filename, d.document_metadata, d.title
        FROM documents d
        WHERE d.folder_id = ? AND d.file_type IN ('HTML', 'HTM') AND d.file_size = 0
    ''', (folder_id,))
    
    zero_byte_docs = cursor.fetchall()
    print(f"找到 {len(zero_byte_docs)} 个零字节HTML文档")
    
    fixed_count = 0
    for doc in zero_byte_docs:
        doc_id, filename, file_type, file_size, stored_filename, metadata_json, title = doc
        
        print(f"\n处理文档: ID={doc_id}, 文件名={filename}, 标题={title}")
        
        # 解析元数据
        try:
            metadata = json.loads(metadata_json) if metadata_json else {}
        except:
            metadata = {}
            print(f"  警告: 无法解析元数据JSON")
        
        # 获取html_content
        html_content = metadata.get('html_content')
        if not html_content:
            print(f"  跳过: 元数据中没有html_content字段")
            continue
        
        content_len = len(html_content) if html_content else 0
        print(f"  元数据html_content长度: {content_len} 字符")
        
        if content_len == 0:
            print(f"  跳过: html_content为空")
            continue
        
        # 构建文件路径
        if stored_filename:
            # 尝试多个可能的路径
            possible_paths = [
                Path("data/documents") / stored_filename,
                Path("data/files/original") / stored_filename,
                Path(stored_filename) if os.path.isabs(stored_filename) else None
            ]
            
            file_path = None
            for path in possible_paths:
                if path and path.exists():
                    file_path = path
                    break
            
            if not file_path:
                # 如果文件不存在，尝试基于文件夹ID和文件名构建路径
                file_path = Path("data/documents") / folder_id / filename
                print(f"  警告: 使用推测路径: {file_path}")
        else:
            # 没有存储路径，构建一个
            file_path = Path("data/documents") / folder_id / filename
        
        print(f"  文件路径: {file_path}")
        
        # 检查文件是否确实为0字节
        if file_path.exists():
            current_size = file_path.stat().st_size
            if current_size > 0:
                print(f"  跳过: 文件大小已为 {current_size} 字节（非零字节）")
                # 更新数据库记录以反映实际大小
                cursor.execute('UPDATE documents SET file_size = ? WHERE id = ?', (current_size, doc_id))
                conn.commit()
                print(f"  已更新数据库file_size字段: {current_size} 字节")
                fixed_count += 1
                continue
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件内容
        try:
            # 检查html_content是否有效
            if not html_content or not html_content.strip():
                # 创建占位符HTML
                placeholder = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="description" content="此页面内容为空，由FileBot系统自动生成">
</head>
<body>
    <h1>{title}</h1>
    <p>原始页面内容为空。此文件由FileBot系统自动生成。</p>
</body>
</html>"""
                html_content = placeholder
                print(f"  警告: html_content为空，使用占位符")
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 验证写入
            new_size = file_path.stat().st_size
            expected_size = len(html_content.encode('utf-8'))
            
            if new_size == expected_size:
                # 更新数据库记录
                cursor.execute('UPDATE documents SET file_size = ? WHERE id = ?', (new_size, doc_id))
                conn.commit()
                print(f"  ✓ 修复成功: 文件大小 {new_size} 字节")
                fixed_count += 1
            else:
                print(f"  ✗ 修复失败: 文件大小不匹配! 预期: {expected_size}, 实际: {new_size}")
        
        except Exception as e:
            print(f"  ✗ 修复失败: {e}")
    
    conn.close()
    print(f"\n修复完成: 成功修复 {fixed_count} 个文件")
    
    # 验证修复结果
    print("\n验证修复结果:")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM documents 
        WHERE folder_id = ? AND file_type IN ('HTML', 'HTM') AND file_size = 0
    ''', (folder_id,))
    remaining_zero = cursor.fetchone()[0]
    print(f"  剩余零字节HTML文档: {remaining_zero} 个")
    conn.close()

if __name__ == "__main__":
    print("开始修复Boarding应用中/en文件夹的零字节HTML文件...")
    fix_zero_byte_html_files()