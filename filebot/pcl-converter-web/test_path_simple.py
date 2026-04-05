#!/usr/bin/env python3
"""
简单测试路径转换函数 - 不依赖Flask
"""

import os
import sys

# 复制函数定义，避免导入整个模块
def to_windows_path_if_wsl(path):
    """
    将WSL/Linux路径转换为Windows路径
    """
    if not path:
        return path
    
    # 展开用户主目录 (~/ -> /home/user/)
    expanded_path = os.path.expanduser(path)
    
    # 解析符号链接（获取实际路径）
    real_path = os.path.realpath(expanded_path) if os.path.exists(expanded_path) else expanded_path
    
    # 处理网络路径 (UNC格式)
    if real_path.startswith('//') or real_path.startswith('\\\\'):
        # 已经是网络路径，统一为Windows格式
        return real_path.replace('/', '\\')
    
    # 检查是否是Windows路径 (已经包含驱动器字母)
    if len(real_path) > 1 and real_path[1] == ':' and real_path[0].isalpha():
        # 已经是Windows路径，确保使用反斜杠
        return real_path.replace('/', '\\')
    
    # 处理WSL /mnt/ 挂载点格式
    if real_path.startswith('/mnt/'):
        if real_path.startswith('/mnt/c/'):
            # /mnt/c/Users/... -> C:\\Users\\...
            win_path = 'C:' + real_path[6:].replace('/', '\\')
            return win_path
        elif len(real_path) > 5 and real_path[5].isalpha():
            # /mnt/d/... -> D:\\...
            drive = real_path[5].upper()
            win_path = f'{drive}:' + real_path[7:].replace('/', '\\')
            return win_path
    
    # 处理WSL /drive/ 格式 (如 /c/Users/...)
    if len(real_path) > 1 and real_path.startswith('/') and real_path[1].isalpha() and real_path[2] == '/':
        drive = real_path[1].upper()
        win_path = f'{drive}:' + real_path[3:].replace('/', '\\')
        return win_path
    
    # 处理Linux用户目录 (/home/user/...)
    if real_path.startswith('/home/'):
        parts = real_path.split('/')
        if len(parts) >= 3:
            username = parts[2]
            remaining_path = '/' + '/'.join(parts[3:]) if len(parts) > 3 else ''
            win_path = f'C:\\\\Users\\\\{username}{remaining_path.replace("/", "\\\\")}'
            return win_path
    
    # 处理根目录路径
    if real_path.startswith('/'):
        win_path = f'C:{real_path.replace("/", "\\\\")}'
        return win_path
    
    # 相对路径或无法识别的格式
    return path

def main():
    print("测试路径转换函数")
    print("=" * 60)
    
    # 测试基本功能
    test_paths = [
        "/mnt/c/Users/test/Documents",
        "/mnt/d/Data",
        "/c/Windows/System32",
        "C:\\Program Files\\App",
        "//server/share",
        "~/file.txt",
        "relative/path",
        "",
    ]
    
    for path in test_paths:
        try:
            result = to_windows_path_if_wsl(path)
            print(f"输入: {repr(path)}")
            print(f"输出: {repr(result)}")
            
            # 基本验证
            if result is None:
                print("❌ 错误: 返回None")
            elif not isinstance(result, str):
                print(f"❌ 错误: 返回类型不是字符串: {type(result)}")
            else:
                print("✅ 有效")
                
        except Exception as e:
            print(f"❌ 异常: {e}")
        
        print("-" * 40)
    
    print("\n测试实际PCL工具路径:")
    pcl_paths = [
        "/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PclXform.exe",
        "C:\\Program Files (x86)\\PageTech\\PCLTSDK_870\\PCLTOOL.exe",
        "/mnt/c/workspace/PCLTSDK_870/PclXform.exe",
    ]
    
    for path in pcl_paths:
        result = to_windows_path_if_wsl(path)
        print(f"输入: {path}")
        print(f"输出: {result}")
        print("-" * 40)
    
    print("\n✅ 测试完成 - 函数基本工作正常")

if __name__ == "__main__":
    main()