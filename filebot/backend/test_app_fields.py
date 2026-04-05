#!/usr/bin/env python3
"""
测试App API是否返回新字段 (redirect_url, icon)
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

# 获取应用列表
print('\n📋 获取应用列表...')
apps_resp = requests.get(f'{BASE_URL}/apps/', headers=headers)
if apps_resp.status_code != 200:
    print(f'获取应用列表失败: {apps_resp.status_code}')
    exit(1)

apps = apps_resp.json()
print(f'✅ 获取到 {len(apps)} 个应用')

# 检查每个应用是否包含新字段
print('\n🔍 检查应用字段...')
for i, app in enumerate(apps[:3]):  # 检查前3个应用
    print(f'\n应用 {i+1}: {app["name"]}')
    print(f'  ID: {app["id"]}')
    print(f'  重定向URL: {app.get("redirect_url", "未设置")}')
    print(f'  图标: {app.get("icon", "未设置")}')
    
    # 检查字段是否存在（即使是None）
    has_redirect_url = 'redirect_url' in app
    has_icon = 'icon' in app
    
    if not has_redirect_url:
        print('  ⚠️  缺少redirect_url字段')
    if not has_icon:
        print('  ⚠️  缺少icon字段')

# 获取第一个应用的详情
if apps:
    first_app = apps[0]
    print(f'\n📄 获取应用详情: {first_app["name"]}')
    app_detail_resp = requests.get(f'{BASE_URL}/apps/{first_app["id"]}', headers=headers)
    if app_detail_resp.status_code == 200:
        app_detail = app_detail_resp.json()
        print(f'✅ 应用详情:')
        print(f'  重定向URL: {app_detail.get("redirect_url", "未设置")}')
        print(f'  图标: {app_detail.get("icon", "未设置")}')
        
        # 测试更新应用
        print(f'\n✏️ 测试更新应用...')
        update_data = {
            'name': app_detail['name'],
            'redirect_url': 'https://webbot.example.com/dashboard',
            'icon': '🔍',  # 使用emoji作为图标
            'updated_by': 'admin'
        }
        update_resp = requests.put(f'{BASE_URL}/apps/{first_app["id"]}', 
                                 json=update_data, headers=headers)
        if update_resp.status_code == 200:
            updated_app = update_resp.json()
            print(f'✅ 更新成功!')
            print(f'  重定向URL: {updated_app.get("redirect_url", "未设置")}')
            print(f'  图标: {updated_app.get("icon", "未设置")}')
        else:
            print(f'❌ 更新失败: {update_resp.status_code} - {update_resp.text[:200]}')
    else:
        print(f'❌ 获取应用详情失败: {app_detail_resp.status_code}')

print('\n✅ 测试完成!')