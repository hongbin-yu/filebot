#!/usr/bin/env python3
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
