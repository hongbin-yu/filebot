#!/usr/bin/env python3
import sqlite3
import json
import sys

def check_document_metadata():
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 查找特定图片文档
    cursor.execute("""
        SELECT id, original_filename, file_type, document_metadata 
        FROM documents 
        WHERE original_filename LIKE '%cvtp_bnnr_360x203%' 
        OR original_filename LIKE '%jpg%'
        LIMIT 5
    """)
    
    rows = cursor.fetchall()
    
    print("文档元数据检查:")
    print("=" * 80)
    
    for row in rows:
        doc_id, filename, file_type, metadata_json = row
        print(f"文档ID: {doc_id}")
        print(f"文件名: {filename}")
        print(f"文件类型: {file_type}")
        
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
                print(f"元数据字段: {list(metadata.keys())}")
                
                # 检查是否有URL字段
                if 'url' in metadata:
                    print(f"原始URL: {metadata['url']}")
                elif 'original_url' in metadata:
                    print(f"原始URL: {metadata['original_url']}")
                else:
                    print("无URL字段")
                    
                # 打印部分元数据内容
                print(f"元数据预览: {json.dumps(metadata, indent=2)[:200]}...")
                
            except json.JSONDecodeError as e:
                print(f"元数据JSON解析错误: {e}")
                print(f"原始元数据: {metadata_json[:100]}")
        else:
            print("无元数据")
        
        print("-" * 80)
    
    conn.close()

if __name__ == "__main__":
    check_document_metadata()