#!/usr/bin/env python3
import requests
import json

# 测试API端点
base_url = "http://localhost:8001/api/v1"

# 测试获取文件夹列表
# 首先需要知道app_id或slug
# 从数据库或日志中获取一个已知的app

# 从数据库获取一个app ID
import sqlite3
conn = sqlite3.connect('filebot.db')
cursor = conn.cursor()

# 获取一个应用
cursor.execute("SELECT id, slug, name FROM apps LIMIT 1")
app = cursor.fetchone()
if app:
    app_id, app_slug, app_name = app
    print(f"测试应用: {app_name} (ID: {app_id}, Slug: {app_slug})")
    
    # 测试API
    # 方法1: 使用app_id
    print(f"\n测试 /api/v1/folders/?app_id={app_id}")
    try:
        response = requests.get(f"{base_url}/folders/?app_id={app_id}")
        if response.status_code == 200:
            folders = response.json()
            print(f"返回 {len(folders)} 个文件夹")
            for i, folder in enumerate(folders[:3]):  # 显示前3个
                print(f"  文件夹 {i+1}: {folder.get('name')} - 文档数量: {folder.get('document_count', 'N/A')}")
        else:
            print(f"错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 方法2: 使用app_slug
    print(f"\n测试 /api/v1/folders/?app_id={app_slug}")
    try:
        response = requests.get(f"{base_url}/folders/?app_id={app_slug}")
        if response.status_code == 200:
            folders = response.json()
            print(f"返回 {len(folders)} 个文件夹")
            for i, folder in enumerate(folders[:3]):
                print(f"  文件夹 {i+1}: {folder.get('name')} - 文档数量: {folder.get('document_count', 'N/A')}")
        else:
            print(f"错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    # 获取一个文件夹ID进行详细测试
    cursor.execute("SELECT id, name FROM folders WHERE app_id = ? LIMIT 1", (app_id,))
    folder = cursor.fetchone()
    if folder:
        folder_id, folder_name = folder
        print(f"\n测试单个文件夹: {folder_name} (ID: {folder_id})")
        try:
            response = requests.get(f"{base_url}/folders/{folder_id}")
            if response.status_code == 200:
                folder_data = response.json()
                print(f"文件夹详情:")
                print(f"  名称: {folder_data.get('name')}")
                print(f"  路径: {folder_data.get('path')}")
                print(f"  文档数量: {folder_data.get('document_count', 'N/A')}")
            else:
                print(f"错误: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"请求失败: {e}")

conn.close()