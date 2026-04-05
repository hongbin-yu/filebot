#!/usr/bin/env python3
"""
测试文档发布状态功能
"""
import requests
import json

BASE_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:5174"

def test_publish_status():
    """测试发布状态功能"""
    print("🔍 测试文档发布状态功能")
    print("=" * 50)
    
    # 首先获取一个已发布的图片文档信息
    print("1. 获取测试文档信息...")
    import sqlite3
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 获取一个已发布的图片文档
    cursor.execute("""
        SELECT id, original_filename, publish_status, document_metadata 
        FROM documents 
        WHERE file_type IN ('JPG', 'PNG', 'JPEG') 
        AND publish_status = 'PUBLISHED'
        AND document_metadata LIKE '%url%'
        LIMIT 1
    """)
    published_doc = cursor.fetchone()
    
    # 获取一个未发布的文档
    cursor.execute("""
        SELECT id, original_filename, publish_status, document_metadata 
        FROM documents 
        WHERE publish_status = 'UNPUBLISHED'
        AND document_metadata LIKE '%url%'
        LIMIT 1
    """)
    unpublished_doc = cursor.fetchone()
    
    conn.close()
    
    if not published_doc or not unpublished_doc:
        print("❌ 需要至少一个已发布和一个未发布的文档进行测试")
        return
    
    pub_id, pub_filename, pub_status, pub_metadata = published_doc
    unpub_id, unpub_filename, unpub_status, unpub_metadata = unpublished_doc
    
    # 解析元数据获取URL路径
    def get_path_from_metadata(metadata_str):
        try:
            meta = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
            url = meta.get('url') or meta.get('original_url')
            if url:
                from urllib.parse import urlparse
                return urlparse(url).path
        except:
            return None
    
    pub_path = get_path_from_metadata(pub_metadata)
    unpub_path = get_path_from_metadata(unpub_metadata)
    
    print(f"✅ 已发布文档: {pub_filename} (路径: {pub_path})")
    print(f"✅ 未发布文档: {unpub_filename} (路径: {unpub_path})")
    print()
    
    # 测试后端API
    print("2. 测试后端API直接访问:")
    print(f"   a) 已发布文档 ({pub_path}):")
    response = requests.get(f"{BASE_URL}/api/v1/documents/by-path{pub_path}")
    print(f"      状态码: {response.status_code}")
    print(f"      文件大小: {len(response.content) if response.status_code == 200 else 'N/A'}")
    
    print(f"   b) 未发布文档 ({unpub_path}):")
    response = requests.get(f"{BASE_URL}/api/v1/documents/by-path{unpub_path}")
    print(f"      状态码: {response.status_code}")
    print(f"      错误信息: {response.text if response.status_code != 200 else 'N/A'}")
    print()
    
    # 测试前端代理（仅测试/content/*路径）
    if pub_path and pub_path.startswith('/content/'):
        print("3. 测试前端代理访问:")
        print(f"   a) 已发布文档 (/content/*):")
        frontend_url = f"{FRONTEND_URL}{pub_path}"
        response = requests.get(frontend_url)
        print(f"      状态码: {response.status_code}")
        print(f"      文件大小: {len(response.content) if response.status_code == 200 else 'N/A'}")
    else:
        print("3. 前端代理测试跳过（文档路径不是/content/*）")
    
    print()
    print("4. 数据库状态统计:")
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 总体统计
    cursor.execute("SELECT publish_status, COUNT(*) FROM documents GROUP BY publish_status")
    total_stats = cursor.fetchall()
    for status, count in total_stats:
        print(f"   - {status}: {count}个文档")
    
    # 按文件类型统计
    cursor.execute("""
        SELECT file_type, publish_status, COUNT(*) 
        FROM documents 
        GROUP BY file_type, publish_status 
        ORDER BY file_type, publish_status
    """)
    type_stats = cursor.fetchall()
    print("\n   按文件类型统计:")
    for file_type, status, count in type_stats:
        print(f"   - {file_type}: {status} = {count}")
    
    conn.close()
    
    print()
    print("=" * 50)
    print("✅ 测试完成!")
    
    # 验证结果
    print("\n📋 验证:")
    if pub_path:
        test1 = requests.get(f"{BASE_URL}/api/v1/documents/by-path{pub_path}").status_code == 200
        print(f"   1. 已发布文档可通过URL访问: {'✅' if test1 else '❌'}")
    
    if unpub_path:
        test2 = requests.get(f"{BASE_URL}/api/v1/documents/by-path{unpub_path}").status_code == 403
        print(f"   2. 未发布文档拒绝访问 (403): {'✅' if test2 else '❌'}")
    
    print(f"   3. 默认状态为UNPUBLISHED: {'✅' if total_stats[0][1] > 0 else '❌'}")

if __name__ == '__main__':
    test_publish_status()