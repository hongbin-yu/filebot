#!/usr/bin/env python3
import sqlite3
import os
import json

DB_PATH = 'filebot.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查找200.html文档
    cursor.execute("""
        SELECT id, original_filename, stored_filename, file_size, folder_id, 
               document_metadata, file_type, title, description,
               created_at, uploaded_by
        FROM documents 
        WHERE original_filename LIKE '%200.html%' OR stored_filename LIKE '%200.html%'
    """)
    docs = cursor.fetchall()
    
    print(f"找到 {len(docs)} 个200.html文档")
    
    for doc in docs:
        print(f"\n文档ID: {doc['id']}")
        print(f"原始文件名: {doc['original_filename']}")
        print(f"存储文件名: {doc['stored_filename']}")
        print(f"文件类型: {doc['file_type']}")
        print(f"文件大小: {doc['file_size']} 字节")
        print(f"文件夹ID: {doc['folder_id']}")
        print(f"标题: {doc['title']}")
        print(f"描述: {doc['description']}")
        print(f"创建时间: {doc['created_at']}")
        print(f"上传者: {doc['uploaded_by']}")
        
        # 检查元数据
        metadata_str = doc['document_metadata']
        if metadata_str:
            try:
                metadata = json.loads(metadata_str)
                print(f"\n元数据内容:")
                for key, value in metadata.items():
                    if key == 'html_content':
                        content_len = len(value) if value else 0
                        print(f"  {key}: 长度={content_len} 字符")
                        if content_len > 0:
                            print(f"    预览: {value[:200]}...")
                    else:
                        print(f"  {key}: {value}")
            except json.JSONDecodeError:
                print(f"元数据JSON解析失败: {metadata_str[:100]}")
        else:
            print(f"\n无元数据")
        
        # 检查文件系统
        possible_paths = [
            os.path.join("data/documents", doc['stored_filename']),
            os.path.join("data/files/original", doc['stored_filename']),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                actual_size = os.path.getsize(path)
                print(f"\n文件路径: {path}")
                print(f"实际文件大小: {actual_size} 字节")
                
                if actual_size == 0:
                    print("⚠️  文件为空")
                    # 尝试读取文件内容
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            print(f"文件内容: '{content}' (长度: {len(content)})")
                    except Exception as e:
                        print(f"读取文件失败: {e}")
                break
        else:
            print(f"\n❌ 文件未找到")
    
    # 检查文件夹信息
    if docs:
        folder_id = docs[0]['folder_id']
        cursor.execute("SELECT id, name, path FROM folders WHERE id = ?", (folder_id,))
        folder = cursor.fetchone()
        if folder:
            print(f"\n📁 文件夹信息:")
            print(f"  文件夹ID: {folder['id']}")
            print(f"  文件夹名称: {folder['name']}")
            print(f"  文件夹路径: {folder['path']}")
    
    conn.close()

if __name__ == "__main__":
    main()