#!/usr/bin/env python3
import requests
import json
import sqlite3

def get_auth_token():
    """获取管理员token"""
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post("http://localhost:8001/api/v1/auth/login", data=login_data)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"登录请求失败: {e}")
        return None

def test_folder_api():
    """测试文件夹API"""
    token = get_auth_token()
    if not token:
        print("无法获取token，跳过API测试")
        return
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 获取canada-site应用的文件夹
    print("测试1: 获取canada-site应用的文件夹列表")
    try:
        response = requests.get(
            "http://localhost:8001/api/v1/folders/?app_id=canada-site",
            headers=headers
        )
        
        if response.status_code == 200:
            folders = response.json()
            print(f"成功获取 {len(folders)} 个文件夹")
            
            # 查找en文件夹
            en_folders = [f for f in folders if f.get('name') == 'en']
            print(f"找到 {len(en_folders)} 个en文件夹")
            
            for i, folder in enumerate(en_folders):
                print(f"\nen文件夹 {i+1}:")
                print(f"  ID: {folder.get('id')[:8]}...")
                print(f"  路径: {folder.get('path')}")
                print(f"  document_count: {folder.get('document_count', '未找到字段')}")
                
                # 验证document_count是否正确
                folder_id = folder.get('id')
                if folder_id:
                    # 直接从数据库验证
                    conn = sqlite3.connect('filebot.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE folder_id = ?", (folder_id,))
                    db_count = cursor.fetchone()[0]
                    conn.close()
                    
                    api_count = folder.get('document_count', 0)
                    status = "✓" if api_count == db_count else "✗"
                    print(f"  数据库直接文档数: {db_count}")
                    print(f"  API返回文档数: {api_count}")
                    print(f"  匹配状态: {status}")
        else:
            print(f"API请求失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求异常: {e}")

def test_single_folder():
    """测试单个文件夹API"""
    token = get_auth_token()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 测试两个en文件夹
    test_folder_ids = [
        "2db73b44-660a-42ed-bc63-c97751dae48b",  # /canada-site/en/en
        "21877994-0884-4dd3-8232-93355c90e315"   # /canada-site/en
    ]
    
    for folder_id in test_folder_ids:
        print(f"\n测试文件夹: {folder_id[:8]}...")
        try:
            response = requests.get(
                f"http://localhost:8001/api/v1/folders/{folder_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                folder = response.json()
                print(f"  名称: {folder.get('name')}")
                print(f"  路径: {folder.get('path')}")
                print(f"  document_count字段: {folder.get('document_count', '未找到')}")
                
                # 检查字段是否存在
                if 'document_count' in folder:
                    print(f"  ✓ 包含document_count字段")
                else:
                    print(f"  ✗ 不包含document_count字段")
                    
                # 列出所有返回的字段
                print(f"  返回字段: {', '.join(sorted(folder.keys()))}")
            else:
                print(f"  ✗ API错误: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"  ✗ 请求异常: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("测试后端API文档计数功能")
    print("=" * 60)
    
    test_folder_api()
    test_single_folder()