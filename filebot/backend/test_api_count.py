#!/usr/bin/env python3
import requests
import json
import sys

# 测试API端点 - 模拟前端请求
base_url = "http://localhost:8001/api/v1"

# 测试数据：使用public用户（用于Client门户的特殊处理）
# 在folders.py中，public用户可以访问所有文件夹
headers = {}

def test_folders_api():
    print("测试文件夹API文档计数功能...")
    
    # 从数据库获取测试数据
    import sqlite3
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 获取canada-site应用的ID
    cursor.execute("SELECT id, slug FROM apps WHERE slug = 'canada-site' OR name LIKE '%canada%' LIMIT 1")
    app = cursor.fetchone()
    if not app:
        print("未找到测试应用")
        return
    
    app_id, app_slug = app
    print(f"测试应用: {app_slug} (ID: {app_id})")
    
    # 获取该应用的en文件夹
    cursor.execute("""
        SELECT id, name, path 
        FROM folders 
        WHERE app_id = ? AND name = 'en' 
        LIMIT 1
    """, (app_id,))
    
    en_folder = cursor.fetchone()
    if not en_folder:
        print("未找到en文件夹")
        return
    
    folder_id, folder_name, folder_path = en_folder
    print(f"测试文件夹: {folder_name} (ID: {folder_id[:8]}..., 路径: {folder_path})")
    
    # 查询数据库中的实际文档数量
    cursor.execute("SELECT COUNT(*) FROM documents WHERE folder_id = ?", (folder_id,))
    db_count = cursor.fetchone()[0]
    print(f"数据库中的实际文档数量: {db_count}")
    
    conn.close()
    
    # 测试1: 获取文件夹列表（应该包含document_count）
    print(f"\n测试1: 获取文件夹列表 (app_id={app_slug})")
    try:
        response = requests.get(f"{base_url}/folders/?app_id={app_slug}", headers=headers)
        if response.status_code == 200:
            folders = response.json()
            print(f"返回 {len(folders)} 个文件夹")
            
            # 查找en文件夹
            for folder in folders:
                if folder.get('id') == folder_id:
                    api_count = folder.get('document_count', 'N/A')
                    print(f"  找到en文件夹: {folder.get('name')}")
                    print(f"  API返回的文档数量: {api_count}")
                    print(f"  与数据库对比: {'✓ 匹配' if api_count == db_count else '✗ 不匹配'}")
                    break
            else:
                print("  ✗ 未在API响应中找到en文件夹")
        else:
            print(f"  ✗ 错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
    
    # 测试2: 获取单个文件夹详情
    print(f"\n测试2: 获取单个文件夹详情 (folder_id={folder_id[:8]}...)")
    try:
        response = requests.get(f"{base_url}/folders/{folder_id}", headers=headers)
        if response.status_code == 200:
            folder_data = response.json()
            api_count = folder_data.get('document_count', 'N/A')
            print(f"  文件夹名称: {folder_data.get('name')}")
            print(f"  文件夹路径: {folder_data.get('path')}")
            print(f"  API返回的文档数量: {api_count}")
            print(f"  与数据库对比: {'✓ 匹配' if api_count == db_count else '✗ 不匹配'}")
            
            # 检查是否包含document_count字段
            if 'document_count' in folder_data:
                print(f"  ✓ 包含document_count字段")
            else:
                print(f"  ✗ 不包含document_count字段")
        else:
            print(f"  ✗ 错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
    
    # 测试3: 检查几个文档数量较多的文件夹
    print(f"\n测试3: 检查文档数量较多的文件夹")
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT f.id, f.name, COUNT(d.id) as doc_count
        FROM folders f
        LEFT JOIN documents d ON f.id = d.folder_id
        WHERE f.app_id = ?
        GROUP BY f.id
        HAVING doc_count > 0
        ORDER BY doc_count DESC
        LIMIT 5
    """, (app_id,))
    
    top_folders = cursor.fetchall()
    conn.close()
    
    for folder_id, folder_name, db_count in top_folders:
        print(f"\n  检查文件夹: {folder_name} (数据库: {db_count} 文档)")
        try:
            response = requests.get(f"{base_url}/folders/{folder_id}", headers=headers, timeout=5)
            if response.status_code == 200:
                folder_data = response.json()
                api_count = folder_data.get('document_count', 0)
                status = "✓" if api_count == db_count else "✗"
                print(f"    API返回: {api_count} 文档 {status}")
            else:
                print(f"    ✗ 错误: {response.status_code}")
        except Exception as e:
            print(f"    ✗ 请求失败: {e}")

if __name__ == "__main__":
    test_folders_api()