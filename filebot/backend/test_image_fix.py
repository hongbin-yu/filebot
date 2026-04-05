#!/usr/bin/env python3
"""
测试图片下载修复
"""
import sys
sys.path.insert(0, '.')

# 测试get_filetype_for_filename函数
from app.ai.website_crawler import get_filetype_for_filename
from app.models.document import FileType

print("测试文件类型映射函数...")

test_cases = [
    ("image.jpg", FileType.JPG),
    ("photo.jpeg", FileType.JPEG),
    ("picture.png", FileType.PNG),
    ("diagram.tiff", FileType.TIFF),
    ("graphic.gif", FileType.OTHER),  # GIF -> OTHER
    ("icon.ico", FileType.OTHER),     # ICO -> OTHER
    ("document.pdf", FileType.PDF),
    ("test.html", FileType.HTML),
    ("unknown.xyz", FileType.OTHER),  # 未知扩展名 -> OTHER
]

all_passed = True
for filename, expected in test_cases:
    result = get_filetype_for_filename(filename)
    status = "✓" if result == expected else "✗"
    print(f"{status} {filename:20} -> {result.value:10} (期望: {expected.value})")
    if result != expected:
        all_passed = False

print(f"\n测试结果: {'所有测试通过' if all_passed else '有测试失败'}")

# 测试实际的爬虫代码是否能够正确导入
print("\n测试爬虫模块导入...")
try:
    from app.ai.website_crawler import WebsiteCrawler
    print("✓ WebsiteCrawler 导入成功")
except Exception as e:
    print(f"✗ WebsiteCrawler 导入失败: {e}")

# 测试FileType枚举
print("\n测试FileType枚举...")
try:
    print(f"  JPG: {FileType.JPG}")
    print(f"  JPEG: {FileType.JPEG}")
    print(f"  PNG: {FileType.PNG}")
    print(f"  OTHER: {FileType.OTHER}")
    print("✓ FileType枚举访问正常")
except Exception as e:
    print(f"✗ FileType枚举访问失败: {e}")