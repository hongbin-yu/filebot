#!/usr/bin/env python3
"""
清理旧的Smarti导入数据
"""

import sqlite3
import json

def cleanup_smarti():
    conn = sqlite3.connect('filebot.db')
    cursor = conn.cursor()
    
    print("🧹 清理旧的Smarti导入数据...")
    
    # 1. 删除映射表
    print("  删除映射表...")
    cursor.execute("DROP TABLE IF EXISTS smarti_import_mapping")
    
    # 2. 查找并删除Smarti应用及其相关数据
    cursor.execute("SELECT id FROM apps WHERE name LIKE '[Smarti]%' OR slug LIKE 'smarti%'")
    smarti_app_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"  找到 {len(smarti_app_ids)} 个Smarti应用")
    
    for app_id in smarti_app_ids:
        # 删除应用下的文件夹
        cursor.execute("SELECT id FROM folders WHERE app_id = ?", (app_id,))
        folder_ids = [row[0] for row in cursor.fetchall()]
        
        if folder_ids:
            print(f"    删除应用 {app_id} 的 {len(folder_ids)} 个文件夹...")
            # 删除文件夹下的文档
            placeholders = ','.join(['?' for _ in folder_ids])
            cursor.execute(f"DELETE FROM documents WHERE folder_id IN ({placeholders})", folder_ids)
            # 删除文件夹
            cursor.execute(f"DELETE FROM folders WHERE id IN ({placeholders})", folder_ids)
        
        # 删除应用
        cursor.execute("DELETE FROM apps WHERE id = ?", (app_id,))
    
    # 3. 删除文档元数据中包含smarti的文档（备用）
    cursor.execute("DELETE FROM documents WHERE document_metadata LIKE '%smarti%'")
    
    conn.commit()
    conn.close()
    
    print("✅ 清理完成")

if __name__ == "__main__":
    cleanup_smarti()