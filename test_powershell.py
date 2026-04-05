#!/usr/bin/env python3
import subprocess

# 使用PowerShell
tool_dir_win = r'C:\Program Files (x86)\PageTech\PCLTSDK_870'
input_dir_win = r'C:\workspace\sample'
input_file = '00000001.pcl'
output_file = 'test_ps.pdf'

# PowerShell命令
ps_command = f'& "{tool_dir_win}\\PclXform.exe" "{tool_dir_win}\\default.tpt" inp="{input_dir_win}" inf="{input_file}" outp="{input_dir_win}" outf="{output_file}"'
cmd = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-Command', ps_command]

print(f"命令: {' '.join(cmd)}")
try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15
    )
    print(f"返回码: {result.returncode}")
    if result.stdout:
        print(f"标准输出: {result.stdout[:300]}")
    if result.stderr:
        print(f"标准错误: {result.stderr[:300]}")
except subprocess.TimeoutExpired:
    print("超时")
except Exception as e:
    print(f"错误: {e}")

# 使用Start-Process
print("\n=== 使用Start-Process ===")
ps_command2 = f'Start-Process -FilePath "{tool_dir_win}\\PclXform.exe" -ArgumentList "\\"{tool_dir_win}\\default.tpt\\"", \\"inp={input_dir_win}\\", \\"inf={input_file}\\", \\"outp={input_dir_win}\\", \\"outf={output_file}\\" -Wait -NoNewWindow'
cmd2 = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-Command', ps_command2]
print(f"命令: {' '.join(cmd2)}")
try:
    result = subprocess.run(
        cmd2,
        capture_output=True,
        text=True,
        timeout=15
    )
    print(f"返回码: {result.returncode}")
    if result.stdout:
        print(f"标准输出: {result.stdout[:300]}")
    if result.stderr:
        print(f"标准错误: {result.stderr[:300]}")
except subprocess.TimeoutExpired:
    print("超时")
except Exception as e:
    print(f"错误: {e}")