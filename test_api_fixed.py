#!/usr/bin/env python3
"""
测试修复后的API
"""

import requests
import json
import sys

def test_api():
    """测试API"""
    base_url = "http://localhost:8000"
    
    print("=== 测试修复后的FileBot API ===\n")
    
    # 1. 登录
    print("1. 登录...")
    login_url = f"{base_url}/api/v1/auth/login"
    login_data = {"username": "admin", "password": "FileBot2026!"}
    
    try:
        response = requests.post(login_url, data=login_data, timeout=10)
        if response.status_code != 200:
            print(f"❌ 登录失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
        
        token = response.json().get("access_token")
        print(f"✅ 登录成功，令牌: {token[:30]}...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 2. 获取应用列表
        print("\n2. 获取应用列表...")
        apps_url = f"{base_url}/api/v1/apps/"
        apps_response = requests.get(apps_url, headers=headers, timeout=10)
        
        if apps_response.status_code != 200:
            print(f"❌ 获取应用列表失败: {apps_response.status_code}")
            print(f"响应: {apps_response.text}")
            return None
        
        apps = apps_response.json()
        print(f"✅ 获取到 {len(apps)} 个应用")
        
        if not apps:
            print("❌ 没有应用，创建一个新的...")
            return None
        
        app_id = apps[0].get("id")
        app_name = apps[0].get("name")
        print(f"使用应用: {app_name} (ID: {app_id})")
        
        # 3. 获取应用详情
        print(f"\n3. 获取应用详情...")
        app_url = f"{base_url}/api/v1/apps/{app_id}"
        app_response = requests.get(app_url, headers=headers, timeout=10)
        
        if app_response.status_code != 200:
            print(f"❌ 获取应用详情失败: {app_response.status_code}")
            print(f"响应: {app_response.text}")
            return None
        
        app_data = app_response.json()
        print(f"✅ 获取应用详情成功!")
        print(f"  名称: {app_data.get('name')}")
        print(f"  描述: {app_data.get('description', '无')}")
        print(f"  设置字段: {len(json.dumps(app_data.get('settings', {})))} 字节")
        
        # 4. 测试更新设置（Smart iAdmin配置）
        print(f"\n4. 测试更新Smart iAdmin配置...")
        
        # 加载Smart iAdmin配置
        config_path = "/home/hongb/.openclaw/workspace/cold_indexes_config_v2.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                smart_config = json.load(f)
            
            print(f"✅ 加载Smart iAdmin配置成功")
            print(f"  版本: {smart_config.get('version')}")
            print(f"  表数量: {len(smart_config.get('tables', []))}")
            print(f"  记录总数: {smart_config.get('total_records')}")
            
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            smart_config = {
                "test": True,
                "message": "Smart iAdmin配置测试",
                "tables": 8,
                "records": 712
            }
        
        # 准备更新数据
        update_data = {
            "name": app_data.get("name"),
            "description": app_data.get("description", ""),
            "settings": {
                "smart_iadmin_config": smart_config,
                "config_version": "1.0",
                "last_updated": "2026-03-16"
            }
        }
        
        print(f"更新数据大小: {len(json.dumps(update_data))} 字节")
        
        update_response = requests.put(app_url, headers=headers, 
                                      json=update_data, timeout=30)
        
        if update_response.status_code == 200:
            updated_app = update_response.json()
            print(f"✅ Smart iAdmin配置上传成功!")
            print(f"  应用名称: {updated_app.get('name')}")
            print(f"  设置字段大小: {len(json.dumps(updated_app.get('settings', {})))} 字节")
            
            # 检查配置是否存储
            settings = updated_app.get("settings", {})
            if "smart_iadmin_config" in settings:
                config = settings["smart_iadmin_config"]
                if isinstance(config, dict):
                    print(f"  Smart iAdmin配置详情:")
                    print(f"    - 版本: {config.get('version', '未知')}")
                    print(f"    - 表数量: {len(config.get('tables', []))}")
                    print(f"    - 记录数: {config.get('total_records', config.get('records', '未知'))}")
                else:
                    print(f"  Smart iAdmin配置已存储 (类型: {type(config).__name__})")
            
            return updated_app
            
        else:
            print(f"❌ 配置上传失败: {update_response.status_code}")
            print(f"响应: {update_response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 服务器可能未运行")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_document_upload(token, app_id):
    """测试文档上传"""
    if not token:
        return
    
    print("\n5. 测试文档上传功能...")
    
    base_url = "http://localhost:8000"
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    # 创建一个测试.cld文件
    test_cld_content = """PO Number: 4500002860
Vendor: ACME Corp
Amount: $1,234.56
Date: 03/16/2026
Description: Test Purchase Order
    
Line Item 1: Widget A - 10 units @ $50.00
Line Item 2: Widget B - 5 units @ $100.00
Total: $1,000.00
"""
    
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cld', delete=False) as f:
        f.write(test_cld_content)
        temp_file = f.name
    
    try:
        url = f"{base_url}/api/v1/documents/upload/"
        
        files = {
            "file": (os.path.basename(temp_file), open(temp_file, "rb"))
        }
        data = {
            "app_id": app_id,
            "title": "测试Purchase Order文档",
            "description": "Smart iAdmin集成测试 - .cld文件"
        }
        
        print(f"上传测试文件: {os.path.basename(temp_file)}")
        response = requests.post(url, headers=headers, data=data, 
                               files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 文档上传成功!")
            print(f"  文档ID: {result.get('id')}")
            print(f"  文档名称: {result.get('name')}")
            print(f"  状态: {result.get('status')}")
            return result.get("id")
        else:
            print(f"❌ 文档上传失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 上传错误: {e}")
        return None
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_file)
        except:
            pass

def main():
    """主函数"""
    # 测试API
    result = test_api()
    
    if result:
        print("\n" + "="*60)
        print("✅ Smart iAdmin配置集成测试完成!")
        print("="*60)
        
        print(f"\n配置存储位置:")
        print(f"  应用ID: {result.get('id')}")
        print(f"  应用名称: {result.get('name')}")
        print(f"  访问API: GET /api/v1/apps/{result.get('id')}")
        
        print(f"\n下一步:")
        print(f"  1. 修改转换服务以使用Smart iAdmin配置")
        print(f"  2. 测试.cld文件解析")
        print(f"  3. 验证字段提取准确性")
        
        # 可以在这里调用test_document_upload来测试文档上传
        # 但需要token和app_id
        
    else:
        print("\n❌ Smart iAdmin配置集成测试失败")
        print("需要进一步调试")

if __name__ == "__main__":
    main()