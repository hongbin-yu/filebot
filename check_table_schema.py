#!/usr/bin/env python3
import sqlite3
import sys

def check_table_schema():
    db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查webbot_page表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_page'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ webbot_page表不存在")
            return
        
        # 获取表结构
        cursor.execute("PRAGMA table_info(webbot_page)")
        columns = cursor.fetchall()
        
        print("📋 webbot_page表结构:")
        print("-" * 80)
        print(f"{'序号':<4} {'字段名':<30} {'类型':<20} {'非空':<5} {'默认值':<20}")
        print("-" * 80)
        
        for col in columns:
            cid, name, type_, notnull, dflt_value, pk = col
            print(f"{cid:<4} {name:<30} {type_:<20} {notnull:<5} {str(dflt_value)[:20]:<20}")
        
        print("-" * 80)
        print(f"总计: {len(columns)} 个字段")
        
        # 检查是否有description字段
        description_exists = any(col[1] == 'description' for col in columns)
        print(f"\n📝 description字段存在: {'✅' if description_exists else '❌'}")
        
        # 检查是否有hide_in_navigation字段
        hide_exists = any(col[1] == 'hide_in_navigation' or col[1] == 'hide_in_nav' for col in columns)
        print(f"🔒 hide_in_navigation字段存在: {'✅' if hide_exists else '❌'}")
        
        # 查看前几条数据样本
        cursor.execute("SELECT id, title, language_code, status FROM webbot_page LIMIT 5")
        rows = cursor.fetchall()
        
        print(f"\n📊 数据样本 (前{len(rows)}条):")
        for row in rows:
            print(f"  - {row[0]}: {row[1]} ({row[2]}, {row[3]})")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_table_schema()