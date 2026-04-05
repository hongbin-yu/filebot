#!/usr/bin/env python3
"""
最终UUID格式修复 - 确保所有ID存储为标准格式
"""

import sqlite3
import uuid
import os
import sys

def fix_all_uuids():
    """修复所有表中的UUID格式"""
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    
    print(f"打开数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 需要修复UUID的表和列
        tables_to_fix = [
            ("users", "id", "用户ID"),
            ("users", "id", "用户ID"),  # 主键
            ("apps", "id", "应用ID"),
            ("apps", "owner_id", "所有者ID"),
            ("permissions", "id", "权限ID"),
            ("permissions", "user_id", "用户ID"),
            ("permissions", "resource_id", "资源ID"),
            ("drawers", "id", "抽屉ID"),
            ("drawers", "app_id", "应用ID"),
            ("folders", "id", "文件夹ID"),
            ("folders", "drawer_id", "抽屉ID"),
            ("folders", "parent_folder_id", "父文件夹ID"),
            ("documents", "id", "文档ID"),
            ("documents", "folder_id", "文件夹ID"),
            ("documents", "uploaded_by", "上传者ID"),
            ("pages", "id", "页面ID"),
            ("pages", "document_id", "文档ID"),
            ("conversion_tasks", "id", "任务ID"),
            ("conversion_tasks", "document_id", "文档ID"),
        ]
        
        # 去重
        tables_to_fix = list(dict.fromkeys(tables_to_fix))
        
        print(f"需要修复 {len(tables_to_fix)} 个ID列")
        
        # 修复每个表的每个ID列
        for table, column, description in tables_to_fix:
            print(f"\n修复 {table}.{column} ({description})...")
            
            # 检查表是否存在该列
            cursor.execute(f"PRAGMA table_info({table});")
            columns_info = cursor.fetchall()
            column_names = [col[1] for col in columns_info]
            
            if column not in column_names:
                print(f"  ⚠️  列不存在，跳过")
                continue
            
            # 获取当前数据
            cursor.execute(f"SELECT {column} FROM {table};")
            rows = cursor.fetchall()
            
            if not rows:
                print(f"  ℹ️  表为空，跳过")
                continue
            
            print(f"  找到 {len(rows)} 行")
            
            updated_count = 0
            for row in rows:
                original_id = row[0]
                if not original_id:
                    continue
                
                # 转换为字符串
                id_str = str(original_id)
                
                # 如果已经是标准UUID格式，跳过
                if len(id_str) == 36 and '-' in id_str:
                    # 验证格式
                    try:
                        uuid.UUID(id_str)
                        continue  # 已经是标准格式
                    except ValueError:
                        pass  # 不是有效UUID，需要修复
                
                # 尝试转换为标准UUID格式
                new_id = None
                
                # 情况1: 32字符无连字符
                if len(id_str) == 32 and '-' not in id_str:
                    try:
                        new_id = f"{id_str[:8]}-{id_str[8:12]}-{id_str[12:16]}-{id_str[16:20]}-{id_str[20:]}"
                        # 验证
                        uuid.UUID(new_id)
                    except ValueError:
                        new_id = None
                
                # 情况2: 可能是字节或其他格式
                if not new_id:
                    try:
                        # 尝试作为UUID对象处理
                        if isinstance(original_id, bytes):
                            uuid_obj = uuid.UUID(bytes=original_id)
                        else:
                            uuid_obj = uuid.UUID(id_str)
                        new_id = str(uuid_obj)
                    except (ValueError, TypeError):
                        # 生成新的UUID
                        new_id = str(uuid.uuid4())
                        print(f"    ⚠️  无法转换 {original_id}，生成新的: {new_id}")
                
                # 更新数据库
                try:
                    cursor.execute(f"UPDATE {table} SET {column} = ? WHERE {column} = ?", 
                                 (new_id, original_id))
                    updated_count += 1
                    
                    # 显示第一个示例
                    if updated_count == 1:
                        print(f"    示例转换: {original_id} → {new_id}")
                        
                except Exception as e:
                    print(f"    ❌ 更新错误: {e}")
            
            if updated_count > 0:
                print(f"  ✅ 更新了 {updated_count} 行")
            else:
                print(f"  ℹ️  无需更新")
        
        conn.commit()
        print(f"\n✅ 所有UUID格式修复完成")
        
        # 验证修复结果
        print("\n验证修复结果:")
        
        test_queries = [
            ("SELECT id, username FROM users LIMIT 1", "用户表"),
            ("SELECT id, name, owner_id FROM apps LIMIT 1", "应用表"),
        ]
        
        for query, description in test_queries:
            try:
                cursor.execute(query)
                row = cursor.fetchone()
                if row:
                    print(f"  {description}:")
                    for i, value in enumerate(row):
                        col_name = query.split("SELECT ")[1].split(" FROM")[0].split(",")[i].strip()
                        print(f"    {col_name}: {value}")
                        if isinstance(value, str) and len(value) == 36 and '-' in value:
                            try:
                                uuid.UUID(value)
                                print(f"      ✅ 标准UUID格式")
                            except ValueError:
                                print(f"      ❌ 无效UUID格式")
            except Exception as e:
                print(f"  ❌ {description}查询错误: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库错误: {e}")
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
    login_data = {"username": "admin", "password": "admin123"}
    
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
                    print(f"应用设置字段: {len(json.dumps(app_data.get('settings', {})))} 字节")
                    
                    return app_id, token
                else:
                    print(f"❌ 获取应用详情失败: {app_response.status_code}")
                    print(f"响应: {app_response.text}")
                    
        else:
            print(f"❌ 获取应用列表失败: {apps_response.status_code}")
            print(f"响应: {apps_response.text}")
            
    except Exception as e:
        print(f"❌ API测试错误: {e}")
    
    return None, None

def upload_smart_iadmin_config(app_id, token):
    """上传Smart iAdmin配置"""
    if not app_id or not token:
        return
    
    print("\n" + "="*60)
    print("上传Smart iAdmin配置")
    print("="*60)
    
    import requests
    import json
    
    base_url = "http://localhost:8000"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 加载配置
    config_path = "/home/hongb/.openclaw/workspace/cold_indexes_config_v2.json"
    
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✅ 加载Smart iAdmin配置成功")
        print(f"  版本: {config.get('version')}")
        print(f"  表数量: {len(config.get('tables', []))}")
        print(f"  记录总数: {config.get('total_records')}")
        
    except Exception as e:
        print(f"❌ 加载配置错误: {e}")
        return
    
    # 获取当前应用信息
    app_url = f"{base_url}/api/v1/apps/{app_id}"
    response = requests.get(app_url, headers=headers, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ 获取应用详情失败: {response.status_code}")
        return
    
    current_app = response.json()
    
    # 准备更新数据
    update_data = {
        "name": current_app.get("name"),
        "description": current_app.get("description", ""),
        "settings": {
            "smart_iadmin_config": config,
            "config_version": "1.0",
            "last_updated": "2026-03-16",
            "integration_status": "active"
        }
    }
    
    print(f"上传配置大小: {len(json.dumps(update_data))} 字节")
    
    update_response = requests.put(app_url, headers=headers, 
                                 json=update_data, timeout=30)
    
    if update_response.status_code == 200:
        updated_app = update_response.json()
        print(f"✅ Smart iAdmin配置上传成功!")
        print(f"  应用: {updated_app.get('name')}")
        
        settings = updated_app.get("settings", {})
        if "smart_iadmin_config" in settings:
            print(f"  ✅ 配置验证通过")
            
            # 保存结果
            result_path = "/home/hongb/.openclaw/workspace/integration_result.json"
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "app_id": app_id,
                    "app_name": updated_app.get("name"),
                    "config_uploaded": True,
                    "config_size": len(json.dumps(settings)),
                    "timestamp": "2026-03-16"
                }, f, indent=2, ensure_ascii=False)
            
            print(f"  结果保存到: {result_path}")
            return True
        else:
            print(f"  ❌ 配置未找到")
            return False
    else:
        print(f"❌ 配置上传失败: {update_response.status_code}")
        print(f"响应: {update_response.text}")
        return False

def main():
    """主函数"""
    print("=== 最终UUID格式修复与Smart iAdmin集成 ===")
    
    # 1. 修复UUID格式
    fix_all_uuids()
    
    # 2. 重启FileBot后端
    print("\n重启FileBot后端...")
    import subprocess
    import time
    
    try:
        subprocess.run(["pkill", "-f", "uvicorn"], timeout=5)
        time.sleep(2)
        
        backend_dir = "/home/hongb/.openclaw/workspace/filebot/backend"
        log_file = f"{backend_dir}/restart_final_fix.log"
        cmd = f"cd {backend_dir} && nohup ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload > {log_file} 2>&1 &"
        subprocess.run(cmd, shell=True, timeout=5)
        print(f"✅ 后端重启命令已发送")
        print(f"日志文件: {log_file}")
        
        # 等待后端启动
        print("等待后端启动...")
        time.sleep(5)
        
    except Exception as e:
        print(f"❌ 重启错误: {e}")
    
    # 3. 测试API
    app_id, token = test_api_after_fix()
    
    if app_id and token:
        # 4. 上传Smart iAdmin配置
        success = upload_smart_iadmin_config(app_id, token)
        
        if success:
            print("\n" + "="*60)
            print("✅ Smart iAdmin集成测试完成!")
            print("="*60)
            print(f"\n配置已成功存储到FileBot应用")
            print(f"应用ID: {app_id}")
            print(f"\n下一步:")
            print(f"  1. 修改conversion_service.py读取配置")
            print(f"  2. 测试.cld文件解析")
            print(f"  3. 验证字段提取准确性")
        else:
            print("\n❌ Smart iAdmin配置上传失败")
    else:
        print("\n❌ API测试失败，无法继续集成")

if __name__ == "__main__":
    main()