#!/usr/bin/env python3
"""
WebBot API测试脚本
测试核心API端点是否正常工作
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 10  # 秒

def test_api_health():
    """测试API健康检查"""
    print("🔍 测试API健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过: {data}")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_api_info():
    """测试API信息端点"""
    print("🔍 测试API信息...")
    try:
        response = requests.get(f"{BASE_URL}/api", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API信息: {data['name']} v{data['version']}")
            print(f"   数据库状态: {data['database']}")
            print(f"   可用端点: {', '.join(data['endpoints'].keys())}")
            return True
        else:
            print(f"❌ API信息获取失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_pages_api():
    """测试页面管理API"""
    print("🔍 测试页面管理API...")
    
    # 测试获取页面列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/pages", timeout=TIMEOUT)
        if response.status_code == 200:
            pages = response.json()
            print(f"✅ 获取页面列表: 共{len(pages)}个页面")
        else:
            print(f"❌ 获取页面列表失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")
        return False
    
    # 测试创建页面
    test_page = {
        "title": "Test Page from API",
        "content": "<h1>Test Page</h1><p>Created by API test</p>",
        "language": "en",
        "status": "draft"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/pages",
            json=test_page,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            created_page = response.json()
            page_id = created_page["id"]
            print(f"✅ 创建页面成功: {created_page['title']} (ID: {page_id})")
            
            # 测试获取单个页面
            response = requests.get(f"{BASE_URL}/api/v1/pages/{page_id}", timeout=TIMEOUT)
            if response.status_code == 200:
                print(f"✅ 获取页面详情成功")
            else:
                print(f"❌ 获取页面详情失败: HTTP {response.status_code}")
            
            # 测试删除页面
            response = requests.delete(f"{BASE_URL}/api/v1/pages/{page_id}", timeout=TIMEOUT)
            if response.status_code == 200:
                print(f"✅ 删除页面成功")
            else:
                print(f"❌ 删除页面失败: HTTP {response.status_code}")
            
            return True
        else:
            print(f"❌ 创建页面失败: HTTP {response.status_code}")
            if response.text:
                print(f"   错误信息: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_ai_api():
    """测试AI功能API"""
    print("🔍 测试AI功能API...")
    
    # 测试快速AI创页
    ai_request = {
        "action": "create_page",
        "content": "Test page about AI capabilities"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/create-page",
            json=ai_request,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                print(f"✅ AI创页成功: {result['result'][:50]}...")
            else:
                print(f"❌ AI创页失败: {result.get('error', 'Unknown error')}")
            return result["success"]
        else:
            print(f"❌ AI创页请求失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_frontend():
    """测试前端界面可访问性"""
    print("🔍 测试前端界面...")
    
    try:
        response = requests.get(f"{BASE_URL}/static/index.html", timeout=TIMEOUT)
        if response.status_code == 200:
            print("✅ 前端界面可访问")
            return True
        else:
            print(f"❌ 前端界面访问失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 WebBot API测试开始")
    print("=" * 50)
    
    tests = [
        ("API健康检查", test_api_health),
        ("API信息", test_api_info),
        ("页面管理API", test_pages_api),
        ("AI功能API", test_ai_api),
        ("前端界面", test_frontend),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
            time.sleep(1)  # 避免请求过于频繁
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("✨ 所有测试通过！WebBot系统正常工作。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查WebBot服务状态。")
        return 1

if __name__ == "__main__":
    # 等待服务器启动（如果刚启动）
    print("⏳ 等待5秒让服务器启动...")
    time.sleep(5)
    
    exit_code = main()
    exit(exit_code)