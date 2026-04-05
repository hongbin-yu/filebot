#!/usr/bin/env python3
"""
WebBot数据库迁移脚本
将webbot_page表的主键从单一id改为复合主键(id, parent_id)
以支持多语言相同页面名（如/en/contact和/fr/contact）
"""

import sqlite3
import os
import sys
import time
import shutil

def backup_database(db_path):
    """创建数据库备份"""
    timestamp = int(time.time())
    backup_path = f"{db_path}.backup.{timestamp}"
    
    print(f"创建数据库备份: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    # 同时创建一个最近的备份链接，方便恢复
    recent_backup = f"{db_path}.backup.recent"
    if os.path.exists(recent_backup):
        os.remove(recent_backup)
    os.symlink(backup_path, recent_backup)
    
    return backup_path

def check_database_state(db_path):
    """检查数据库当前状态"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== 检查数据库状态 ===")
    
    # 1. 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_page'")
    if not cursor.fetchone():
        print("错误: webbot_page表不存在")
        conn.close()
        return False
    
    # 2. 检查是否有重复的(id, parent_id)组合
    cursor.execute('''
        SELECT id, parent_id, COUNT(*) as cnt 
        FROM webbot_page 
        GROUP BY id, parent_id 
        HAVING cnt > 1
    ''')
    duplicates = cursor.fetchall()
    if duplicates:
        print("警告: 发现重复的(id, parent_id)组合:")
        for dup in duplicates:
            print(f"  id={dup[0]}, parent_id={dup[1]}, 数量={dup[2]}")
        # 这不应该发生，但我们会继续
    
    # 3. 统计页面数量
    cursor.execute("SELECT COUNT(*) FROM webbot_page")
    total_pages = cursor.fetchone()[0]
    print(f"总页面数: {total_pages}")
    
    # 4. 检查外键依赖
    cursor.execute("SELECT COUNT(*) FROM webbot_page_tag")
    tag_count = cursor.fetchone()[0]
    print(f"页面标签关联数: {tag_count}")
    
    conn.close()
    return True

def migrate_database(db_path):
    """执行数据库迁移"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\\n=== 开始数据库迁移 ===")
    
    # 启用外键约束（SQLite默认关闭）
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # 步骤1: 创建新表结构（使用复合主键）
    print("1. 创建新表 webbot_page_new...")
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
    print("2. 复制数据到新表...")
    cursor.execute('''
        INSERT INTO webbot_page_new 
        SELECT 
            id, title, content, language, parent_id, other_lang_page_id,
            status, created_by, created_at, last_modified, last_published,
            metadata, description, hide_in_navigation, keywords
        FROM webbot_page
    ''')
    
    # 步骤3: 复制页面标签关联（如果有的话）
    cursor.execute("SELECT COUNT(*) FROM webbot_page_tag")
    tag_count = cursor.fetchone()[0]
    if tag_count > 0:
        print(f"3. 复制 {tag_count} 个页面标签关联...")
        # 注意：webbot_page_tag表使用page_id作为外键
        # 由于我们只改变了主键定义，但没有改变id值，所以关联仍然有效
        pass  # 不需要操作，因为外键引用的是id字段
    
    # 步骤4: 创建索引
    print("4. 创建索引...")
    cursor.execute("CREATE INDEX idx_webbot_page_parent_new ON webbot_page_new(parent_id)")
    cursor.execute("CREATE INDEX idx_webbot_page_language_new ON webbot_page_new(language)")
    cursor.execute("CREATE INDEX idx_webbot_page_status_new ON webbot_page_new(status)")
    
    # 步骤5: 验证数据完整性
    print("5. 验证数据完整性...")
    cursor.execute("SELECT COUNT(*) FROM webbot_page_new")
    new_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM webbot_page")
    old_count = cursor.fetchone()[0]
    
    if new_count != old_count:
        print(f"错误: 数据数量不匹配! 旧表: {old_count}, 新表: {new_count}")
        conn.rollback()
        conn.close()
        return False
    
    print(f"数据验证通过: 迁移了 {new_count} 条记录")
    
    # 步骤6: 删除旧索引
    print("6. 删除旧索引...")
    cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_parent")
    cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_language")
    cursor.execute("DROP INDEX IF EXISTS idx_webbot_page_status")
    
    # 步骤7: 备份旧表并重命名新表
    print("7. 替换表...")
    cursor.execute("ALTER TABLE webbot_page RENAME TO webbot_page_old")
    cursor.execute("ALTER TABLE webbot_page_new RENAME TO webbot_page")
    
    # 步骤8: 重命名索引
    print("8. 重命名索引...")
    cursor.execute("ALTER INDEX idx_webbot_page_parent_new RENAME TO idx_webbot_page_parent")
    cursor.execute("ALTER INDEX idx_webbot_page_language_new RENAME TO idx_webbot_page_language")
    cursor.execute("ALTER INDEX idx_webbot_page_status_new RENAME TO idx_webbot_page_status")
    
    # 步骤9: 验证主键约束
    print("9. 验证主键约束...")
    cursor.execute('''
        SELECT id, parent_id, COUNT(*) as cnt 
        FROM webbot_page 
        GROUP BY id, parent_id 
        HAVING cnt > 1
    ''')
    duplicates = cursor.fetchone()
    if duplicates:
        print(f"警告: 迁移后仍有重复记录: id={duplicates[0]}, parent_id={duplicates[1]}")
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print("\\n✅ 数据库迁移完成!")
    return True

def test_migration(db_path):
    """测试迁移后的数据库"""
    print("\\n=== 测试迁移结果 ===")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 检查表结构
    cursor.execute("PRAGMA table_info(webbot_page)")
    columns = cursor.fetchall()
    print("1. 表结构验证:")
    has_composite_pk = False
    for col in columns:
        if col[1] == 'id' and col[5] > 0:
            print(f"   {col[1]}: 是主键的一部分 (pk={col[5]})")
            has_composite_pk = True
    
    if not has_composite_pk:
        print("   警告: 未检测到复合主键")
    
    # 2. 尝试插入多语言相同ID的测试数据
    print("\\n2. 测试多语言相同ID支持:")
    
    # 检查是否已存在en和fr根页面
    cursor.execute("SELECT id FROM webbot_page WHERE id='en' AND parent_id IS NULL")
    if not cursor.fetchone():
        print("   跳过测试: 'en'根页面不存在")
    else:
        cursor.execute("SELECT id FROM webbot_page WHERE id='fr' AND parent_id IS NULL")
        if not cursor.fetchone():
            print("   跳过测试: 'fr'根页面不存在")
        else:
            # 尝试创建法语contact页面（如果英语contact已存在）
            cursor.execute("SELECT id FROM webbot_page WHERE id='contact' AND parent_id='en'")
            if cursor.fetchone():
                print("   'contact'页面已存在 (parent_id='en')")
                
                # 尝试插入法语版本
                try:
                    cursor.execute('''
                        INSERT INTO webbot_page 
                        (id, title, content, language, parent_id, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        'contact', 
                        'Contactez-nous (测试)',
                        '<p>Page de contact en français</p>',
                        'fr',
                        'fr',
                        'draft'
                    ))
                    conn.commit()
                    print("   ✅ 成功插入法语'contact'页面 (parent_id='fr')")
                    
                    # 清理测试数据
                    cursor.execute("DELETE FROM webbot_page WHERE id='contact' AND parent_id='fr' AND title LIKE '%(测试)%'")
                    conn.commit()
                    print("   已清理测试数据")
                    
                except sqlite3.IntegrityError as e:
                    print(f"   ❌ 插入失败: {e}")
                    conn.rollback()
    
    # 3. 测试路径查找
    print("\\n3. 测试路径解析逻辑:")
    
    def find_page_by_path(path_parts):
        """模拟API中的路径查找逻辑"""
        current_parent = None
        for part in path_parts:
            if current_parent is None:
                cursor.execute("SELECT id FROM webbot_page WHERE id=? AND parent_id IS NULL", (part,))
            else:
                cursor.execute("SELECT id FROM webbot_page WHERE id=? AND parent_id=?", (part, current_parent))
            
            page = cursor.fetchone()
            if not page:
                return None
            current_parent = page[0]
        
        return current_parent
    
    # 测试 /en/contact
    result = find_page_by_path(['en', 'contact'])
    if result:
        print(f"   ✅ /en/contact -> 找到页面: id={result}")
    else:
        print("   ❌ /en/contact -> 未找到")
    
    conn.close()
    return True

def main():
    """主函数"""
    db_path = "filebot/backend/filebot.db"
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    print("WebBot数据库迁移工具")
    print("=" * 50)
    
    # 检查当前目录
    if not os.path.exists("webbot"):
        print("警告: 当前目录可能不是OpenClaw工作空间根目录")
    
    # 第一步：检查数据库状态
    if not check_database_state(db_path):
        print("数据库状态检查失败，中止迁移")
        sys.exit(1)
    
    # 第二步：确认用户
    print("\\n=== 确认操作 ===")
    print("此操作将修改数据库结构：")
    print("  - 将webbot_page表的主键改为复合主键(id, parent_id)")
    print("  - 支持多语言相同页面名（如/en/contact和/fr/contact）")
    print("  - 创建数据库备份")
    print("  - WebBot服务需要重启")
    
    response = input("\\n是否继续? (yes/no): ")
    if response.lower() != 'yes':
        print("操作取消")
        sys.exit(0)
    
    # 第三步：创建备份
    backup_path = backup_database(db_path)
    print(f"备份已创建: {backup_path}")
    
    # 第四步：执行迁移
    if not migrate_database(db_path):
        print("迁移失败，已回滚")
        sys.exit(1)
    
    # 第五步：测试迁移
    test_migration(db_path)
    
    print("\\n" + "=" * 50)
    print("迁移完成!")
    print(f"原始数据库备份: {backup_path}")
    print("下一步:")
    print("1. 重启WebBot服务")
    print("2. 测试页面创建功能")
    print("3. 测试路径参数功能")
    print("=" * 50)

if __name__ == "__main__":
    main()