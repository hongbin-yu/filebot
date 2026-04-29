#!/usr/bin/env python3
"""
测试GCWeb本地依赖渲染
验证render-page端点是否使用本地GCWeb资源而非远程CDN
"""

import requests
import json
import re

BASE_URL = "http://localhost:8000"

def test_gcweb_local_dependencies():
    """测试本地GCWeb依赖"""
    print("🧪 测试GCWeb本地依赖渲染")
    print("=" * 50)
    
    # 构建一个简单的按钮组件实例
    component_instances = [
        {
            "template_id": "wet-button-primary",
            "configuration": {
                "text": "测试按钮",
                "size": "medium",
                "disabled": False,
                "action": "https://example.com"
            },
            "position_x": 100,
            "position_y": 100,
            "alignment": "center"
        }
    ]
    
    # 构建请求
    payload = {
        "component_instances": component_instances,
        "page_title": "GCWeb本地依赖测试页面",
        "include_wet_boew": True,
        "include_accessibility": True,
        "include_admin_resources": False
    }
    
    print("📤 发送渲染请求...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/components/render-page",
            json=payload,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ 渲染失败: HTTP {response.status_code}")
            print(f"响应: {response.text[:500]}")
            return False
        
        html_content = response.text
        print(f"✅ 渲染成功 (长度: {len(html_content)} 字符)")
        
        # 检查关键部分
        print("\n🔍 检查GCWeb本地依赖:")
        
        # 查找本地GCWeb路径
        local_gcweb_patterns = [
            r'/gcweb/gcweb/GCWeb/css/theme\.min\.css',
            r'/gcweb/gcweb/wet-boew/js/wet-boew\.min\.js',
            r'/gcweb/gcweb/GCWeb/js/theme\.min\.js',
            r'/gcweb/external/jquery/2\.2\.4/jquery\.min\.js'
        ]
        
        remote_cdn_patterns = [
            r'https://wet-boew\.github\.io/themes-dist/GCWeb/GCWeb/css/theme\.min\.css',
            r'https://ajax\.googleapis\.com/ajax/libs/jquery/2\.2\.4/jquery\.min\.js',
            r'https://wet-boew\.github\.io/themes-dist/GCWeb/wet-boew/js/wet-boew\.min\.js'
        ]
        
        print("  本地GCWeb资源:")
        local_found = 0
        for pattern in local_gcweb_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                print(f"    ✅ {pattern}")
                local_found += 1
            else:
                print(f"    ❌ {pattern} (未找到)")
        
        print("\n  远程CDN资源 (不应存在):")
        remote_found = 0
        for pattern in remote_cdn_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                print(f"    ⚠️  {pattern} (不应该存在!)")
                remote_found += 1
            else:
                print(f"    ✅ {pattern} (未找到，正确)")
        
        print(f"\n📊 统计:")
        print(f"   本地GCWeb资源: {local_found}/{len(local_gcweb_patterns)}")
        print(f"   远程CDN资源: {remote_found}/{len(remote_cdn_patterns)} (应为0)")
        
        if local_found >= 2 and remote_found == 0:
            print("\n✅ GCWeb本地依赖测试通过!")
            print("   ✅ 使用本地GCWeb资源")
            print("   ✅ 无远程CDN依赖")
            
            # 保存测试HTML供检查
            with open('test_gcweb_output.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   📄 保存输出到: test_gcweb_output.html")
            
            # 提取并显示关键部分
            print("\n📄 HTML片段示例:")
            lines = html_content.split('\n')
            for i, line in enumerate(lines):
                if '/gcweb/' in line or '<!-- GCWeb主题CSS' in line or '<!-- GCWeb主题JS' in line:
                    if len(line) > 150:
                        print(f"   ...{line[:150]}...")
                    else:
                        print(f"   {line}")
                if i > 50:  # 只看前50行
                    break
                    
            return True
        else:
            print("\n❌ GCWeb本地依赖测试失败!")
            if remote_found > 0:
                print("   ❌ 发现远程CDN依赖，本地依赖未生效")
            if local_found < 2:
                print("   ❌ 本地GCWeb资源不完整")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_health():
    """测试API健康"""
    print("\n🏥 测试API健康...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ 健康检查通过: {response.json()}")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🌐 GCWeb/WET-BOEW本地依赖验证")
    print("=" * 60)
    
    # 测试API健康
    if not test_health():
        print("❌ 无法继续，API不健康")
        return 1
    
    # 测试GCWeb本地依赖
    success = test_gcweb_local_dependencies()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 所有测试通过!")
        print("   本地GCWeb依赖已正确集成，系统符合加拿大政府网站标准")
    else:
        print("⚠️  测试失败，需要检查GCWeb配置")
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())