#!/usr/bin/env python3
"""
下载加拿大政府网站(canada.ca)使用的GCWeb/WET-BOEW依赖文件
用于本地对比和系统验证
"""

import os
import sys
import requests
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import time

# 创建必要的目录
def ensure_dir(directory):
    """确保目录存在"""
    Path(directory).mkdir(parents=True, exist_ok=True)
    print(f"✓ 目录已创建/确认: {directory}")

# 下载文件函数
def download_file(url, save_path, retry=3):
    """下载文件并保存到指定路径"""
    try:
        print(f"正在下载: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # 检查HTTP错误
        
        # 保存文件
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        # 计算文件哈希
        file_hash = hashlib.md5(response.content).hexdigest()
        file_size = len(response.content) / 1024  # KB
        
        print(f"✓ 下载完成: {save_path} ({file_size:.1f} KB, MD5: {file_hash[:8]})")
        return True
        
    except requests.exceptions.RequestException as e:
        if retry > 0:
            print(f"下载失败，重试中... ({retry}次剩余)")
            time.sleep(2)
            return download_file(url, save_path, retry - 1)
        else:
            print(f"✗ 下载失败: {url}")
            print(f"错误: {e}")
            return False

# 主要的GCWeb资源列表 (与canada.ca保持一致)
GCWEB_RESOURCES = [
    # CSS文件
    {
        "url": "https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/css/theme.min.css",
        "local_path": "static/gcweb/GCWeb/css/theme.min.css",
        "description": "GCWeb主题主CSS (压缩版)"
    },
    {
        "url": "https://wet-boew.github.io/themes-dist/GCWeb/wet-boew/css/noscript.min.css",
        "local_path": "static/gcweb/wet-boew/css/noscript.min.css",
        "description": "无JavaScript支持时的备用CSS"
    },
    
    # JavaScript文件
    {
        "url": "https://ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js",
        "local_path": "static/external/jquery/2.2.4/jquery.min.js",
        "description": "jQuery 2.2.4 (Google CDN)"
    },
    {
        "url": "https://wet-boew.github.io/themes-dist/GCWeb/wet-boew/js/wet-boew.min.js",
        "local_path": "static/gcweb/wet-boew/js/wet-boew.min.js",
        "description": "WET-BOEW核心JavaScript (压缩版)"
    },
    {
        "url": "https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/js/theme.min.js",
        "local_path": "static/gcweb/GCWeb/js/theme.min.js",
        "description": "GCWeb主题JavaScript (压缩版)"
    },
    
    # Font Awesome (可选)
    {
        "url": "https://use.fontawesome.com/releases/v5.8.1/css/all.css",
        "local_path": "static/external/font-awesome/5.8.1/css/all.css",
        "description": "Font Awesome图标库"
    },
    
    # 额外的验证文件 (从canada.ca首页获取)
    {
        "url": "https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/css/theme.css",
        "local_path": "static/gcweb/GCWeb/css/theme.css",
        "description": "GCWeb主题主CSS (未压缩版，用于对比)"
    },
    {
        "url": "https://wet-boew.github.io/themes-dist/GCWeb/wet-boew/js/wet-boew.js",
        "local_path": "static/gcweb/wet-boew/js/wet-boew.js",
        "description": "WET-BOEW核心JavaScript (未压缩版)"
    },
]

# 加拿大政府网站canada.ca的示例页面
CANADA_CA_RESOURCES = [
    {
        "url": "https://www.canada.ca/content/dam/canada/sitemenu/sitemenu-v2-en.html",
        "local_path": "static/canada-ca/sitemenu-v2-en.html",
        "description": "Canada.ca站点菜单模板"
    },
    {
        "url": "https://www.canada.ca/etc/designs/canada/wet-boew/assets/favicon.ico",
        "local_path": "static/canada-ca/favicon.ico",
        "description": "Canada.ca网站图标"
    }
]

def main():
    """主函数：下载所有资源"""
    print("=" * 70)
    print("加拿大政府网站(GCWeb/WET-BOEW)依赖文件下载工具")
    print("=" * 70)
    
    # 确定工作目录
    script_dir = Path(__file__).parent
    print(f"工作目录: {script_dir}")
    
    # 下载计数器
    success_count = 0
    fail_count = 0
    
    # 下载GCWeb资源
    print("\n" + "=" * 70)
    print("下载GCWeb/WET-BOEW官方资源")
    print("=" * 70)
    
    for resource in GCWEB_RESOURCES:
        local_path = script_dir / resource["local_path"]
        
        # 确保目录存在
        ensure_dir(local_path.parent)
        
        # 下载文件
        if download_file(resource["url"], local_path):
            success_count += 1
        else:
            fail_count += 1
        
        # 稍微延迟，避免请求过快
        time.sleep(0.5)
    
    # 尝试下载Canada.ca资源 (可能被限制访问)
    print("\n" + "=" * 70)
    print("尝试下载Canada.ca示例资源 (可能受访问限制)")
    print("=" * 70)
    
    for resource in CANADA_CA_RESOURCES:
        local_path = script_dir / resource["local_path"]
        
        # 确保目录存在
        ensure_dir(local_path.parent)
        
        # 下载文件
        if download_file(resource["url"], local_path):
            success_count += 1
        else:
            fail_count += 1
            print("注意: Canada.ca资源可能受CORS或访问限制")
        
        # 稍微延迟
        time.sleep(1)
    
    # 生成对比报告
    print("\n" + "=" * 70)
    print("下载完成统计")
    print("=" * 70)
    print(f"成功: {success_count} 个文件")
    print(f"失败: {fail_count} 个文件")
    
    if success_count > 0:
        print("\n已下载文件位置:")
        for resource in GCWEB_RESOURCES:
            local_path = script_dir / resource["local_path"]
            if local_path.exists():
                size_kb = local_path.stat().st_size / 1024
                print(f"  • {resource['local_path']} ({size_kb:.1f} KB) - {resource['description']}")
    
    # 创建验证脚本
    create_verification_script(script_dir)
    
    print("\n✓ 下载完成！")
    print("您可以使用以下命令验证下载的文件:")
    print(f"  cd {script_dir}")
    print("  python verify_gcweb_deps.py")
    
    return 0 if fail_count == 0 else 1

def create_verification_script(script_dir):
    """创建验证脚本"""
    verification_script = script_dir / "verify_gcweb_deps.py"
    
    script_content = '''#!/usr/bin/env python3
"""
验证下载的GCWeb依赖文件与远程文件的一致性
"""

import os
import hashlib
import requests
from pathlib import Path

def get_file_hash(filepath):
    """计算文件MD5哈希"""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_file(local_path, remote_url, description):
    """验证本地文件与远程文件是否一致"""
    print(f"验证: {description}")
    print(f"  本地: {local_path}")
    print(f"  远程: {remote_url}")
    
    if not Path(local_path).exists():
        print("  ✗ 本地文件不存在")
        return False
    
    try:
        # 获取远程文件
        response = requests.get(remote_url, timeout=10)
        remote_hash = hashlib.md5(response.content).hexdigest()
        
        # 计算本地文件哈希
        local_hash = get_file_hash(local_path)
        
        # 比较
        if remote_hash == local_hash:
            print(f"  ✓ 文件一致 (MD5: {local_hash[:8]}...)")
            return True
        else:
            print(f"  ✗ 文件不一致 (本地: {local_hash[:8]}, 远程: {remote_hash[:8]})")
            return False
            
    except Exception as e:
        print(f"  ✗ 验证失败: {e}")
        return False

def main():
    print("GCWeb依赖文件验证工具")
    print("=" * 60)
    
    script_dir = Path(__file__).parent
    
    # 需要验证的文件列表
    files_to_verify = [
        {
            "local": "static/gcweb/GCWeb/css/theme.min.css",
            "remote": "https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/css/theme.min.css",
            "desc": "GCWeb主题CSS"
        },
        {
            "local": "static/gcweb/wet-boew/js/wet-boew.min.js", 
            "remote": "https://wet-boew.github.io/themes-dist/GCWeb/wet-boew/js/wet-boew.min.js",
            "desc": "WET-BOEW核心JS"
        },
        {
            "local": "static/gcweb/GCWeb/js/theme.min.js",
            "remote": "https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/js/theme.min.js",
            "desc": "GCWeb主题JS"
        }
    ]
    
    verified = 0
    total = len(files_to_verify)
    
    for file_info in files_to_verify:
        local_path = script_dir / file_info["local"]
        success = verify_file(local_path, file_info["remote"], file_info["desc"])
        if success:
            verified += 1
        print()
    
    print(f"验证完成: {verified}/{total} 个文件通过验证")
    
    if verified == total:
        print("✓ 所有文件与远程源一致")
    else:
        print("⚠️ 部分文件不一致，请重新下载")

if __name__ == "__main__":
    main()
'''
    
    with open(verification_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # 设置执行权限
    verification_script.chmod(0o755)
    print(f"✓ 验证脚本已创建: {verification_script}")

if __name__ == "__main__":
    sys.exit(main())