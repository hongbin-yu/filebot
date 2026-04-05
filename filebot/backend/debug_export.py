#!/usr/bin/env python3
"""
调试导出API 500错误
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8001"
API_PREFIX = "/api/v1"

def login():
    """登录获取token"""
    url = f"{BASE_URL}{API_PREFIX}/auth/login"
    data = {
        "username": "admin",
        "password": "admin123"
    }
    print(f"🔐 登录: {url}")
    response = requests.post(url, data=data)
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"  ✅ Token: {token[:20]}...")
        return token
    else:
        print(f"  ❌ 登录失败: {response.status_code}")
        print(f"     响应: {response.text}")
        return None

def test_export_full(token):
    """测试完整导出端点"""
    url = f"{BASE_URL}{API_PREFIX}/export/full"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print(f"\n🔍 测试完整导出: {url}")
    response = requests.get(url, headers=headers)
    print(f"  状态码: {response.status_code}")
    print(f"  响应头: {dict(response.headers)}")
    
    # 尝试解析JSON错误信息
    try:
        error_data = response.json()
        print(f"  响应JSON: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
    except:
        print(f"  响应文本: {response.text[:500]}")
    
    return response.status_code

def test_export_app(token, app_id):
    """测试应用导出端点"""
    url = f"{BASE_URL}{API_PREFIX}/export/app/{app_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print(f"\n📱 测试应用导出: {url}")
    response = requests.get(url, headers=headers)
    print(f"  状态码: {response.status_code}")
    
    try:
        error_data = response.json()
        print(f"  响应JSON: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
    except:
        print(f"  响应文本: {response.text[:500]}")
    
    return response.status_code

def test_export_folder(token, folder_id):
    """测试文件夹导出端点"""
    url = f"{BASE_URL}{API_PREFIX}/export/folder/{folder_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print(f"\n📁 测试文件夹导出: {url}")
    response = requests.get(url, headers=headers)
    print(f"  状态码: {response.status_code}")
    
    try:
        error_data = response.json()
        print(f"  响应JSON: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
    except:
        print(f"  响应文本: {response.text[:500]}")
    
    return response.status_code

def main():
    print("==========================================")
    print("调试导出API 500错误")
    print("==========================================")
    
    # 登录
    token = login()
    if not token:
        sys.exit(1)
    
    # 获取一个应用ID用于测试
    print(f"\n📱 获取应用列表...")
    url = f"{BASE_URL}{API_PREFIX}/apps"
    headers = {"Authorization": f"Bearer {token}"}
    apps_response = requests.get(url, headers=headers)
    
    app_id = None
    if apps_response.status_code == 200:
        apps = apps_response.json()
        if apps and len(apps) > 0:
            app_id = apps[0].get("id")
            print(f"  使用应用: {apps[0].get('name')} (ID: {app_id})")
    
    # 获取一个文件夹ID用于测试
    folder_id = None
    if app_id:
        print(f"\n📁 获取文件夹列表...")
        url = f"{BASE_URL}{API_PREFIX}/folders/?app_id={app_id}"
        folders_response = requests.get(url, headers=headers)
        if folders_response.status_code == 200:
            folders = folders_response.json()
            if folders and len(folders) > 0:
                folder_id = folders[0].get("id")
                print(f"  使用文件夹: {folders[0].get('name')} (ID: {folder_id})")
    
    # 测试各个端点
    print(f"\n🚀 开始测试...")
    
    # 1. 完整导出
    test_export_full(token)
    
    # 2. 应用导出
    if app_id:
        test_export_app(token, app_id)
    
    # 3. 文件夹导出
    if folder_id:
        test_export_folder(token, folder_id)
    
    print(f"\n✅ 调试完成")

if __name__ == "__main__":
    main()