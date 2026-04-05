#!/usr/bin/env python3
import subprocess
import os

# 使用cd命令切换到工具目录然后执行
tool_dir_win = r'C:\Program Files (x86)\PageTech\PCLTSDK_870'
dos_command = f'cd /d "{tool_dir_win}" && PclXform.exe "default.tpt" inp="C:\workspace\sample" inf="00000001.pcl" outp="C:\workspace\sample" outf="test_cd.pdf"'
cmd = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command]

print(f"命令: {' '.join(cmd)}")
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

# 使用完整路径
print("\n=== 使用完整路径 ===")
dos_command2 = f'"{tool_dir_win}\\PclXform.exe" "{tool_dir_win}\\default.tpt" inp="C:\\workspace\\sample" inf="00000001.pcl" outp="C:\\workspace\\sample" outf="test_fullpath.pdf"'
cmd2 = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command2]
print(f"命令: {' '.join(cmd2)}")
try:
    result = subprocess.run(
        cmd2,
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

# 使用wslpath转换工作目录
print("\n=== 使用wslpath转换cwd ===")
tool_dir_wsl = r'/mnt/c/Program Files (x86)/PageTech/PCLTSDK_870'
# 获取Windows路径
result = subprocess.run(['wslpath', '-w', tool_dir_wsl], capture_output=True, text=True)
if result.returncode == 0:
    tool_dir_win_wslpath = result.stdout.strip()
    print(f"WSL路径: {tool_dir_wsl}")
    print(f"Windows路径 (wslpath): {tool_dir_win_wslpath}")
    
    dos_command3 = f'PclXform.exe "default.tpt" inp="C:\\workspace\\sample" inf="00000001.pcl" outp="C:\\workspace\\sample" outf="test_wslpath.pdf"'
    cmd3 = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command3]
    print(f"命令: {' '.join(cmd3)}")
    print(f"cwd (WSL): {tool_dir_wsl}")
    try:
        result = subprocess.run(
            cmd3,
            cwd=tool_dir_wsl,
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