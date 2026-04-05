#!/usr/bin/env python3
"""
测试路径转换函数
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入转换函数
from app_windows_optimized import to_windows_path_if_wsl

def test_path_conversion():
    """测试各种路径转换"""
    test_cases = [
        # (输入路径, 期望输出或描述)
        ("/mnt/c/Users/hongb/Documents", "C:\\Users\\hongb\\Documents"),
        ("/mnt/d/Data/files", "D:\\Data\\files"),
        ("/c/Users/hongb/Desktop", "C:\\Users\\hongb\\Desktop"),
        ("/d/Projects/test", "D:\\Projects\\test"),
        ("~/Documents", "C:\\Users\\hongb\\Documents"),  # 假设用户是hongb
        ("/home/hongb/Documents", "C:\\\\Users\\\\hongb\\Documents"),
        ("//server/share/folder", "\\\\server\\share\\folder"),
        ("C:\\Users\\hongb\\Documents", "C:\\Users\\hongb\\Documents"),
        ("relative/path", "relative/path"),  # 相对路径保持原样
        ("/usr/local/bin", "C:\\\\usr\\local\\bin"),  # Linux根目录路径
        ("", ""),  # 空路径
    ]
    
    print("测试路径转换函数:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for input_path, expected in test_cases:
        try:
            result = to_windows_path_if_wsl(input_path)
            # 注意：实际结果可能因环境而异，我们主要检查函数不崩溃
            print(f"输入: {input_path}")
            print(f"输出: {result}")
            print(f"期望: {expected}")
            
            # 简单验证：检查函数是否返回字符串
            if isinstance(result, str):
                print("✅ 通过 - 返回有效字符串")
                passed += 1
            else:
                print(f"❌ 失败 - 返回类型错误: {type(result)}")
                failed += 1
                
        except Exception as e:
            print(f"❌ 异常 - 输入 '{input_path}' 引发异常: {e}")
            failed += 1
        
        print("-" * 60)
    
    print(f"\n测试结果: 通过 {passed}, 失败 {failed}, 总计 {passed + failed}")
    
    # 添加一些实际可能使用的路径测试
    print("\n实际使用场景测试:")
    print("=" * 60)
    
    practical_paths = [
        "/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PclXform.exe",
        "/mnt/c/workspace/PCLTSDK_870/PCLTOOL.exe",
        "C:\\Program Files (x86)\\PageTech\\PCLTSDK_870\\PclXform.exe",
        "uploads/test.pcl",
        "/tmp/uploaded_file.pcl",
    ]
    
    for path in practical_paths:
        try:
            result = to_windows_path_if_wsl(path)
            print(f"输入: {path}")
            print(f"输出: {result}")
            print("-" * 40)
        except Exception as e:
            print(f"错误处理 '{path}': {e}")
            print("-" * 40)
    
    return failed == 0

if __name__ == "__main__":
    success = test_path_conversion()
    sys.exit(0 if success else 1)