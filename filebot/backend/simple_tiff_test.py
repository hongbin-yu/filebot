#!/usr/bin/env python3
"""
简化版TIFF测试：创建必要结构并测试提取功能
"""

import requests
import json
import uuid
from pathlib import Path
import sys

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin123"
TIFF_FILE = "/mnt/c/workspace/tiff_input/fin00000.tif"

class TiffTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        self.folder_id = None
        
    def login(self):
        """登录并获取用户ID"""
        url = f"{BASE_URL}/auth/login"
        response = self.session.post(url, data={
            "username": USERNAME,
            "password": PASSWORD
        })
        
        if response.status_code != 200:
            print(f"登录失败: {response.text}")
            return False
        
        data = response.json()
        self.token = data["access_token"]
        self.user_id = data["user"]["id"]
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })
        
        print(f"登录成功，用户ID: {self.user_id}")
        return True
    
    def create_test_structure(self):
        """创建测试应用、抽屉和文件夹"""
        # 1. 创建应用
        print("\n1. 创建测试应用...")
        app_data = {
            "name": "TIFF测试应用",
            "description": "用于测试TIFF页面提取功能",
            "owner_id": self.user_id,
            "settings": {},
            "created_by": "admin"
        }
        
        response = self.session.post(f"{BASE_URL}/apps/", json=app_data)
        if response.status_code not in [200, 201]:
            print(f"创建应用失败: {response.status_code}")
            print(response.text)
            return None
        
        app = response.json()
        app_id = app["id"]
        print(f"  应用创建成功: {app_id}")
        
        # 2. 创建抽屉
        print("\n2. 创建测试抽屉...")
        drawer_data = {
            "name": "TIFF测试抽屉",
            "order_index": 1,
            "app_id": app_id
        }
        
        response = self.session.post(
            f"{BASE_URL}/apps/{app_id}/drawers", 
            json=drawer_data
        )
        
        if response.status_code not in [200, 201]:
            print(f"创建抽屉失败: {response.status_code}")
            print(response.text)
            return None
        
        drawer = response.json()
        drawer_id = drawer["id"]
        print(f"  抽屉创建成功: {drawer_id}")
        
        # 3. 创建文件夹
        print("\n3. 创建测试文件夹...")
        folder_data = {
            "name": "TIFF测试文件夹",
            "path": "/tiff_test",
            "drawer_id": drawer_id
        }
        
        response = self.session.post(
            f"{BASE_URL}/drawers/{drawer_id}/folders", 
            json=folder_data
        )
        
        if response.status_code not in [200, 201]:
            print(f"创建文件夹失败: {response.status_code}")
            print(response.text)
            return None
        
        folder = response.json()
        folder_id = folder["id"]
        print(f"  文件夹创建成功: {folder_id}")
        
        return folder_id
    
    def upload_tiff(self, folder_id, tiff_path):
        """上传TIFF文件"""
        print(f"\n4. 上传TIFF文件: {Path(tiff_path).name}")
        
        with open(tiff_path, 'rb') as f:
            files = {'file': (Path(tiff_path).name, f, 'image/tiff')}
            data = {
                'folder_id': str(folder_id),
                'title': Path(tiff_path).stem,
                'description': 'TIFF功能测试文件',
                'document_type': 'general'
            }
            
            response = self.session.post(
                f"{BASE_URL}/documents/upload/",
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            document = response.json()
            print(f"  文件上传成功")
            print(f"  文档ID: {document['id']}")
            print(f"  文件名: {document['original_filename']}")
            print(f"  文件类型: {document['file_type']}")
            return document
        else:
            print(f"  文件上传失败: {response.status_code}")
            print(f"  错误: {response.text}")
            return None
    
    def test_extraction(self, document_id, page_numbers, output_format):
        """测试页面提取功能"""
        print(f"\n5. 测试页面提取 (格式: {output_format}, 页码: {page_numbers})")
        
        # 构建查询参数
        params = {"output_format": output_format}
        for page_num in page_numbers:
            params["page_numbers"] = page_num
        
        response = self.session.post(
            f"{BASE_URL}/documents/{document_id}/extract-tiff-pages",
            params=params
        )
        
        if response.status_code == 200:
            # 保存文件
            output_file = f"test_output_{output_format}_pages_{'_'.join(map(str, page_numbers))}.{output_format}"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print(f"  ✓ 提取成功!")
            print(f"    保存到: {output_file}")
            print(f"    大小: {len(response.content)} 字节")
            print(f"    Content-Type: {response.headers.get('Content-Type')}")
            return True
        else:
            print(f"  ✗ 提取失败: {response.status_code}")
            print(f"    错误: {response.text[:500]}")
            return False
    
    def run(self):
        """运行完整测试"""
        print("=" * 60)
        print("TIFF页面提取功能测试")
        print("=" * 60)
        
        # 1. 登录
        if not self.login():
            return False
        
        # 2. 创建测试结构
        self.folder_id = self.create_test_structure()
        if not self.folder_id:
            print("创建测试结构失败")
            return False
        
        # 3. 上传TIFF文件
        if not Path(TIFF_FILE).exists():
            print(f"TIFF文件不存在: {TIFF_FILE}")
            return False
        
        document = self.upload_tiff(self.folder_id, TIFF_FILE)
        if not document:
            print("文件上传失败")
            return False
        
        document_id = document['id']
        
        # 4. 测试提取功能
        print("\n" + "=" * 60)
        print("TIFF页面提取测试")
        print("=" * 60)
        
        test_cases = [
            {"pages": [1], "format": "pdf", "desc": "单页转PDF"},
            {"pages": [1], "format": "tiff", "desc": "单页转TIFF"},
        ]
        
        all_passed = True
        for test in test_cases:
            print(f"\n测试: {test['desc']}")
            success = self.test_extraction(
                document_id, test['pages'], test['format']
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
    tester = TiffTester()
    success = tester.run()
    sys.exit(0 if success else 1)