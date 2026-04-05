#!/usr/bin/env python3
"""
WebBot数据库迁移脚本（非交互式）
将webbot_page表的主键从单一id改为复合主键(id, parent_id)
"""

import sqlite3
import os
import sys
import time
import shutil

def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def backup_database(db_path):
    """创建数据库备份"""
    timestamp = int(time.time())
    backup_path = f"{db_path}.backup.{timestamp}"
    
    log(f"创建数据库备份: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    # 同时创建一个最近的备份链接，方便恢复
    recent_backup = f"{db_path}.backup.recent"
    if os.path.exists(recent_backup):
        os.remove(recent_backup)
    try:
        os.symlink(backup_path, recent_backup)
        log(f"创建备份链接: {recent_backup} -> {backup_path}")
    except:
        pass  # 如果无法创建链接也没关系
    
    return backup_path

def check_database_state(db_path):
    """检查数据库当前状态"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    log("检查数据库状态")
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_page'")
    if not cursor.fetchone():
        log("错误: webbot_page表不存在")
        conn.close()
        return False
    
    # 检查是否有重复的(id, parent_id)组合
    cursor.execute('''
        SELECT id, parent_id, COUNT(*) as cnt 
        FROM webbot_page 
        GROUP BY id, parent_id 
        HAVING cnt > 1
    ''')
    duplicates = cursor.fetchall()
    if duplicates:
        log("警告: 发现重复的(id, parent_id)组合:")
        for dup in duplicates:
            log(f"  id={dup[0]}, parent_id={dup[1]}, 数量={dup[2]}")
    
    # 统计页面数量
    cursor.execute("SELECT COUNT(*) FROM webbot_page")
    total_pages = cursor.fetchone()[0]
    log(f"总页面数: {total_pages}")
    
    # 检查外键依赖
    cursor.execute("SELECT COUNT(*) FROM webbot_page_tag")
    tag_count = cursor.fetchone()[0]
    log(f"页面标签关联数: {tag_count}")
    
    conn.close()
    return True

def migrate_database(db_path):
    """执行数据库迁移"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    log("开始数据库迁移")
    
    # 启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON")
    
    try:
        # 步骤1: 创建新表结构（使用复合主键）
        log("1. 创建新表 webbot_page_new...")
        cursor.execute('''
            CREATE TABLE webbot_page_new (
                id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                language TEXT DEFAULT 'en',
                parent_id TEXT,
                other_lang_page_id TEXT,
                status TEXT DEFAULT 'draft',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_published TIMESTAMP,
                metadata TEXT,
                description TEXT,
                hide_in_navigation BOOLEAN DEFAULT 0,
                keywords TEXT DEFAULT '',
                PRIMARY KEY (id, parent_id)
            )
        ''')
        
        # 步骤2: 复制数据到新表
        log("2. 复制数据到新表...")
        cursor.execute('''
            INSERT INTO webbot_page_new 
            SELECT 
                id, title, content, language, parent_id, other_lang_page_id,
                status, created_by, created_at, last_modified, last_published,
                metadata, description, hide_in_navigation, keywords
            FROM webbot_page
        ''')
        
        # 步骤3: 创建索引
        log("3. 创建索引...")
        cursor.execute("CREATE INDEX idx_webbot_page_parent_new ON webbot_page_new(parent_id)")
        cursor.execute("CREATE INDEX idx_webbot_page_language_new ON webbot_page_new(language)")
        cursor.execute("CREATE INDEX idx_webbot_page_status_new ON webbot_page_new(status)")
        
        # 步骤4: 验证数据完整性
        log("4. 验证数据完整性...")
        cursor.execute("SELECT COUNT(*) FROM webbot_page_new")
        new_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM webbot_page")
        old_count = cursor.fetchone()[0]
        
        if new_count != old_count:
            log(f"错误: 数据数量不匹配! 旧表: {old_count}, 新表: {new_count}")
            raise Exception("数据数量不匹配")
        
        log(f"数据验证通过: 迁移了 {new_count} 条记录")
        
        # 步骤5: 删除旧索引
        log("5. 删除旧索引...")
        cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_parent")
        cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_language")
        cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_status")
        
        # 步骤6: 备份旧表并重命名新表
        log("6. 替换表...")
        cursor.execute("ALTER TABLE webbot_page RENAME TO webbot_page_old")
        cursor.execute("ALTER TABLE webbot_page_new RENAME TO webbot_page")
        
        # 步骤7: 删除新索引并创建与原名称相同的索引
        log("7. 重建索引使用原名...")
        cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_parent_new")
        cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_language_new")
        cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_status_new")
        
        # 创建与原名称相同的索引
        cursor.execute("CREATE INDEX idx_webbot_page_parent ON webbot_page(parent_id)")
        cursor.execute("CREATE INDEX idx_webbot_page_language ON webbot_page(language)")
        cursor.execute("CREATE INDEX idx_webbot_page_status ON webbot_page(status)")
        
        # 步骤8: 验证主键约束
        log("8. 验证主键约束...")
        cursor.execute('''
            SELECT id, parent_id, COUNT(*) as cnt 
            FROM webbot_page 
            GROUP BY id, parent_id 
            HAVING cnt > 1
        ''')
        duplicates = cursor.fetchone()
        if duplicates:
            log(f"警告: 迁移后仍有重复记录: id={duplicates[0]}, parent_id={duplicates[1]}")
        
        # 提交更改
        conn.commit()
        log("数据库迁移完成!")
        
    except Exception as e:
        log(f"迁移过程中出错: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()
    
    return True

def test_migration(db_path):
    """测试迁移后的数据库"""
    log("测试迁移结果")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 检查表结构
    cursor.execute("PRAGMA table_info(webbot_page)")
    columns = cursor.fetchall()
    log("1. 表结构验证:")
    pk_columns = []
    for col in columns:
        if col[5] > 0:
            pk_columns.append(col[1])
    
    if len(pk_columns) >= 2 and 'id' in pk_columns and 'parent_id' in pk_columns:
        log(f"   ✅ 复合主键设置正确: {pk_columns}")
    else:
        log(f"   ❌ 主键设置可能有问题: {pk_columns}")
    
    # 2. 测试多语言相同ID支持
    log("2. 测试多语言相同ID支持:")
    
    # 检查是否已存在en和fr根页面
    cursor.execute("SELECT id FROM webbot_page WHERE id='en' AND parent_id IS NULL")
    en_exists = cursor.fetchone()
    
    cursor.execute("SELECT id FROM webbot_page WHERE id='fr' AND parent_id IS NULL")
    fr_exists = cursor.fetchone()
    
    if en_exists and fr_exists:
        # 尝试创建法语contact页面（如果英语contact已存在）
        cursor.execute("SELECT id FROM webbot_page WHERE id='contact' AND parent_id='en'")
        if cursor.fetchone():
            log("   'contact'页面已存在 (parent_id='en')")
            
            # 尝试插入法语版本
            try:
                cursor.execute('''
                    INSERT INTO webbot_page 
                    (id, title, content, language, parent_id, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'contact', 
                    'Contactez-nous (测试迁移)',
                    '<p>Page de contact en français</p>',
                    'fr',
                    'fr',
                    'draft'
                ))
                conn.commit()
                log("   ✅ 成功插入法语'contact'页面 (parent_id='fr')")
                
                # 清理测试数据
                cursor.execute("DELETE FROM webbot_page WHERE id='contact' AND parent_id='fr' AND title LIKE '%(测试迁移)%'")
                conn.commit()
                log("   已清理测试数据")
                
            except sqlite3.IntegrityError as e:
                log(f"   ❌ 插入失败: {e}")
                conn.rollback()
    else:
        log("   跳过测试: 必要的根页面不存在")
    
    conn.close()
    log("迁移测试完成")
    return True

def main():
    """主函数"""
    db_path = "filebot/backend/filebot.db"
    
    if not os.path.exists(db_path):
        log(f"错误: 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    log("WebBot数据库迁移开始")
    log("将webbot_page表的主键改为复合主键(id, parent_id)")
    log(f"数据库路径: {db_path}")
    log(f"当前工作目录: {os.getcwd()}")
    
    # 检查当前目录
    if not os.path.exists("webbot"):
        log("警告: 当前目录可能不是OpenClaw工作空间根目录")
    
    # 第一步：检查数据库状态
    if not check_database_state(db_path):
        log("数据库状态检查失败，中止迁移")
        sys.exit(1)
    
    # 第二步：创建备份
    try:
        backup_path = backup_database(db_path)
        log(f"备份已创建: {backup_path}")
    except Exception as e:
        log(f"备份失败: {e}")
        sys.exit(1)
    
    # 第三步：执行迁移
    try:
        if migrate_database(db_path):
            log("数据库迁移成功!")
    except Exception as e:
        log(f"迁移失败: {e}")
        log(f"请恢复备份: {backup_path}")
        sys.exit(1)
    
    # 第四步：测试迁移
    try:
        test_migration(db_path)
    except Exception as e:
        log(f"迁移测试出错: {e}")
        # 测试失败不一定需要回滚
    
    log("=" * 50)
    log("数据库迁移完成!")
    log(f"原始数据库备份: {backup_path}")
    log("下一步:")
    log("1. 重启WebBot服务")
    log("2. 测试页面创建功能")
    log("3. 测试路径参数功能")
    log("=" * 50)

if __name__ == "__main__":
    main()