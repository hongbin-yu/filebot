#!/usr/bin/env python3
import os
from pathlib import Path

# 测试写入文件
test_content = "Test HTML content"
test_dir = Path("data/documents/test_folder")
test_dir.mkdir(parents=True, exist_ok=True)

test_file = test_dir / "test.html"

print(f"写入到: {test_file}")
print(f"内容长度: {len(test_content)} 字符, {len(test_content.encode('utf-8'))} 字节")

# 尝试写入
try:
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    print("写入成功")
    
    # 检查文件大小
    if test_file.exists():
        actual_size = test_file.stat().st_size
        expected_size = len(test_content.encode('utf-8'))
        print(f"文件大小: {actual_size} 字节")
        print(f"预期大小: {expected_size} 字节")
        if actual_size == expected_size:
            print("✓ 大小匹配")
        else:
            print(f"✗ 大小不匹配! 差: {actual_size - expected_size} 字节")
            
        # 读取内容验证
        with open(test_file, 'r', encoding='utf-8') as f:
            read_content = f.read()
            if read_content == test_content:
                print("✓ 内容匹配")
            else:
                print(f"✗ 内容不匹配! 读取长度: {len(read_content)}")
    else:
        print("✗ 文件不存在")
        
except Exception as e:
    print(f"写入失败: {e}")

# 测试空内容
print("\n测试空内容...")
test_file2 = test_dir / "test_empty.html"
try:
    with open(test_file2, 'w', encoding='utf-8') as f:
        f.write("")
    print(f"空文件大小: {test_file2.stat().st_size} 字节")
except Exception as e:
    print(f"空文件写入失败: {e}")

# 测试实际爬虫可能的内容
print("\n测试实际HTML内容...")
sample_html = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Test Content</h1>
    <p>This is a test paragraph with some content.</p>
</body>
</html>"""

test_file3 = test_dir / "test_real.html"
try:
    with open(test_file3, 'w', encoding='utf-8') as f:
        f.write(sample_html)
    print(f"实际HTML文件大小: {test_file3.stat().st_size} 字节")
except Exception as e:
    print(f"实际HTML写入失败: {e}")

# 清理
test_file.unlink(missing_ok=True)
test_file2.unlink(missing_ok=True)
test_file3.unlink(missing_ok=True)
test_dir.rmdir()