#!/usr/bin/env python3
"""
将publish_status值从小写更新为大写
"""
import sqlite3

def update_publish_status_case():
    """将publish_status值从小写更新为大写"""
    db_path = 'filebot.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 统计当前值
        cursor.execute('SELECT publish_status, COUNT(*) FROM documents GROUP BY publish_status')
        before_stats = cursor.fetchall()
        print("📊 更新前的状态分布:")
        for status, count in before_stats:
            print(f"  - {status}: {count}个文档")
        
        # 更新小写值为大写
        cursor.execute('''
            UPDATE documents 
            SET publish_status = 'PUBLISHED' 
            WHERE publish_status = 'published'
        ''')
        updated_published = cursor.rowcount
        
        cursor.execute('''
            UPDATE documents 
            SET publish_status = 'UNPUBLISHED' 
            WHERE publish_status = 'unpublished'
        ''')
        updated_unpublished = cursor.rowcount
        
        conn.commit()
        
        # 统计更新后的值
        cursor.execute('SELECT publish_status, COUNT(*) FROM documents GROUP BY publish_status')
        after_stats = cursor.fetchall()
        
        print(f"\n✅ 更新完成:")
        print(f"  - 更新为PUBLISHED: {updated_published}个文档")
        print(f"  - 更新为UNPUBLISHED: {updated_unpublished}个文档")
        
        print("\n📊 更新后的状态分布:")
        for status, count in after_stats:
            print(f"  - {status}: {count}个文档")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ SQLite错误: {e}")

if __name__ == '__main__':
    print("🔧 更新publish_status值为大写")
    update_publish_status_case()
    print("✅ 更新完成")