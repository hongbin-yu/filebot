#!/usr/bin/env python3
"""
测试路径映射API
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8001"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
TEST_PATH = "/content/dam/cra-arc/camp-promo/features/cvtp_bnnr_360x203.jpg"

def test_path_mapping():
    """测试路径映射API"""
    
    # 1. 登录获取token
    print("1. 登录获取token...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(LOGIN_URL, json=login_data)
        response.raise_for_status()
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"   登录成功，token: {token[:20]}...")
    except Exception as e:
        print(f"   登录失败: {e}")
        return False
    
    # 2. 测试路径映射API
    print(f"2. 测试路径映射API: {TEST_PATH}")
    path_url = f"{BASE_URL}/api/v1/documents/by-path{TEST_PATH}"
    
    try:
        # 先测试GET请求
        response = requests.get(path_url, headers=headers)
        print(f"   状态码: {response.status_code}")
        print(f"   响应头: {{")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'location']:
                print(f"     {key}: {value}")
        print(f"   }}")
        
        if response.status_code == 307:  # 临时重定向
            print(f"   重定向到: {response.headers.get('Location')}")
            return True
        elif response.status_code == 200:
            print(f"   直接返回文件，大小: {len(response.content)} 字节")
            return True
        else:
            print(f"   响应内容: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   请求失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("测试路径映射API")
    print("=" * 60)
    
    success = test_path_mapping()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试成功!")
    else:
        print("❌ 测试失败!")
    print("=" * 60)