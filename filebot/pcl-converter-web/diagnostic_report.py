#!/usr/bin/env python3
"""
PCL转换环境诊断报告
"""

import os
import sys
import subprocess
import platform
import stat
from pathlib import Path

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def check_command(cmd, args=["--version"]):
    """检查命令是否可用"""
    try:
        result = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, result.stdout.strip()[:100]
        else:
            return False, f"返回码: {result.returncode}"
    except FileNotFoundError:
        return False, "未找到"
    except subprocess.TimeoutExpired:
        return False, "超时"
    except Exception as e:
        return False, f"错误: {str(e)[:50]}"

def find_windows_tools():
    """查找Windows PCL工具"""
    windows_paths = [
        "/mnt/c/Program Files",
        "/mnt/c/Program Files (x86)", 
        "/mnt/c/Windows/System32",
        "/mnt/c/Windows",
        "/mnt/c"
    ]
    
    tools_found = []
    exe_patterns = ["*pcl*.exe", "*gpcl*.exe", "*ghostpcl*.exe", "*pcl6*.exe"]
    
    for base_path in windows_paths:
        if os.path.exists(base_path):
            for pattern in exe_patterns:
                try:
                    for path in Path(base_path).rglob(pattern):
                        tools_found.append(str(path))
                except:
                    continue
    
    return tools_found[:20]  # 返回前20个

def test_pcl_conversion():
    """测试PCL转换"""
    test_file = "/mnt/c/workspace/sample/00000001.pcl"
    if not os.path.exists(test_file):
        return "测试文件不存在"
    
    output_file = "/tmp/test_output.pdf"
    
    # 测试Ghostscript
    print("  测试Ghostscript转换...")
    try:
        cmd = ["gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-dSAFER",
               f"-sOutputFile={output_file}", test_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            os.remove(output_file)
            
            if result.returncode == 0 and size > 0:
                return f"Ghostscript: 转换成功 ({size} bytes)"
            else:
                return f"Ghostscript: 失败 (返回码: {result.returncode}, 输出大小: {size})"
        else:
            error_msg = result.stderr[:200] if result.stderr else "无错误输出"
            return f"Ghostscript: 失败 - {error_msg}"
    except Exception as e:
        return f"Ghostscript测试异常: {str(e)[:100]}"
    
    return "未测试"

def check_hplip():
    """检查hplip安装"""
    hplip_tools = {
        "commandtopclx": "/usr/lib/cups/filter/commandtopclx",
        "pclmtoraster": "/usr/lib/cups/filter/pclmtoraster", 
        "rastertopclx": "/usr/lib/cups/filter/rastertopclx",
        "ippevepcl": "/usr/sbin/ippevepcl"
    }
    
    results = {}
    for name, path in hplip_tools.items():
        if os.path.exists(path):
            try:
                st = os.stat(path)
                executable = bool(st.st_mode & stat.S_IEXEC)
                results[name] = {
                    "path": path,
                    "executable": executable,
                    "size": st.st_size
                }
            except:
                results[name] = {"path": path, "error": "无法访问"}
        else:
            results[name] = {"path": path, "found": False}
    
    return results

def main():
    print_header("PCL转换环境诊断报告")
    print(f"生成时间: 2026-03-17")
    print(f"系统: {platform.system()} {platform.release()} {platform.version()}")
    print(f"Python: {platform.python_version()}")
    print(f"工作目录: {os.getcwd()}")
    
    # 1. Python环境
    print_header("1. Python环境检查")
    
    python_packages = ["flask", "requests", "werkzeug", "python-dotenv"]
    for pkg in python_packages:
        try:
            __import__(pkg)
            print(f"   ✓ {pkg}: 已安装")
        except ImportError:
            print(f"   ✗ {pkg}: 未安装")
    
    # 2. 系统工具
    print_header("2. 系统工具检查")
    
    tools = [
        ("gs", ["--version"]),
        ("pcl6", ["--version"]),
        ("gpcl6", ["--version"]),
        ("pcltopdf", []),
        ("pcl2pdf", []),
    ]
    
    for cmd, args in tools:
        available, info = check_command(cmd, args)
        status = "✓" if available else "✗"
        print(f"   {status} {cmd}: {info}")
    
    # 3. hplip工具
    print_header("3. hplip工具检查")
    hplip_results = check_hplip()
    for name, info in hplip_results.items():
        if "error" in info:
            print(f"   ? {name}: {info['error']}")
        elif "found" in info and not info["found"]:
            print(f"   ✗ {name}: 未找到 ({info['path']})")
        else:
            exec_status = "可执行" if info.get("executable", False) else "不可执行"
            print(f"   ✓ {name}: {info['path']} ({exec_status}, {info.get('size', 0)} bytes)")
    
    # 4. Windows工具
    print_header("4. Windows PCL工具搜索")
    windows_tools = find_windows_tools()
    if windows_tools:
        print(f"   找到 {len(windows_tools)} 个可能工具:")
        for tool in windows_tools[:10]:  # 显示前10个
            print(f"   • {tool}")
        if len(windows_tools) > 10:
            print(f"   ... 还有 {len(windows_tools) - 10} 个")
    else:
        print("   未找到Windows PCL工具")
    
    # 5. 测试文件
    print_header("5. 测试文件检查")
    test_file = "/mnt/c/workspace/sample/00000001.pcl"
    if os.path.exists(test_file):
        size = os.path.getsize(test_file)
        print(f"   ✓ 测试文件存在: {test_file}")
        print(f"     大小: {size} bytes ({size/1024:.1f} KB)")
        
        # 检查文件内容
        try:
            with open(test_file, 'rb') as f:
                header = f.read(200)
                # PCL特征检查
                has_esc = b'\x1b' in header
                has_pcl_text = b'PCL' in header
                has_pjl = b'@PJL' in header
                
                features = []
                if has_esc: features.append("ESC序列")
                if has_pcl_text: features.append("PCL文本")
                if has_pjl: features.append("PJL命令")
                
                if features:
                    print(f"     特征: {', '.join(features)}")
                
                # 显示部分内容
                hex_preview = header[:50].hex()
                ascii_preview = "".join(chr(b) if 32 <= b < 127 else '.' for b in header[:50])
                print(f"     头部(hex): {hex_preview}")
                print(f"     头部(ascii): {ascii_preview}")
        except Exception as e:
            print(f"     无法读取文件: {e}")
    else:
        print(f"   ✗ 测试文件不存在: {test_file}")
    
    # 6. 转换测试
    print_header("6. PCL转换测试")
    conversion_test = test_pcl_conversion()
    print(f"   {conversion_test}")
    
    # 7. 建议
    print_header("7. 建议和下一步")
    
    print("   A. 安装缺失的Python包:")
    print("      sudo apt install python3-pip")
    print("      pip3 install -r requirements.txt")
    print()
    
    print("   B. PCL工具解决方案:")
    print("      1. 安装GhostPCL (推荐):")
    print("         • 下载Ghostscript商业版 (含GhostPCL)")
    print("         • 从 https://www.artifex.com/downloads/ 获取")
    print("         • 安装后确保 gpcl6.exe 在PATH中")
    print()
    print("      2. 使用hplip工具链:")
    print("         • commandtopclx: 命令到PCL转换")
    print("         • 可能需要配合其他工具完成PCL→PDF")
    print()
    print("      3. 寻找其他PCL工具:")
    print("         • pcltopdf (开源)")
    print("         • 专用PCL转换软件")
    print()
    
    print("   C. 快速测试命令:")
    print("      # 使用Ghostscript尝试转换")
    print(f"      gs -sDEVICE=pdfwrite -o /tmp/output.pdf {test_file}")
    print()
    print("      # 检查hplip工具")
    print("      /usr/lib/cups/filter/commandtopclx --help")
    print()
    
    print("   D. Web应用启动:")
    print("      # 安装依赖后")
    print("      python3 app_enhanced.py")
    print("      # 访问 http://localhost:5000")
    
    print_header("报告结束")

if __name__ == '__main__':
    main()