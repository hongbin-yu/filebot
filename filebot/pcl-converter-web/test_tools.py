#!/usr/bin/env python3
"""
测试PCL工具检测功能
"""

import os
import sys
import subprocess
import platform

def detect_pcl_tools_basic():
    """基础版工具检测"""
    tools_to_check = [
        ('gpcl6', ['gpcl6', 'gpcl6.exe']),
        ('pcl6', ['pcl6', 'pcl6.exe']),
        ('gs', ['gs', 'gswin64c.exe', 'gswin32c.exe']),
        ('pcltopdf', ['pcltopdf', 'pcltopdf.exe']),
        ('pcl2pdf', ['pcl2pdf', 'pcl2pdf.exe']),
        ('pdftopcl', ['pdftopcl', 'pdftopcl.exe']),
    ]
    
    # 添加hplip工具
    hplip_tools = [
        ('pclmtoraster', ['pclmtoraster']),
        ('rastertopclx', ['rastertopclx']),
        ('commandtopclx', ['commandtopclx']),
        ('ippevepcl', ['ippevepcl']),
    ]
    
    detected_tools = []
    
    print("=" * 60)
    print("PCL工具检测报告")
    print("=" * 60)
    print(f"系统平台: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    print()
    
    # 检查标准工具
    print("1. 标准PCL转换工具:")
    for tool_name, tool_commands in tools_to_check:
        found = False
        for cmd in tool_commands:
            try:
                result = subprocess.run(
                    ['which', cmd] if not cmd.endswith('.exe') else ['where', cmd],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    path = result.stdout.strip()
                    print(f"   ✓ {tool_name}: {path}")
                    
                    # 尝试获取版本
                    try:
                        ver_result = subprocess.run(
                            [cmd, '--version'] if '--version' in tool_name else [cmd, '-v'],
                            capture_output=True,
                            text=True,
                            timeout=3
                        )
                        version = ver_result.stdout[:50].strip() if ver_result.stdout else "版本未知"
                        if version:
                            print(f"       版本: {version}")
                    except:
                        pass
                    
                    found = True
                    break
            except:
                continue
        
        if not found:
            print(f"   ✗ {tool_name}: 未找到")
    
    print()
    
    # 检查hplip工具
    print("2. hplip工具 (HP打印系统):")
    for tool_name, tool_commands in hplip_tools:
        found = False
        for cmd in tool_commands:
            try:
                result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    path = result.stdout.strip()
                    print(f"   ✓ {tool_name}: {path}")
                    found = True
                    break
            except:
                continue
        
        if not found:
            print(f"   ✗ {tool_name}: 未找到")
    
    print()
    
    # 检查文件系统
    print("3. 系统工具搜索:")
    search_paths = [
        '/usr/bin',
        '/usr/local/bin', 
        '/usr/lib/cups/filter',
        '/usr/sbin',
        '/usr/lib/cups/backend',
        '/mnt/c/Program Files',
        '/mnt/c/Program Files (x86)',
        '/mnt/c/Windows/System32'
    ]
    
    pcl_tools_found = []
    for search_path in search_paths:
        if os.path.exists(search_path):
            try:
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        if 'pcl' in file.lower():
                            full_path = os.path.join(root, file)
                            pcl_tools_found.append((file, full_path))
            except:
                continue
    
    if pcl_tools_found:
        print("   发现以下PCL相关文件:")
        for file, path in pcl_tools_found[:10]:  # 显示前10个
            print(f"   • {file}: {path}")
        if len(pcl_tools_found) > 10:
            print(f"   ... 还有 {len(pcl_tools_found) - 10} 个文件")
    else:
        print("   未发现PCL相关文件")
    
    print()
    
    # 测试文件检查
    test_file = "/mnt/c/workspace/sample/00000001.pcl"
    print("4. 测试文件检查:")
    if os.path.exists(test_file):
        size = os.path.getsize(test_file)
        print(f"   ✓ 测试文件存在: {test_file}")
        print(f"     文件大小: {size} bytes ({size/1024:.1f} KB)")
        
        # 检查文件类型
        try:
            with open(test_file, 'rb') as f:
                header = f.read(100)
                hex_header = header.hex()[:50]
                print(f"     文件头部(hex): {hex_header}...")
                
                # 简单PCL识别
                if b'PCL' in header or b'\x1b' in header:  # ESC字符是PCL常见
                    print("     → 可能包含PCL命令序列")
        except:
            print("     无法读取文件头部")
    else:
        print(f"   ✗ 测试文件不存在: {test_file}")
    
    print()
    
    # 环境检查
    print("5. 环境检查:")
    print(f"   PATH环境变量包含 {len(os.environ.get('PATH', '').split(':'))} 个目录")
    
    # 检查hplip包
    try:
        result = subprocess.run(['dpkg', '-s', 'hplip'], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✓ hplip包已安装")
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    print(f"     版本: {line.split(':')[1].strip()}")
        else:
            print("   ✗ hplip包未安装")
    except:
        print("   ? 无法检查hplip包状态")
    
    # 检查ghostscript
    try:
        result = subprocess.run(['dpkg', '-s', 'ghostscript'], capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✓ ghostscript包已安装")
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    print(f"     版本: {line.split(':')[1].strip()}")
        else:
            print("   ✗ ghostscript包未安装")
    except:
        print("   ? 无法检查ghostscript包状态")
    
    print("=" * 60)
    print("检测完成")
    print("=" * 60)

if __name__ == '__main__':
    detect_pcl_tools_basic()