#!/usr/bin/env python3
"""
使用FastAPI TestClient测试路径API
"""
import sys
sys.path.insert(0, '/home/hongb/.openclaw/workspace/webbot')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("测试FastAPI应用路由")
print("=" * 50)

# 列出所有路由
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"{route.path} - {route.methods if hasattr(route, 'methods') else 'N/A'}")

print("\\n测试路径API:")
print("-" * 30)

# 测试 /en/contact
response = client.get("/api/v1/pages/by-path", params={"path": "/en/contact"})
print(f"GET /api/v1/pages/by-path?path=/en/contact")
print(f"状态: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✅ 成功: id={data['id']}, parent={data['parent_id']}")
else:
    print(f"响应: {response.text}")

# 测试基础API
print("\\n测试基础API:")
response2 = client.get("/api/v1/pages/contact")
print(f"GET /api/v1/pages/contact")
print(f"状态: {response2.status_code}")
if response2.status_code == 200:
    data = response2.json()
    print(f"✅ 成功: id={data['id']}, parent={data['parent_id']}")