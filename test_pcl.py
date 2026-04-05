#!/usr/bin/env python3
import subprocess
import os
import sys
import time

def to_windows_path_if_wsl(path):
    """如果是WSL路径，转换为Windows路径"""
    if path.startswith('/mnt/c/'):
        win_path = 'C:' + path[6:].replace('/', '\\')
        return win_path
    elif path.startswith('/mnt/'):
        drive = path[5:6].upper()
        win_path = f'{drive}:' + path[7:].replace('/', '\\')
        return win_path
    else:
        return path

# 路径配置
tool_cmd = r'/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/PclXform.exe'
template_path = r'/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870/default.tpt'
input_file = '00000001.pcl'
input_dir = r'/mnt/c/workspace/sample'
output_file = 'test_python.pdf'
output_dir = r'/mnt/c/workspace/pcl-converted'

# 构建完整路径
input_path = os.path.join(input_dir, input_file)
output_path = os.path.join(output_dir, output_file)

# 转换为Windows格式
tool_cmd_win = to_windows_path_if_wsl(tool_cmd)
template_path_win = to_windows_path_if_wsl(template_path)
input_dir_win = to_windows_path_if_wsl(input_dir)
output_dir_win = to_windows_path_if_wsl(output_dir)

# 构建命令
dos_command = f'"{tool_cmd_win}" "{template_path_win}" inp="{input_file}" inf="{input_dir_win}" outp="{output_file}" outf="{output_dir_win}" Silent=true'
cmd = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command]

print(f"工具: {tool_cmd_win}")
print(f"模板: {template_path_win}")
print(f"输入文件: {input_file}")
print(f"输入目录: {input_dir_win}")
print(f"输出文件: {output_file}")
print(f"输出目录: {output_dir_win}")
print(f"命令: {dos_command}")
print(f"完整命令: {' '.join(cmd)}")
print()

# 检查输入文件是否存在
if not os.path.exists(input_path):
    print(f"错误: 输入文件不存在: {input_path}")
    sys.exit(1)

print(f"输入文件大小: {os.path.getsize(input_path)} 字节")

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 运行转换
print("开始转换...")
start_time = time.time()

# 设置工作目录为工具所在目录的WSL路径（避免UNC路径错误）
tool_dir_wsl = os.path.dirname(tool_cmd)
cwd = tool_dir_wsl
print(f"工作目录(WSL): {cwd}")

try:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30
    )
    elapsed = time.time() - start_time
    
    print(f"返回码: {result.returncode}")
    print(f"耗时: {elapsed:.2f}秒")
    if result.stdout:
        print(f"标准输出: {result.stdout}")
    if result.stderr:
        print(f"标准错误: {result.stderr}")
    
    # 检查输出文件
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f"成功: 输出文件已创建: {output_path} ({size} 字节)")
    else:
        print(f"警告: 输出文件未创建: {output_path}")
        # 检查输出目录内容
        print(f"输出目录内容: {os.listdir(output_dir)}")
        
except subprocess.TimeoutExpired:
    print("错误: 转换超时 (30秒)")
except Exception as e:
    print(f"错误: {e}")