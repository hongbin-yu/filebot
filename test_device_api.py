#!/usr/bin/env python3
"""测试设备管理API"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def login(username="admin", password="admin123"):
    """登录获取JWT令牌"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            print("登录失败: 未获取到访问令牌")
            return None
        print(f"登录成功，用户: {data.get('user', {}).get('username')}")
        return token
    except Exception as e:
        print(f"登录失败: {e}")
        return None

def test_device_apis(token):
    """测试设备API"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== 测试设备API ===")
    
    # 1. 获取设备列表
    print("1. 获取设备列表...")
    response = requests.get(f"{BASE_URL}/devices/", headers=headers)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        devices = response.json()
        print(f"   设备数量: {len(devices)}")
        for device in devices:
            print(f"   - {device['name']} ({device['type']}): {device['used_mb']}/{device['capacity_mb']}MB")
    else:
        print(f"   错误: {response.text}")
    
    # 2. 创建设备
    print("\n2. 创建设备...")
    device_data = {
        "name": "测试存储设备",
        "description": "API测试创建的设备",
        "path": "/tmp/filebot_test_storage",
        "type": "storage",
        "capacity_mb": 1024,
        "warning_threshold": 85,
        "priority": 1
    }
    response = requests.post(f"{BASE_URL}/devices/", headers=headers, json=device_data)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 201:
        created_device = response.json()
        device_id = created_device['id']
        print(f"   创建设备成功: {created_device['name']} (ID: {device_id})")
        
        # 3. 测试设备状态检测
        print("\n3. 测试设备状态检测...")
        response = requests.get(f"{BASE_URL}/devices/{device_id}/status?update_capacity=true", headers=headers)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            status_data = response.json()
            print(f"   设备状态: {status_data['status']}")
            print(f"   使用率: {status_data['usage_percentage']}%")
            print(f"   状态消息: {status_data['status_message']}")
        
        return device_id
    else:
        print(f"   创建设备失败: {response.text}")
        return None

def test_naming_rule_apis(token):
    """测试命名规则API"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== 测试文件命名规则API ===")
    
    # 1. 获取应用列表（需要先有应用）
    print("1. 获取应用列表...")
    response = requests.get(f"{BASE_URL}/apps/", headers=headers)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        apps = response.json()
        if apps:
            app_id = apps[0]['id']
            print(f"   使用应用: {apps[0]['name']} (ID: {app_id})")
            
            # 2. 创建命名规则
            print("\n2. 创建文件命名规则...")
            rule_data = {
                "app_id": app_id,
                "name": "测试采购订单规则",
                "basename": "PO-",
                "max_number": 1000,
                "increment_by": 1,
                "description": "API测试创建的命名规则",
                "subfolder_name": "purchase_orders"  # 指定子文件夹
            }
            response = requests.post(f"{BASE_URL}/file-naming-rules/", headers=headers, json=rule_data)
            print(f"   状态码: {response.status_code}")
            if response.status_code == 201:
                rule = response.json()
                rule_id = rule['id']
                print(f"   创建规则成功: {rule['basename']} (子文件夹: {rule.get('subfolder_name', 'default')})")
                return rule_id
    else:
        print(f"   获取应用失败: {response.text}")
    return None

def test_system_status(token):
    """测试系统状态API"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== 测试系统状态API ===")
    
    # 1. 系统存储状态概览
    print("1. 系统存储状态概览...")
    response = requests.get(f"{BASE_URL}/devices/system/status", headers=headers)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        system_status = response.json()
        print(f"   总设备数: {system_status.get('total_devices', 0)}")
        print(f"   活跃设备: {system_status.get('active_devices', 0)}")
        print(f"   警告设备: {len(system_status.get('warning_devices', []))}")
        print(f"   已满设备: {len(system_status.get('full_devices', []))}")
        
        # 显示警告设备
        warnings = system_status.get('warning_devices', [])
        if warnings:
            print("   警告设备列表:")
            for warning in warnings:
                print(f"   - {warning['device_name']}: {warning['status_message']}")
    
    # 2. 容量批量检测
    print("\n2. 容量批量检测...")
    response = requests.post(f"{BASE_URL}/devices/capacity-detection", headers=headers, json={"update_all": True})
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        detection_results = response.json()
        print(f"   检测设备数: {detection_results.get('total_devices', 0)}")
        print(f"   成功检测: {detection_results.get('successful_detections', 0)}")
        print(f"   失败检测: {detection_results.get('failed_detections', 0)}")

def main():
    print("FileBot Phase 2 设备管理和命名规则API测试")
    print("=" * 50)
    
    # 登录
    token = login()
    if not token:
        print("登录失败，无法继续测试")
        sys.exit(1)
    
    # 测试设备API
    device_id = test_device_apis(token)
    
    # 测试命名规则API
    rule_id = test_naming_rule_apis(token)
    
    # 测试系统状态API
    test_system_status(token)
    
    print("\n" + "=" * 50)
    print("测试完成!")
    
    if device_id:
        print(f"创建的测试设备ID: {device_id}")
    if rule_id:
        print(f"创建的测试命名规则ID: {rule_id}")
    
    # 提示
    print("\n注意:")
    print("1. 测试设备存储在: /tmp/filebot_test_storage")
    print("2. 可以手动清理测试目录: rm -rf /tmp/filebot_test_storage")
    print("3. 测试设备可在管理界面删除")

if __name__ == "__main__":
    main()