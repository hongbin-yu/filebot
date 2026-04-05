#!/usr/bin/env python3
"""
调试导出API错误
"""
import json
import requests
import sys

# 配置
BASE_URL = "http://localhost:8001/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0ZGFkNmZhMS1kNTIxLTQxN2YtODg3Ny1lZmU5NWZjZjFmMDQiLCJleHAiOjE3NzU5NDEzNjl9.jmjy9DKJN1jBz3gSNz7z9oRYcA0BaOJdYqm6DMm8mcA"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

def test_app_export(app_id):
    """测试应用导出"""
    print(f"\n🔍 测试应用导出: {app_id}")
    url = f"{BASE_URL}/export/app/{app_id}?include_documents=false"
    response = requests.get(url, headers=headers)
    
    print(f"状态码: {response.status_code}")
    if response.status_code != 200:
        print(f"错误: {response.text[:500]}")
        # 尝试获取更多调试信息
        try:
            error_data = response.json()
            print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            pass
    else:
        print("✅ 成功")
        data = response.json()
        print(f"应用名称: {data.get('name')}")
        print(f"文件夹数量: {len(data.get('folders', []))}")

def test_folder_export(folder_id, include_docs=True):
    """测试文件夹导出"""
    print(f"\n🔍 测试文件夹导出: {folder_id}, include_documents={include_docs}")
    url = f"{BASE_URL}/export/folder/{folder_id}?include_documents={str(include_docs).lower()}"
    response = requests.get(url, headers=headers)
    
    print(f"状态码: {response.status_code}")
    if response.status_code != 200:
        print(f"错误: {response.text[:500]}")
        try:
            error_data = response.json()
            print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            pass
    else:
        print("✅ 成功")
        data = response.json()
        print(f"文件夹名称: {data.get('name')}")
        print(f"文档数量: {data.get('document_count')}")
        if include_docs:
            print(f"实际文档数: {len(data.get('documents', []))}")

def test_full_export(app_slug=None):
    """测试完整导出"""
    print(f"\n🔍 测试完整导出: app_slug={app_slug}")
    url = f"{BASE_URL}/export/full"
    if app_slug:
        url += f"?app_slug={app_slug}"
    
    response = requests.get(url, headers=headers)
    
    print(f"状态码: {response.status_code}")
    if response.status_code != 200:
        print(f"错误: {response.text[:500]}")
        try:
            error_data = response.json()
            print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            pass
    else:
        print("✅ 成功")
        data = response.json()
        print(f"应用数量: {data.get('total_apps')}")
        print(f"文件夹总数: {data.get('total_folders')}")
        print(f"文档总数: {data.get('total_documents')}")

def test_document_metadata():
    """检查文档元数据"""
    print("\n🔍 检查文档元数据")
    # 查询数据库
    import sqlite3
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 获取一个文档的元数据
    cursor.execute("SELECT id, title, document_metadata FROM documents LIMIT 5")
    docs = cursor.fetchall()
    
    for doc_id, title, metadata in docs:
        print(f"\n文档: {title} ({doc_id})")
        print(f"元数据类型: {type(metadata)}")
        if metadata:
            try:
                if isinstance(metadata, str):
                    parsed = json.loads(metadata)
                    print(f"解析成功: {json.dumps(parsed, indent=2, ensure_ascii=False)[:200]}")
                else:
                    print(f"非字符串: {metadata}")
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"原始内容: {metadata[:200]}")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 开始调试导出API错误")
    
    # 从映射文件读取ID
    try:
        with open('smarti_import_mapping.json', 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        app_mapping = mapping.get('mappings', {}).get('app', {})
        fold_mapping = mapping.get('mappings', {}).get('fold', {})
        
        if app_mapping:
            print(f"\n📋 找到 {len(app_mapping)} 个应用")
            # 测试第一个应用
            first_app_id = list(app_mapping.values())[0]
            test_app_export(first_app_id)
            
            # 测试第二个应用
            if len(app_mapping) > 1:
                second_app_id = list(app_mapping.values())[1]
                test_app_export(second_app_id)
        
        if fold_mapping:
            print(f"\n📁 找到 {len(fold_mapping)} 个文件夹")
            # 测试第一个文件夹，不带文档
            first_folder_id = list(fold_mapping.values())[0]
            test_folder_export(first_folder_id, include_docs=False)
            
            # 测试同一个文件夹，带文档
            test_folder_export(first_folder_id, include_docs=True)
        
        # 测试完整导出
        test_full_export("smarti-sample-financial")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 检查文档元数据
    test_document_metadata()