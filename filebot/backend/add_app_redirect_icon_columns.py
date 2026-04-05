#!/usr/bin/env python3
"""
添加redirect_url和icon列到apps表的迁移脚本
"""
import sqlite3
import sys

def add_app_columns():
    """向apps表添加redirect_url和icon列"""
    db_path = 'filebot.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查列是否已存在
        cursor.execute('PRAGMA table_info(apps)')
        columns = [col[1] for col in cursor.fetchall()]
        
        columns_added = []
        
        # 添加redirect_url列
        if 'redirect_url' not in columns:
            cursor.execute('''
                ALTER TABLE apps 
                ADD COLUMN redirect_url VARCHAR(500)
            ''')
            columns_added.append('redirect_url')
            print("✅ 添加redirect_url列")
        else:
            print("ℹ️  redirect_url列已存在")
        
        # 添加icon列  
        if 'icon' not in columns:
            cursor.execute('''
                ALTER TABLE apps 
                ADD COLUMN icon VARCHAR(200)
            ''')
            columns_added.append('icon')
            print("✅ 添加icon列")
        else:
            print("ℹ️  icon列已存在")
        
        # 提交更改
        if columns_added:
            conn.commit()
            print(f"✅ 成功添加列: {', '.join(columns_added)}")
            
            # 显示一些应用数据
            cursor.execute('SELECT id, name, redirect_url, icon FROM apps LIMIT 5')
            apps = cursor.fetchall()
            
            if apps:
                print("\n📊 应用数据示例:")
                for app_id, name, redirect_url, icon in apps:
                    redirect_display = redirect_url[:30] + '...' if redirect_url and len(redirect_url) > 30 else redirect_url or 'NULL'
                    icon_display = icon[:20] + '...' if icon and len(icon) > 20 else icon or 'NULL'
                    print(f"  - {name[:25]:25} | 重定向: {redirect_display:35} | 图标: {icon_display}")
        else:
            print("ℹ️  所有列都已存在，无需更改")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ SQLite错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("🔧 开始迁移：添加redirect_url和icon列到apps表")
    add_app_columns()
    print("✅ 迁移完成")