#!/usr/bin/env python3
"""
Smart iAdmin集成 - 阶段1：配置上传
"""

import requests
import json
import sys
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"

def login():
    """登录获取令牌"""
    print("1. 登录获取令牌...")
    
    login_url = f"{BASE_URL}/api/v1/auth/login"
    login_data = {"username": "admin", "password": "admin123"}
    
    try:
        response = requests.post(login_url, data=login_data, timeout=10)
        if response.status_code != 200:
            print(f"❌ 登录失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
        
        result = response.json()
        token = result.get("access_token")
        print(f"✅ 登录成功")
        print(f"   令牌: {token[:30]}...")
        
        # 解码令牌查看用户信息
        import jwt
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("sub")
            print(f"   用户ID: {user_id}")
        except:
            pass
        
        return token
        
    except Exception as e:
        print(f"❌ 登录错误: {e}")
        return None

def get_or_create_app(token):
    """获取或创建测试应用"""
    print("\n2. 获取或创建测试应用...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    apps_url = f"{BASE_URL}/api/v1/apps/"
    
    # 获取现有应用
    response = requests.get(apps_url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        apps = response.json()
        if apps:
            app = apps[0]
            print(f"✅ 使用现有应用: {app.get('name')}")
            print(f"   应用ID: {app.get('id')}")
            return app.get("id")
    
    # 创建新应用
    print("创建新的测试应用...")
    
    # 从令牌获取用户ID
    import jwt
    decoded = jwt.decode(token, options={"verify_signature": False})
    user_id = decoded.get("sub")
    
    create_data = {
        "name": "Smart iAdmin集成测试",
        "description": "用于测试Smart iAdmin配置集成的应用",
        "owner_id": user_id
    }
    
    create_response = requests.post(apps_url, headers=headers, 
                                  json=create_data, timeout=10)
    
    if create_response.status_code == 200:
        app = create_response.json()
        print(f"✅ 应用创建成功: {app.get('name')}")
        print(f"   应用ID: {app.get('id')}")
        return app.get("id")
    else:
        print(f"❌ 创建应用失败: {create_response.status_code}")
        print(f"响应: {create_response.text}")
        return None

def load_smart_iadmin_config():
    """加载Smart iAdmin配置"""
    print("\n3. 加载Smart iAdmin配置...")
    
    config_path = "/home/hongb/.openclaw/workspace/cold_indexes_config_v2.json"
    
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✅ 配置加载成功")
        print(f"   版本: {config.get('version')}")
        print(f"   表数量: {len(config.get('tables', []))}")
        print(f"   记录总数: {config.get('total_records')}")
        print(f"   配置大小: {len(json.dumps(config))} 字节")
        
        return config
        
    except Exception as e:
        print(f"❌ 加载配置错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def upload_config_to_app(token, app_id, config):
    """上传配置到应用"""
    print(f"\n4. 上传Smart iAdmin配置到应用...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    app_url = f"{BASE_URL}/api/v1/apps/{app_id}"
    
    # 先获取当前应用信息
    response = requests.get(app_url, headers=headers, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ 获取应用详情失败: {response.status_code}")
        print(f"响应: {response.text}")
        return False
    
    current_app = response.json()
    print(f"✅ 获取应用详情成功: {current_app.get('name')}")
    
    # 准备更新数据
    update_data = {
        "name": current_app.get("name"),
        "description": current_app.get("description", ""),
        "settings": {
            "smart_iadmin_config": config,
            "config_version": "1.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "integration": {
                "status": "active",
                "tables_loaded": len(config.get("tables", [])),
                "records_loaded": config.get("total_records", 0),
                "notes": "Smart iAdmin字段定义配置，用于解析.cld文件"
            }
        }
    }
    
    print(f"更新数据大小: {len(json.dumps(update_data))} 字节")
    
    update_response = requests.put(app_url, headers=headers, 
                                 json=update_data, timeout=30)
    
    if update_response.status_code == 200:
        updated_app = update_response.json()
        print(f"✅ Smart iAdmin配置上传成功!")
        print(f"   应用: {updated_app.get('name')}")
        print(f"   设置字段大小: {len(json.dumps(updated_app.get('settings', {})))} 字节")
        
        # 验证配置存储
        settings = updated_app.get("settings", {})
        if "smart_iadmin_config" in settings:
            stored_config = settings["smart_iadmin_config"]
            print(f"   ✅ Smart iAdmin配置验证通过")
            print(f"     配置版本: {stored_config.get('version')}")
            print(f"     表数量: {len(stored_config.get('tables', []))}")
            print(f"     记录数: {stored_config.get('total_records')}")
            
            # 保存更新后的应用信息
            with open("/home/hongb/.openclaw/workspace/app_with_config.json", "w", encoding='utf-8') as f:
                json.dump(updated_app, f, indent=2, ensure_ascii=False)
            print(f"     应用配置已保存到: app_with_config.json")
            
            return True
        else:
            print(f"   ❌ Smart iAdmin配置未找到")
            return False
    else:
        print(f"❌ 配置上传失败: {update_response.status_code}")
        print(f"响应: {update_response.text}")
        return False

def verify_api_access(token):
    """验证API访问权限"""
    print("\n5. 验证API访问权限...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    test_urls = [
        (f"{BASE_URL}/api/v1/auth/me", "获取当前用户信息"),
        (f"{BASE_URL}/api/v1/apps/", "获取应用列表"),
    ]
    
    all_success = True
    
    for url, description in test_urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"   ✅ {description}: 成功")
            else:
                print(f"   ❌ {description}: 失败 ({response.status_code})")
                all_success = False
        except Exception as e:
            print(f"   ❌ {description}: 错误 ({e})")
            all_success = False
    
    return all_success

def main():
    """主函数"""
    print("="*60)
    print("Smart iAdmin集成 - 阶段1：配置上传")
    print("="*60)
    
    # 1. 登录
    token = login()
    if not token:
        return
    
    # 2. 验证API访问
    if not verify_api_access(token):
        print("❌ API访问验证失败，无法继续")
        return
    
    # 3. 获取或创建应用
    app_id = get_or_create_app(token)
    if not app_id:
        return
    
    # 4. 加载配置
    config = load_smart_iadmin_config()
    if not config:
        return
    
    # 5. 上传配置
    success = upload_config_to_app(token, app_id, config)
    
    print("\n" + "="*60)
    if success:
        print("✅ 阶段1：配置上传 完成!")
        print("="*60)
        print(f"\n配置已成功存储到FileBot应用:")
        print(f"  应用ID: {app_id}")
        print(f"  访问API: GET /api/v1/apps/{app_id}")
        print(f"  配置文件: app_with_config.json")
        
        print(f"\n下一步：")
        print(f"  1. 修改conversion_service.py读取Smart iAdmin配置")
        print(f"  2. 测试.cld文件解析")
        print(f"  3. 验证字段提取准确性")
    else:
        print("❌ 阶段1：配置上传 失败")
        print("="*60)
        print(f"\n需要进一步调试:")
        print(f"  1. 检查FileBot后端日志")
        print(f"  2. 验证数据库连接")
        print(f"  3. 检查配置文件格式")

if __name__ == "__main__":
    main()