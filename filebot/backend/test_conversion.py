#!/usr/bin/env python3
"""
测试转换服务功能
"""
import sys
import os
from pathlib import Path
import tempfile
import shutil

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.conversion_service import get_conversion_service, ConversionService, ConversionFormat

def test_service_initialization():
    """测试服务初始化"""
    print("1. 测试服务初始化...")
    try:
        service = get_conversion_service()
        print(f"   ✅ 服务初始化成功")
        print(f"   支持的源格式: {service.get_supported_formats()}")
        return service
    except Exception as e:
        print(f"   ❌ 服务初始化失败: {e}")
        return None

def test_txt_to_pdf(service, test_dir):
    """测试文本转PDF"""
    print("\n2. 测试文本转PDF...")
    
    source_path = Path(test_dir) / "test.txt"
    target_path = Path(test_dir) / "test_output.pdf"
    
    # 确保源文件存在
    if not source_path.exists():
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write("FileBot转换引擎测试文档\n")
            f.write("这是测试内容\n")
            f.write("多行文本测试\n" * 5)
    
    print(f"   源文件: {source_path} ({source_path.stat().st_size} 字节)")
    
    success, message, metadata = service.convert_file(
        source_path, target_path, source_format="txt", target_format="pdf"
    )
    
    if success:
        print(f"   ✅ 转换成功: {message}")
        print(f"   目标文件: {target_path} ({target_path.stat().st_size} 字节)")
        if metadata:
            print(f"   元数据: {metadata}")
        return True
    else:
        print(f"   ❌ 转换失败: {message}")
        return False

def test_pdf_to_pdf(service, test_dir):
    """测试PDF到PDF（复制）"""
    print("\n3. 测试PDF到PDF复制...")
    
    # 首先创建一个PDF文件（使用前面的转换结果）
    source_pdf = Path(test_dir) / "test_output.pdf"
    if not source_pdf.exists():
        print(f"   需要先运行文本转PDF测试")
        return False
    
    target_pdf = Path(test_dir) / "test_copy.pdf"
    
    print(f"   源PDF: {source_pdf} ({source_pdf.stat().st_size} 字节)")
    
    success, message, metadata = service.convert_file(
        source_pdf, target_pdf, source_format="pdf", target_format="pdf"
    )
    
    if success:
        print(f"   ✅ 复制成功: {message}")
        print(f"   目标PDF: {target_pdf} ({target_pdf.stat().st_size} 字节)")
        if metadata:
            print(f"   元数据: {metadata}")
        
        # 验证文件内容
        if source_pdf.stat().st_size == target_pdf.stat().st_size:
            print(f"   ✅ 文件大小匹配")
        else:
            print(f"   ⚠️  文件大小不匹配: 源={source_pdf.stat().st_size}, 目标={target_pdf.stat().st_size}")
        return True
    else:
        print(f"   ❌ 复制失败: {message}")
        return False

def test_image_to_pdf(service, test_dir):
    """测试图像转PDF"""
    print("\n4. 测试图像转PDF...")
    
    # 创建一个简单的测试图像（使用Pillow）
    try:
        from PIL import Image
        import numpy as np
        
        image_path = Path(test_dir) / "test_image.png"
        
        # 创建一个小图像（10x10像素）
        img_array = np.zeros((10, 10, 3), dtype=np.uint8)
        img_array[2:8, 2:8] = [255, 0, 0]  # 红色方块
        
        img = Image.fromarray(img_array, 'RGB')
        img.save(image_path)
        
        print(f"   创建测试图像: {image_path} ({image_path.stat().st_size} 字节)")
        
        target_pdf = Path(test_dir) / "test_image.pdf"
        
        success, message, metadata = service.convert_file(
            image_path, target_pdf, source_format="png", target_format="pdf"
        )
        
        if success:
            print(f"   ✅ 图像转PDF成功: {message}")
            print(f"   目标PDF: {target_pdf} ({target_pdf.stat().st_size} 字节)")
            if metadata:
                print(f"   元数据: {metadata}")
            return True
        else:
            print(f"   ❌ 图像转PDF失败: {message}")
            return False
            
    except ImportError as e:
        print(f"   ⚠️  跳过图像测试: 缺少依赖 {e}")
        return False
    except Exception as e:
        print(f"   ❌ 图像测试出错: {e}")
        return False

def test_unsupported_format(service, test_dir):
    """测试不支持格式的处理"""
    print("\n5. 测试不支持格式处理...")
    
    source_path = Path(test_dir) / "test.unknown"
    target_path = Path(test_dir) / "test_unknown.pdf"
    
    # 创建虚拟文件
    with open(source_path, 'w') as f:
        f.write("dummy content")
    
    success, message, metadata = service.convert_file(
        source_path, target_path, source_format="unknown", target_format="pdf"
    )
    
    if not success:
        print(f"   ✅ 正确拒绝不支持格式: {message}")
        return True
    else:
        print(f"   ❌ 应该拒绝不支持格式但转换成功了")
        return False

def test_format_detection(service, test_dir):
    """测试格式自动检测"""
    print("\n6. 测试格式自动检测...")
    
    test_cases = [
        ("test.txt", "txt"),
        ("test.pdf", "pdf"),
        ("test.png", "png"),
        ("test.jpg", "jpg"),
        ("test.tiff", "tiff"),
        ("test.doc", "doc"),
        ("test.docx", "docx"),
    ]
    
    all_passed = True
    for filename, expected_format in test_cases:
        path = Path(test_dir) / filename
        try:
            # 服务内部使用_detect_format方法，这里直接调用
            detected = service._detect_format(path)
            if detected == expected_format:
                print(f"   ✅ {filename}: 检测为 {detected}")
            else:
                print(f"   ❌ {filename}: 期望 {expected_format}, 实际 {detected}")
                all_passed = False
        except Exception as e:
            print(f"   ❌ {filename}: 检测失败 {e}")
            all_passed = False
    
    return all_passed

def main():
    """主测试函数"""
    print("=" * 60)
    print("FileBot 转换服务测试")
    print("=" * 60)
    
    # 创建临时测试目录
    test_dir = Path(__file__).parent / "data" / "temp" / "conversion_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"测试目录: {test_dir}")
    
    # 清理之前的测试文件
    for f in test_dir.glob("*"):
        if f.is_file():
            f.unlink()
    
    # 运行测试
    service = test_service_initialization()
    if not service:
        print("\n❌ 服务初始化失败，无法继续测试")
        return 1
    
    results = []
    
    results.append(test_txt_to_pdf(service, test_dir))
    results.append(test_pdf_to_pdf(service, test_dir))
    results.append(test_image_to_pdf(service, test_dir))
    results.append(test_unsupported_format(service, test_dir))
    results.append(test_format_detection(service, test_dir))
    
    # 统计结果
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有测试通过!")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())