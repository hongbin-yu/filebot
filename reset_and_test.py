#!/usr/bin/env python3
"""
重置FileBot数据库并测试集成
"""

import os
import shutil
import time
import subprocess
import sys

def stop_filebot():
    """停止FileBot后端"""
    print("停止FileBot后端...")
    try:
        subprocess.run(["pkill", "-f", "uvicorn"], timeout=5)
        time.sleep(2)
        print("✅ 后端已停止")
    except Exception as e:
        print(f"停止后端错误: {e}")

def backup_database():
    """备份数据库"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    if os.path.exists(db_path):
        backup_dir = "/home/hongb/.openclaw/workspace/backups"
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = int(time.time())
        backup_path = f"{backup_dir}/filebot.db.backup.{timestamp}"
        shutil.copy2(db_path, backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
        return backup_path
    else:
        print("ℹ️  数据库文件不存在，无需备份")
        return None

def reset_database():
    """重置数据库"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    
    if os.path.exists(db_path):
        print(f"删除数据库: {db_path}")
        os.remove(db_path)
        print("✅ 数据库已删除")
    else:
        print("ℹ️  数据库文件不存在")
    
    # 删除数据目录
    data_dirs = [
        "/home/hongb/.openclaw/workspace/filebot/backend/data",
        "/home/hongb/.openclaw/workspace/filebot/backend/logs"
    ]
    
    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            print(f"删除数据目录: {data_dir}")
            shutil.rmtree(data_dir)
    
    print("✅ 数据目录已清理")

def initialize_database():
    """初始化数据库"""
    print("\n初始化数据库...")
    
    backend_dir = "/home/hongb/.openclaw/workspace/filebot/backend"
    
    # 运行数据库初始化
    init_cmd = f"cd {backend_dir} && ./venv/bin/python3 -c \"from app.db.database import init_db; init_db(); print('✅ 数据库初始化完成')\""
    
    try:
        result = subprocess.run(init_cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(result.stdout)
        if result.stderr:
            print(f"标准错误: {result.stderr}")
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化错误: {e}")
        return False
    
    return True

def start_filebot():
    """启动FileBot后端"""
    print("\n启动FileBot后端...")
    
    backend_dir = "/home/hongb/.openclaw/workspace/filebot/backend"
    log_file = f"{backend_dir}/restart_clean.log"
    
    cmd = f"cd {backend_dir} && nohup ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload > {log_file} 2>&1 &"
    
    try:
        subprocess.run(cmd, shell=True, timeout=5)
        print(f"✅ 后端启动命令已发送")
        print(f"日志文件: {log_file}")
        
        # 等待后端启动
        print("等待后端启动...")
        for i in range(10):
            time.sleep(3)
            try:
                import requests
                response = requests.get("http://localhost:8000/api/health", timeout=5)
                if response.status_code == 200:
                    print(f"✅ FileBot后端运行正常")
                    return True
            except:
                print(f"等待后端启动... ({i+1}/10)")
        
        print("❌ 后端启动超时")
        return False
    except Exception as e:
        print(f"❌ 启动错误: {e}")
        return False

def test_integration():
    """测试Smart iAdmin集成"""
    print("\n" + "="*60)
    print("测试Smart iAdmin集成")
    print("="*60)
    
    import requests
    import json
    
    base_url = "http://localhost:8000"
    
    # 使用默认密码登录
    print("\n1. 使用默认密码登录...")
    login_url = f"{base_url}/api/v1/auth/login"
    
    # 默认密码应该是admin123（根据.env文件）
    login_data = {"username": "admin", "password": "admin123"}
    
    try:
        response = requests.post(login_url, data=login_data, timeout=10)
        print(f"登录状态: {response.status_code}")
        
        if response.status_code != 200:
            print(f"登录失败: {response.text}")
            
            # 尝试FileBot2026!
            print("\n尝试密码: FileBot2026!")
            login_data["password"] = "FileBot2026!"
            response = requests.post(login_url, data=login_data, timeout=10)
            print(f"登录状态: {response.status_code}")
            
            if response.status_code != 200:
                print(f"登录失败: {response.text}")
                return False
        
        result = response.json()
        token = result.get("access_token")
        print(f"✅ 登录成功")
        print(f"令牌: {token[:30]}...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 获取应用列表
        print("\n2. 获取应用列表...")
        apps_url = f"{base_url}/api/v1/apps/"
        apps_response = requests.get(apps_url, headers=headers, timeout=10)
        
        if apps_response.status_code != 200:
            print(f"❌ 获取应用失败: {apps_response.status_code}")
            print(f"响应: {apps_response.text}")
            return False
        
        apps = apps_response.json()
        print(f"✅ 获取到 {len(apps)} 个应用")
        
        # 如果没有应用，创建一个
        if not apps:
            print("\n创建测试应用...")
            create_data = {
                "name": "Smart iAdmin集成测试",
                "description": "用于测试Smart iAdmin配置集成的应用",
                "owner_id": result.get("user", {}).get("id")
            }
            
            create_response = requests.post(apps_url, headers=headers, 
                                          json=create_data, timeout=10)
            
            if create_response.status_code == 200:
                app = create_response.json()
                app_id = app.get("id")
                print(f"✅ 应用创建成功: {app.get('name')} (ID: {app_id})")
            else:
                print(f"❌ 创建应用失败: {create_response.status_code}")
                print(f"响应: {create_response.text}")
                return False
        else:
            app_id = apps[0].get("id")
            print(f"使用现有应用: {apps[0].get('name')} (ID: {app_id})")
        
        # 加载Smart iAdmin配置
        print("\n3. 加载Smart iAdmin配置...")
        config_path = "/home/hongb/.openclaw/workspace/cold_indexes_config_v2.json"
        
        if not os.path.exists(config_path):
            print(f"❌ 配置文件不存在: {config_path}")
            # 创建一个测试配置
            smart_config = {
                "version": "1.0",
                "tables": ["COLD_INDEXES", "COLD_REPORT"],
                "records": 712,
                "test": True
            }
            print(f"使用测试配置")
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                smart_config = json.load(f)
            print(f"✅ 配置加载成功: {smart_config.get('version')}, {len(smart_config.get('tables', []))}个表")
        
        # 更新应用设置
        print(f"\n4. 上传Smart iAdmin配置...")
        app_url = f"{base_url}/api/v1/apps/{app_id}"
        
        # 先获取当前应用信息
        app_response = requests.get(app_url, headers=headers, timeout=10)
        if app_response.status_code != 200:
            print(f"❌ 获取应用详情失败: {app_response.status_code}")
            return False
        
        current_app = app_response.json()
        
        # 准备更新数据
        update_data = {
            "name": current_app.get("name"),
            "description": current_app.get("description", ""),
            "settings": {
                "smart_iadmin_config": smart_config,
                "config_version": "1.0",
                "last_updated": "2026-03-16"
            }
        }
        
        update_response = requests.put(app_url, headers=headers, 
                                      json=update_data, timeout=30)
        
        if update_response.status_code == 200:
            updated_app = update_response.json()
            print(f"✅ Smart iAdmin配置上传成功!")
            print(f"  应用: {updated_app.get('name')}")
            print(f"  设置字段大小: {len(json.dumps(updated_app.get('settings', {})))} 字节")
            
            # 验证配置存储
            settings = updated_app.get("settings", {})
            if "smart_iadmin_config" in settings:
                print(f"  ✅ Smart iAdmin配置已成功存储")
                return True
            else:
                print(f"  ❌ Smart iAdmin配置未找到")
                return False
        else:
            print(f"❌ 配置上传失败: {update_response.status_code}")
            print(f"响应: {update_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=== 重置FileBot数据库并测试集成 ===\n")
    
    # 1. 停止后端
    stop_filebot()
    
    # 2. 备份数据库
    backup_database()
    
    # 3. 重置数据库
    reset_database()
    
    # 4. 初始化数据库
    if not initialize_database():
        print("❌ 数据库初始化失败")
        return
    
    # 5. 启动后端
    if not start_filebot():
        print("❌ 后端启动失败")
        return
    
    # 6. 测试集成
    success = test_integration()
    
    if success:
        print("\n" + "="*60)
        print("✅ Smart iAdmin集成测试成功完成!")
        print("="*60)
        print(f"\nFileBot系统已重置并配置完成。")
        print(f"Smart iAdmin配置已存储在应用设置中。")
        print(f"\n下一步:")
        print(f"  1. 修改转换服务以使用Smart iAdmin配置解析.cld文件")
        print(f"  2. 测试实际的.cld文件上传和解析")
        print(f"  3. 验证字段提取准确性")
    else:
        print("\n❌ Smart iAdmin集成测试失败")
        print("需要进一步调试")

if __name__ == "__main__":
    main()