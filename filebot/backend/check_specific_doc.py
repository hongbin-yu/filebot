#!/usr/bin/env python3
import sqlite3
import json
import re

def check_specific_document():
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 查找特定文档
    cursor.execute("""
        SELECT id, original_filename, file_type, document_metadata 
        FROM documents 
        WHERE original_filename = 'cvtp_bnnr_360x203.jpg'
        OR original_filename LIKE '%cvtp_bnnr%'
    """)
    
    rows = cursor.fetchall()
    
    print("特定文档检查 (cvtp_bnnr_360x203.jpg):")
    print("=" * 80)
    
    if not rows:
        print("未找到文档，尝试搜索所有JPG文件...")
        cursor.execute("""
            SELECT id, original_filename, file_type, document_metadata 
            FROM documents 
            WHERE file_type = 'JPG' 
            LIMIT 10
        """)
        rows = cursor.fetchall()
    
    for row in rows:
        doc_id, filename, file_type, metadata_json = row
        print(f"文档ID: {doc_id}")
        print(f"文件名: {filename}")
        print(f"文件类型: {file_type}")
        
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
                
                # 检查是否有URL字段
                url = metadata.get('url') or metadata.get('original_url')
                if url:
                    print(f"原始URL: {url}")
                    
                    # 提取路径
                    if url.startswith('http'):
                        import urllib.parse
                        parsed = urllib.parse.urlparse(url)
                        path = parsed.path
                        print(f"URL路径: {path}")
                        
                        # 构建前端URL
                        frontend_url = f"/content{path}"
                        print(f"前端预览URL: {frontend_url}")
                        
                        # 测试URL可访问性
                        import requests
                        test_url = f"http://localhost:5174{frontend_url}"
                        print(f"测试URL: {test_url}")
                else:
                    print("无URL字段")
                    
            except Exception as e:
                print(f"处理元数据时出错: {e}")
        else:
            print("无元数据")
        
        print("-" * 80)
    
    conn.close()

if __name__ == "__main__":
    check_specific_document()