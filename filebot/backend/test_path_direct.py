#!/usr/bin/env python3
"""
直接测试路径映射API - 不跟随重定向
"""
import requests
import sys

BASE_URL = "http://localhost:8001"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
TEST_PATH = "/content/dam/cra-arc/camp-promo/features/cvtp_bnnr_360x203.jpg"

def get_auth_token():
    """获取认证token"""
    form_data = {"username": "admin", "password": "admin123"}
    response = requests.post(LOGIN_URL, data=form_data)
    response.raise_for_status()
    return response.json()["access_token"]

def main():
    print("测试直接路径映射...")
    
    try:
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        url = f"{BASE_URL}/api/v1/documents/by-path{TEST_PATH}"
        print(f"请求URL: {url}")
        
        response = requests.get(url, headers=headers, allow_redirects=False)
        
        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Content-Disposition: {response.headers.get('Content-Disposition')}")
        print(f"Content-Length: {response.headers.get('Content-Length')}")
        
        if response.status_code == 200:
            # 检查是否是图片
            content_type = response.headers.get('Content-Type', '')
            if 'image' in content_type:
                print(f"✅ 成功获取图片! 大小: {len(response.content)} 字节")
                # 保存测试文件
                with open('/tmp/test_image.jpg', 'wb') as f:
                    f.write(response.content)
                print(f"测试图片保存到: /tmp/test_image.jpg")
                return True
            else:
                print(f"⚠️  响应不是图片: {content_type}")
                print(f"前100字节: {response.content[:100]}")
                return False
        else:
            print(f"❌ 错误响应: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)