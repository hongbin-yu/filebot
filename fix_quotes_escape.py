#!/usr/bin/env python3
"""
修复updatePreview函数中的转义逻辑，添加双引号转义
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

def fix_escape_logic(content):
    """修复转义逻辑，添加双引号转义"""
    
    # 查找updatePreview函数中的转义代码
    # 模式1: const safeGcwebContent = String(gcwebContent).replace(/`/g, "'").replace(/\$/g, "$$");
    pattern1 = r'(const safeGcwebContent = String\(gcwebContent\))([\s\S]*?)(;)'
    
    def replace_pattern1(match):
        full_match = match.group(0)
        # 检查是否已经包含双引号转义
        if '.replace(/"/g' in full_match or '.replace(/\\"/g' in full_match:
            return full_match  # 已经修复
        
        # 添加双引号转义
        new_str = full_match.replace(';', '.replace(/"/g, \'"\');')
        return new_str
    
    content = re.sub(pattern1, replace_pattern1, content)
    
    # 模式2: 类似的转义模式（用于safeCleaned）
    pattern2 = r'(const safeCleaned = String\(cleaned[^)]*\))([\s\S]*?)(;)'
    
    def replace_pattern2(match):
        full_match = match.group(0)
        # 检查是否已经包含双引号转义
        if '.replace(/"/g' in full_match or '.replace(/\\"/g' in full_match:
            return full_match  # 已经修复
        
        # 添加双引号转义
        new_str = full_match.replace(';', '.replace(/"/g, \'"\');')
        return new_str
    
    content = re.sub(pattern2, replace_pattern2, content)
    
    # 模式3: 错误消息的转义
    pattern3 = r'(const safeErrorMessage = String\(errorMessage[^)]*\))([\s\S]*?)(;)'
    
    def replace_pattern3(match):
        full_match = match.group(0)
        # 检查是否已经包含双引号转义
        if '.replace(/"/g' in full_match or '.replace(/\\"/g' in full_match:
            return full_match  # 已经修复
        
        # 添加双引号转义
        new_str = full_match.replace(';', '.replace(/"/g, \'"\');')
        return new_str
    
    content = re.sub(pattern3, replace_pattern3, content)
    
    return content

def main():
    editor_path = '/home/hongb/.openclaw/workspace/webbot/static/editor.html'
    
    if not os.path.exists(editor_path):
        print(f"文件不存在: {editor_path}")
        return
    
    # 备份原文件
    backup_path = editor_path + '.backup_quote_fix'
    content = read_file(editor_path)
    write_file(backup_path, content)
    print(f"已创建备份: {backup_path}")
    
    # 修复
    content = fix_escape_logic(content)
    
    # 写入修复后的文件
    write_file(editor_path, content)
    print(f"已修复文件: {editor_path}")
    
    # 复制到前端目录
    frontend_path = '/home/hongb/.openclaw/workspace/webbot/frontend/editor.html'
    write_file(frontend_path, content)
    print(f"已复制到前端目录: {frontend_path}")

if __name__ == '__main__':
    main()