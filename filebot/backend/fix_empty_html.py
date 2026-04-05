#!/usr/bin/env python3
"""
修复空HTML文件：从元数据中提取html_content并写入文件
"""
import sqlite3
import os
import json
import sys
from pathlib import Path

DB_PATH = 'filebot.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查找所有大小为0的HTML文件（不区分大小写）
    cursor.execute("""
        SELECT id, original_filename, stored_filename, file_size, folder_id, document_metadata 
        FROM documents 
        WHERE LOWER(file_type) IN ('html', 'htm') AND file_size = 0
    """)
    empty_html = cursor.fetchall()
    
    print(f"找到 {len(empty_html)} 个大小为0的HTML文件")
    
    fixed_count = 0
    for doc in empty_html:
        doc_id = doc['id']
        original_filename = doc['original_filename']
        stored_filename = doc['stored_filename']
        folder_id = doc['folder_id']
        metadata_str = doc['document_metadata']
        
        print(f"\n处理文档: {original_filename} (ID: {doc_id})")
        
        # 解析元数据
        try:
            metadata = json.loads(metadata_str) if metadata_str else {}
        except json.JSONDecodeError:
            print(f"  ⚠️  元数据JSON解析失败: {metadata_str[:100]}")
            metadata = {}
        
        # 检查html_content字段
        html_content = metadata.get('html_content')
        if not html_content:
            print(f"  ⚠️  元数据中没有html_content字段")
            continue
        
        # 确定文件路径
        possible_paths = [
            Path("data/documents") / stored_filename,
            Path("data/files/original") / stored_filename,
        ]
        
        file_path = None
        for path in possible_paths:
            if path.exists():
                file_path = path
                break
        
        if not file_path:
            # 文件不存在，尝试创建
            file_path = Path("data/documents") / stored_filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"  📁 创建新文件路径: {file_path}")
        
        # 检查当前文件大小
        current_size = file_path.stat().st_size if file_path.exists() else 0
        print(f"  当前文件大小: {current_size} 字节")
        
        # 如果文件非空，跳过
        if current_size > 0:
            print(f"  ⚠️  文件已有内容，跳过")
            continue
        
        # 写入HTML内容
        try:
            # 确保内容不为空
            if not html_content or html_content.strip() == '':
                print(f"  ⚠️  html_content为空，跳过")
                continue
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 获取实际文件大小
            actual_size = os.path.getsize(file_path)
            print(f"  ✅ 写入成功，新文件大小: {actual_size} 字节")
            
            # 更新数据库记录
            cursor.execute(
                "UPDATE documents SET file_size = ? WHERE id = ?",
                (actual_size, doc_id)
            )
            conn.commit()
            print(f"  ✅ 数据库记录更新: file_size = {actual_size}")
            
            fixed_count += 1
            
        except Exception as e:
            print(f"  ❌ 写入文件失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"修复完成: {fixed_count}/{len(empty_html)} 个文件已修复")
    
    # 验证修复结果
    print("\n验证修复结果:")
    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE file_type IN ('html', 'htm') AND file_size = 0")
    still_empty = cursor.fetchone()['count']
    print(f"仍然为空的HTML文件: {still_empty} 个")
    
    conn.close()
    
    if still_empty > 0:
        print("\n⚠️  仍有空HTML文件，可能需要手动检查或重新爬取")
        return 1
    else:
        print("\n✅ 所有HTML文件都已修复！")
        return 0

if __name__ == "__main__":
    sys.exit(main())