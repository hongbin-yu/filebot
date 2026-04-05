#!/usr/bin/env python3
"""
测试FileBot API登录
"""

import requests
import json
import sys

def test_login(username, password):
    """测试API登录"""
    url = "http://localhost:8000/api/v1/auth/login"
    
    # 使用表单数据格式
    data = {
        "username": username,
        "password": password
    }
    
    print(f"测试登录: {username}/{password}")
    
    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 登录成功!")
            print(f"访问令牌: {result.get('access_token', '未找到')[:30]}...")
            print(f"令牌类型: {result.get('token_type', '未找到')}")
            return result.get("access_token")
        else:
            print(f"❌ 登录失败")
            print(f"响应: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败 - FileBot后端可能未运行")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

def test_update_app_config(token, app_id):
    """测试更新App配置"""
    url = f"http://localhost:8000/api/v1/apps/{app_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试配置
    config = {
        "settings": {
            "smart_iadmin_config": {
                "test": True,
                "message": "Smart iAdmin配置集成测试"
            }
        }
    }
    
    print(f"\n测试更新App配置 (App ID: {app_id})")
    
    try:
        response = requests.put(url, headers=headers, json=config, timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 配置更新成功!")
            print(f"App名称: {result.get('name', '未找到')}")
            print(f"设置字段: {json.dumps(result.get('settings', {}), indent=2)}")
            return True
        else:
            print(f"❌ 配置更新失败")
            print(f"响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    """主函数"""
    print("=== FileBot API登录测试 ===\n")
    
    # 测试各种用户名密码组合
    test_combinations = [
        ("admin", "fmdba"),
        ("admin", "password"),
        ("fmdba", "password"),
        ("admin", "admin"),
        ("admin", "Admin123!"),
        ("admin", "filebot"),
    ]
    
    token = None
    
    for username, password in test_combinations:
        token = test_login(username, password)
        if token:
            break
        print()
    
    if token:
        # 测试配置更新
        app_id = "28516d7d-e499-4be4-b150-7d69ab742055"  # TestApp ID
        test_update_app_config(token, app_id)
    else:
        print("\n❌ 所有登录尝试失败")
        print("建议重置admin用户密码")

if __name__ == "__main__":
    main()