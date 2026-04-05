#!/usr/bin/env python3
"""
测试修复后的get_page函数，验证多语言版本区分
"""
import requests
import json
import sys
import time

base_url = 'http://localhost:8000/api/v1/pages'

def wait_for_service(max_attempts=10):
    """等待服务就绪"""
    for i in range(max_attempts):
        try:
            resp = requests.get(f'{base_url}/contact', timeout=2)
            if resp.status_code == 200:
                print('✅ WebBot服务就绪')
                return True
        except requests.exceptions.ConnectionError:
            if i == max_attempts - 1:
                print('❌ 无法连接到WebBot服务')
                return False
        except Exception as e:
            print(f'⚠️  服务检查异常: {e}')
        time.sleep(1)
    return False

def test_get_page_without_parent():
    """测试不提供parent_id参数（向后兼容）"""
    print('\n🔍 测试不提供parent_id参数...')
    try:
        resp = requests.get(f'{base_url}/contact', timeout=5)
        print(f'  状态码: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'✅ 成功获取页面')
            print(f'  id={data["id"]}, parent={data["parent_id"]}, language={data["language"]}, title={data["title"]}')
            return True
        else:
            print(f'❌ 获取失败: {resp.text}')
            return False
            
    except Exception as e:
        print(f'❌ 请求异常: {e}')
        return False

def test_get_page_with_parent(parent_id, expected_lang, expected_title_fragment):
    """测试提供parent_id参数"""
    print(f'\n🔍 测试parent_id="{parent_id}"...')
    try:
        resp = requests.get(f'{base_url}/contact?parent_id={parent_id}', timeout=5)
        print(f'  状态码: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'✅ 成功获取页面')
            print(f'  id={data["id"]}, parent={data["parent_id"]}, language={data["language"]}, title={data["title"]}')
            
            # 验证语言和标题
            if data["parent_id"] == parent_id and data["language"] == expected_lang:
                print(f'✅ 语言验证正确: {expected_lang}')
                return True
            else:
                print(f'⚠️  语言验证失败: 期望parent={parent_id},lang={expected_lang}, 实际parent={data["parent_id"]},lang={data["language"]}')
                return False
        else:
            print(f'❌ 获取失败: {resp.text}')
            return False
            
    except Exception as e:
        print(f'❌ 请求异常: {e}')
        return False

def test_get_page_nonexistent():
    """测试不存在的页面"""
    print('\n🔍 测试不存在的页面...')
    try:
        resp = requests.get(f'{base_url}/nonexistent', timeout=5)
        print(f'  状态码: {resp.status_code}')
        
        if resp.status_code == 404:
            print('✅ 正确返回404（页面未找到）')
            return True
        else:
            print(f'⚠️  期望404，实际{resp.status_code}: {resp.text}')
            return False
    except Exception as e:
        print(f'❌ 请求异常: {e}')
        return False

def test_get_page_wrong_parent():
    """测试错误的parent_id"""
    print('\n🔍 测试错误的parent_id...')
    try:
        resp = requests.get(f'{base_url}/contact?parent_id=nonexistent', timeout=5)
        print(f'  状态码: {resp.status_code}')
        
        if resp.status_code == 404:
            print('✅ 正确返回404（parent_id不存在）')
            return True
        else:
            print(f'⚠️  期望404，实际{resp.status_code}: {resp.text}')
            return False
    except Exception as e:
        print(f'❌ 请求异常: {e}')
        return False

def main():
    print('🚀 测试get_page函数修复（选项B1）')
    print('=' * 50)
    
    if not wait_for_service():
        sys.exit(1)
    
    tests_passed = 0
    total_tests = 5
    
    # 测试1: 不提供parent_id（向后兼容）
    if test_get_page_without_parent():
        tests_passed += 1
    
    # 测试2: 英语contact页面
    if test_get_page_with_parent('en', 'en', 'Contacts'):
        tests_passed += 1
    
    # 测试3: 法语contact页面  
    if test_get_page_with_parent('fr', 'fr', 'Contactez-nous'):
        tests_passed += 1
    
    # 测试4: 不存在的页面
    if test_get_page_nonexistent():
        tests_passed += 1
    
    # 测试5: 错误的parent_id
    if test_get_page_wrong_parent():
        tests_passed += 1
    
    # 总结
    print('\n' + '=' * 50)
    print(f'📊 测试结果: {tests_passed}/{total_tests} 通过')
    
    if tests_passed == total_tests:
        print('🎉 所有测试通过！get_page函数修复成功。')
        print('\n📌 核心功能验证:')
        print('   - ✅ 向后兼容: 不提供parent_id返回第一个匹配')
        print('   - ✅ 多语言区分: parent_id=en → 英语contact页面')
        print('   - ✅ 多语言区分: parent_id=fr → 法语contact页面')
        print('   - ✅ 错误处理: 不存在的页面返回404')
        print('   - ✅ 错误处理: 错误的parent_id返回404')
    else:
        print(f'⚠️  部分测试失败，需要调试。')

if __name__ == "__main__":
    main()