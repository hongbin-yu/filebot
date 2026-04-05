#!/usr/bin/env python3
"""
修复webBotHeader和webBotFooter的模板字符串
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

def fix_webbot_strings(content):
    """修复webBotHeader和webBotFooter模板字符串"""
    
    # 查找webBotHeader定义
    header_pattern = r'(const webBotHeader = `)([\s\S]*?)(`;)'
    header_match = re.search(header_pattern, content)
    
    if header_match:
        header_content = header_match.group(2)
        
        # 转义特殊字符
        header_content = header_content.replace('\\', '\\\\').replace('"', '\\"')
        
        # 处理换行符
        lines = header_content.split('\n')
        escaped_lines = []
        for i, line in enumerate(lines):
            escaped_line = line.replace('\\', '\\\\').replace('"', '\\"')
            if i < len(lines) - 1:
                escaped_line = escaped_line + '\\n\\\n                '
            escaped_lines.append(escaped_line)
        
        escaped_content = ''.join(escaped_lines)
        
        # 构建新的定义
        new_header = 'const webBotHeader = \\\n                "' + escaped_content + '";'
        
        # 替换
        content = content.replace(header_match.group(0), new_header)
        print("已修复webBotHeader")
    
    # 查找webBotFooter定义
    footer_pattern = r'(const webBotFooter = `)([\s\S]*?)(`;)'
    footer_match = re.search(footer_pattern, content)
    
    if footer_match:
        footer_content = footer_match.group(2)
        
        # 转义特殊字符
        footer_content = footer_content.replace('\\', '\\\\').replace('"', '\\"')
        
        # 处理换行符
        lines = footer_content.split('\n')
        escaped_lines = []
        for i, line in enumerate(lines):
            escaped_line = line.replace('\\', '\\\\').replace('"', '\\"')
            if i < len(lines) - 1:
                escaped_line = escaped_line + '\\n\\\n                '
            escaped_lines.append(escaped_line)
        
        escaped_content = ''.join(escaped_lines)
        
        # 构建新的定义
        new_footer = 'const webBotFooter = \\\n                "' + escaped_content + '";'
        
        # 替换
        content = content.replace(footer_match.group(0), new_footer)
        print("已修复webBotFooter")
    
    return content

def main():
    editor_path = '/home/hongb/.openclaw/workspace/webbot/static/editor.html'
    
    if not os.path.exists(editor_path):
        print(f"文件不存在: {editor_path}")
        return
    
    # 备份原文件
    backup_path = editor_path + '.backup_webbot_fix'
    content = read_file(editor_path)
    write_file(backup_path, content)
    print(f"已创建备份: {backup_path}")
    
    # 修复
    content = fix_webbot_strings(content)
    
    # 写入修复后的文件
    write_file(editor_path, content)
    print(f"已修复文件: {editor_path}")
    
    # 复制到前端目录
    frontend_path = '/home/hongb/.openclaw/workspace/webbot/frontend/editor.html'
    write_file(frontend_path, content)
    print(f"已复制到前端目录: {frontend_path}")

if __name__ == '__main__':
    main()