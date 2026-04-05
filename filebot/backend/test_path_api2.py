#!/usr/bin/env python3
"""
测试路径映射API - 使用正确的表单登录
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8001"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
TEST_PATH = "/content/dam/cra-arc/camp-promo/features/cvtp_bnnr_360x203.jpg"

def test_path_mapping():
    """测试路径映射API"""
    
    # 1. 登录获取token - 使用表单数据
    print("1. 登录获取token...")
    form_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        # 使用data参数发送表单数据
        response = requests.post(LOGIN_URL, data=form_data)
        print(f"   响应状态: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        token = result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"   登录成功，token: {token[:20]}...")
    except Exception as e:
        print(f"   登录失败: {e}")
        print(f"   响应内容: {response.text if 'response' in locals() else '无响应'}")
        return False
    
    # 2. 测试路径映射API
    print(f"\n2. 测试路径映射API: {TEST_PATH}")
    path_url = f"{BASE_URL}/api/v1/documents/by-path{TEST_PATH}"
    
    try:
        # 先测试GET请求
        response = requests.get(path_url, headers=headers, allow_redirects=False)
        print(f"   状态码: {response.status_code}")
        print(f"   响应头:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'location', 'content-disposition']:
                print(f"     {key}: {value}")
        
        if response.status_code == 307:  # 临时重定向
            location = response.headers.get('Location')
            print(f"   重定向到: {location}")
            
            # 跟随重定向
            print(f"   跟随重定向...")
            redirect_response = requests.get(location, headers=headers)
            print(f"   重定向响应状态: {redirect_response.status_code}")
            print(f"   重定向响应类型: {redirect_response.headers.get('Content-Type')}")
            print(f"   重定向响应大小: {len(redirect_response.content)} 字节")
            return True
        elif response.status_code == 200:
            print(f"   直接返回文件，大小: {len(response.content)} 字节")
            print(f"   内容类型: {response.headers.get('Content-Type')}")
            return True
        else:
            print(f"   响应内容: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"   请求失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("测试路径映射API (表单登录)")
    print("=" * 60)
    
    success = test_path_mapping()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试成功!")
    else:
        print("❌ 测试失败!")
    print("=" * 60)