#!/usr/bin/env python3
"""
修复剩余的零字节HTML文件。
针对有html_content元数据但文件大小为0的文件。
"""
import sqlite3
import json
import os
import sys
from pathlib import Path

def main():
    # 连接到数据库
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 获取所有零字节HTML文件
    cursor.execute('''
        SELECT id, original_filename, file_type, file_size, stored_filename, folder_id, document_metadata
        FROM documents 
        WHERE file_type IN ("html", "htm", "HTML", "HTM") AND file_size = 0
    ''')
    
    files = cursor.fetchall()
    print(f'发现 {len(files)} 个零字节HTML文件')
    
    repaired_count = 0
    skipped_count = 0
    error_count = 0
    
    for doc_id, filename, file_type, file_size, stored_filename, folder_id, metadata_json in files:
        print(f'\n处理: {filename} (ID: {doc_id})')
        
        # 解析元数据
        metadata = json.loads(metadata_json) if metadata_json else {}
        html_content = metadata.get('html_content', '')
        html_content_len = len(html_content) if html_content else 0
        
        # 检查文件路径
        if not stored_filename:
            print(f'  ⚠️  跳过: 无存储路径')
            skipped_count += 1
            continue
            
        file_path = Path('data/documents') / stored_filename
        
        # 情况1: 有html_content但文件为空
        if html_content_len > 0:
            print(f'  📄 有html_content内容: {html_content_len} 字符')
            
            # 检查文件是否存在
            if not file_path.exists():
                print(f'  ⚠️  文件不存在: {file_path}')
                # 创建目录
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                actual_size = file_path.stat().st_size
                print(f'  📊 当前文件大小: {actual_size} 字节')
            
            # 写入内容
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # 验证写入
                if file_path.exists():
                    new_size = file_path.stat().st_size
                    print(f'  ✅ 写入成功: {new_size} 字节')
                    
                    # 更新数据库
                    cursor.execute('UPDATE documents SET file_size = ? WHERE id = ?', 
                                  (new_size, doc_id))
                    conn.commit()
                    repaired_count += 1
                    print(f'  🔄 数据库已更新')
                else:
                    print(f'  ❌ 写入后文件不存在')
                    error_count += 1
                    
            except Exception as e:
                print(f'  ❌ 写入失败: {e}')
                error_count += 1
                
        # 情况2: 没有html_content但有其他内容字段
        else:
            # 检查其他可能的内容字段
            content = metadata.get('content', '') or metadata.get('text', '') or metadata.get('body', '')
            if content:
                print(f'  📄 使用其他内容字段: {len(content)} 字符')
                
                # 创建HTML包装
                html_wrapped = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{filename}</title>
</head>
<body>
    <h1>{filename}</h1>
    <div>{content}</div>
</body>
</html>"""
                
                try:
                    # 创建目录
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(html_wrapped)
                    
                    new_size = file_path.stat().st_size
                    print(f'  ✅ 写入包装HTML: {new_size} 字节')
                    
                    # 更新数据库
                    cursor.execute('UPDATE documents SET file_size = ? WHERE id = ?', 
                                  (new_size, doc_id))
                    conn.commit()
                    repaired_count += 1
                    
                except Exception as e:
                    print(f'  ❌ 写入失败: {e}')
                    error_count += 1
            else:
                # 情况3: 完全没有内容 - 创建占位符
                print(f'  ⚠️  无可用内容')
                
                placeholder = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{filename} (空文件)</title>
</head>
<body>
    <h1>{filename}</h1>
    <p>此文件在原始爬取时没有内容，已自动创建此占位符。</p>
    <p>文档ID: {doc_id}</p>
    <p>原始URL可能为空或无法访问。</p>
</body>
</html>"""
                
                try:
                    # 创建目录
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(placeholder)
                    
                    new_size = file_path.stat().st_size
                    print(f'  📝 创建占位符: {new_size} 字节')
                    
                    # 更新数据库
                    cursor.execute('UPDATE documents SET file_size = ? WHERE id = ?', 
                                  (new_size, doc_id))
                    conn.commit()
                    repaired_count += 1
                    
                except Exception as e:
                    print(f'  ❌ 创建占位符失败: {e}')
                    error_count += 1
    
    # 最终统计
    print(f'\n{'='*60}')
    print(f'修复完成统计:')
    print(f'  总共处理: {len(files)} 个文件')
    print(f'  成功修复: {repaired_count} 个文件')
    print(f'  跳过: {skipped_count} 个文件')
    print(f'  错误: {error_count} 个文件')
    
    # 验证修复结果
    cursor.execute('SELECT COUNT(*) FROM documents WHERE file_type IN ("html", "htm", "HTML", "HTM") AND file_size = 0')
    remaining = cursor.fetchone()[0]
    print(f'  剩余零字节文件: {remaining} 个')
    
    conn.close()
    
    # 检查文件系统
    zero_files = list(Path('data/documents').rglob('*.html'))
    zero_files = [f for f in zero_files if f.stat().st_size == 0]
    print(f'  文件系统零字节HTML文件: {len(zero_files)} 个')
    
    return 0 if remaining == 0 and len(zero_files) == 0 else 1

if __name__ == '__main__':
    sys.exit(main())