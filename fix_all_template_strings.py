#!/usr/bin/env python3
"""
彻底修复editor.html中的所有模板字符串
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

def fix_template_strings(content):
    """修复所有模板字符串"""
    
    # 查找所有模板字符串（反引号包裹的多行字符串）
    # 模式：`...` 或 `...` + variable + `...`
    lines = content.split('\n')
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检查是否以反引号开头
        if line.strip().startswith('`'):
            # 收集所有相关行直到结束反引号
            template_lines = []
            j = i
            while j < len(lines):
                template_lines.append(lines[j])
                if lines[j].rstrip().endswith('`') and not lines[j].rstrip().endswith('\\`'):
                    break
                j += 1
            
            template_block = '\n'.join(template_lines)
            
            # 检查是否有字符串拼接（`...` + variable + `...`）
            if '` + ' in template_block or '+ `' in template_block:
                # 这是带拼接的模板字符串，需要特殊处理
                # 简化：替换为字符串拼接格式
                
                # 将反引号内容转换为字符串
                # 1. 移除开头的反引号
                if template_block.startswith('`'):
                    template_block = template_block[1:]
                
                # 2. 移除结尾的反引号
                if template_block.endswith('`'):
                    template_block = template_block[:-1]
                
                # 3. 转义特殊字符
                template_block = template_block.replace('\\', '\\\\').replace('"', '\\"')
                
                # 4. 拆分拼接部分
                # 简单方法：替换整个块为字符串字面量
                # 但我们先尝试更智能的方法
                
                # 查找所有 ` + variable + ` 模式
                pattern = r'`\s*\+\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\+\s*`'
                matches = list(re.finditer(pattern, template_block))
                
                if matches:
                    # 有变量拼接
                    # 构建字符串拼接表达式
                    result_parts = []
                    last_end = 0
                    
                    for match in matches:
                        # 添加前面的文本
                        before = template_block[last_end:match.start()]
                        if before:
                            # 转义并添加到结果
                            before_escaped = before.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
                            result_parts.append('"' + before_escaped + '"')
                        
                        # 添加变量
                        var_name = match.group(1)
                        result_parts.append(var_name)
                        
                        last_end = match.end()
                    
                    # 添加最后的部分
                    after = template_block[last_end:]
                    if after:
                        after_escaped = after.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
                        result_parts.append('"' + after_escaped + '"')
                    
                    # 构建最终表达式
                    result = ' + '.join(result_parts)
                    
                    # 替换原行
                    new_line = lines[i].replace(template_lines[0], result, 1)
                    new_lines.append(new_line)
                    
                    # 跳过已处理的模板行
                    i = j + 1
                    continue
                else:
                    # 没有变量拼接，只是普通模板字符串
                    # 替换为普通字符串
                    escaped = template_block.replace('\n', '\\n\\\n    ')
                    new_line = lines[i].replace(template_lines[0], '"' + escaped + '"', 1)
                    new_lines.append(new_line)
                    
                    # 跳过已处理的模板行
                    i = j + 1
                    continue
            else:
                # 普通模板字符串，没有拼接
                # 替换为普通字符串
                # 移除反引号
                if template_block.startswith('`'):
                    template_block = template_block[1:]
                if template_block.endswith('`'):
                    template_block = template_block[:-1]
                
                # 转义
                escaped = template_block.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
                
                # 替换
                new_line = lines[i].replace(template_lines[0], '"' + escaped + '"', 1)
                new_lines.append(new_line)
                
                # 跳过已处理的模板行
                i = j + 1
                continue
        
        new_lines.append(line)
        i += 1
    
    return '\n'.join(new_lines)

def fix_specific_patterns(content):
    """修复特定的模板字符串模式"""
    
    # 模式1: previewIframe.srcdoc = `...` + variable + `...`
    pattern1 = r'(previewIframe\.srcdoc\s*=\s*)`([^`]*?)`\s*\+\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\+\s*`([^`]*?)`'
    
    def replace_pattern1(match):
        before = match.group(2)
        var = match.group(3)
        after = match.group(4)
        
        # 转义
        before = before.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n        ')
        after = after.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n        ')
        
        return f'{match.group(1)}" {before}" + {var} + " {after}";'
    
    content = re.sub(pattern1, replace_pattern1, content, flags=re.DOTALL)
    
    # 模式2: const htmlDoc = `...` + variable + `...`
    pattern2 = r'(const htmlDoc\s*=\s*)`([^`]*?)`\s*\+\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\+\s*`([^`]*?)`'
    
    def replace_pattern2(match):
        before = match.group(2)
        var = match.group(3)
        after = match.group(4)
        
        # 转义
        before = before.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
        after = after.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n\\\n    ')
        
        return f'{match.group(1)}" {before}" + {var} + " {after}";'
    
    content = re.sub(pattern2, replace_pattern2, content, flags=re.DOTALL)
    
    return content

def main():
    editor_path = '/home/hongb/.openclaw/workspace/webbot/static/editor.html'
    
    if not os.path.exists(editor_path):
        print(f"文件不存在: {editor_path}")
        return
    
    # 备份原文件
    backup_path = editor_path + '.backup_all_fix'
    content = read_file(editor_path)
    write_file(backup_path, content)
    print(f"已创建备份: {backup_path}")
    
    # 修复特定模式
    content = fix_specific_patterns(content)
    
    # 写入修复后的文件
    write_file(editor_path, content)
    print(f"已修复文件: {editor_path}")
    
    # 复制到前端目录
    frontend_path = '/home/hongb/.openclaw/workspace/webbot/frontend/editor.html'
    write_file(frontend_path, content)
    print(f"已复制到前端目录: {frontend_path}")
    
    # 验证修复
    print("\n验证修复结果:")
    print("检查是否还有模板字符串（反引号）:")
    result = os.popen(f'grep -n "`" {editor_path} | head -10').read()
    if result:
        print("发现反引号:")
        print(result)
    else:
        print("未发现反引号，修复成功!")

if __name__ == '__main__':
    main()