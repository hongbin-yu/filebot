#!/usr/bin/env python3
"""
清理FileBot数据库中的重复文档记录。
保留每个stored_filename的最新记录（MAX(id)）。
"""

import sqlite3
import os
import shutil
from datetime import datetime

def main():
    db_path = 'filebot.db'
    
    if not os.path.exists(db_path):
        print(f'❌ 数据库文件不存在: {db_path}')
        return
    
    # 备份数据库
    backup_path = f'filebot_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    print(f'🔒 备份数据库到: {backup_path}')
    shutil.copy2(db_path, backup_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 开始事务
        cursor.execute('BEGIN TRANSACTION')
        
        # 1. 检查清理前状态
        print('\n📊 清理前数据库状态:')
        cursor.execute('SELECT COUNT(*) FROM documents')
        total_before = cursor.fetchone()[0]
        print(f'   总文档记录数: {total_before}')
        
        cursor.execute('''
            SELECT COUNT(DISTINCT stored_filename) 
            FROM documents 
            WHERE stored_filename IS NOT NULL AND stored_filename != ''
        ''')
        unique_files_before = cursor.fetchone()[0]
        print(f'   唯一文件数: {unique_files_before}')
        
        # 检查重复记录
        cursor.execute('''
            SELECT stored_filename, COUNT(*) as cnt 
            FROM documents 
            WHERE stored_filename IS NOT NULL AND stored_filename != ''
            GROUP BY stored_filename 
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
        ''')
        duplicates = cursor.fetchall()
        print(f'   有重复的文件名数: {len(duplicates)}')
        
        duplicate_total = sum(cnt for _, cnt in duplicates)
        print(f'   重复记录总数: {duplicate_total}')
        
        if duplicates:
            print('\n🔴 前5个最严重的重复:')
            for i, (filename, cnt) in enumerate(duplicates[:5]):
                print(f'   {i+1}. {filename}: {cnt}个记录')
        
        # 2. 执行清理
        print('\n🗑️  执行重复记录清理...')
        
        # 方法：删除不是每个stored_filename最新ID的记录
        cursor.execute('''
            DELETE FROM documents 
            WHERE id IN (
                SELECT d.id
                FROM documents d
                WHERE d.stored_filename IS NOT NULL 
                  AND d.stored_filename != ''
                  AND EXISTS (
                    SELECT 1
                    FROM documents d2
                    WHERE d2.stored_filename = d.stored_filename
                      AND d2.id > d.id
                  )
            )
        ''')
        
        deleted_count = cursor.rowcount
        print(f'   删除了 {deleted_count} 个重复记录')
        
        # 3. 检查清理后状态
        cursor.execute('SELECT COUNT(*) FROM documents')
        total_after = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT stored_filename, COUNT(*) as cnt 
            FROM documents 
            WHERE stored_filename IS NOT NULL AND stored_filename != ''
            GROUP BY stored_filename 
            HAVING COUNT(*) > 1
        ''')
        remaining_duplicates = cursor.fetchall()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT stored_filename) 
            FROM documents 
            WHERE stored_filename IS NOT NULL AND stored_filename != ''
        ''')
        unique_files_after = cursor.fetchone()[0]
        
        # 4. 提交事务
        conn.commit()
        
        print('\n✅ 清理完成!')
        print(f'📊 清理前记录数: {total_before}')
        print(f'🗑️  删除的重复记录: {deleted_count}')
        print(f'📊 清理后记录数: {total_after}')
        print(f'📈 清理后唯一文件数: {unique_files_after}')
        print(f'🔍 剩余重复文件名: {len(remaining_duplicates)}')
        
        if remaining_duplicates:
            print('⚠️  仍有重复文件需要处理:')
            for filename, cnt in remaining_duplicates:
                print(f'   - {filename}: {cnt}个记录')
        
        # 5. 统计清理效果
        reduction = total_before - total_after
        reduction_percent = (reduction / total_before * 100) if total_before > 0 else 0
        print(f'\n🎯 清理效果:')
        print(f'   记录数减少: {reduction} ({reduction_percent:.1f}%)')
        print(f'   数据库空间预计节省: {reduction} 条记录')
        
        # 6. 检查其他问题
        cursor.execute('''
            SELECT COUNT(*) 
            FROM documents 
            WHERE stored_filename IS NULL OR stored_filename = ''
        ''')
        null_count = cursor.fetchone()[0]
        if null_count > 0:
            print(f'\n⚠️  发现 {null_count} 个stored_filename为空/空的记录')
            print('   这些记录未被清理，可能需要手动处理')
        
    except Exception as e:
        conn.rollback()
        print(f'\n❌ 清理失败: {e}')
        raise
    finally:
        conn.close()
        print('\n🔧 数据库连接已关闭')

if __name__ == '__main__':
    main()