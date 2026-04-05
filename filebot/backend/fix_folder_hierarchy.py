#!/usr/bin/env python3
"""
修复Smarti文件夹层级结构
创建DRAW文件夹并建立正确的父子关系
"""

import re
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import uuid
import hashlib

# 路径配置
BACKUP_FILE = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924/smarti.script.backup")
FILEBOT_DB = Path("filebot.db")
MAPPING_FILE = Path("smarti_import_mapping.json")

class FolderHierarchyFixer:
    def __init__(self):
        self.content = None
        self.draws = []
        self.folds = []
        self.mapping = None
        self.conn = None
        self.cursor = None
        self.draw_folders_created = {}  # DRAW_ID -> FileBot folder_id
        self.updated_folders = 0
        
    def load_data(self):
        """加载数据和映射"""
        print("📖 加载数据和映射...")
        
        # 加载映射文件
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            self.mapping = json.load(f)
        
        # 加载原始SQL脚本
        with open(BACKUP_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            self.content = f.read()
        
        # 解析DRAW数据
        draw_pattern = r"INSERT INTO DRAW VALUES\((\d+),(\d+),'([^']*)','([^']*)',([^,]*),([^,]*),([^)]*)\)"
        draw_matches = re.findall(draw_pattern, self.content)
        
        for match in draw_matches:
            draw_id, app_id, name, create_date, admin_id, deleted, draw_order = match
            self.draws.append({
                'draw_id': draw_id,
                'app_id': app_id,
                'name': name.strip(),
                'create_date': create_date,
                'admin_id': admin_id,
                'deleted': deleted,
                'draw_order': draw_order
            })
        
        print(f"  解析到 {len(self.draws)} 个DRAW记录")
        
        # 解析FOLD数据
        fold_pattern = r"INSERT INTO FOLD VALUES\((\d+),(\d+),'([^']*)','([^']*)',([^,]*),([^,]*),([^)]*)\)"
        fold_matches = re.findall(fold_pattern, self.content)
        
        for match in fold_matches:
            fold_id, parent_id, name, create_date, admin_id, deleted, reports = match
            self.folds.append({
                'fold_id': fold_id,
                'parent_id': parent_id,
                'name': name.strip(),
                'create_date': create_date,
                'admin_id': admin_id,
                'deleted': deleted,
                'reports': reports
            })
        
        print(f"  解析到 {len(self.folds)} 个FOLD记录")
        
        # 连接数据库
        self.conn = sqlite3.connect(FILEBOT_DB)
        self.cursor = self.conn.cursor()
        
    def generate_slug(self, name):
        """生成文件夹slug"""
        # 简单实现：小写，替换空格为横线，移除特殊字符
        slug = name.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)  # 移除特殊字符
        slug = re.sub(r'[-\s]+', '-', slug)   # 空格和多个横线替换为单个横线
        slug = slug.strip('-')
        return slug
    
    def get_app_mapping(self, smarti_app_id):
        """获取APP映射"""
        app_mapping = self.mapping['mappings']['app']
        return app_mapping.get(str(smarti_app_id))
    
    def create_draw_folder(self, draw):
        """创建DRAW文件夹"""
        draw_id = draw['draw_id']
        draw_name = draw['name']
        smarti_app_id = draw['app_id']
        
        # 检查是否已存在
        if draw_id in self.draw_folders_created:
            return self.draw_folders_created[draw_id]
        
        # 获取对应的FileBot应用ID
        filebot_app_id = self.get_app_mapping(smarti_app_id)
        if not filebot_app_id:
            print(f"  ⚠️  DRAW {draw_id} ({draw_name}) 没有对应的APP映射 (Smarti APP ID: {smarti_app_id})")
            return None
        
        # 获取应用slug
        self.cursor.execute("SELECT slug FROM apps WHERE id = ?", (filebot_app_id,))
        app_slug_row = self.cursor.fetchone()
        if not app_slug_row:
            print(f"  ❌ 找不到应用: {filebot_app_id}")
            return None
        
        app_slug = app_slug_row[0]
        
        # 生成DRAW文件夹slug
        base_slug = self.generate_slug(draw_name)
        slug = base_slug
        
        # 检查slug是否已存在（在同一个应用下）
        counter = 1
        while True:
            self.cursor.execute(
                "SELECT id FROM folders WHERE app_id = ? AND path LIKE ?",
                (filebot_app_id, f'%/{slug}')
            )
            if not self.cursor.fetchone():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # 生成文件夹路径
        path = f"/{app_slug}/{slug}"
        
        # 创建文件夹ID
        folder_id = str(uuid.uuid4())
        
        # 插入数据库
        try:
            self.cursor.execute("""
                INSERT INTO folders 
                (id, app_id, parent_folder_id, name, path, description, 
                 is_system_folder, order_index, created_at, created_by, updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'hierarchy-fixer', datetime('now'), 'hierarchy-fixer')
            """, (
                folder_id,
                filebot_app_id,
                None,  # DRAW文件夹在应用根目录下
                f"[DRAW] {draw_name}",
                path,
                f"从Smarti导入的DRAW: {draw_name} (原始ID: {draw_id})",
                False,
                0
            ))
            
            # 添加到映射表
            self.cursor.execute("""
                INSERT INTO smarti_import_mapping 
                (smarti_table, smarti_id, filebot_table, filebot_id, original_data)
                VALUES (?, ?, ?, ?, ?)
            """, (
                'DRAW',
                str(draw_id),
                'folders',
                folder_id,
                json.dumps(draw)
            ))
            
            self.draw_folders_created[draw_id] = folder_id
            print(f"  ✅ 创建DRAW文件夹: {draw_name} ({folder_id})")
            
            return folder_id
            
        except sqlite3.IntegrityError as e:
            print(f"  ❌ 创建DRAW文件夹失败: {e}")
            return None
    
    def update_fold_parents(self):
        """更新FOLD文件夹的父级关系"""
        print("\n🔄 更新FOLD文件夹父级关系...")
        
        fold_mapping = self.mapping['mappings']['fold']  # Smarti FOLD_ID -> FileBot folder_id
        
        updated_count = 0
        errors = []
        
        for fold in self.folds:
            fold_id = fold['fold_id']
            parent_draw_id = fold['parent_id']
            
            # 获取FileBot文件夹ID
            filebot_folder_id = fold_mapping.get(str(fold_id))
            if not filebot_folder_id:
                errors.append(f"找不到FOLD {fold_id} ({fold['name']}) 的映射")
                continue
            
            # 获取DRAW文件夹ID
            draw_folder_id = self.draw_folders_created.get(parent_draw_id)
            if not draw_folder_id:
                errors.append(f"FOLD {fold_id} 的父DRAW {parent_draw_id} 没有对应的文件夹")
                continue
            
            # 更新parent_folder_id
            try:
                self.cursor.execute(
                    "UPDATE folders SET parent_folder_id = ?, updated_at = datetime('now') WHERE id = ?",
                    (draw_folder_id, filebot_folder_id)
                )
                
                updated_count += 1
                
            except sqlite3.Error as e:
                errors.append(f"更新FOLD {fold_id} 失败: {e}")
        
        self.conn.commit()
        
        print(f"  ✅ 更新了 {updated_count}/{len(self.folds)} 个FOLD文件夹")
        if errors:
            print(f"  ⚠️  错误 ({len(errors)} 个):")
            for error in errors[:5]:
                print(f"    {error}")
            if len(errors) > 5:
                print(f"    ... 还有 {len(errors)-5} 个错误")
        
        self.updated_folders = updated_count
        
    def update_folder_paths(self):
        """更新文件夹路径"""
        print("\n🔄 更新文件夹路径...")
        
        # 获取所有需要更新的文件夹（包括DRAW和FOLD）
        all_folder_ids = list(self.draw_folders_created.values())
        
        # 添加FOLD文件夹ID
        fold_mapping = self.mapping['mappings']['fold']
        for fold_id, filebot_id in fold_mapping.items():
            all_folder_ids.append(filebot_id)
        
        # 去重
        all_folder_ids = list(set(all_folder_ids))
        
        updated_count = 0
        
        for folder_id in all_folder_ids:
            # 获取文件夹信息
            self.cursor.execute(
                "SELECT id, name, parent_folder_id, app_id FROM folders WHERE id = ?",
                (folder_id,)
            )
            row = self.cursor.fetchone()
            if not row:
                continue
                
            folder_id, name, parent_id, app_id = row
            
            # 获取应用slug
            self.cursor.execute("SELECT slug FROM apps WHERE id = ?", (app_id,))
            app_slug_row = self.cursor.fetchone()
            if not app_slug_row:
                continue
            app_slug = app_slug_row[0]
            
            # 构建路径
            if parent_id:
                # 获取父文件夹路径
                self.cursor.execute("SELECT path FROM folders WHERE id = ?", (parent_id,))
                parent_path_row = self.cursor.fetchone()
                if parent_path_row:
                    parent_path = parent_path_row[0]
                    # 生成当前文件夹slug
                    slug = self.generate_slug(name)
                    # 检查同父文件夹下是否有相同slug
                    base_slug = slug
                    counter = 1
                    while True:
                        test_path = f"{parent_path}/{slug}"
                        self.cursor.execute(
                            "SELECT id FROM folders WHERE path = ? AND id != ?",
                            (test_path, folder_id)
                        )
                        if not self.cursor.fetchone():
                            break
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                    
                    new_path = f"{parent_path}/{slug}"
                else:
                    # 父文件夹不存在，使用根路径
                    slug = self.generate_slug(name)
                    new_path = f"/{app_slug}/{slug}"
            else:
                # 根文件夹（DRAW文件夹）
                slug = self.generate_slug(name)
                new_path = f"/{app_slug}/{slug}"
            
            # 更新路径
            self.cursor.execute(
                "UPDATE folders SET path = ?, updated_at = datetime('now') WHERE id = ?",
                (new_path, folder_id)
            )
            updated_count += 1
        
        self.conn.commit()
        print(f"  ✅ 更新了 {updated_count} 个文件夹的路径")
        
    def verify_fix(self):
        """验证修复结果"""
        print("\n🔍 验证修复结果...")
        
        # 检查有父文件夹的FOLD数量
        fold_mapping = self.mapping['mappings']['fold']
        fold_ids = list(fold_mapping.values())
        
        if not fold_ids:
            print("  ⚠️  没有FOLD文件夹ID")
            return
        
        self.cursor.execute(f"""
            SELECT COUNT(*) FROM folders 
            WHERE id IN ({','.join(['?']*len(fold_ids))}) 
            AND parent_folder_id IS NOT NULL
        """, fold_ids)
        
        with_parent = self.cursor.fetchone()[0]
        
        print(f"  FOLD文件夹有父级的: {with_parent}/{len(fold_ids)}")
        
        # 检查DRAW文件夹数量
        draw_folder_ids = list(self.draw_folders_created.values())
        if draw_folder_ids:
            self.cursor.execute(f"""
                SELECT COUNT(*) FROM folders 
                WHERE id IN ({','.join(['?']*len(draw_folder_ids))})
            """, draw_folder_ids)
            draw_count = self.cursor.fetchone()[0]
            print(f"  DRAW文件夹数量: {draw_count}/{len(draw_folder_ids)}")
        
        # 检查层级深度
        print("\n📊 层级结构示例:")
        self.cursor.execute("""
            SELECT f1.name, f1.path, f2.name as parent_name
            FROM folders f1
            LEFT JOIN folders f2 ON f1.parent_folder_id = f2.id
            WHERE f1.id IN (SELECT filebot_id FROM smarti_import_mapping WHERE smarti_table = 'FOLD')
            LIMIT 5
        """)
        
        examples = self.cursor.fetchall()
        for child_name, path, parent_name in examples:
            if parent_name:
                print(f"  {child_name} -> {parent_name} ({path})")
            else:
                print(f"  {child_name} (根文件夹, {path})")
        
    def backup_database(self):
        """备份数据库"""
        print("\n💾 备份数据库...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"filebot_backup_before_hierarchy_fix_{timestamp}.db"
        
        import shutil
        shutil.copy2(FILEBOT_DB, backup_path)
        print(f"  ✅ 数据库已备份到: {backup_path}")
        
    def run(self):
        """执行修复"""
        print("=" * 60)
        print("Smarti文件夹层级结构修复")
        print("=" * 60)
        
        # 备份数据库
        self.backup_database()
        
        # 加载数据
        self.load_data()
        
        print("\n🔄 创建DRAW文件夹...")
        for draw in self.draws:
            self.create_draw_folder(draw)
        
        print(f"\n✅ 创建了 {len(self.draw_folders_created)}/{len(self.draws)} 个DRAW文件夹")
        
        # 更新FOLD父级关系
        self.update_fold_parents()
        
        # 更新路径
        self.update_folder_paths()
        
        # 验证
        self.verify_fix()
        
        # 关闭连接
        self.conn.close()
        
        print("\n" + "=" * 60)
        print("修复完成")
        print("=" * 60)
        print(f"📊 修复统计:")
        print(f"  - 创建的DRAW文件夹: {len(self.draw_folders_created)}")
        print(f"  - 更新的FOLD文件夹: {self.updated_folders}")
        print(f"\n⚠️  注意: 可能需要重启后端服务以应用更改")

def main():
    fixer = FolderHierarchyFixer()
    try:
        fixer.run()
    except Exception as e:
        print(f"\n❌ 修复过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()