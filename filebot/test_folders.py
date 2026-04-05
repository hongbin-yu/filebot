import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

# 登录获取token
login_data = {"username": "admin", "password": "admin123"}
print("登录...")
response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
if response.status_code != 200:
    print(f"登录失败: {response.text}")
    exit()

token_data = response.json()
access_token = token_data["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

# 获取应用列表，找到service canada应用
print("\n获取应用列表...")
apps_response = requests.get(f"{BASE_URL}/apps/", headers=headers)
if apps_response.status_code != 200:
    print(f"获取应用失败: {apps_response.text}")
    exit()

apps = apps_response.json()
print(f"找到 {len(apps)} 个应用")

# 查找service canada应用
service_canada = None
for app in apps:
    if app.get('name') == 'service canada' or app.get('slug') == 'service-canada':
        service_canada = app
        break

if not service_canada:
    print("未找到service canada应用")
    # 使用第一个应用
    service_canada = apps[0]

app_id = service_canada['id']
print(f"使用应用: {service_canada['name']} (ID: {app_id})")

# 测试folders端点，根据app_id获取文件夹
print(f"\n测试folders端点，app_id={app_id}...")
folders_response = requests.get(f"{BASE_URL}/folders/", headers=headers, params={"app_id": app_id})
print(f"Folders状态码: {folders_response.status_code}")
print(f"Folders响应: {folders_response.text}")

# 如果没有文件夹，尝试创建一个
if folders_response.status_code == 200 and len(folders_response.json()) == 0:
    print("\n尝试创建文件夹...")
    folder_data = {
        "name": "测试文件夹",
        "description": "通过API创建的测试文件夹",
        "app_id": app_id
    }
    create_response = requests.post(f"{BASE_URL}/folders/", headers=headers, json=folder_data)
    print(f"创建文件夹状态码: {create_response.status_code}")
    print(f"创建文件夹响应: {create_response.text}")
    
    # 再次获取文件夹列表
    print("\n重新获取文件夹列表...")
    folders_response = requests.get(f"{BASE_URL}/folders/", headers=headers, params={"app_id": app_id})
    print(f"Folders状态码: {folders_response.status_code}")
    print(f"Folders响应: {folders_response.text}")

# 测试documents端点（需要folder_id）
if folders_response.status_code == 200 and len(folders_response.json()) > 0:
    folder = folders_response.json()[0]
    folder_id = folder['id']
    print(f"\n测试documents端点，folder_id={folder_id}...")
    docs_response = requests.get(f"{BASE_URL}/documents/", headers=headers, params={"folder_id": folder_id})
    print(f"Documents状态码: {docs_response.status_code}")
    print(f"Documents响应: {docs_response.text}")