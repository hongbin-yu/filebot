#!/usr/bin/env python3
"""
测试图片文件公开访问
"""
import requests
import sys

BASE_URL = "http://localhost:8001"
TEST_PATH = "/content/dam/cra-arc/camp-promo/features/cvtp_bnnr_360x203.jpg"

def test_public_access():
    """测试无需认证的图片访问"""
    
    print(f"测试公开访问: {TEST_PATH}")
    url = f"{BASE_URL}/api/v1/documents/by-path{TEST_PATH}"
    
    try:
        # 不发送认证头
        response = requests.get(url, allow_redirects=False)
        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Content-Length: {response.headers.get('Content-Length')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'image' in content_type:
                print(f"✅ 成功获取图片! 大小: {len(response.content)} 字节")
                # 保存测试文件
                with open('/tmp/test_public_image.jpg', 'wb') as f:
                    f.write(response.content)
                print(f"测试图片保存到: /tmp/test_public_image.jpg")
                
                # 检查文件头
                if len(response.content) >= 2:
                    file_header = response.content[:2].hex()
                    if file_header == 'ffd8':
                        print(f"✅ 文件头正确: {file_header} (JPEG)")
                    else:
                        print(f"⚠️  文件头异常: {file_header}")
                
                return True
            else:
                print(f"⚠️  响应不是图片: {content_type}")
                print(f"前100字节: {response.content[:100]}")
                return False
        else:
            print(f"❌ 错误响应: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_auth():
    """测试带认证的访问（对比）"""
    print(f"\n测试带认证访问: {TEST_PATH}")
    
    # 登录获取token
    form_data = {"username": "admin", "password": "admin123"}
    login_url = f"{BASE_URL}/api/v1/auth/login"
    
    try:
        response = requests.post(login_url, data=form_data)
        response.raise_for_status()
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        url = f"{BASE_URL}/api/v1/documents/by-path{TEST_PATH}"
        response = requests.get(url, headers=headers, allow_redirects=False)
        
        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"大小: {len(response.content)} 字节")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"认证测试失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("测试图片文件公开访问")
    print("=" * 60)
    
    print("\n1. 测试无需认证访问:")
    public_success = test_public_access()
    
    print("\n2. 测试带认证访问:")
    auth_success = test_with_auth()
    
    print("\n" + "=" * 60)
    if public_success:
        print("✅ 公开访问测试成功!")
    else:
        print("❌ 公开访问测试失败!")
    
    if auth_success:
        print("✅ 认证访问测试成功!")
    else:
        print("❌ 认证访问测试失败!")
    print("=" * 60)
    
    sys.exit(0 if public_success else 1)