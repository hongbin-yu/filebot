#!/usr/bin/env python3
"""
测试/by-path API端点
"""
import requests
import sys
import time

base_url = 'http://localhost:8000/api/v1/pages'

def test_by_path(path, expected_status=200):
    """测试路径API"""
    print(f'\n🔍 测试路径: {path}')
    try:
        resp = requests.get(f'{base_url}/by-path', params={'path': path}, timeout=10)
        print(f'  状态码: {resp.status_code}')
        print(f'  响应: {resp.text[:200]}')
        
        if resp.status_code == expected_status:
            if expected_status == 200:
                data = resp.json()
                print(f'✅ 成功获取页面')
                print(f'  id={data["id"]}, parent={data["parent_id"]}, language={data["language"]}, title={data["title"]}')
            else:
                print(f'✅ 预期错误状态码: {expected_status}')
            return True
        else:
            print(f'❌ 状态码不匹配: 期望{expected_status}, 实际{resp.status_code}')
            return False
            
    except requests.exceptions.RequestException as e:
        print(f'❌ 请求异常: {e}')
        return False
    except Exception as e:
        print(f'❌ 其他异常: {e}')
        return False

def main():
    print('🚀 测试/by-path API端点（选项B2）')
    print('=' * 50)
    
    # 等待服务就绪
    for i in range(10):
        try:
            resp = requests.get(f'{base_url}/contact', timeout=2)
            if resp.status_code == 200:
                print('✅ WebBot服务就绪')
                break
        except:
            pass
        if i == 9:
            print('❌ 无法连接到WebBot服务')
            return
        time.sleep(1)
    
    # 测试各种路径
    tests = [
        ('/en/contact', 200, '英语contact页面'),
        ('/fr/contact', 200, '法语contact页面'),
        ('/en', 200, '英语根页面（en页面）'),
        ('/nonexistent/path', 404, '不存在的路径'),
        ('/', 400, '根路径（错误）'),
    ]
    
    passed = 0
    for path, expected_status, description in tests:
        print(f'\n📋 测试: {description}')
        if test_by_path(path, expected_status):
            passed += 1
    
    print('\n' + '=' * 50)
    print(f'📊 测试结果: {passed}/{len(tests)} 通过')
    
    if passed == len(tests):
        print('🎉 /by-path API工作正常！')
    else:
        print('⚠️ 部分测试失败，需要调试。')

if __name__ == "__main__":
    main()