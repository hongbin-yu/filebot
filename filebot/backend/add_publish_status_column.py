#!/usr/bin/env python3
"""
添加publish_status列到documents表的迁移脚本
"""
import sqlite3
import sys

def add_publish_status_column():
    """向documents表添加publish_status列"""
    db_path = 'filebot.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查列是否已存在
        cursor.execute('PRAGMA table_info(documents)')
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'publish_status' in columns:
            print("✅ publish_status列已存在，跳过迁移")
            conn.close()
            return
        
        # 添加publish_status列，VARCHAR(12)足够存储'enum值'
        # 默认值为'unpublished'（小写以匹配枚举值）
        cursor.execute('''
            ALTER TABLE documents 
            ADD COLUMN publish_status VARCHAR(12) DEFAULT 'unpublished'
        ''')
        
        # 提交更改
        conn.commit()
        
        # 验证列已添加
        cursor.execute('PRAGMA table_info(documents)')
        columns = cursor.fetchall()
        publish_status_exists = any(col[1] == 'publish_status' for col in columns)
        
        if publish_status_exists:
            print("✅ 成功添加publish_status列到documents表")
            
            # 显示示例数据
            cursor.execute('SELECT id, original_filename, publish_status FROM documents LIMIT 5')
            samples = cursor.fetchall()
            print("\n📊 示例文档的发布状态:")
            for doc_id, filename, status in samples:
                print(f"  - {filename[:30]:30} -> {status}")
                
            # 统计状态分布
            cursor.execute('SELECT publish_status, COUNT(*) FROM documents GROUP BY publish_status')
            stats = cursor.fetchall()
            print("\n📈 发布状态统计:")
            for status, count in stats:
                print(f"  - {status}: {count}个文档")
        else:
            print("❌ 添加publish_status列失败")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ SQLite错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("🔧 开始迁移：添加publish_status列")
    add_publish_status_column()
    print("✅ 迁移完成")