#!/usr/bin/env python3
"""
为应用(apps)和抽屉(drawers)表添加slug字段的迁移脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def main():
    """执行数据库迁移"""
    # 使用SQLite数据库连接
    db_url = settings.DATABASE_URL
    print(f"连接数据库: {db_url}")
    
    engine = create_engine(db_url)
    
    with engine.begin() as conn:
        # 1. 为apps表添加slug字段
        print("检查apps表的slug字段...")
        result = conn.execute(text("PRAGMA table_info(apps)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'slug' not in columns:
            print("添加slug字段到apps表...")
            conn.execute(text("ALTER TABLE apps ADD COLUMN slug VARCHAR(120)"))
            # 添加唯一索引
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_apps_slug ON apps (slug)"))
            print("✓ apps表slug字段添加完成")
        else:
            print("✓ apps表已有slug字段")
        
        # 2. 为drawers表添加slug字段
        print("\n检查drawers表的slug字段...")
        result = conn.execute(text("PRAGMA table_info(drawers)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'slug' not in columns:
            print("添加slug字段到drawers表...")
            conn.execute(text("ALTER TABLE drawers ADD COLUMN slug VARCHAR(120)"))
            # 添加索引（不需要唯一，因为同一应用内唯一即可）
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_drawers_slug ON drawers (slug)"))
            print("✓ drawers表slug字段添加完成")
        else:
            print("✓ drawers表已有slug字段")
        
        # 3. 为现有的应用和抽屉生成slug值
        print("\n为现有数据生成slug值...")
        
        # 生成应用的slug
        result = conn.execute(text("SELECT id, name FROM apps WHERE slug IS NULL OR slug = ''"))
        apps = result.fetchall()
        
        for app_id, app_name in apps:
            # 生成简单的slug（转换为小写，替换空格为短横线）
            import re
            slug = re.sub(r'[^a-z0-9]+', '-', app_name.lower().strip())
            slug = re.sub(r'^-+|-+$', '', slug)  # 移除开头和结尾的短横线
            
            # 确保slug不为空
            if not slug:
                slug = f"app-{app_id[:8]}"
            
            # 更新数据库
            conn.execute(
                text("UPDATE apps SET slug = :slug WHERE id = :id"),
                {"slug": slug, "id": app_id}
            )
            print(f"  应用 '{app_name}' → slug: '{slug}'")
        
        # 生成抽屉的slug
        result = conn.execute(text("""
            SELECT d.id, d.name, a.slug as app_slug 
            FROM drawers d 
            JOIN apps a ON d.app_id = a.id 
            WHERE d.slug IS NULL OR d.slug = ''
        """))
        drawers = result.fetchall()
        
        for drawer_id, drawer_name, app_slug in drawers:
            # 生成简单的slug
            import re
            slug = re.sub(r'[^a-z0-9]+', '-', drawer_name.lower().strip())
            slug = re.sub(r'^-+|-+$', '', slug)  # 移除开头和结尾的短横线
            
            # 确保slug不为空
            if not slug:
                slug = f"drawer-{drawer_id[:8]}"
            
            # 更新数据库
            conn.execute(
                text("UPDATE drawers SET slug = :slug WHERE id = :id"),
                {"slug": slug, "id": drawer_id}
            )
            print(f"  抽屉 '{drawer_name}' (应用: {app_slug}) → slug: '{slug}'")
    
    print("\n✅ 数据库迁移完成！")
    print("   应用的slug字段: 唯一索引")
    print("   抽屉的slug字段: 普通索引（同一应用内唯一）")

if __name__ == "__main__":
    main()