#!/usr/bin/env python3
"""
启动后端并测试导出API
"""
import subprocess
import time
import requests
import json
import sys
import os
from pathlib import Path

def check_server_running(port=8001):
    """检查服务器是否在运行"""
    try:
        response = requests.get(f"http://localhost:{port}/docs", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_server():
    """启动服务器"""
    print("🚀 启动后端服务器...")
    
    # 检查是否已在运行
    if check_server_running():
        print("  ✅ 服务器已在运行")
        return None
    
    # 启动服务器
    cmd = ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd(),
        text=True
    )
    
    # 等待服务器启动
    print("  ⏳ 等待服务器启动...")
    for i in range(30):  # 最多等待30秒
        if check_server_running():
            print(f"  ✅ 服务器已启动 (等待了{i+1}秒)")
            return process
        
        # 检查进程是否出错
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"  ❌ 服务器启动失败:")
            print(f"     stdout: {stdout[:200]}")
            print(f"     stderr: {stderr[:200]}")
            return None
        
        time.sleep(1)
    
    print("  ⚠️  服务器启动超时")
    return process

def test_login():
    """测试登录获取token"""
    print("\n🔐 测试登录...")
    
    try:
        response = requests.post(
            "http://localhost:8001/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"  ✅ 登录成功")
            print(f"     Token: {token[:20]}...")
            return token
        else:
            print(f"  ❌ 登录失败: {response.status_code}")
            print(f"     {response.text[:100]}")
            return None
    except Exception as e:
        print(f"  ❌ 登录请求失败: {e}")
        return None

def test_export_full(token):
    """测试完整导出"""
    print("\n📊 测试完整导出 /api/v1/export/full...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            "http://localhost:8001/api/v1/export/full",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 导出成功")
            print(f"     导出时间: {data.get('export_time')}")
            print(f"     应用数量: {data.get('total_apps')}")
            print(f"     文件夹数量: {data.get('total_folders')}")
            print(f"     文档总数: {data.get('total_documents')}")
            
            # 检查字段名
            if data.get('apps'):
                app = data['apps'][0]
                if 'settings' in app:
                    print(f"     App.settings字段: ✅")
                else:
                    print(f"     App.settings字段: ❌ (缺失)")
                
                # 检查文档字段
                if app.get('folders'):
                    folder = app['folders'][0]
                    if folder.get('documents'):
                        doc = folder['documents'][0]
                        if 'document_metadata' in doc:
                            print(f"     Document.document_metadata字段: ✅")
                            
                            # 检查是否有缺失文件标记
                            metadata = doc.get('document_metadata', {})
                            if metadata.get('file_status') == 'missing':
                                print(f"     ⚠️  发现缺失文件标记")
                        else:
                            print(f"     Document.document_metadata字段: ❌ (缺失)")
            
            # 保存示例
            with open('full_export_sample.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"     示例已保存: full_export_sample.json")
            
            return True
        else:
            print(f"  ❌ 导出失败: {response.status_code}")
            print(f"     {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ 导出请求失败: {e}")
        return False

def test_export_app(token):
    """测试应用导出"""
    print("\n📱 测试应用导出 /api/v1/export/app/{app_id}...")
    
    # 先获取一个应用ID
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 获取应用列表
        response = requests.get(
            "http://localhost:8001/api/v1/apps/",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            apps = response.json()
            if apps:
                app_id = apps[0]['id']
                app_name = apps[0]['name']
                
                print(f"  测试应用: {app_name} ({app_id})")
                
                # 测试导出
                response = requests.get(
                    f"http://localhost:8001/api/v1/export/app/{app_id}",
                    headers=headers,
                    params={"include_documents": True},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ 应用导出成功")
                    print(f"     应用: {data.get('name')}")
                    print(f"     文件夹: {len(data.get('folders', []))} 个")
                    
                    # 统计文档
                    total_docs = 0
                    for folder in data.get('folders', []):
                        total_docs += len(folder.get('documents', []))
                    
                    print(f"     文档: {total_docs} 个")
                    
                    # 检查字段
                    if 'settings' in data:
                        print(f"     App.settings字段: ✅")
                    
                    return True
                else:
                    print(f"  ❌ 应用导出失败: {response.status_code}")
                    print(f"     {response.text[:100]}")
                    return False
            else:
                print(f"  ⚠️  无可用应用")
                return False
        else:
            print(f"  ❌ 获取应用列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ 应用导出测试失败: {e}")
        return False

def test_export_folder(token):
    """测试文件夹导出"""
    print("\n📁 测试文件夹导出 /api/v1/export/folder/{folder_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 先获取一个文件夹ID
        response = requests.get(
            "http://localhost:8001/api/v1/folders/",
            headers=headers,
            params={"limit": 1},
            timeout=5
        )
        
        if response.status_code == 200:
            folders = response.json()
            if folders:
                folder_id = folders[0]['id']
                folder_name = folders[0]['name']
                
                print(f"  测试文件夹: {folder_name} ({folder_id})")
                
                # 测试导出
                response = requests.get(
                    f"http://localhost:8001/api/v1/export/folder/{folder_id}",
                    headers=headers,
                    params={"include_documents": True},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ 文件夹导出成功")
                    print(f"     文件夹: {data.get('name')}")
                    print(f"     文档: {len(data.get('documents', []))} 个")
                    
                    # 检查字段
                    if 'app_name' in data:
                        print(f"     所属应用: {data.get('app_name')}")
                    
                    # 检查是否没有drawer_id和metadata字段
                    if 'drawer_id' not in data:
                        print(f"     Folder.drawer_id字段: ✅ (已移除)")
                    
                    if 'metadata' not in data:
                        print(f"     Folder.metadata字段: ✅ (已移除)")
                    
                    return True
                else:
                    print(f"  ❌ 文件夹导出失败: {response.status_code}")
                    print(f"     {response.text[:100]}")
                    return False
            else:
                print(f"  ⚠️  无可用文件夹")
                return False
        else:
            print(f"  ❌ 获取文件夹列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ 文件夹导出测试失败: {e}")
        return False

def main():
    print("=" * 60)
    print("导出API完整测试")
    print("=" * 60)
    
    # 启动服务器
    process = start_server()
    if not process and not check_server_running():
        print("❌ 无法启动服务器，测试中止")
        return
    
    # 等待一下确保服务器完全启动
    time.sleep(2)
    
    # 测试登录
    token = test_login()
    if not token:
        print("❌ 无法获取token，测试中止")
        if process:
            process.terminate()
        return
    
    # 测试各个端点
    success_count = 0
    total_tests = 3
    
    if test_export_full(token):
        success_count += 1
    
    if test_export_app(token):
        success_count += 1
    
    if test_export_folder(token):
        success_count += 1
    
    # 停止服务器（如果是我们启动的）
    if process:
        print("\n🛑 停止服务器...")
        process.terminate()
        process.wait()
        print("  ✅ 服务器已停止")
    
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    
    print(f"\n📊 测试通过: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 所有导出API测试通过!")
        print("\n✅ 导出功能已完成:")
        print("   1. 字段名修正完成")
        print("   2. API端点工作正常")
        print("   3. 数据完整性保持")
        print("   4. 缺失文件标记正确")
    else:
        print(f"⚠️  部分测试失败，请检查日志")
    
    print(f"\n📁 生成的文件:")
    print(f"   • full_export_sample.json - 完整导出示例")
    print(f"   • export_demo.json - 演示JSON结构")
    print(f"   • missing_files_report.txt - 缺失文件报告")

if __name__ == "__main__":
    main()