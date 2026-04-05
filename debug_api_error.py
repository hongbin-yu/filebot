#!/usr/bin/env python3
"""
调试API错误
"""

import requests
import json
import traceback

def debug_api():
    """调试API"""
    base_url = "http://localhost:8000"
    
    # 1. 登录
    print("1. 登录测试...")
    login_url = f"{base_url}/api/v1/auth/login"
    login_data = {"username": "admin", "password": "FileBot2026!"}
    
    try:
        response = requests.post(login_url, data=login_data, timeout=10)
        print(f"登录状态: {response.status_code}")
        print(f"登录响应: {response.text[:200]}")
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"获取到令牌: {token[:30]}...")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # 2. 测试健康端点
            print("\n2. 测试健康端点...")
            health_url = f"{base_url}/api/health"
            health_response = requests.get(health_url, timeout=5)
            print(f"健康状态: {health_response.status_code}")
            print(f"健康响应: {health_response.text}")
            
            # 3. 测试获取应用列表
            print("\n3. 测试获取应用列表...")
            apps_url = f"{base_url}/api/v1/apps/"
            apps_response = requests.get(apps_url, headers=headers, timeout=10)
            print(f"应用列表状态: {apps_response.status_code}")
            print(f"应用列表响应: {apps_response.text[:500]}")
            
            if apps_response.status_code == 200:
                apps = apps_response.json()
                print(f"应用数量: {len(apps)}")
                
                if apps:
                    # 4. 测试获取第一个应用
                    app_id = apps[0].get("id")
                    print(f"\n4. 测试获取应用 {app_id}...")
                    app_url = f"{base_url}/api/v1/apps/{app_id}"
                    app_response = requests.get(app_url, headers=headers, timeout=10)
                    print(f"应用详情状态: {app_response.status_code}")
                    print(f"应用详情响应: {app_response.text[:500]}")
                    
                    # 如果有错误，显示更多信息
                    if app_response.status_code >= 400:
                        print(f"\n⚠️ 错误详情:")
                        try:
                            error_data = app_response.json()
                            print(json.dumps(error_data, indent=2))
                        except:
                            print(f"原始响应: {app_response.text}")
                    
            # 5. 测试创建一个简单的应用
            print("\n5. 测试创建简单应用...")
            create_url = f"{base_url}/api/v1/apps/"
            create_data = {
                "name": "测试应用",
                "description": "用于调试API的应用"
            }
            create_response = requests.post(create_url, headers=headers, 
                                          json=create_data, timeout=10)
            print(f"创建应用状态: {create_response.status_code}")
            print(f"创建应用响应: {create_response.text[:500]}")
            
        else:
            print("登录失败")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 服务器可能未运行")
    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()

def check_database():
    """检查数据库状态"""
    print("\n检查数据库状态...")
    
    import sqlite3
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"数据库表数量: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} 行")
            
            if table_name == "apps":
                cursor.execute(f"SELECT id, name FROM {table_name};")
                apps = cursor.fetchall()
                print(f"    应用数据: {apps}")
                
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库检查错误: {e}")

if __name__ == "__main__":
    print("=== FileBot API调试 ===\n")
    debug_api()
    check_database()