#!/usr/bin/env python3
"""
简单测试认证流程
"""

import requests
import json
import sys

def test_auth_flow():
    """测试认证流程"""
    base_url = "http://localhost:8000"
    
    print("=== 简单认证测试 ===\n")
    
    # 1. 登录
    print("1. 登录...")
    login_url = f"{base_url}/api/v1/auth/login"
    login_data = {"username": "admin", "password": "FileBot2026!"}
    
    try:
        # 使用data参数而不是json参数（因为是表单数据）
        response = requests.post(login_url, data=login_data, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应体: {response.text[:200]}")
        
        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            print(f"\n✅ 登录成功")
            print(f"令牌前30字符: {token[:30]}...")
            
            # 2. 测试令牌 - 方法1：只带Authorization头
            print("\n2. 测试获取应用列表（方法1）...")
            headers1 = {"Authorization": f"Bearer {token}"}
            apps_url = f"{base_url}/api/v1/apps/"
            
            response1 = requests.get(apps_url, headers=headers1, timeout=10)
            print(f"状态码: {response1.status_code}")
            print(f"响应: {response1.text[:200]}")
            
            # 3. 测试令牌 - 方法2：带Authorization和Content-Type头
            print("\n3. 测试获取应用列表（方法2）...")
            headers2 = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            response2 = requests.get(apps_url, headers=headers2, timeout=10)
            print(f"状态码: {response2.status_code}")
            print(f"响应: {response2.text[:200]}")
            
            # 4. 测试获取当前用户信息
            print("\n4. 测试获取当前用户信息...")
            me_url = f"{base_url}/api/v1/auth/me"
            response3 = requests.get(me_url, headers=headers1, timeout=10)
            print(f"状态码: {response3.status_code}")
            print(f"响应: {response3.text[:200]}")
            
            # 5. 检查令牌内容（解码）
            print("\n5. 分析令牌...")
            import jwt
            try:
                # 尝试解码令牌（不带验证，只看内容）
                decoded = jwt.decode(token, options={"verify_signature": False})
                print(f"令牌载荷: {json.dumps(decoded, indent=2)}")
                
                # 检查sub字段（用户ID）
                user_id = decoded.get("sub")
                print(f"用户ID (sub): {user_id}")
                
                # 检查数据库中的用户ID
                import sqlite3
                db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id, username FROM users;")
                users = cursor.fetchall()
                conn.close()
                
                print(f"数据库中的用户:")
                for uid, username in users:
                    print(f"  - {username}: {uid}")
                    if uid == user_id:
                        print(f"    ✅ 匹配令牌中的sub字段")
                    else:
                        print(f"    ❌ 不匹配令牌中的sub字段")
                        
            except Exception as e:
                print(f"令牌解码错误: {e}")
                
        else:
            print(f"❌ 登录失败")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

def check_jwt_secret():
    """检查JWT密钥配置"""
    print("\n=== 检查JWT配置 ===")
    
    # 检查环境变量
    import os
    from dotenv import load_dotenv
    
    env_path = "/home/hongb/.openclaw/workspace/filebot/backend/.env"
    if os.path.exists(env_path):
        load_dotenv(env_path)
        secret_key = os.getenv("SECRET_KEY")
        print(f"环境变量SECRET_KEY: {secret_key}")
    else:
        print(f"未找到.env文件: {env_path}")
    
    # 检查配置类
    import sys
    sys.path.insert(0, '/home/hongb/.openclaw/workspace/filebot/backend')
    try:
        from app.core.config import settings
        print(f"配置类SECRET_KEY: {settings.SECRET_KEY}")
        print(f"配置类ALGORITHM: {settings.ALGORITHM}")
        print(f"配置类ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
    except Exception as e:
        print(f"导入配置错误: {e}")

def main():
    """主函数"""
    test_auth_flow()
    check_jwt_secret()

if __name__ == "__main__":
    main()