#!/usr/bin/env python3
"""
修复UUID格式问题
"""

import sqlite3
import uuid
import sys

def fix_database():
    """修复数据库中的UUID格式"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    
    print(f"打开数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查当前应用数据
        print("\n1. 检查当前应用数据:")
        cursor.execute("SELECT id, name FROM apps;")
        apps = cursor.fetchall()
        
        for app in apps:
            app_id, app_name = app
            print(f"  应用: {app_name}")
            print(f"    ID (原始): {app_id}")
            print(f"    ID 长度: {len(app_id)}")
            
            # 尝试转换为标准UUID格式
            try:
                # 如果是32字符无连字符
                if len(app_id) == 32 and '-' not in app_id:
                    standard_uuid = f"{app_id[:8]}-{app_id[8:12]}-{app_id[12:16]}-{app_id[16:20]}-{app_id[20:]}"
                    print(f"    标准UUID格式: {standard_uuid}")
                    
                    # 验证格式
                    uuid_obj = uuid.UUID(standard_uuid)
                    print(f"    UUID验证成功: {uuid_obj}")
                    
                    # 更新到标准格式
                    cursor.execute("UPDATE apps SET id = ? WHERE id = ?", 
                                 (standard_uuid, app_id))
                    print(f"    ✅ 已更新为标准UUID格式")
                else:
                    print(f"    当前格式: {'带连字符' if '-' in app_id else '未知格式'}")
                    
            except ValueError as e:
                print(f"    ❌ UUID转换错误: {e}")
        
        # 2. 检查用户表
        print("\n2. 检查用户表:")
        cursor.execute("SELECT id, username FROM users;")
        users = cursor.fetchall()
        
        for user in users:
            user_id, username = user
            print(f"  用户: {username}")
            print(f"    ID (原始): {user_id}")
            print(f"    ID 长度: {len(user_id)}")
            
            # 尝试转换为标准UUID格式
            try:
                if len(user_id) == 32 and '-' not in user_id:
                    standard_uuid = f"{user_id[:8]}-{user_id[8:12]}-{user_id[12:16]}-{user_id[16:20]}-{user_id[20:]}"
                    print(f"    标准UUID格式: {standard_uuid}")
                    
                    # 验证格式
                    uuid_obj = uuid.UUID(standard_uuid)
                    print(f"    UUID验证成功: {uuid_obj}")
                    
                    # 更新到标准格式
                    cursor.execute("UPDATE users SET id = ? WHERE id = ?", 
                                 (standard_uuid, user_id))
                    print(f"    ✅ 已更新为标准UUID格式")
            except ValueError as e:
                print(f"    ❌ UUID转换错误: {e}")
        
        # 3. 检查外键约束
        print("\n3. 检查外键关系:")
        
        # 检查apps表中的owner_id
        cursor.execute("SELECT owner_id FROM apps LIMIT 1;")
        owner_id = cursor.fetchone()
        if owner_id:
            owner_id = owner_id[0]
            print(f"  apps.owner_id: {owner_id}")
            if len(owner_id) == 32 and '-' not in owner_id:
                standard_uuid = f"{owner_id[:8]}-{owner_id[8:12]}-{owner_id[12:16]}-{owner_id[16:20]}-{owner_id[20:]}"
                print(f"  更新owner_id为标准格式: {standard_uuid}")
                cursor.execute("UPDATE apps SET owner_id = ? WHERE owner_id = ?", 
                             (standard_uuid, owner_id))
        
        conn.commit()
        print(f"\n✅ 数据库更新完成")
        
        # 显示更新后的数据
        print("\n4. 更新后的应用数据:")
        cursor.execute("SELECT id, name FROM apps;")
        updated_apps = cursor.fetchall()
        for app in updated_apps:
            app_id, app_name = app
            print(f"  - {app_name}: {app_id}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库操作错误: {e}")
        import traceback
        traceback.print_exc()

def test_api_after_fix():
    """修复后测试API"""
    print("\n" + "="*60)
    print("测试API修复后效果")
    print("="*60)
    
    import requests
    import json
    
    base_url = "http://localhost:8000"
    
    # 登录
    login_url = f"{base_url}/api/v1/auth/login"
    login_data = {"username": "admin", "password": "FileBot2026!"}
    
    try:
        response = requests.post(login_url, data=login_data, timeout=10)
        if response.status_code != 200:
            print(f"❌ 登录失败: {response.status_code}")
            return
        
        token = response.json().get("access_token")
        print(f"✅ 登录成功")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 获取应用列表
        apps_url = f"{base_url}/api/v1/apps/"
        apps_response = requests.get(apps_url, headers=headers, timeout=10)
        
        if apps_response.status_code == 200:
            apps = apps_response.json()
            print(f"✅ 获取到 {len(apps)} 个应用")
            
            if apps:
                app_id = apps[0].get("id")
                print(f"测试应用ID: {app_id}")
                
                # 测试获取应用详情
                app_url = f"{base_url}/api/v1/apps/{app_id}"
                app_response = requests.get(app_url, headers=headers, timeout=10)
                
                if app_response.status_code == 200:
                    app_data = app_response.json()
                    print(f"✅ 获取应用详情成功: {app_data.get('name')}")
                    
                    # 测试更新设置
                    update_data = {
                        "name": app_data.get("name"),
                        "description": app_data.get("description", ""),
                        "settings": {"test": True, "message": "测试配置"}
                    }
                    
                    update_response = requests.put(app_url, headers=headers, 
                                                  json=update_data, timeout=10)
                    
                    if update_response.status_code == 200:
                        print(f"✅ 更新应用设置成功")
                        updated_app = update_response.json()
                        print(f"新设置: {json.dumps(updated_app.get('settings', {}), indent=2)}")
                    else:
                        print(f"❌ 更新失败: {update_response.status_code}")
                        print(f"响应: {update_response.text}")
                        
                else:
                    print(f"❌ 获取应用详情失败: {app_response.status_code}")
                    print(f"响应: {app_response.text}")
                    
    except Exception as e:
        print(f"❌ API测试错误: {e}")

def main():
    """主函数"""
    print("=== 修复FileBot数据库UUID格式问题 ===\n")
    
    # 备份原始数据库
    import shutil
    import os
    
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    backup_path = f"{db_path}.backup.{int(__import__('time').time())}"
    
    if os.path.exists(db_path):
        print(f"备份数据库: {db_path} -> {backup_path}")
        shutil.copy2(db_path, backup_path)
        print(f"✅ 备份完成")
    else:
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    print()
    
    # 修复数据库
    fix_database()
    
    print()
    
    # 重启FileBot后端
    print("重启FileBot后端...")
    import subprocess
    import time
    
    # 查找并杀死现有进程
    try:
        subprocess.run(["pkill", "-f", "uvicorn"], timeout=5)
        time.sleep(2)
    except:
        pass
    
    # 启动新进程
    try:
        backend_dir = "/home/hongb/.openclaw/workspace/filebot/backend"
        log_file = f"{backend_dir}/restart_after_fix.log"
        cmd = f"cd {backend_dir} && nohup ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload > {log_file} 2>&1 &"
        subprocess.run(cmd, shell=True, timeout=5)
        print(f"✅ 后端重启命令已发送")
        print(f"日志文件: {log_file}")
        
        # 等待后端启动
        print("等待后端启动...")
        time.sleep(5)
        
    except Exception as e:
        print(f"❌ 重启错误: {e}")
    
    print()
    
    # 测试API
    test_api_after_fix()

if __name__ == "__main__":
    main()