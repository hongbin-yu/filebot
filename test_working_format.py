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
output_file = 'test_working.pdf'
output_dir = r'/mnt/c/workspace/sample'  # 根据用户格式，outp应该是输出目录

# 构建完整路径
input_path = os.path.join(input_dir, input_file)
output_path = os.path.join(output_dir, output_file) if output_dir != '' else output_file

# 转换为Windows格式
tool_cmd_win = to_windows_path_if_wsl(tool_cmd)
template_path_win = to_windows_path_if_wsl(template_path)
input_dir_win = to_windows_path_if_wsl(input_dir)
output_dir_win = to_windows_path_if_wsl(output_dir) if output_dir != '' else ''

print("=== 测试用户验证的工作格式 ===")
print(f"工具: {tool_cmd_win}")
print(f"模板: {template_path_win}")
print(f"输入文件: {input_file}")
print(f"输入目录: {input_dir_win}")
print(f"输出文件: {output_file}")
print(f"输出目录: {output_dir_win}")
print()

# 测试不同的格式组合
test_cases = [
    {
        'name': '用户已验证格式',
        'inp': input_dir_win,    # 目录
        'inf': input_file,       # 文件名
        'outp': output_dir_win,  # 目录 (用户命令中 outp="c:\workspace\sample")
        'outf': output_file,     # 文件名 (用户命令中 outf="test_cmd.pdf")
        'description': 'inp=目录, inf=文件名, outp=目录, outf=文件名'
    },
    {
        'name': '传统格式',
        'inp': input_file,       # 文件名
        'inf': input_dir_win,    # 目录
        'outp': output_file,     # 文件名
        'outf': output_dir_win,  # 目录
        'description': 'inp=文件名, inf=目录, outp=文件名, outf=目录'
    },
    {
        'name': '混合格式1',
        'inp': input_dir_win,    # 目录
        'inf': input_file,       # 文件名
        'outp': output_file,     # 文件名
        'outf': output_dir_win,  # 目录
        'description': 'inp=目录, inf=文件名, outp=文件名, outf=目录'
    },
    {
        'name': '混合格式2',
        'inp': input_file,       # 文件名
        'inf': input_dir_win,    # 目录
        'outp': output_dir_win,  # 目录
        'outf': output_file,     # 文件名
        'description': 'inp=文件名, inf=目录, outp=目录, outf=文件名'
    }
]

# 检查输入文件
if not os.path.exists(input_path):
    print(f"错误: 输入文件不存在: {input_path}")
    sys.exit(1)

print(f"输入文件大小: {os.path.getsize(input_path)} 字节")
print()

# 运行所有测试用例
for i, test_case in enumerate(test_cases):
    print(f"\n=== 测试 {i+1}: {test_case['name']} ===")
    print(f"描述: {test_case['description']}")
    
    # 构建命令
    dos_command = f'"{tool_cmd_win}" "{template_path_win}" inp="{test_case["inp"]}" inf="{test_case["inf"]}" outp="{test_case["outp"]}" outf="{test_case["outf"]}" Silent=true'
    cmd = ['/mnt/c/Windows/System32/cmd.exe', '/c', dos_command]
    
    # 设置工作目录
    tool_dir_wsl = os.path.dirname(tool_cmd)
    cwd = tool_dir_wsl
    
    print(f"命令: {dos_command}")
    
    # 运行转换
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=15
        )
        elapsed = time.time() - start_time
        
        print(f"返回码: {result.returncode}")
        print(f"耗时: {elapsed:.2f}秒")
        if result.stdout and result.stdout.strip():
            print(f"标准输出: {result.stdout[:200]}")
        if result.stderr and result.stderr.strip():
            print(f"标准错误: {result.stderr[:200]}")
        
        # 检查输出文件
        # 确定输出文件实际位置（根据参数猜测）
        if test_case['outf'] == output_file and test_case['outp'] == output_dir_win:
            # 用户格式: outf=文件名, outp=目录
            actual_output = os.path.join(output_dir_win, output_file)
        elif test_case['outp'] == output_file and test_case['outf'] == output_dir_win:
            # 传统格式: outp=文件名, outf=目录
            actual_output = os.path.join(output_dir_win, output_file)
        else:
            # 其他情况，假设输出在当前目录
            actual_output = os.path.join(output_dir, output_file)
        
        print(f"检查输出文件: {actual_output}")
        if os.path.exists(actual_output):
            size = os.path.getsize(actual_output)
            print(f"✓ 成功: 输出文件已创建 ({size} 字节)")
        else:
            print(f"✗ 失败: 输出文件未创建")
            # 检查可能的其他位置
            print(f"搜索可能的输出位置...")
            search_dirs = [output_dir, '/mnt/c/workspace/sample', '/mnt/c/workspace/pcl-converted', os.path.dirname(tool_cmd)]
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    files = os.listdir(search_dir)
                    pdf_files = [f for f in files if f.endswith('.pdf')]
                    if pdf_files:
                        print(f"  在 {search_dir} 中找到PDF文件: {pdf_files}")
            
    except subprocess.TimeoutExpired:
        print("错误: 转换超时 (15秒)")
    except Exception as e:
        print(f"错误: {e}")

print("\n=== 测试完成 ===")