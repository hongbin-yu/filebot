#!/usr/bin/env python3
"""
修复文件系统中的零字节HTML文件。
从数据库元数据恢复内容，或创建占位符。
"""
import sqlite3
import json
import os
import sys
from pathlib import Path

def get_document_by_stored_filename(stored_filename):
    """通过存储文件名查找文档记录"""
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 精确匹配存储文件名
    cursor.execute('''
        SELECT id, original_filename, file_type, file_size, document_metadata
        FROM documents WHERE stored_filename = ?
    ''', (stored_filename,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        doc_id, original_name, file_type, file_size, metadata_json = result
        metadata = json.loads(metadata_json) if metadata_json else {}
        return {
            'id': doc_id,
            'original_filename': original_name,
            'file_type': file_type,
            'file_size': file_size,
            'metadata': metadata
        }
    return None

def fix_zero_byte_files():
    """修复文件系统中的零字节HTML文件"""
    # 找到所有零字节HTML文件
    zero_files = []
    for html_file in Path('data/documents').rglob('*.html'):
        if html_file.stat().st_size == 0:
            zero_files.append(html_file)
    
    print(f"发现 {len(zero_files)} 个零字节HTML文件")
    
    if not zero_files:
        return
    
    repaired = 0
    errors = 0
    
    for file_path in zero_files:
        print(f"\n处理: {file_path}")
        
        # 转换为存储文件名格式
        # 从完整路径中提取相对路径
        rel_path = file_path.relative_to('data/documents')
        stored_filename = str(rel_path)
        
        # 查找数据库记录
        doc_info = get_document_by_stored_filename(stored_filename)
        
        if not doc_info:
            print(f"  ⚠️  未找到数据库记录: {stored_filename}")
            # 尝试通过文件夹和文件名查找
            folder_id = file_path.parent.name
            filename = file_path.name
            
            conn = sqlite3.connect('filebot.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, original_filename, file_type, file_size, document_metadata
                FROM documents WHERE stored_filename LIKE ? 
                OR (original_filename = ? AND folder_id = ?)
            ''', (f'%/{filename}', filename, folder_id))
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                print(f"  🔍 找到 {len(results)} 个可能匹配的记录")
                # 使用第一个匹配的记录
                doc_id, original_name, file_type, file_size, metadata_json = results[0]
                metadata = json.loads(metadata_json) if metadata_json else {}
                doc_info = {
                    'id': doc_id,
                    'original_filename': original_name,
                    'file_type': file_type,
                    'file_size': file_size,
                    'metadata': metadata
                }
            else:
                print(f"  ❌ 无法找到任何匹配的数据库记录")
                errors += 1
                continue
        
        # 现在有文档信息，尝试修复
        doc_id = doc_info['id']
        metadata = doc_info['metadata']
        
        # 尝试从元数据获取内容
        html_content = metadata.get('html_content', '')
        if not html_content:
            html_content = metadata.get('content', '') or metadata.get('text', '') or metadata.get('body', '')
        
        if html_content and html_content.strip():
            # 有内容，写入文件
            print(f"  📄 从元数据恢复内容，长度: {len(html_content)} 字符")
            try:
                # 确保目录存在
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # 验证写入
                if file_path.exists():
                    new_size = file_path.stat().st_size
                    print(f"  ✅ 写入成功: {new_size} 字节")
                    
                    # 更新数据库
                    conn = sqlite3.connect('filebot.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE documents SET file_size = ? WHERE id = ?', 
                                  (new_size, doc_id))
                    conn.commit()
                    conn.close()
                    
                    repaired += 1
                else:
                    print(f"  ❌ 写入后文件不存在")
                    errors += 1
                    
            except Exception as e:
                print(f"  ❌ 写入失败: {e}")
                errors += 1
                
        else:
            # 无内容，创建占位符
            print(f"  ⚠️  元数据中无可用内容")
            placeholder = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{file_path.name} (空文件)</title>
</head>
<body>
    <h1>{file_path.name}</h1>
    <p>此文件在原始爬取时没有内容，已自动创建此占位符。</p>
    <p>文件路径: {file_path}</p>
    <p>文档可能为空或无法访问。</p>
</body>
</html>"""
            
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(placeholder)
                
                new_size = file_path.stat().st_size
                print(f"  📝 创建占位符: {new_size} 字节")
                
                # 更新数据库
                conn = sqlite3.connect('filebot.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE documents SET file_size = ? WHERE id = ?', 
                              (new_size, doc_id))
                conn.commit()
                conn.close()
                
                repaired += 1
                
            except Exception as e:
                print(f"  ❌ 创建占位符失败: {e}")
                errors += 1
    
    # 最终统计
    print(f"\n{'='*60}")
    print(f"修复完成:")
    print(f"  总共处理: {len(zero_files)} 个文件")
    print(f"  成功修复: {repaired} 个文件")
    print(f"  错误: {errors} 个文件")
    
    # 再次检查
    zero_files_after = list(Path('data/documents').rglob('*.html'))
    zero_files_after = [f for f in zero_files_after if f.stat().st_size == 0]
    print(f"  修复后零字节文件: {len(zero_files_after)} 个")
    
    if zero_files_after:
        print("  剩余零字节文件:")
        for f in zero_files_after:
            print(f"    - {f}")
    
    return repaired, errors, len(zero_files_after)

def check_duplicate_documents():
    """检查重复的文档记录（相同存储文件名）"""
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 查找重复的存储文件名
    cursor.execute('''
        SELECT stored_filename, COUNT(*) as count
        FROM documents 
        WHERE stored_filename IS NOT NULL AND stored_filename != ''
        GROUP BY stored_filename 
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    ''')
    
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"\n🔍 发现 {len(duplicates)} 个重复存储文件名:")
        for stored_filename, count in duplicates:
            print(f"  {stored_filename}: {count} 个重复记录")
            
            # 获取详细信息
            cursor.execute('''
                SELECT id, original_filename, file_type, file_size, created_at
                FROM documents WHERE stored_filename = ?
                ORDER BY created_at
            ''', (stored_filename,))
            
            docs = cursor.fetchall()
            for doc_id, original_name, file_type, file_size, created_at in docs:
                print(f"    - ID: {doc_id}, 文件名: {original_name}, 大小: {file_size} 字节, 创建时间: {created_at}")
    
    conn.close()
    return duplicates

if __name__ == '__main__':
    print("🛠️ 修复文件系统零字节HTML文件")
    print("="*60)
    
    # 1. 修复零字节文件
    repaired, errors, remaining = fix_zero_byte_files()
    
    # 2. 检查重复记录
    duplicates = check_duplicate_documents()
    
    # 3. 建议
    print(f"\n📋 建议:")
    if remaining > 0:
        print(f"  ⚠️  仍有 {remaining} 个零字节文件需要手动检查")
    
    if duplicates:
        print(f"  ⚠️  发现 {len(duplicates)} 个重复记录，建议清理")
        print(f"     重复记录可能导致界面显示多个相同文件")
    
    if repaired > 0:
        print(f"  ✅ 成功修复 {repaired} 个文件")
    
    if errors > 0:
        print(f"  ❌ 有 {errors} 个文件修复失败，需要进一步调查")
    
    exit(0 if remaining == 0 else 1)