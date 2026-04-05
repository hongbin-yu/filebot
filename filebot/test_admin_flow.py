import requests
import json
import time

BASE_URL = "http://localhost:8001/api/v1"

def get_token():
    """获取管理员token"""
    login_data = {"username": "admin", "password": "admin123"}
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        raise Exception(f"登录失败: {response.text}")
    return response.json()["access_token"]

def create_app(token, name, slug, description=""):
    """创建应用"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    app_data = {
        "name": name,
        "slug": slug,
        "description": description
    }
    response = requests.post(f"{BASE_URL}/apps/", headers=headers, json=app_data)
    if response.status_code not in [200, 201]:
        print(f"创建应用失败: {response.status_code} - {response.text}")
        return None
    return response.json()

def create_folder(token, app_id, name, description=""):
    """创建文件夹"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    folder_data = {
        "name": name,
        "description": description,
        "app_id": app_id
    }
    response = requests.post(f"{BASE_URL}/folders/", headers=headers, json=folder_data)
    if response.status_code not in [200, 201]:
        print(f"创建文件夹失败: {response.status_code} - {response.text}")
        return None
    return response.json()

def main():
    print("=== 测试Admin功能流程 ===\n")
    
    # 1. 获取token
    print("1. 登录获取token...")
    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        print("   ✓ 登录成功")
    except Exception as e:
        print(f"   ✗ 登录失败: {e}")
        return
    
    # 2. 检查现有应用
    print("\n2. 获取应用列表...")
    response = requests.get(f"{BASE_URL}/apps/", headers=headers)
    if response.status_code != 200:
        print(f"   ✗ 获取应用失败: {response.status_code} - {response.text}")
        return
    
    apps = response.json()
    print(f"   现有应用数: {len(apps)}")
    
    # 3. 如果没有应用，创建测试应用
    if len(apps) == 0:
        print("\n3. 创建测试应用...")
        app = create_app(token, "Admin测试应用", "admin-test", "用于Admin功能测试的应用")
        if app:
            print(f"   ✓ 创建应用成功: {app['name']} (ID: {app['id']})")
            apps = [app]
        else:
            print("   ✗ 创建应用失败")
            return
    else:
        print("\n3. 使用现有应用")
        app = apps[0]
        print(f"   使用应用: {app['name']} (ID: {app['id']})")
    
    app_id = app['id']
    
    # 4. 创建文件夹
    print("\n4. 创建测试文件夹...")
    folder = create_folder(token, app_id, "公共文档", "共享PDF文档文件夹")
    if folder:
        print(f"   ✓ 创建文件夹成功: {folder['name']} (ID: {folder['id']})")
    else:
        print("   ✗ 创建文件夹失败")
        # 检查错误
        response = requests.get(f"{BASE_URL}/folders/", headers=headers, params={"app_id": app_id})
        print(f"   Folders端点响应: {response.status_code} - {response.text}")
        return
    
    # 5. 获取文件夹列表
    print("\n5. 获取文件夹列表...")
    response = requests.get(f"{BASE_URL}/folders/", headers=headers, params={"app_id": app_id})
    if response.status_code == 200:
        folders = response.json()
        print(f"   文件夹数: {len(folders)}")
        for f in folders:
            print(f"   - {f['name']} ({f['id']})")
    else:
        print(f"   ✗ 获取文件夹失败: {response.status_code} - {response.text}")
    
    # 6. 测试文档端点
    print("\n6. 测试文档端点...")
    folder_id = folder['id']
    response = requests.get(f"{BASE_URL}/documents/", headers=headers, params={"folder_id": folder_id})
    if response.status_code == 200:
        docs = response.json()
        print(f"   文档数: {len(docs)}")
    else:
        print(f"   文档端点响应: {response.status_code} - {response.text}")
        print("   (这是正常的，因为还没有文档)")
    
    print("\n=== 测试完成 ===")
    print(f"前端Admin URL: http://localhost:5173/admin/apps")
    print(f"应用详情URL: http://localhost:5173/admin/apps/{app.get('slug', app['id'])}")
    print(f"文件夹文档URL: http://localhost:5173/admin/apps/{app.get('slug', app['id'])}/folders/{folder['id']}/documents")

if __name__ == "__main__":
    main()