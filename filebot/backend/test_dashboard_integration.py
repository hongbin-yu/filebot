#!/usr/bin/env python3
"""
测试FileBot和WebBot集成到统一仪表板
"""
import requests
import json

BASE_URL = 'http://localhost:8001/api/v1'

# 登录
print('🔐 登录...')
resp = requests.post(f'{BASE_URL}/auth/login', data={'username': 'admin', 'password': 'admin123'})
if resp.status_code != 200:
    print('登录失败')
    exit(1)

token = resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

print('\n🚀 测试FileBot和WebBot统一仪表板集成')

# 1. 获取所有应用
print('\n1️⃣ 获取所有应用列表...')
apps_resp = requests.get(f'{BASE_URL}/apps/', headers=headers)
apps = apps_resp.json()
print(f'  找到 {len(apps)} 个应用')

# 2. 为每个应用设置重定向URL和图标
print('\n2️⃣ 更新应用以支持统一仪表板...')
dashboard_apps = []

for app in apps[:3]:  # 只更新前3个应用作为示例
    app_type = ''
    redirect_url = ''
    icon = ''
    
    # 根据应用名称设置不同的类型
    app_name = app['name'].lower()
    if 'webbot' in app_name or 'crawl' in app_name or 'scan' in app_name:
        app_type = 'WebBot'
        redirect_url = 'http://localhost:8000'  # WebBot前端
        icon = '🌐'
    elif 'invoice' in app_name:
        app_type = '发票系统'
        redirect_url = f'http://localhost:5174/apps/{app["id"]}'  # FileBot应用门户
        icon = '🧾'
    elif 'canada' in app_name:
        app_type = '政府服务'
        redirect_url = f'http://localhost:5174/apps/{app["id"]}'
        icon = '🏛️'
    else:
        app_type = '文档管理'
        redirect_url = f'http://localhost:5174/apps/{app["id"]}'
        icon = '📁'
    
    # 更新应用
    update_data = {
        'name': app['name'],
        'redirect_url': redirect_url,
        'icon': icon,
        'updated_by': 'admin'
    }
    
    update_resp = requests.put(f'{BASE_URL}/apps/{app["id"]}', 
                             json=update_data, headers=headers)
    
    if update_resp.status_code == 200:
        updated_app = update_resp.json()
        dashboard_apps.append({
            'id': updated_app['id'],
            'name': updated_app['name'],
            'type': app_type,
            'redirect_url': updated_app.get('redirect_url'),
            'icon': updated_app.get('icon'),
            'description': updated_app.get('description', '')
        })
        print(f'  ✅ {app["name"]:25} -> {app_type:10} {icon} 重定向: {redirect_url[:40]}...')
    else:
        print(f'  ❌ {app["name"]}: 更新失败')

# 3. 显示统一仪表板视图
print('\n3️⃣ 统一仪表板预览:')
print('=' * 80)
print('🏠 FILEBOT + WEBBOT 统一仪表板')
print('=' * 80)

for i, app in enumerate(dashboard_apps):
    print(f'\n  [{i+1}] {app["icon"]} {app["name"]}')
    print(f'     类型: {app["type"]}')
    print(f'     描述: {app["description"][:60]}{"..." if app["description"] and len(app["description"]) > 60 else ""}')
    print(f'     重定向: {app["redirect_url"]}')
    print(f'     访问: curl -H "Authorization: Bearer TOKEN" {BASE_URL}/apps/{app["id"]}')

# 4. 测试公共访问（用于客户端门户）
print('\n4️⃣ 测试公共访问（Client门户）...')
# 使用public用户或无认证访问（如果允许）
try:
    # 先登录获取public用户的令牌
    public_resp = requests.post(f'{BASE_URL}/auth/login', 
                              data={'username': 'public', 'password': 'public123'})
    if public_resp.status_code == 200:
        public_token = public_resp.json()['access_token']
        public_headers = {'Authorization': f'Bearer {public_token}'}
        
        public_apps_resp = requests.get(f'{BASE_URL}/apps/', headers=public_headers)
        if public_apps_resp.status_code == 200:
            public_apps = public_apps_resp.json()
            print(f'  ✅ 公共用户可访问 {len(public_apps)} 个应用')
            
            # 显示前2个应用的仪表板卡片
            print('\n  📱 客户端门户视图:')
            for app in public_apps[:2]:
                icon = app.get('icon', '📄')
                name = app['name']
                redirect = app.get('redirect_url', f'http://localhost:5174/apps/{app["id"]}')
                print(f'     {icon} {name:25} -> {redirect[:50]}...')
        else:
            print(f'  ⚠️  公共用户访问受限: {public_apps_resp.status_code}')
    else:
        print('  ℹ️  使用admin令牌继续测试')
except Exception as e:
    print(f'  ℹ️  公共用户测试跳过: {e}')

print('\n5️⃣ API端点总结:')
print('   - GET /apps/              - 获取所有应用（支持统一仪表板）')
print('   - GET /apps/{id}          - 获取单个应用详情')
print('   - PUT /apps/{id}          - 更新应用（设置redirect_url和icon）')
print('   - POST /apps/             - 创建新应用')
print('   - 前端访问: http://localhost:5174  - FileBot前端')
print('   - WebBot访问: http://localhost:8000 - WebBot前端')

print('\n✅ 统一仪表板集成测试完成!')
print('\n🎯 下一步:')
print('   1. 更新前端ClientAppSelection以显示图标和重定向链接')
print('   2. 添加新的统一仪表板页面（可选）')
print('   3. 创建WebBot应用并设置重定向到WebBot前端')
print('   4. 测试点击应用卡片重定向功能')