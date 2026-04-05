#!/usr/bin/env python3
"""
测试遗留格式支持 (.cld, .pcl, .ps)
"""
import sys
import os
import tempfile
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.conversion_service import ConversionService, ConversionFormat

def test_format_support():
    """测试格式支持"""
    service = ConversionService()
    
    print("=== 测试遗留格式支持 ===")
    
    # 获取支持的格式列表
    supported = service.get_supported_formats()
    print(f"支持的源格式: {supported['source_formats']}")
    print(f"支持的目标格式: {supported['target_formats']}")
    
    # 检查特定格式
    test_formats = ['cld', 'pcl', 'ps', 'txt', 'pdf']
    print("\n=== 格式支持检查 ===")
    for fmt in test_formats:
        try:
            enum_fmt = ConversionFormat(fmt)
            if enum_fmt in service.supported_formats:
                print(f"✅ {fmt}: 已支持")
            else:
                print(f"❌ {fmt}: 在枚举中但不在supported_formats中")
        except ValueError:
            print(f"❌ {fmt}: 不在ConversionFormat枚举中")
    
    # 测试CLD格式（文本转换）
    print("\n=== 测试CLD格式转换 (模拟) ===")
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cld', delete=False) as f:
            f.write("这是一个测试的.cld文件内容\n")
            f.write("第二行内容\n")
            f.write("第三行内容\n")
            cld_file = f.name
        
        cld_path = Path(cld_file)
        print(f"创建测试CLD文件: {cld_path}")
        
        # 检查是否可以被识别为CLD格式
        service = ConversionService()
        detected = service._detect_format(cld_path)
        print(f"自动检测格式: {detected}")
        
        if detected == 'cld':
            print("✅ CLD格式自动检测成功")
        else:
            print(f"⚠️  CLD格式检测为: {detected} (应为'cld')")
        
        os.unlink(cld_file)
        
    except Exception as e:
        print(f"❌ CLD测试失败: {e}")
    
    # 测试PCL格式支持
    print("\n=== 测试PCL格式支持 ===")
    try:
        pcl_enum = ConversionFormat('pcl')
        converter = service.supported_formats.get(pcl_enum)
        if converter:
            print("✅ PCL格式在supported_formats中有映射")
            print(f"   转换器: {converter.__name__ if hasattr(converter, '__name__') else converter}")
        else:
            print("❌ PCL格式在supported_formats中无映射")
    except Exception as e:
        print(f"❌ PCL测试失败: {e}")
    
    # 列出所有支持的格式
    print("\n=== 完整支持格式列表 ===")
    for i, (fmt, converter) in enumerate(service.supported_formats.items(), 1):
        converter_name = converter.__name__ if hasattr(converter, '__name__') else str(converter)
        print(f"{i:2d}. {fmt.value:8s} -> {converter_name}")


def test_cld_compression():
    """测试CLD空格压缩功能（每行255字符固定宽度）"""
    print("\n=== 测试CLD空格压缩功能 ===")
    
    # 创建模拟的.cld文件（每行255字符，包含空格）
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cld', delete=False) as f:
        # 第一行：数据+空格填充到255字符
        data1 = "DATA001:Customer Name:John Doe"
        spaces1 = ' ' * (255 - len(data1))
        f.write(data1 + spaces1 + '\n')
        
        # 第二行：更多数据
        data2 = "DATA002:Order ID:1234567890"
        spaces2 = ' ' * (255 - len(data2))
        f.write(data2 + spaces2 + '\n')
        
        # 第三行：空行（只有空格）
        f.write(' ' * 255 + '\n')
        
        # 第四行：带空格的数据
        data4 = "ITEM  DESCRIPTION  QUANTITY  PRICE"
        spaces4 = ' ' * (255 - len(data4))
        f.write(data4 + spaces4 + '\n')
        
        cld_file = f.name
    
    try:
        cld_path = Path(cld_file)
        print(f"创建模拟CLD文件: {cld_path}")
        print(f"文件大小: {cld_path.stat().st_size} 字节")
        
        # 读取文件验证
        with open(cld_path, 'r') as f:
            lines = f.readlines()
            print(f"总行数: {len(lines)}")
            for i, line in enumerate(lines, 1):
                line = line.rstrip('\n')
                print(f"  第{i}行: {len(line)} 字符, 前50字符: '{line[:50]}...'")
        
        # 测试转换服务
        service = ConversionService()
        
        # 检测格式
        detected = service._detect_format(cld_path)
        print(f"\n自动检测格式: {detected}")
        
        if detected != 'cld':
            print(f"⚠️ 格式检测错误，应为'cld'")
            return
        
        # 创建临时输出PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_temp:
            pdf_path = Path(pdf_temp.name)
        
        print(f"\n开始CLD到PDF转换...")
        try:
            # 调用转换方法（直接调用内部方法测试）
            result = service._convert_cld_to_pdf(cld_path, pdf_path)
            
            print(f"✅ 转换成功!")
            print(f"   转换器: {result.get('converter', 'N/A')}")
            print(f"   原始大小: {result.get('original_size', 0)} 字节")
            print(f"   输出大小: {result.get('output_size', 0)} 字节")
            print(f"   行数: {result.get('line_count', 0)}")
            print(f"   有效行数: {result.get('valid_line_count', 0)}")
            print(f"   平均行长度: {result.get('avg_line_length', 0)} 字符")
            print(f"   移除空格总数: {result.get('total_spaces_removed', 0)}")
            
            # 检查PDF文件
            if pdf_path.exists():
                print(f"✅ PDF文件生成: {pdf_path}")
                print(f"   PDF大小: {pdf_path.stat().st_size} 字节")
            else:
                print(f"❌ PDF文件未生成")
                
        except Exception as e:
            print(f"❌ 转换失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 清理
        os.unlink(cld_file)
        if pdf_path.exists():
            os.unlink(pdf_path)
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(cld_file):
            os.unlink(cld_file)


if __name__ == "__main__":
    test_format_support()
    test_cld_compression()