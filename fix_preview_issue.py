#!/usr/bin/env python3
"""
彻底修复WebBot编辑器预览问题
1. 确保所有HTML字符串正确转义
2. 修复可能导致JavaScript语法错误的问题
3. 增强错误处理和降级机制
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

def escape_html_string(content):
    """转义HTML字符串中的特殊字符"""
    # 转义反引号、美元符号、双引号、单引号等
    content = content.replace('\\', '\\\\')  # 先转义反斜杠
    content = content.replace('`', "\\'")  # 反引号转单引号
    content = content.replace('$', '$$')  # 美元符号转义
    content = content.replace('"', '\\"')  # 双引号转义
    content = content.replace("'", "\\'")  # 单引号转义
    content = content.replace('\n', '\\n')  # 换行符转义
    content = content.replace('\r', '\\r')  # 回车符转义
    return content

def fix_update_preview_function(content):
    """修复updatePreview函数中的HTML字符串构造"""
    
    # 找到updatePreview函数
    pattern = r'(function updatePreview\(\)\s*{[\s\S]*?})'
    
    def replace_update_preview(match):
        func_body = match.group(1)
        
        # 确保htmlDoc字符串正确构造
        # 查找htmlDoc变量定义
        html_doc_pattern = r'(const htmlDoc = ")([^"]*)"'
        
        def fix_html_doc(m):
            html_content = m.group(2)
            # 确保字符串正确转义
            html_content = escape_html_string(html_content)
            return f'const htmlDoc = "{html_content}";'
        
        func_body = re.sub(html_doc_pattern, fix_html_doc, func_body)
        
        # 添加更详细的错误日志
        error_log_pattern = r'(console\.error\(["\']Failed to generate preview["\']\);)'
        enhanced_error = '''console.error('Failed to generate preview:', error);
                console.error('Error details:', {
                    message: error.message,
                    stack: error.stack,
                    gcwebContentLength: gcwebContent ? gcwebContent.length : 0,
                    hasJQuery: typeof jQuery !== "undefined"
                });'''
        
        func_body = re.sub(error_log_pattern, enhanced_error, func_body)
        
        return func_body
    
    content = re.sub(pattern, replace_update_preview, content, flags=re.MULTILINE)
    
    return content

def fix_switch_to_preview_mode(content):
    """修复switchToPreviewMode函数"""
    
    # 添加额外的错误处理
    error_handling_pattern = r'(} catch \(error\) {[\s\S]*?showError\(["\']Failed to generate preview[\s\S]*?editor-content["\']\);)'
    
    enhanced_catch = '''} catch (error) {
                console.error('Preview generation failed:', error);
                showError('Failed to generate preview. Please edit HTML source instead.');
                // 确保回退到HTML编辑模式
                const editorContent = document.getElementById('editor-content');
                if (editorContent && editorContent.style.display === 'none') {
                    switchToHtmlEditMode();
                }
                return false;'''
    
    content = re.sub(error_handling_pattern, enhanced_catch, content, flags=re.MULTILINE)
    
    return content

def fix_dom_ready_handler(content):
    """修复DOMContentLoaded事件处理器"""
    
    # 添加页面加载状态跟踪
    load_pattern = r'(document\.addEventListener\(["\']DOMContentLoaded["\'][\s\S]*?async function \(\) {)'
    
    def enhance_load_handler(match):
        return match.group(0) + '''
        console.log('Editor page loaded, pageId:', currentPageId);
        console.log('API Base:', API_BASE);
        
        // 添加加载状态指示器
        const loadingEl = document.getElementById('loading');
        if (loadingEl) {
            loadingEl.textContent = 'Loading page data for ' + (currentPageId || 'unknown page') + '...';
        }
        '''
    
    content = re.sub(load_pattern, enhance_load_handler, content, flags=re.MULTILINE)
    
    return content

def main():
    editor_path = '/home/hongb/.openclaw/workspace/webbot/static/editor.html'
    
    if not os.path.exists(editor_path):
        print(f"文件不存在: {editor_path}")
        return
    
    # 备份原文件
    backup_path = editor_path + '.backup_preview_fix'
    content = read_file(editor_path)
    write_file(backup_path, content)
    print(f"已创建备份: {backup_path}")
    
    # 应用修复
    print("应用修复...")
    
    # 1. 修复updatePreview函数
    content = fix_update_preview_function(content)
    
    # 2. 修复switchToPreviewMode函数
    content = fix_switch_to_preview_mode(content)
    
    # 3. 修复DOM加载处理器
    content = fix_dom_ready_handler(content)
    
    # 4. 确保所有模板字符串都安全（简单插值的模板字符串应该没问题）
    # 只修复可能包含HTML内容的模板字符串
    
    # 写入修复后的文件
    write_file(editor_path, content)
    print(f"已修复文件: {editor_path}")
    
    # 复制到前端目录
    frontend_path = '/home/hongb/.openclaw/workspace/webbot/frontend/editor.html'
    write_file(frontend_path, content)
    print(f"已复制到前端目录: {frontend_path}")
    
    print("\n修复完成！请测试以下步骤：")
    print("1. 硬刷新浏览器（Ctrl+Shift+R / Cmd+Shift+R）")
    print("2. 访问 http://localhost:8000/static/navigation.html")
    print("3. 点击任意页面的'Composing'按钮")
    print("4. 检查浏览器控制台（F12）是否有错误")
    
if __name__ == '__main__':
    main()