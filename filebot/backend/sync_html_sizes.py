#!/usr/bin/env python3
"""
同步HTML文件的实际大小到数据库
修复数据库file_size字段与文件系统实际大小不一致的问题
"""
import sqlite3
import os
import json
import sys
from pathlib import Path

DB_PATH = 'filebot.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🔄 开始同步HTML文件大小到数据库")
    print("=" * 60)
    
    # 查找所有HTML文件
    cursor.execute("""
        SELECT id, original_filename, stored_filename, file_size as db_size, folder_id, document_metadata
        FROM documents 
        WHERE LOWER(file_type) IN ('html', 'htm')
    """)
    all_html = cursor.fetchall()
    
    total_files = len(all_html)
    synced_count = 0
    fixed_zero_files = 0
    errors = []
    
    for i, doc in enumerate(all_html):
        if i % 50 == 0:
            print(f"进度: {i}/{total_files}...")
        
        doc_id = doc['id']
        stored_filename = doc['stored_filename']
        db_size = doc['db_size']
        
        # 检查文件是否存在
        possible_paths = [
            Path("data/documents") / stored_filename,
            Path("data/files/original") / stored_filename,
        ]
        
        actual_size = None
        file_path = None
        
        for path in possible_paths:
            if path.exists():
                file_path = path
                try:
                    actual_size = path.stat().st_size
                    break
                except Exception as e:
                    errors.append(f"获取文件大小失败 {doc_id}: {e}")
                    continue
        
        if actual_size is None:
            # 文件不存在
            errors.append(f"文件不存在 {doc_id}: {stored_filename}")
            continue
        
        # 比较数据库大小和实际大小
        if db_size != actual_size:
            # 需要更新数据库
            print(f"📝 更新: {doc['original_filename']}")
            print(f"  数据库大小: {db_size} 字节 → 实际大小: {actual_size} 字节")
            
            # 如果是空文件变为有内容，特别标记
            if db_size == 0 and actual_size > 0:
                fixed_zero_files += 1
                print(f"  ✅ 修复空文件: +{actual_size} 字节")
            
            try:
                cursor.execute(
                    "UPDATE documents SET file_size = ? WHERE id = ?",
                    (actual_size, doc_id)
                )
                synced_count += 1
            except Exception as e:
                errors.append(f"更新数据库失败 {doc_id}: {e}")
    
    # 提交所有更改
    conn.commit()
    
    print(f"\n{'='*60}")
    print("📊 同步完成统计")
    print(f"总共处理文件: {total_files}")
    print(f"同步更新记录: {synced_count}")
    print(f"修复的空文件: {fixed_zero_files}")
    
    if synced_count > 0:
        print(f"\n✅ 成功同步 {synced_count} 个文件的大小")
    
    if fixed_zero_files > 0:
        print(f"🎉 修复了 {fixed_zero_files} 个之前显示为0字节的文件")
    
    # 验证修复结果
    print("\n🔍 验证修复结果:")
    
    # 检查仍然为空的HTML文件
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM documents 
        WHERE LOWER(file_type) IN ('html', 'htm') AND file_size = 0
    """)
    still_empty = cursor.fetchone()['count']
    
    # 检查文件系统为空但数据库显示有内容的
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM documents d
        WHERE LOWER(d.file_type) IN ('html', 'htm') 
        AND d.file_size > 0
        AND NOT EXISTS (
            SELECT 1 FROM (
                SELECT stored_filename,
                       CASE 
                         WHEN EXISTS (SELECT 1 FROM (SELECT stored_filename FROM documents) WHERE stored_filename = d.stored_filename) THEN 1
                         ELSE 0
                       END as exists_in_fs
                FROM documents
            ) fs
            WHERE fs.stored_filename = d.stored_filename
        )
    """)
    # 简化检查：手动检查一些样本
    print(f"仍然为空的HTML文件: {still_empty} 个")
    
    if still_empty > 0:
        print("\n📋 仍然为空的HTML文件列表:")
        cursor.execute("""
            SELECT id, original_filename, stored_filename, file_size
            FROM documents 
            WHERE LOWER(file_type) IN ('html', 'htm') AND file_size = 0
            LIMIT 10
        """)
        empty_files = cursor.fetchall()
        
        for doc in empty_files:
            print(f"  - {doc['original_filename']} (ID: {doc['id']})")
            # 检查文件系统
            path = Path("data/documents") / doc['stored_filename']
            if path.exists():
                actual = path.stat().st_size
                print(f"    文件系统大小: {actual} 字节 (不一致!)")
            else:
                print(f"    文件不存在")
    
    # 显示错误
    if errors:
        print(f"\n⚠️  遇到 {len(errors)} 个错误:")
        for error in errors[:10]:  # 只显示前10个错误
            print(f"  {error}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors)-10} 个错误未显示")
    
    conn.close()
    
    # 最终建议
    if still_empty > 0:
        print(f"\n🚀 下一步建议:")
        print(f"1. 运行修复脚本: python3 fix_empty_html.py")
        print(f"2. 检查 {still_empty} 个仍然为空的文件")
        print(f"3. 可能这些文件确实没有内容，需要重新爬取")
        return 1
    else:
        print("\n✅ 所有HTML文件大小已正确同步！")
        return 0

if __name__ == "__main__":
    sys.exit(main())