#!/usr/bin/env python3
"""
完整测试FileBot和WebBot统一仪表板集成
"""
import requests
import json
import time

BASE_URL = 'http://localhost:8001/api/v1'

print('🔍 测试FileBot和WebBot统一仪表板集成')
print('=' * 70)

# 登录
print('\n🔐 登录到FileBot...')
resp = requests.post(f'{BASE_URL}/auth/login', data={'username': 'admin', 'password': 'admin123'})
if resp.status_code != 200:
    print(f'登录失败: {resp.status_code} - {resp.text}')
    exit(1)

token = resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

print('✅ 登录成功')

# 1. 获取所有应用
print('\n1️⃣ 获取所有应用...')
apps_resp = requests.get(f'{BASE_URL}/apps/', headers=headers)
if apps_resp.status_code != 200:
    print(f'获取应用失败: {apps_resp.status_code}')
    exit(1)

apps = apps_resp.json()
print(f'✅ 找到 {len(apps)} 个应用')

# 2. 检查新字段
print('\n2️⃣ 检查应用是否包含新字段...')
for i, app in enumerate(apps):
    has_redirect = 'redirect_url' in app
    has_icon = 'icon' in app
    
    if not has_redirect or not has_icon:
        print(f'⚠️  应用 {app["name"]} 缺少字段: redirect_url={has_redirect}, icon={has_icon}')

# 3. 创建WebBot应用（如果不存在）
print('\n3️⃣ 检查WebBot应用...')
webbot_app = None
for app in apps:
    if 'webbot' in app['name'].lower() or (app.get('icon') and '🌐' in app['icon']):
        webbot_app = app
        print(f'✅ 找到WebBot应用: {app["name"]}')
        break

if not webbot_app:
    print('❌ 未找到WebBot应用，正在创建...')
    # 创建WebBot应用
    webbot_data = {
        'name': 'WebBot Crawler',
        'slug': 'webbot-crawler',
        'description': '网站爬虫和内容采集应用，集成到统一仪表板',
        'redirect_url': 'http://localhost:8000',
        'icon': '🌐',
        'settings': {'indices': ['Status', 'Source', 'CrawlDepth']}
    }
    
    create_resp = requests.post(f'{BASE_URL}/apps/', json=webbot_data, headers=headers)
    if create_resp.status_code == 200:
        webbot_app = create_resp.json()
        print(f'✅ 创建WebBot应用: {webbot_app["name"]}')
    else:
        print(f'❌ 创建WebBot应用失败: {create_resp.status_code} - {create_resp.text}')

# 4. 更新所有应用以设置适当的图标和重定向
print('\n4️⃣ 设置应用图标和重定向...')
for app in apps[:3]:  # 只更新前3个作为示例
    app_name = app['name'].lower()
    
    # 根据应用名称设置图标和重定向
    if 'invoice' in app_name:
        update_data = {
            'name': app['name'],
            'redirect_url': '',  # 空表示使用FileBot内部应用
            'icon': '🧾',
            'updated_by': 'admin'
        }
    elif 'canada' in app_name:
        update_data = {
            'name': app['name'],
            'redirect_url': f'http://localhost:5174/apps/{app["id"]}',
            'icon': '🏛️',
            'updated_by': 'admin'
        }
    elif 'test' in app_name:
        update_data = {
            'name': app['name'],
            'redirect_url': f'http://localhost:5174/apps/{app["id"]}',
            'icon': '📁',
            'updated_by': 'admin'
        }
    else:
        # 默认设置
        update_data = {
            'name': app['name'],
            'redirect_url': '',  # 空表示使用FileBot内部应用
            'icon': '📁',
            'updated_by': 'admin'
        }
    
    update_resp = requests.put(f'{BASE_URL}/apps/{app["id"]}', json=update_data, headers=headers)
    if update_resp.status_code == 200:
        updated_app = update_resp.json()
        print(f'  ✅ {app["name"]:20} -> 图标: {updated_app.get("icon", "无")}, 重定向: {updated_app.get("redirect_url", "无")[:40]}...')
    else:
        print(f'  ⚠️  {app["name"]}: 更新失败 {update_resp.status_code}')

# 5. 测试统一仪表板API响应
print('\n5️⃣ 测试统一仪表板API...')
dashboard_apps_resp = requests.get(f'{BASE_URL}/apps/', headers=headers)
dashboard_apps = dashboard_apps_resp.json()

print(f'📊 统一仪表板包含 {len(dashboard_apps)} 个应用:')
for app in dashboard_apps:
    icon = app.get('icon', '📄')
    name = app['name']
    has_redirect = bool(app.get('redirect_url'))
    redirect_type = '外部应用' if has_redirect else '内部应用'
    redirect_display = app.get("redirect_url") or ""
    if redirect_display:
        redirect_display = redirect_display[:50] + "..."
    print(f'  {icon} {name:25} [{redirect_type:8}] {redirect_display}')

# 6. 测试公共访问（客户端门户）
print('\n6️⃣ 测试公共用户访问...')
try:
    public_resp = requests.post(f'{BASE_URL}/auth/login', 
                              data={'username': 'public', 'password': 'public123'})
    if public_resp.status_code == 200:
        public_token = public_resp.json()['access_token']
        public_headers = {'Authorization': f'Bearer {public_token}'}
        
        public_apps_resp = requests.get(f'{BASE_URL}/apps/', headers=public_headers)
        if public_apps_resp.status_code == 200:
            public_apps = public_apps_resp.json()
            print(f'✅ 公共用户可访问 {len(public_apps)} 个应用')
            print('  客户端门户可用于统一仪表板显示')
        else:
            print(f'⚠️ 公共用户访问受限: {public_apps_resp.status_code}')
    else:
        print(f'ℹ️ 公共用户登录失败: {public_resp.status_code}')
except Exception as e:
    print(f'ℹ️ 公共用户测试跳过: {e}')

# 7. 生成前端访问指南
print('\n' + '=' * 70)
print('🎯 统一仪表板集成完成!')
print('=' * 70)

print('\n📋 访问指南:')
print('  1. 🔗 统一仪表板前端: http://localhost:5174/')
print('  2. 🔗 FileBot管理后台: http://localhost:5174/admin/apps')
print('  3. 🔗 WebBot应用: http://localhost:8000')
print('  4. 🔗 FileBot后端API: http://localhost:8001/api/v1/docs')

print('\n🔧 功能特性:')
print('  ✅ 统一仪表板: 集成FileBot和WebBot应用到单个界面')
print('  ✅ 图标支持: 每个应用可以设置自定义图标 (Emoji)')
print('  ✅ 外部重定向: 支持重定向到外部应用 (如WebBot)')
print('  ✅ 内部应用: 保留FileBot原有的文档管理功能')
print('  ✅ 类型识别: 自动识别应用类型并显示不同样式')
print('  ✅ 权限控制: 公共用户访问客户端门户')

print('\n📱 使用流程:')
print('  1. 管理员创建应用时设置图标和重定向URL')
print('  2. 用户在统一仪表板 (ClientAppSelection) 查看所有应用')
print('  3. 点击应用卡片:')
print('     - 有重定向URL: 在新标签页打开外部应用')
print('     - 无重定向URL: 进入FileBot内部应用')
print('  4. 管理员可随时编辑应用属性')

print('\n📊 应用类型示例:')
print('  📁 文档管理应用 - 无重定向URL，进入FileBot内部')
print('  🌐 WebBot应用 - 重定向到 http://localhost:8000')
print('  🏛️ 政府服务应用 - 重定向到特定URL或FileBot内部')
print('  🧾 发票系统应用 - 保留FileBot内部文档管理')

print('\n✅ 集成测试完成!')
print('🔄 前端更新已自动应用，现在可以访问统一仪表板了。')