#!/usr/bin/env python3
"""
将图片文档的发布状态更新为published
"""
import sqlite3

def update_image_documents():
    """将所有图片文档的publish_status设置为published"""
    db_path = 'filebot.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 首先查找所有图片文档（注意：file_type存储为大写）
        cursor.execute('''
            SELECT id, original_filename, file_type, publish_status 
            FROM documents 
            WHERE file_type IN ('JPG', 'JPEG', 'PNG', 'TIFF', 'GIF')
        ''')
        image_docs = cursor.fetchall()
        
        print(f"📊 找到 {len(image_docs)} 个图片文档")
        
        # 更新这些文档为published状态
        update_count = 0
        for doc_id, filename, file_type, current_status in image_docs:
            # 只更新当前为unpublished的文档
            if current_status == 'unpublished':
                cursor.execute('''
                    UPDATE documents 
                    SET publish_status = 'published' 
                    WHERE id = ?
                ''', (doc_id,))
                update_count += 1
                print(f"  - 更新: {filename} ({file_type}) -> published")
        
        conn.commit()
        
        # 验证更新
        cursor.execute('''
            SELECT publish_status, COUNT(*) 
            FROM documents 
            WHERE file_type IN ('jpg', 'jpeg', 'png', 'tiff', 'gif')
            GROUP BY publish_status
        ''')
        stats = cursor.fetchall()
        
        print(f"\n✅ 成功更新 {update_count} 个图片文档为published状态")
        print("📈 图片文档发布状态统计:")
        for status, count in stats:
            print(f"  - {status}: {count}个文档")
        
        # 总体统计
        cursor.execute('SELECT publish_status, COUNT(*) FROM documents GROUP BY publish_status')
        total_stats = cursor.fetchall()
        print("\n📊 所有文档发布状态统计:")
        for status, count in total_stats:
            print(f"  - {status}: {count}个文档")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ SQLite错误: {e}")

if __name__ == '__main__':
    print("🔧 更新图片文档发布状态为published")
    update_image_documents()
    print("✅ 更新完成")