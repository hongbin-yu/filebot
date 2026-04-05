#!/usr/bin/env python3
"""
测试转换服务依赖
"""
import sys
import subprocess

def check_import(module_name, pip_name=None):
    """检查模块是否可以导入"""
    try:
        __import__(module_name)
        print(f"✅ {module_name}")
        return True
    except ImportError:
        pip_name = pip_name or module_name
        print(f"❌ {module_name} (需要安装: pip install {pip_name})")
        return False

def check_pip_install(package_name):
    """检查包是否已安装（通过pip）"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def main():
    print("检查转换服务依赖...")
    print("=" * 50)
    
    dependencies = [
        ("PIL", "Pillow"),  # Pillow包提供PIL模块
        ("PyPDF2", "PyPDF2"),
        ("img2pdf", "img2pdf"),
        ("reportlab", "reportlab"),
        ("docx", "python-docx"),
        ("cv2", "opencv-python"),  # OpenCV for TIFF等
        ("pytesseract", "pytesseract"),
    ]
    
    missing = []
    for import_name, pip_name in dependencies:
        if not check_import(import_name, pip_name):
            missing.append(pip_name)
    
    print("\n" + "=" * 50)
    print(f"总依赖: {len(dependencies)}, 缺失: {len(missing)}")
    
    if missing:
        print(f"\n缺失的依赖: {', '.join(missing)}")
        print("\n建议安装命令:")
        print(f"  pip install {' '.join(missing)}")
        
        # 检查是否在虚拟环境中
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("\n当前在虚拟环境中，可以直接安装")
        else:
            print("\n⚠️  不在虚拟环境中，建议先激活虚拟环境")
    else:
        print("\n✅ 所有依赖已安装!")
    
    # 检查系统依赖
    print("\n" + "=" * 50)
    print("系统命令检查:")
    system_commands = ["tesseract", "convert", "unoconv"]
    for cmd in system_commands:
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            print(f"✅ {cmd} (已安装)")
        except:
            print(f"❌ {cmd} (未安装，某些功能可能受限)")

if __name__ == "__main__":
    main()