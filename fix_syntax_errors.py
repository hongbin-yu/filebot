#!/usr/bin/env python3
"""
修复updatePreview函数中的语法错误
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

def fix_syntax_errors(content):
    """修复语法错误"""
    
    # 修复第1166行的语法错误
    # 错误的: .replace(/</g, "&lt.replace(/"/g, '"');")
    # 正确的: .replace(/</g, "&lt;").replace(/"/g, '"')
    
    error_pattern = r'\.replace\(/</g, "&lt\.replace\(/"/g, \'"\'\);\"\)'
    correct_replacement = '.replace(/</g, "&lt;").replace(/"/g, \'"\')'
    
    content = re.sub(error_pattern, correct_replacement, content)
    
    # 修复第1165行，确保replace调用正确连接
    # 查找模式: .replace(/\$/g, "$$")\n                        .replace(/</g, "&lt;")
    # 应该确保有.连接
    
    pattern2 = r'(\.replace\(/\\\\\$/g, "\$\$"\)\s*\n\s*)(\.replace\(/</g, "&lt;"\))'
    replacement2 = r'\1.\2'
    
    content = re.sub(pattern2, replacement2, content)
    
    # 修复所有类似的replace链问题
    # 确保每个replace调用都以.开头（除了第一个）
    lines = content.split('\n')
    in_replace_chain = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('.replace('):
            if not stripped.startswith('.replace(') and in_replace_chain:
                # 如果应该以.开头但没有
                if not stripped.startswith('.'):
                    lines[i] = line.replace(stripped, '.' + stripped, 1)
                    print(f"修复第{i+1}行: 添加.前缀到replace调用")
            in_replace_chain = True
        elif stripped and not stripped.startswith('.replace('):
            in_replace_chain = False
    
    content = '\n'.join(lines)
    
    return content

def main():
    editor_path = '/home/hongb/.openclaw/workspace/webbot/static/editor.html'
    
    if not os.path.exists(editor_path):
        print(f"文件不存在: {editor_path}")
        return
    
    # 备份原文件
    backup_path = editor_path + '.backup_syntax_fix'
    content = read_file(editor_path)
    write_file(backup_path, content)
    print(f"已创建备份: {backup_path}")
    
    # 应用修复
    print("修复语法错误...")
    content = fix_syntax_errors(content)
    
    # 写入修复后的文件
    write_file(editor_path, content)
    print(f"已修复文件: {editor_path}")
    
    # 验证修复
    if '.replace(/</g, "&lt.replace(/"/g, \'"\');")' in content:
        print("警告: 可能还有语法错误未修复")
    else:
        print("语法错误修复完成")
    
    # 复制到前端目录
    frontend_path = '/home/hongb/.openclaw/workspace/webbot/frontend/editor.html'
    write_file(frontend_path, content)
    print(f"已复制到前端目录: {frontend_path}")

if __name__ == '__main__':
    main()