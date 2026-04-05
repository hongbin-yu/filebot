#!/usr/bin/env python3
import os
import sys
import subprocess

# 模拟转换函数的关键部分
def to_windows_path_if_wsl(path):
    """如果是WSL路径，转换为Windows路径"""
    if path.startswith('/mnt/c/'):
        # /mnt/c/Users/... -> C:\Users\...
        win_path = 'C:' + path[6:].replace('/', '\\')
        return win_path
    elif path.startswith('/mnt/'):
        # 其他驱动器，如/mnt/d/ -> D:\
        drive = path[5:6].upper()  # 获取驱动器字母
        win_path = f'{drive}:' + path[7:].replace('/', '\\')
        return win_path
    else:
        # 已经是Windows路径或相对路径
        return path

# 测试参数
tool_cmd = r'/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PclXform.exe'
input_path = r'/mnt/c/workspace/sample/00000001.pcl'
output_path = r'/mnt/c/workspace/sample/test_web.pdf'

# 模拟转换函数逻辑
input_dir = os.path.dirname(input_path)
input_file = os.path.basename(input_path)
output_dir = os.path.dirname(output_path)
output_file = os.path.basename(output_path)

tool_dir = os.path.dirname(tool_cmd)
template_path = os.path.join(tool_dir, 'default.tpt')

# 转换为Windows格式
tool_cmd_win = to_windows_path_if_wsl(tool_cmd)
template_path_win = to_windows_path_if_wsl(template_path)
input_dir_win = to_windows_path_if_wsl(input_dir)
output_dir_win = to_windows_path_if_wsl(output_dir)

# 构建命令（用户验证的格式）
dos_command = f'"{tool_cmd_win}" "{template_path_win}" inp="{input_dir_win}" inf="{input_file}" outp="{output_dir_win}" outf="{output_file}" Silent=true'
cmd = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command]

print("=== 模拟转换命令 ===")
print(f"工具路径 (WSL): {tool_cmd}")
print(f"工具路径 (Windows): {tool_cmd_win}")
print(f"输入文件: {input_file}")
print(f"输入目录 (WSL): {input_dir}")
print(f"输入目录 (Windows): {input_dir_win}")
print(f"输出文件: {output_file}")
print(f"输出目录 (WSL): {output_dir}")
print(f"输出目录 (Windows): {output_dir_win}")
print(f"模板路径: {template_path_win}")
print(f"\nDOS命令: {dos_command}")
print(f"\n完整命令: {' '.join(cmd)}")

# 测试是否可以使用不带工作目录的方式运行
print("\n=== 测试执行（无cwd）===")
try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"返回码: {result.returncode}")
    if result.stdout:
        print(f"标准输出: {result.stdout[:200]}")
    if result.stderr:
        print(f"标准错误: {result.stderr[:200]}")
except subprocess.TimeoutExpired:
    print("超时")
except Exception as e:
    print(f"错误: {e}")

# 测试使用工具目录作为cwd
print("\n=== 测试执行（cwd=tool_dir）===")
cwd = tool_dir  # WSL路径
print(f"工作目录 (WSL): {cwd}")
try:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"返回码: {result.returncode}")
    if result.stdout:
        print(f"标准输出: {result.stdout[:200]}")
    if result.stderr:
        print(f"标准错误: {result.stderr[:200]}")
except subprocess.TimeoutExpired:
    print("超时")
except Exception as e:
    print(f"错误: {e}")

# 测试用户验证的命令格式
print("\n=== 用户验证的命令格式 ===")
user_cmd = ['/mnt/c/Windows/System32/cmd.exe', '/c', 
    '"C:\\Program Files (x86)\\PageTech\\PCLTSDK_870\\PclXform.exe" "C:\\Program Files (x86)\\PageTech\\PCLTSDK_870\\default.tpt" inp="C:\\workspace\\sample" inf="00000001.pcl" outp="C:\\workspace\\sample" outf="test_hongbinyu_cmd.pdf"']
print(f"命令: {' '.join(user_cmd)}")
try:
    result = subprocess.run(
        user_cmd,
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"返回码: {result.returncode}")
    if result.stdout:
        print(f"标准输出: {result.stdout[:200]}")
    if result.stderr:
        print(f"标准错误: {result.stderr[:200]}")
except subprocess.TimeoutExpired:
    print("超时")
except Exception as e:
    print(f"错误: {e}")