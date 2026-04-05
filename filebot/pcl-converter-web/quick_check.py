#!/usr/bin/env python3
import os
import subprocess
import platform

print("=== 快速PCL工具检查 ===")
print(f"系统: {platform.system()} {platform.release()}")
print()

# 检查ghostscript
print("1. Ghostscript检查:")
try:
    result = subprocess.run(['gs', '--version'], capture_output=True, text=True, timeout=3)
    if result.returncode == 0:
        print(f"   ✓ gs: {result.stdout.strip()}")
    else:
        print("   ✗ gs命令执行失败")
except FileNotFoundError:
    print("   ✗ gs未找到")
except Exception as e:
    print(f"   ? gs检查错误: {e}")
print()

# 检查hplip工具
print("2. hplip工具检查:")
hplip_tools = ['pclmtoraster', 'rastertopclx', 'commandtopclx', 'ippevepcl']
for tool in hplip_tools:
    try:
        result = subprocess.run(['which', tool], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print(f"   ✓ {tool}: {result.stdout.strip()}")
        else:
            print(f"   ✗ {tool}: 未找到")
    except Exception as e:
        print(f"   ? {tool}: 检查失败 - {e}")
print()

# 检查Windows PCL工具
print("3. Windows PCL工具检查:")
windows_tools = ['pcl6.exe', 'gpcl6.exe', 'pcltopdf.exe']
for tool in windows_tools:
    try:
        # 在WSL中查找Windows工具
        result = subprocess.run(['find', '/mnt/c', '-name', tool, '-type', 'f', '2>/dev/null'], 
                              shell=True, capture_output=True, text=True, timeout=5)
        if result.stdout.strip():
            paths = result.stdout.strip().split('\n')
            for path in paths[:3]:  # 显示前3个
                print(f"   ✓ {tool}: {path}")
        else:
            print(f"   ✗ {tool}: 未找到")
    except Exception as e:
        print(f"   ? {tool}: 检查失败 - {e}")
print()

# 检查测试文件
test_file = "/mnt/c/workspace/sample/00000001.pcl"
print(f"4. 测试文件检查: {test_file}")
if os.path.exists(test_file):
    size = os.path.getsize(test_file)
    print(f"   ✓ 文件存在, 大小: {size} bytes")
    
    # 尝试读取文件头部
    try:
        with open(test_file, 'rb') as f:
            header = f.read(100)
            # 检查PCL特征
            if b'\x1b' in header:  # ESC字符
                print("   → 包含ESC字符 (PCL常见)")
            if b'PCL' in header:
                print("   → 包含'PCL'文本")
            # 显示部分十六进制
            hex_preview = header[:20].hex()
            print(f"   → 头部(hex): {hex_preview}...")
    except Exception as e:
        print(f"   → 无法读取文件: {e}")
else:
    print("   ✗ 文件不存在")
print()

print("=== 检查完成 ===")