#!/usr/bin/env python3
"""
修复editor.html中的模板字符串问题
将所有反引号模板字符串替换为字符串拼接
"""

import re
import os

def read_file(path):
    """读取文件内容"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    """写入文件内容"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_add_gcweb_header_footer(content):
    """修复addGCWebHeaderFooter函数中的模板字符串"""
    
    # 查找函数定义
    func_pattern = r'function addGCWebHeaderFooter\(content\) \{[\s\S]*?return gcwebHeader \+ mainContent \+ gcwebFooter;\s*\n\s*\}'
    match = re.search(func_pattern, content)
    
    if not match:
        print("未找到addGCWebHeaderFooter函数")
        return content
    
    func_content = match.group(0)
    
    # 检查是否已经修复（包含const gcwebHeader = "或const gcwebHeader = '）
    if 'const gcwebHeader = "' in func_content or "const gcwebHeader = '" in func_content:
        print("addGCWebHeaderFooter函数似乎已经修复")
        return content
    
    # 提取gcwebHeader和gcwebFooter变量定义
    # 查找const gcwebHeader = `...`
    header_pattern = r'(const gcwebHeader = `)([\s\S]*?)(`)'
    header_match = re.search(header_pattern, func_content)
    
    footer_pattern = r'(const gcwebFooter = `)([\s\S]*?)(`)'
    footer_match = re.search(footer_pattern, func_content)
    
    if not header_match or not footer_match:
        print("未找到gcwebHeader或gcwebFooter模板字符串")
        return content
    
    # 提取模板字符串内容
    header_content = header_match.group(2)
    footer_content = footer_match.group(2)
    
    # 转义模板字符串内容中的特殊字符
    # 1. 转义反斜杠
    header_content = header_content.replace('\\', '\\\\')
    footer_content = footer_content.replace('\\', '\\\\')
    
    # 2. 转义双引号
    header_content = header_content.replace('"', '\\"')
    footer_content = footer_content.replace('"', '\\"')
    
    # 3. 转义换行符
    header_content = header_content.replace('\n', '\\n\\\n    ')
    footer_content = footer_content.replace('\n', '\\n\\\n    ')
    
    # 构建新的变量定义
    new_header_def = 'const gcwebHeader = \\\n    "' + header_content + '";'
    new_footer_def = 'const gcwebFooter = \\\n    "' + footer_content + '";'
    
    # 替换原内容
    new_func_content = func_content
    new_func_content = new_func_content.replace(header_match.group(0), new_header_def)
    new_func_content = new_func_content.replace(footer_match.group(0), new_footer_def)
    
    # 替换原函数
    new_content = content[:match.start()] + new_func_content + content[match.end():]
    
    print("已修复addGCWebHeaderFooter函数中的模板字符串")
    return new_content

def fix_update_preview(content):
    """修复updatePreview函数中的模板字符串"""
    
    # 查找函数定义
    func_pattern = r'function updatePreview\(content\) \{[\s\S]*?return false; // No iframe found[\s\S]*?\n\s*\}'
    match = re.search(func_pattern, content, re.DOTALL)
    
    if not match:
        print("未找到updatePreview函数")
        return content
    
    func_content = match.group(0)
    
    # 检查是否已经修复（不包含反引号模板字符串）
    if '`<!DOCTYPE html>' not in func_content and '`<div>` + safeCleaned + `</div>`' not in func_content:
        print("updatePreview函数似乎已经修复")
        return content
    
    # 修复第一个模板字符串（当gcwebContent为空时）
    # 查找：previewIframe.srcdoc = `...` + safeCleaned + `...`
    pattern1 = r'(previewIframe\.srcdoc = `)([\s\S]*?)(`\s*\+\s*safeCleaned\s*\+\s*`)([\s\S]*?)(`)'
    match1 = re.search(pattern1, func_content)
    
    if match1:
        before = match1.group(2)
        after = match1.group(4)
        
        # 转义特殊字符
        before = before.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n        ')
        after = after.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n        ')
        
        new_str = 'previewIframe.srcdoc = \\\n        "' + before + '" + safeCleaned + "' + after + '";'
        func_content = func_content.replace(match1.group(0), new_str)
    
    # 修复主要的HTML文档模板字符串
    # 查找：const htmlDoc = `...` + safeGcwebContent + `...`
    pattern2 = r'(const htmlDoc = `)([\s\S]*?)(`\s*\+\s*safeGcwebContent\s*\+\s*`)([\s\S]*?)(`)'
    match2 = re.search(pattern2, func_content, re.DOTALL)
    
    if match2:
        before = match2.group(2)
        after = match2.group(4)
        
        # 转义特殊字符
        before = before.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
        after = after.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
        
        new_str = 'const htmlDoc = \\\n    "' + before + '" + safeGcwebContent + "' + after + '";'
        func_content = func_content.replace(match2.group(0), new_str)
    
    # 修复错误显示模板字符串
    # 查找：previewIframe.srcdoc = `...` + safeErrorMessage + `...`
    pattern3 = r'(previewIframe\.srcdoc = `)([\s\S]*?)(`\s*\+\s*safeErrorMessage\s*\+\s*`)([\s\S]*?)(`)'
    match3 = re.search(pattern3, func_content, re.DOTALL)
    
    if match3:
        before = match3.group(2)
        after = match3.group(4)
        
        # 转义特殊字符
        before = before.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
        after = after.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
        
        new_str = 'previewIframe.srcdoc = \\\n    "' + before + '" + safeErrorMessage + "' + after + '";'
        func_content = func_content.replace(match3.group(0), new_str)
    
    # 替换原函数
    new_content = content[:match.start()] + func_content + content[match.end():]
    
    print("已修复updatePreview函数中的模板字符串")
    return new_content

def main():
    editor_path = '/home/hongb/.openclaw/workspace/webbot/static/editor.html'
    
    if not os.path.exists(editor_path):
        print(f"文件不存在: {editor_path}")
        return
    
    # 备份原文件
    backup_path = editor_path + '.backup_template_fix'
    content = read_file(editor_path)
    write_file(backup_path, content)
    print(f"已创建备份: {backup_path}")
    
    # 修复函数
    content = fix_add_gcweb_header_footer(content)
    content = fix_update_preview(content)
    
    # 写入修复后的文件
    write_file(editor_path, content)
    print(f"已修复文件: {editor_path}")
    
    # 复制到前端目录
    frontend_path = '/home/hongb/.openclaw/workspace/webbot/frontend/editor.html'
    write_file(frontend_path, content)
    print(f"已复制到前端目录: {frontend_path}")

if __name__ == '__main__':
    main()