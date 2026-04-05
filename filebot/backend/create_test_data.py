#!/usr/bin/env python3
"""
创建测试数据用于TIFF提取功能测试
"""

import sqlite3
import uuid
import os
import shutil
from pathlib import Path

def create_test_data():
    """创建测试数据"""
    # 连接数据库
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    # 用户ID (admin)
    user_id = '590aba86-6038-4a72-911a-ce18ab7e0b75'
    
    # 1. 创建应用
    app_id = '11111111-1111-1111-1111-111111111111'
    cursor.execute('''
        INSERT OR IGNORE INTO apps 
        (id, name, description, owner_id, settings, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (app_id, 'TIFF测试应用', '用于TIFF页面提取功能测试', 
          user_id, '{}', 'admin'))
    
    # 2. 创建抽屉
    drawer_id = '22222222-2222-2222-2222-222222222222'
    cursor.execute('''
        INSERT OR IGNORE INTO drawers
        (id, name, order_index, app_id, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (drawer_id, 'TIFF测试抽屉', 1, app_id))
    
    # 3. 创建文件夹
    folder_id = '33333333-3333-3333-3333-333333333333'
    cursor.execute('''
        INSERT OR IGNORE INTO folders
        (id, name, path, drawer_id, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (folder_id, 'TIFF测试文件夹', '/tiff_test', drawer_id))
    
    # 4. 创建文档记录
    doc_id = '44444444-4444-4444-4444-444444444444'
    tiff_file = '/mnt/c/workspace/tiff_input/fin00000.tif'
    
    if not Path(tiff_file).exists():
        print(f"错误: TIFF文件不存在: {tiff_file}")
        return False
    
    file_size = Path(tiff_file).stat().st_size
    
    cursor.execute('''
        INSERT OR IGNORE INTO documents
        (id, folder_id, original_filename, stored_filename, 
         file_size, file_type, mime_type, uploaded_by,
         conversion_status, page_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (
        doc_id, folder_id, 'fin00000.tif', f'{doc_id}.tif',
        file_size, 'tiff', 'image/tiff', user_id,
        'completed', 1
    ))
    
    # 提交事务
    conn.commit()
    
    # 5. 复制TIFF文件到存储目录
    storage_dir = Path('./data/files/original')
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    dest_file = storage_dir / f'{doc_id}.tif'
    shutil.copy2(tiff_file, dest_file)
    
    print(f"测试数据创建完成!")
    print(f"  应用ID: {app_id}")
    print(f"  抽屉ID: {drawer_id}")
    print(f"  文件夹ID: {folder_id}")
    print(f"  文档ID: {doc_id}")
    print(f"  文件复制到: {dest_file}")
    print(f"  文件大小: {file_size} 字节")
    
    # 验证数据
    print(f"\n验证数据:")
    cursor.execute("SELECT COUNT(*) FROM apps WHERE id=?", (app_id,))
    print(f"  应用记录: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM drawers WHERE id=?", (drawer_id,))
    print(f"  抽屉记录: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM folders WHERE id=?", (folder_id,))
    print(f"  文件夹记录: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM documents WHERE id=?", (doc_id,))
    print(f"  文档记录: {cursor.fetchone()[0]}")
    
    print(f"\n文件存在: {dest_file.exists()}")
    
    conn.close()
    return True

if __name__ == "__main__":
    success = create_test_data()
    if success:
        print("\n✅ 测试数据创建成功!")
        print("\n现在可以测试TIFF页面提取功能:")
        print("文档ID: 44444444-4444-4444-4444-444444444444")
        print("测试命令:")
        print("  curl -X POST 'http://localhost:8000/api/v1/documents/44444444-4444-4444-4444-444444444444/extract-tiff-pages?page_numbers=1&output_format=pdf' \\")
        print("    -H 'Authorization: Bearer YOUR_TOKEN' --output test_output.pdf")
    else:
        print("\n❌ 测试数据创建失败")