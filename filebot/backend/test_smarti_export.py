#!/usr/bin/env python3
"""
测试Smarti应用导出功能
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def get_auth_token():
    """获取管理员token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    if response.status_code != 200:
        print(f"❌ 登录失败: {response.status_code}")
        print(response.text)
        return None
    
    token = response.json()["access_token"]
    print(f"✅ 获取token成功")
    return token

def test_app_export(token, app_id):
    """测试应用导出"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/export/app/{app_id}",
        headers=headers
    )
    
    print(f"\n📦 应用导出测试 (App ID: {app_id})")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 导出成功")
        print(f"应用名称: {data.get('name')}")
        print(f"文件夹数量: {len(data.get('folders', []))}")
        
        # 统计文档和缺失文件
        total_docs = 0
        missing_docs = 0
        
        def count_folder(folder):
            nonlocal total_docs, missing_docs
            for doc in folder.get('documents', []):
                total_docs += 1
                metadata = doc.get('document_metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        pass
                if metadata.get('file_status') == 'missing':
                    missing_docs += 1
            
            for sub in folder.get('subfolders', []):
                count_folder(sub)
        
        for folder in data.get('folders', []):
            count_folder(folder)
        
        print(f"文档总数: {total_docs}")
        print(f"缺失文档: {missing_docs}")
        
        # 检查是否包含file_status
        if missing_docs > 0:
            print(f"✅ 缺失文档已正确标记 (file_status='missing')")
        else:
            print(f"⚠️  未发现标记为缺失的文档")
            
        return True
    else:
        print(f"❌ 导出失败")
        print(f"响应: {response.text[:500]}")
        return False

def test_folder_export(token, folder_id):
    """测试文件夹导出"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/export/folder/{folder_id}",
        headers=headers
    )
    
    print(f"\n📁 文件夹导出测试 (Folder ID: {folder_id})")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 导出成功")
        print(f"文件夹名称: {data.get('name')}")
        print(f"文档数量: {len(data.get('documents', []))}")
        
        # 检查文档metadata
        for i, doc in enumerate(data.get('documents', [])[:3]):
            metadata = doc.get('document_metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    pass
            print(f"文档 #{i+1}: {doc.get('title', 'N/A')[:30]}")
            print(f"  文件状态: {metadata.get('file_status', '未设置')}")
            print(f"  原始文件名: {doc.get('original_filename', 'N/A')[:40]}")
        
        return True
    else:
        print(f"❌ 导出失败")
        print(f"响应: {response.text[:500]}")
        return False

def test_full_export(token):
    """测试完整导出"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/export/full",
        headers=headers
    )
    
    print(f"\n🌐 完整导出测试")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 导出成功")
        print(f"应用数量: {len(data.get('apps', []))}")
        return True
    else:
        print(f"❌ 导出失败")
        print(f"响应: {response.text[:500]}")
        return False

def main():
    print("=" * 60)
    print("Smarti导出功能测试")
    print("=" * 60)
    
    # 获取token
    token = get_auth_token()
    if not token:
        sys.exit(1)
    
    # Smarti应用ID
    smarti_app_id = "3dd82912-28f0-40eb-8ed9-263ba19c9420"  # [Smarti] Sample Financial
    
    # 包含缺失文档的文件夹ID
    missing_folder_id = "82651b79-100a-4b35-ae9e-2aed7b0e7a1c"  # 90000150
    
    # 测试应用导出
    app_success = test_app_export(token, smarti_app_id)
    
    # 测试文件夹导出
    folder_success = test_folder_export(token, missing_folder_id)
    
    # 测试完整导出
    full_success = test_full_export(token)
    
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    
    results = {
        "应用导出": "✅ 通过" if app_success else "❌ 失败",
        "文件夹导出": "✅ 通过" if folder_success else "❌ 失败", 
        "完整导出": "✅ 通过" if full_success else "❌ 失败"
    }
    
    for test, result in results.items():
        print(f"{test}: {result}")
    
    # 总体评估
    if all([app_success, folder_success, full_success]):
        print("\n🎉 所有导出测试通过！")
        print("Smarti数据迁移和导出功能已就绪。")
    else:
        print("\n⚠️  部分测试失败，需要进一步调试。")

if __name__ == "__main__":
    main()