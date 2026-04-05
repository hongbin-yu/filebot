import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

# 1. 登录获取token
login_data = {"username": "admin", "password": "admin123"}
print("登录...")
response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
print(f"登录状态码: {response.status_code}")
print(f"登录响应: {response.text}")

if response.status_code == 200:
    token_data = response.json()
    access_token = token_data["access_token"]
    print(f"获取到token: {access_token[:50]}...")
    
    # 2. 使用token访问apps端点
    headers = {"Authorization": f"Bearer {access_token}"}
    print(f"\n访问apps端点...")
    apps_response = requests.get(f"{BASE_URL}/apps/", headers=headers)
    print(f"Apps状态码: {apps_response.status_code}")
    print(f"Apps响应: {apps_response.text}")
    
    # 3. 访问users/me端点
    print(f"\n访问users/me端点...")
    user_response = requests.get(f"{BASE_URL}/users/me", headers=headers)
    print(f"Users/me状态码: {user_response.status_code}")
    print(f"Users/me响应: {user_response.text}")
    
    # 4. 解码token查看payload
    import jwt
    try:
        payload = jwt.decode(access_token, "your-secret-key-change-in-production", algorithms=["HS256"])
        print(f"\nToken payload: {payload}")
    except Exception as e:
        print(f"\nToken解码失败: {e}")
        # 手动检查token结构
        parts = access_token.split('.')
        print(f"Token部分数: {len(parts)}")
        if len(parts) >= 2:
            import base64
            import json as json_module
            # 添加填充
            payload_encoded = parts[1]
            padding = 4 - len(payload_encoded) % 4
            if padding != 4:
                payload_encoded += "=" * padding
            try:
                payload_decoded = base64.urlsafe_b64decode(payload_encoded)
                payload_json = json_module.loads(payload_decoded)
                print(f"手动解码payload: {payload_json}")
            except Exception as e2:
                print(f"手动解码失败: {e2}")