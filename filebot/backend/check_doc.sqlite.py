#!/usr/bin/env python3
import sqlite3
import os
import sys

DB_PATH = 'filebot.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查找文件名包含government-communications的文档
    cursor.execute("SELECT id, original_filename, stored_filename, file_size, file_type, folder_id, document_metadata FROM documents WHERE original_filename LIKE ?", ('%government-communications%',))
    docs = cursor.fetchall()
    
    print(f"找到 {len(docs)} 个文档:")
    for doc in docs:
        print(f"ID: {doc['id']}")
        print(f"原始文件名: {doc['original_filename']}")
        print(f"存储文件名: {doc['stored_filename']}")
        print(f"文件类型: {doc['file_type']}")
        print(f"文件大小: {doc['file_size']} 字节")
        print(f"文件夹ID: {doc['folder_id']}")
        print(f"元数据: {doc['document_metadata']}")
        print("-" * 50)
        
        # 检查文件是否存在
        possible_paths = [
            os.path.join("data/documents", doc['stored_filename']),
            os.path.join("data/files/original", doc['stored_filename']),
        ]
        
        found = False
        for path in possible_paths:
            if os.path.exists(path):
                actual_size = os.path.getsize(path)
                print(f"文件路径: {path}")
                print(f"实际文件大小: {actual_size} 字节")
                print(f"数据库大小 vs 实际大小: {doc['file_size']} vs {actual_size}")
                if actual_size == 0:
                    print("⚠️  警告：实际文件大小为0字节！")
                    
                    # 如果是HTML文件，尝试查看内容
                    if doc['file_type'] in ['html', 'htm']:
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                print(f"文件内容预览（前200字符）: {content[:200]}")
                        except Exception as e:
                            print(f"读取文件失败: {e}")
                found = True
                break
        
        if not found:
            print("❌ 文件未找到在任何路径")
            
        print()
    
    # 同时检查其他HTML文件是否也有相同问题
    print("\n=== 检查其他HTML文件 ===")
    cursor.execute("SELECT id, original_filename, stored_filename, file_size, folder_id FROM documents WHERE file_type IN ('html', 'htm') AND file_size = 0 LIMIT 10")
    empty_html = cursor.fetchall()
    
    print(f"找到 {len(empty_html)} 个大小为0的HTML文件:")
    for doc in empty_html:
        print(f"文件名: {doc['original_filename']}, 大小: {doc['file_size']}, 文件夹ID: {doc['folder_id']}")
        
        # 检查文件
        path = os.path.join("data/documents", doc['stored_filename'])
        if os.path.exists(path):
            actual_size = os.path.getsize(path)
            if actual_size == 0:
                print(f"  -> 文件实际大小也为0: {path}")
            else:
                print(f"  -> 文件实际大小为 {actual_size} 字节（不一致！）")
        else:
            print(f"  -> 文件未找到: {path}")
    
    conn.close()

if __name__ == "__main__":
    main()