#!/usr/bin/env python3
"""
重新排序routes.py中的函数，将get_page_by_path移到get_page之前
"""
import re

file_path = '/home/hongb/.openclaw/workspace/webbot/app/routes/pages.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到get_page函数的开始位置
get_page_pattern = r'(@router\.get\("/\{page_id\}"[^@]+?)(?=@router\.get|@router\.post|@router\.put|@router\.delete|$)'
get_page_match = re.search(get_page_pattern, content, re.DOTALL)

# 找到get_page_by_path函数的开始位置  
get_page_by_path_pattern = r'(@router\.get\("/by-path"[^@]+?)(?=@router\.get|@router\.post|@router\.put|@router\.delete|$)'
get_page_by_path_match = re.search(get_page_by_path_pattern, content, re.DOTALL)

if not get_page_match or not get_page_by_path_match:
    print("❌ 无法找到函数")
    exit(1)

get_page_text = get_page_match.group(1)
get_page_by_path_text = get_page_by_path_match.group(1)

print(f"✅ 找到get_page函数 (长度: {len(get_page_text)})")
print(f"✅ 找到get_page_by_path函数 (长度: {len(get_page_by_path_text)})")

# 替换：先插入get_page_by_path，然后get_page
# 找到get_page之前的位置
get_page_start = get_page_match.start()
get_page_by_path_start = get_page_by_path_match.start()

# 如果get_page_by_path已经在get_page之后，我们需要交换它们
if get_page_by_path_start > get_page_start:
    print("⚠️  get_page_by_path在get_page之后，需要重新排序")
    
    # 获取get_page之前的内容
    before_get_page = content[:get_page_start]
    
    # 获取get_page和get_page_by_path之间的内容
    between_functions = content[get_page_match.end():get_page_by_path_start]
    
    # 获取get_page_by_path之后的内容
    after_get_page_by_path = content[get_page_by_path_match.end():]
    
    # 构建新内容：before_get_page + get_page_by_path_text + between_functions + get_page_text + after_get_page_by_path
    new_content = before_get_page + get_page_by_path_text + between_functions + get_page_text + after_get_page_by_path
    
    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ 函数重新排序完成")
else:
    print("✅ 函数顺序正确，无需修改")

# 验证修改
print("\n🔍 验证修改...")
with open(file_path, 'r', encoding='utf-8') as f:
    new_content = f.read()
    
# 检查顺序
get_page_pos = new_content.find('@router.get("/{page_id}"')
get_page_by_path_pos = new_content.find('@router.get("/by-path"')

if get_page_by_path_pos < get_page_pos:
    print("✅ 顺序正确：get_page_by_path在get_page之前")
else:
    print("❌ 顺序错误：get_page在get_page_by_path之前")