import requests
import json
import sys

BASE_URL = "http://localhost:8001/api/v1"

def get_token():
    """获取管理员token"""
    login_data = {"username": "admin", "password": "admin123"}
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"登录失败: {response.status_code} - {response.text}")
        return None
    return response.json()["access_token"]

def test_folders_api():
    print("=== 测试Folders API ===")
    
    # 1. 登录
    print("\n1. 登录...")
    token = get_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    print("   ✓ 登录成功")
    
    # 2. 获取应用列表
    print("\n2. 获取应用列表...")
    apps_response = requests.get(f"{BASE_URL}/apps/", headers=headers)
    if apps_response.status_code != 200:
        print(f"   ✗ 获取应用失败: {apps_response.status_code} - {apps_response.text}")
        return False
    
    apps = apps_response.json()
    print(f"   应用数: {len(apps)}")
    
    if len(apps) == 0:
        print("   没有应用，需要先创建应用")
        return False
    
    # 使用第一个应用
    app = apps[0]
    app_id = app['id']
    print(f"   使用应用: {app['name']} (ID: {app_id})")
    
    # 3. 测试GET /folders/（无参数）
    print("\n3. 测试GET /folders/（无参数）...")
    folders_response = requests.get(f"{BASE_URL}/folders/", headers=headers)
    print(f"   状态码: {folders_response.status_code}")
    if folders_response.status_code == 200:
        folders = folders_response.json()
        print(f"   文件夹数: {len(folders)}")
    else:
        print(f"   响应: {folders_response.text}")
    
    # 4. 测试GET /folders/（带app_id参数）
    print("\n4. 测试GET /folders/（带app_id参数）...")
    params = {"app_id": app_id}
    folders_response = requests.get(f"{BASE_URL}/folders/", headers=headers, params=params)
    print(f"   状态码: {folders_response.status_code}")
    if folders_response.status_code == 200:
        folders = folders_response.json()
        print(f"   文件夹数: {len(folders)}")
        for folder in folders:
            print(f"   - {folder['name']} (ID: {folder['id']})")
    else:
        print(f"   响应: {folders_response.text}")
        # 检查错误详情
        print(f"   请求URL: {BASE_URL}/folders/?app_id={app_id}")
    
    # 5. 如果没有文件夹，创建测试文件夹
    if folders_response.status_code == 200 and len(folders_response.json()) == 0:
        print("\n5. 创建测试文件夹...")
        folder_data = {
            "name": "测试文件夹",
            "description": "通过API创建的测试文件夹",
            "app_id": app_id
        }
        create_response = requests.post(f"{BASE_URL}/folders/", headers=headers, json=folder_data)
        print(f"   创建状态码: {create_response.status_code}")
        print(f"   创建响应: {create_response.text}")
        
        if create_response.status_code in [200, 201]:
            print("   ✓ 文件夹创建成功")
            # 再次获取文件夹列表
            print("\n6. 重新获取文件夹列表...")
            folders_response = requests.get(f"{BASE_URL}/folders/", headers=headers, params=params)
            print(f"   状态码: {folders_response.status_code}")
            if folders_response.status_code == 200:
                folders = folders_response.json()
                print(f"   文件夹数: {len(folders)}")
        else:
            print("   ✗ 文件夹创建失败")
    
    return True

if __name__ == "__main__":
    success = test_folders_api()
    if success:
        print("\n=== 测试完成 ===")
        print("建议下一步: 测试前端Admin界面连接")
        print("前端URL: http://localhost:5173/admin/apps")
    else:
        print("\n=== 测试失败 ===")
        sys.exit(1)