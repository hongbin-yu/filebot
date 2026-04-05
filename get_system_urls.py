#!/usr/bin/env python3
"""
获取两个系统的URL信息
"""

import requests
import json
import sys

def check_filebot_endpoints():
    """检查FileBot后端端点"""
    base_url = "http://localhost:8000"
    
    print("=== FileBot 系统 (新系统) ===")
    print(f"基础URL: {base_url}")
    
    endpoints = [
        "/",
        "/api/health",
        "/api/docs",
        "/api/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/apps",
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            print(f"✅ {endpoint:30} -> {response.status_code} ({len(response.text)} bytes)")
            if endpoint == "/api/docs":
                print(f"   文档界面: {url} (可在浏览器中打开)")
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint:30} -> 连接失败 (服务可能未运行)")
        except Exception as e:
            print(f"⚠️  {endpoint:30} -> 错误: {e}")
    
    return base_url

def test_filebot_login():
    """测试FileBot登录"""
    print("\n=== FileBot 登录测试 ===")
    url = "http://localhost:8000/api/v1/auth/login"
    
    # 新重置的密码
    data = {
        "username": "admin",
        "password": "FileBot2026!"
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 登录成功!")
            print(f"   访问令牌: {result.get('access_token', '')[:30]}...")
            print(f"   令牌类型: {result.get('token_type', '')}")
            print(f"   登录URL: {url}")
            print(f"   用户名: {data['username']}")
            print(f"   密码: {data['password']}")
            return result.get("access_token")
        else:
            print(f"❌ 登录失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登录错误: {e}")
        return None

def check_hsqldb_status():
    """检查HSQLDB状态"""
    print("\n=== Smart iAdmin HSQLDB 系统 (旧系统) ===")
    
    # 检查端口
    import subprocess
    try:
        result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True, timeout=5)
        if ":9001" in result.stdout:
            print("✅ HSQLDB服务器正在运行 (端口 9001)")
            print(f"   数据库URL: jdbc:hsqldb:hsql://localhost:9001/smarti")
            print(f"   用户名: fmdba")
            print(f"   密码: password")
        else:
            print("❌ HSQLDB服务器未运行 (端口 9001)")
            print("   说明: Smart iAdmin是Java桌面应用，主要通过数据库访问")
            print("   数据库文件: /mnt/c/workspace/demo/smarti.script")
            print("   数据已提取到: /home/hongb/.openclaw/workspace/hsqldb_export_with_headers/")
    except Exception as e:
        print(f"⚠️  检查HSQLDB状态错误: {e}")

def get_app_info(token):
    """获取应用信息"""
    if not token:
        return
    
    print("\n=== FileBot 应用信息 ===")
    url = "http://localhost:8000/api/v1/apps"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            apps = response.json()
            print(f"✅ 找到 {len(apps)} 个应用:")
            for app in apps:
                print(f"   - {app.get('name', '未命名')} (ID: {app.get('id', '未找到')})")
                if app.get('settings'):
                    print(f"     设置: {json.dumps(app.get('settings'), indent=6)}")
        else:
            print(f"❌ 获取应用失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 错误: {e}")

def main():
    """主函数"""
    print("获取两个系统URL信息...\n")
    
    # 检查FileBot端点
    filebot_url = check_filebot_endpoints()
    
    # 测试登录
    token = test_filebot_login()
    
    # 获取应用信息
    if token:
        get_app_info(token)
    
    # 检查HSQLDB状态
    check_hsqldb_status()
    
    print("\n=== 总结 ===")
    print(f"1. FileBot (新系统): {filebot_url}")
    print(f"   - API文档: {filebot_url}/api/docs")
    print(f"   - 登录端点: {filebot_url}/api/v1/auth/login")
    print(f"   - 用户名: admin")
    print(f"   - 密码: FileBot2026! (已重置)")
    
    print(f"\n2. Smart iAdmin (旧系统):")
    print(f"   - 类型: Java桌面应用 + HSQLDB数据库")
    print(f"   - 数据库文件: /mnt/c/workspace/demo/smarti.script")
    print(f"   - 用户名: fmdba")
    print(f"   - 密码: password")
    print(f"   - 数据已提取到CSV，无需直接访问数据库")

if __name__ == "__main__":
    main()