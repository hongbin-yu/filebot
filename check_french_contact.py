#!/usr/bin/env python3
"""
直接检查数据库中是否创建了法语contact页面
"""
import sqlite3
import sys

db_path = '/home/hongb/.openclaw/workspace/filebot/backend/filebot.db'

def check_french_contact():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print('🔍 检查数据库中的contact页面...')
    
    # 查询所有contact页面
    cursor.execute("SELECT id, parent_id, title, language FROM webbot_page WHERE id = 'contact'")
    rows = cursor.fetchall()
    
    print(f'找到 {len(rows)} 个contact页面:')
    for i, row in enumerate(rows):
        print(f'  {i+1}. id={row["id"]}, parent={row["parent_id"]}, language={row["language"]}, title={row["title"][:30] if row["title"] else "None"}')
    
    # 检查复合主键约束
    print('\n📊 复合主键验证:')
    cursor.execute("SELECT id, parent_id, COUNT(*) as count FROM webbot_page GROUP BY id, parent_id HAVING COUNT(*) > 1")
    dupes = cursor.fetchall()
    if dupes:
        print('❌ 发现重复的(id, parent_id)组合:')
        for row in dupes:
            print(f'  id={row["id"]}, parent={row["parent_id"]}, count={row["count"]}')
    else:
        print('✅ 没有重复的(id, parent_id)组合')
    
    # 检查表结构
    print('\n🗄️  表结构:')
    cursor.execute("PRAGMA table_info(webbot_page)")
    columns = cursor.fetchall()
    print('  列信息:')
    for col in columns:
        if col['name'] in ['id', 'parent_id']:
            print(f'    {col["name"]}: type={col["type"]}, pk={col["pk"]}')
    
    conn.close()
    
    # 检查法语contact是否创建
    french_exists = any(row["parent_id"] == "fr" for row in rows)
    if french_exists:
        print('\n✅ 法语contact页面已创建 (parent_id="fr")')
        return True
    else:
        print('\n❌ 法语contact页面未创建 (没有parent_id="fr"的记录)')
        return False

if __name__ == "__main__":
    check_french_contact()