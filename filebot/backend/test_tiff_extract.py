#!/usr/bin/env python3
"""
测试TIFF页面提取功能

步骤：
1. 登录获取token
2. 上传TIFF文件
3. 测试提取页面功能
"""

import requests
import json
import uuid
import time
from pathlib import Path
import sys

# 配置
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin123"
TIFF_FILE = "/mnt/c/workspace/tiff_input/fin00000.tif"  # 使用第一个TIFF文件

def login():
    """登录获取token"""
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    # OAuth2PasswordRequestForm需要表单数据
    response = requests.post(url, data=data)
    if response.status_code != 200:
        print(f"登录失败: {response.status_code}")
        print(response.text)
        return None
    
    result = response.json()
    token = result.get("access_token")
    print(f"登录成功，获取到token: {token[:20]}...")
    return token

def get_or_create_folder(token):
    """获取或创建文件夹"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # 先尝试获取应用
    apps_url = f"{BASE_URL}/apps/"
    response = requests.get(apps_url, headers=headers)
    
    if response.status_code == 200 and response.json():
        apps = response.json()
        app_id = apps[0]["id"]
        print(f"使用现有应用: {app_id}")
    else:
        # 创建测试应用
        app_data = {
            "name": "测试应用",
            "description": "TIFF功能测试应用"
        }
        response = requests.post(apps_url, headers=headers, json=app_data)
        if response.status_code == 201:
            app = response.json()
            app_id = app["id"]
            print(f"创建新应用: {app_id}")
        else:
            print(f"创建应用失败: {response.status_code}")
            print(response.text)
            return None
    
    # 获取或创建抽屉
    drawers_url = f"{BASE_URL}/apps/{app_id}/drawers"
    response = requests.get(drawers_url, headers=headers)
    
    if response.status_code == 200 and response.json():
        drawers = response.json()
        drawer_id = drawers[0]["id"]
        print(f"使用现有抽屉: {drawer_id}")
    else:
        # 创建抽屉
        drawer_data = {
            "name": "测试抽屉",
            "order_index": 1
        }
        response = requests.post(drawers_url, headers=headers, json=drawer_data)
        if response.status_code == 201:
            drawer = response.json()
            drawer_id = drawer["id"]
            print(f"创建新抽屉: {drawer_id}")
        else:
            print(f"创建抽屉失败: {response.status_code}")
            print(response.text)
            return None
    
    # 获取或创建文件夹
    folders_url = f"{BASE_URL}/drawers/{drawer_id}/folders"
    response = requests.get(folders_url, headers=headers)
    
    if response.status_code == 200 and response.json():
        folders = response.json()
        folder_id = folders[0]["id"]
        print(f"使用现有文件夹: {folder_id}")
    else:
        # 创建文件夹
        folder_data = {
            "name": "测试文件夹",
            "path": "/test"
        }
        response = requests.post(folders_url, headers=headers, json=folder_data)
        if response.status_code == 201:
            folder = response.json()
            folder_id = folder["id"]
            print(f"创建新文件夹: {folder_id}")
        else:
            print(f"创建文件夹失败: {response.status_code}")
            print(response.text)
            return None
    
    return folder_id

def upload_tiff(token, folder_id, tiff_path):
    """上传TIFF文件"""
    url = f"{BASE_URL}/documents/upload/"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 准备文件上传
    with open(tiff_path, 'rb') as f:
        files = {'file': (Path(tiff_path).name, f, 'image/tiff')}
        data = {
            'folder_id': str(folder_id),
            'title': Path(tiff_path).stem,
            'description': 'TIFF功能测试文件',
            'document_type': 'general'
        }
        
        response = requests.post(url, headers=headers, files=files, data=data)
    
    if response.status_code == 200:
        document = response.json()
        print(f"文件上传成功: {document['original_filename']}")
        print(f"文档ID: {document['id']}")
        return document
    else:
        print(f"文件上传失败: {response.status_code}")
        print(response.text)
        return None

def test_tiff_extraction(token, document_id, page_numbers=[1], output_format="pdf"):
    """测试TIFF页面提取功能"""
    url = f"{BASE_URL}/documents/{document_id}/extract-tiff-pages"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 构建查询参数
    params = {
        "output_format": output_format
    }
    
    # 添加页码参数
    for page_num in page_numbers:
        params[f"page_numbers"] = page_num
    
    print(f"\n测试TIFF页面提取...")
    print(f"文档ID: {document_id}")
    print(f"页码: {page_numbers}")
    print(f"输出格式: {output_format}")
    
    response = requests.post(url, headers=headers, params=params)
    
    if response.status_code == 200:
        # 保存返回的文件
        output_filename = f"extracted_pages_{output_format}.{output_format}"
        with open(output_filename, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ 页面提取成功!")
        print(f"  保存文件到: {output_filename}")
        print(f"  文件大小: {len(response.content)} 字节")
        
        # 检查Content-Type
        content_type = response.headers.get('Content-Type', '')
        print(f"  Content-Type: {content_type}")
        
        return True
    else:
        print(f"✗ 页面提取失败: {response.status_code}")
        print(f"  响应: {response.text[:200]}")
        return False

def main():
    """主测试流程"""
    print("=" * 60)
    print("TIFF页面提取功能测试")
    print("=" * 60)
    
    # 1. 登录
    token = login()
    if not token:
        print("登录失败，退出测试")
        return False
    
    # 2. 获取或创建文件夹
    folder_id = get_or_create_folder(token)
    if not folder_id:
        print("无法获取文件夹ID，退出测试")
        return False
    
    # 3. 上传TIFF文件
    if not Path(TIFF_FILE).exists():
        print(f"TIFF文件不存在: {TIFF_FILE}")
        return False
    
    document = upload_tiff(token, folder_id, TIFF_FILE)
    if not document:
        print("文件上传失败，退出测试")
        return False
    
    document_id = document['id']
    
    # 4. 测试提取功能
    print("\n" + "=" * 60)
    print("开始TIFF页面提取测试")
    print("=" * 60)
    
    test_cases = [
        {"pages": [1], "format": "pdf", "description": "提取单页为PDF"},
        {"pages": [1], "format": "tiff", "description": "提取单页为TIFF"},
        # 如果是多页TIFF，可以测试多页提取
        # {"pages": [1, 2, 3], "format": "pdf", "description": "提取多页为PDF"},
    ]
    
    all_passed = True
    for test_case in test_cases:
        print(f"\n测试: {test_case['description']}")
        success = test_tiff_extraction(
            token, document_id, 
            test_case['pages'], test_case['format']
        )
        
        if not success:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)