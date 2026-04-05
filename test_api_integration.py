#!/usr/bin/env python3
"""
测试FileBot API集成Smart iAdmin配置
"""

import requests
import json
import sys
import os

class FileBotAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.access_token = None
        
    def login(self, username, password):
        """登录获取访问令牌"""
        url = f"{self.base_url}/api/v1/auth/login"
        data = {
            "username": username,
            "password": password
        }
        
        print(f"登录到 {url}...")
        try:
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                print(f"✅ 登录成功! 令牌: {self.access_token[:30]}...")
                return True
            else:
                print(f"❌ 登录失败: {response.status_code}")
                print(f"响应: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 登录错误: {e}")
            return False
    
    def get_headers(self):
        """获取认证头"""
        if not self.access_token:
            raise ValueError("未登录，请先调用login()方法")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_apps(self):
        """获取应用列表"""
        url = f"{self.base_url}/api/v1/apps/"
        
        print(f"获取应用列表...")
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            if response.status_code == 200:
                apps = response.json()
                print(f"✅ 找到 {len(apps)} 个应用:")
                for app in apps:
                    print(f"  - {app.get('name')} (ID: {app.get('id')})")
                    if app.get('settings'):
                        settings_summary = json.dumps(app.get('settings'), ensure_ascii=False)[:100]
                        print(f"    设置: {settings_summary}...")
                return apps
            else:
                print(f"❌ 获取应用失败: {response.status_code}")
                print(f"响应: {response.text}")
                return []
        except Exception as e:
            print(f"❌ 错误: {e}")
            return []
    
    def get_app(self, app_id):
        """获取指定应用详情"""
        url = f"{self.base_url}/api/v1/apps/{app_id}"
        
        print(f"获取应用 {app_id}...")
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            if response.status_code == 200:
                app = response.json()
                print(f"✅ 获取成功:")
                print(f"  名称: {app.get('name')}")
                print(f"  ID: {app.get('id')}")
                print(f"  描述: {app.get('description', '无')}")
                print(f"  设置字段大小: {len(json.dumps(app.get('settings', {})))} 字节")
                return app
            else:
                print(f"❌ 获取应用失败: {response.status_code}")
                print(f"响应: {response.text}")
                return None
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    def update_app_settings(self, app_id, new_settings):
        """更新应用设置"""
        url = f"{self.base_url}/api/v1/apps/{app_id}"
        
        # 先获取当前应用
        current_app = self.get_app(app_id)
        if not current_app:
            return False
        
        # 准备更新数据
        update_data = {
            "name": current_app.get("name", ""),
            "description": current_app.get("description", ""),
            "settings": new_settings
        }
        
        print(f"更新应用设置 (ID: {app_id})...")
        print(f"新设置大小: {len(json.dumps(new_settings))} 字节")
        
        try:
            response = requests.put(url, headers=self.get_headers(), 
                                   json=update_data, timeout=30)
            if response.status_code == 200:
                updated_app = response.json()
                print(f"✅ 更新成功!")
                print(f"  应用名称: {updated_app.get('name')}")
                print(f"  设置字段大小: {len(json.dumps(updated_app.get('settings', {})))} 字节")
                
                # 检查Smart iAdmin配置是否已存储
                settings = updated_app.get("settings", {})
                if "smart_iadmin_config" in settings:
                    config = settings["smart_iadmin_config"]
                    print(f"  Smart iAdmin配置已存储:")
                    print(f"    - 版本: {config.get('version')}")
                    print(f"    - 表数量: {config.get('tables')}")
                    print(f"    - 记录数: {config.get('records')}")
                    print(f"    - 字段定义: {config.get('field_definitions')}")
                return True
            else:
                print(f"❌ 更新失败: {response.status_code}")
                print(f"响应: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 错误: {e}")
            return False
    
    def test_upload_document(self, app_id, file_path):
        """测试文档上传"""
        url = f"{self.base_url}/api/v1/documents/upload/"
        
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return False
        
        print(f"测试文档上传: {file_path}...")
        
        try:
            files = {
                "file": (os.path.basename(file_path), open(file_path, "rb"))
            }
            data = {
                "app_id": app_id,
                "title": f"测试文档: {os.path.basename(file_path)}",
                "description": "Smart iAdmin集成测试文档"
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
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
            print(f"❌ 错误: {e}")
            return None

def load_smart_iadmin_config():
    """加载Smart iAdmin配置"""
    config_path = "/home/hongb/.openclaw/workspace/cold_indexes_config_v2.json"
    
    if not os.path.exists(config_path):
        print(f"❌ Smart iAdmin配置文件不存在: {config_path}")
        return None
    
    print(f"加载Smart iAdmin配置: {config_path}")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✅ 配置加载成功:")
        print(f"  版本: {config.get('version')}")
        print(f"  表数量: {len(config.get('tables', []))}")
        print(f"  记录总数: {config.get('total_records')}")
        
        # 整理为API格式
        smart_config = {
            "version": config.get("version", "1.0"),
            "tables": config.get("tables", []),
            "records": config.get("total_records", 0),
            "field_definitions": 51,  # cold_indexes表字段数
            "extracted_date": "2026-03-16",
            "data": config
        }
        
        return smart_config
    except Exception as e:
        print(f"❌ 加载配置错误: {e}")
        return None

def main():
    """主函数"""
    print("=== FileBot API集成测试 ===\n")
    
    # 初始化API客户端
    api = FileBotAPI()
    
    # 1. 登录
    if not api.login("admin", "FileBot2026!"):
        print("❌ 无法继续，登录失败")
        return
    
    print()
    
    # 2. 获取应用列表
    apps = api.get_apps()
    if not apps:
        print("❌ 未找到应用，无法继续")
        return
    
    print()
    
    # 3. 确定目标应用ID
    target_app_id = "28516d7d-e499-4be4-b150-7d69ab742055"  # TestApp ID
    
    # 4. 获取应用当前状态
    current_app = api.get_app(target_app_id)
    if not current_app:
        print("❌ 无法获取应用信息")
        return
    
    print()
    
    # 5. 加载Smart iAdmin配置
    smart_config = load_smart_iadmin_config()
    if not smart_config:
        print("❌ 无法加载Smart iAdmin配置")
        return
    
    print()
    
    # 6. 准备新的settings
    current_settings = current_app.get("settings", {})
    
    # 确保不会覆盖其他设置
    new_settings = current_settings.copy()
    new_settings["smart_iadmin_config"] = smart_config
    new_settings["config_version"] = "v1.0"
    new_settings["last_updated"] = "2026-03-16"
    
    print(f"当前设置字段数: {len(current_settings)}")
    print(f"新设置字段数: {len(new_settings)}")
    print()
    
    # 7. 更新应用设置
    success = api.update_app_settings(target_app_id, new_settings)
    
    if success:
        print("\n" + "="*60)
        print("✅ Smart iAdmin配置集成测试成功!")
        print("="*60)
        print(f"\n配置已存储到:")
        print(f"  应用: {current_app.get('name')}")
        print(f"  ID: {target_app_id}")
        print(f"  访问方式: GET /api/v1/apps/{target_app_id}")
        
        # 8. 可选：测试文档上传
        print("\n可选测试:")
        print("  1. 测试文档上传: api.test_upload_document(app_id, file_path)")
        print("  2. 测试配置读取: api.get_app(app_id)")
        
    else:
        print("\n❌ Smart iAdmin配置集成测试失败")
        print("可能原因:")
        print("  1. API权限不足")
        print("  2. 设置数据太大")
        print("  3. 服务器错误")

if __name__ == "__main__":
    main()