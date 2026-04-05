#!/usr/bin/env python3
"""
Smarti数据库导入工具
采用混合策略：核心字段结构化，额外字段存metadata，包含权限数据
"""

import re
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import uuid

# 路径配置
BACKUP_DIR = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")
SMARTI_SCRIPT = BACKUP_DIR / "smarti.script.backup"
FILEBOT_DB = Path("filebot.db")
MAPPING_FILE = Path("smarti_import_mapping.json")

class SmartiImporter:
    def __init__(self):
        self.content = None
        self.tables_data = defaultdict(list)
        self.mappings = {
            'app': {},      # Smarti APP_ID -> FileBot app_id
            'fold': {},     # Smarti FOLD_ID -> FileBot folder_id
            'doc': {},      # Smarti DOC_ID -> FileBot document_id
            'external_file': {},  # Smarti EXTERNAL_FILE_ID -> FileBot document_id
            'user': {},     # Smarti USER_ID -> FileBot user_id
        }
        self.filebot_conn = None
        self.filebot_cursor = None
        
    def load_smarti_script(self):
        """加载Smarti SQL脚本"""
        print("📖 加载Smarti备份脚本...")
        with open(SMARTI_SCRIPT, 'r', encoding='utf-8', errors='ignore') as f:
            self.content = f.read()
        print(f"  文件大小: {len(self.content):,} 字符")
        
    def parse_insert_statements(self):
        """解析INSERT语句，提取表数据"""
        print("\n🔍 解析INSERT语句...")
        
        # 匹配INSERT语句的正则表达式
        insert_pattern = r'INSERT INTO (\w+) VALUES\((.*?)\)(?=\s*(?:INSERT|$))'
        
        # 由于文件很大，我们分块处理
        matches = re.findall(insert_pattern, self.content, re.MULTILINE | re.DOTALL)
        
        total_rows = 0
        for table_name, values_str in matches:
            # 解析VALUES部分（简单分割，注意处理引号内的逗号）
            values = self._parse_values(values_str)
            self.tables_data[table_name].append(values)
            total_rows += 1
            
            # 进度显示
            if total_rows % 1000 == 0:
                print(f"  已解析 {total_rows:,} 行...")
        
        print(f"✅ 解析完成: {total_rows:,} 行数据，{len(self.tables_data)} 个表")
        
        # 显示各表数据量
        print("\n📊 表数据统计:")
        for table_name in sorted(self.tables_data.keys()):
            count = len(self.tables_data[table_name])
            print(f"  {table_name:20} {count:6} 行")
            
    def _parse_values(self, values_str):
        """解析VALUES字符串，返回值列表"""
        # 简单实现：按逗号分割，但需要处理引号内的逗号
        values = []
        current = ""
        in_quotes = False
        quote_char = None
        
        for char in values_str:
            if char in ("'", '"') and not in_quotes:
                in_quotes = True
                quote_char = char
                current += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current += char
            elif char == ',' and not in_quotes:
                values.append(current.strip())
                current = ""
            else:
                current += char
        
        if current:
            values.append(current.strip())
        
        # 处理NULL值和引号
        processed = []
        for v in values:
            if v.upper() == 'NULL':
                processed.append(None)
            elif v.startswith("'") and v.endswith("'"):
                processed.append(v[1:-1].replace("''", "'"))
            elif v.startswith('"') and v.endswith('"'):
                processed.append(v[1:-1].replace('""', '"'))
            else:
                # 尝试转换为数字
                try:
                    if '.' in v:
                        processed.append(float(v))
                    else:
                        processed.append(int(v))
                except ValueError:
                    processed.append(v)
        
        return processed
    
    def connect_filebot(self):
        """连接FileBot数据库"""
        print("\n🔗 连接FileBot数据库...")
        self.filebot_conn = sqlite3.connect(FILEBOT_DB)
        self.filebot_cursor = self.filebot_conn.cursor()
        
        # 检查数据库结构
        self.filebot_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in self.filebot_cursor.fetchall()]
        print(f"  FileBot数据库包含 {len(tables)} 个表")
        
    def create_mapping_table(self):
        """创建映射表（如果不存在）"""
        print("\n🗂️  创建映射表...")
        
        self.filebot_cursor.execute("""
            CREATE TABLE IF NOT EXISTS smarti_import_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                smarti_table VARCHAR(50) NOT NULL,
                smarti_id VARCHAR(50) NOT NULL,
                filebot_table VARCHAR(50) NOT NULL,
                filebot_id VARCHAR(50) NOT NULL,
                original_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(smarti_table, smarti_id, filebot_table)
            )
        """)
        
        # 创建索引
        self.filebot_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_smarti_mapping 
            ON smarti_import_mapping(smarti_table, smarti_id)
        """)
        
        self.filebot_conn.commit()
        print("✅ 映射表创建完成")
        
    def import_apps(self):
        """导入应用数据"""
        print("\n📱 导入应用数据...")
        
        if 'APP' not in self.tables_data:
            print("  ❌ 没有找到APP表数据")
            return
        
        # 获取现有FileBot应用，避免重复
        self.filebot_cursor.execute("SELECT slug FROM apps")
        existing_slugs = {row[0] for row in self.filebot_cursor.fetchall()}
        
        # 获取admin用户ID
        self.filebot_cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_user_row = self.filebot_cursor.fetchone()
        admin_user_id = admin_user_row[0] if admin_user_row else '4dad6fa1-d521-417f-8877-efe95fcf1f04'
        
        apps_data = self.tables_data['APP']
        imported_count = 0
        
        for app_row in apps_data:
            # APP表结构: ID, DISPOSITIONID, NAME, CREATE_DATE, ADMIN_ID, COMMENTS, DELETED, QUERYSEC, VIEW_BASIC_QUERY, FORMTITLE
            if len(app_row) < 10:
                continue
                
            app_id, disposition_id, name, create_date, admin_id, comments, deleted, querysec, view_basic_query, formtitle = app_row
            
            # 生成slug（URL友好）
            slug = re.sub(r'[^\w\s-]', '', name).strip().lower()
            slug = re.sub(r'[-\s]+', '-', slug)
            slug = f"smarti-{slug}"  # 添加前缀避免冲突
            
            # 检查是否已存在
            if slug in existing_slugs:
                # 使用带ID的slug
                slug = f"smarti-{slug}-{app_id}"
            
            # 准备应用数据
            app_uuid = str(uuid.uuid4())
            app_data = {
                'id': app_uuid,
                'name': f"[Smarti] {name}",
                'slug': slug,
                'description': comments or f"从Smarti导入的应用: {name}",
                'owner_id': admin_user_id,
                'settings': {
                    'smarti_app_id': app_id,
                    'original_name': name,
                    'create_date': str(create_date),
                    'admin_id': admin_id,
                    'disposition_id': disposition_id,
                    'formtitle': formtitle,
                    'import_source': 'smarti',
                    'import_time': datetime.now().isoformat()
                }
            }
            
            # 插入数据库
            try:
                self.filebot_cursor.execute("""
                    INSERT INTO apps (id, name, slug, description, owner_id, settings, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 'smarti-importer')
                """, (
                    app_data['id'],
                    app_data['name'],
                    app_data['slug'],
                    app_data['description'],
                    app_data['owner_id'],
                    json.dumps(app_data['settings'])
                ))
                
                # 保存映射
                self.filebot_cursor.execute("""
                    INSERT INTO smarti_import_mapping 
                    (smarti_table, smarti_id, filebot_table, filebot_id, original_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    'APP',
                    str(app_id),
                    'apps',
                    app_data['id'],
                    json.dumps(app_row)
                ))
                
                self.mappings['app'][app_id] = app_data['id']
                imported_count += 1
                
            except sqlite3.IntegrityError as e:
                print(f"  ⚠️  应用 {name} 导入失败: {e}")
                continue
        
        self.filebot_conn.commit()
        print(f"✅ 应用导入完成: {imported_count}/{len(apps_data)} 个")
        
    def import_folders(self):
        """导入文件夹数据"""
        print("\n📁 导入文件夹数据...")
        
        if 'FOLD' not in self.tables_data:
            print("  ❌ 没有找到FOLD表数据")
            return
        
        # 建立DRAW到APP的映射
        draw_to_app = {}
        if 'DRAW' in self.tables_data:
            print("  📂 处理DRAW表映射...")
            for draw_row in self.tables_data['DRAW']:
                if len(draw_row) >= 2:
                    draw_id, app_id = draw_row[0], draw_row[1]
                    draw_to_app[draw_id] = app_id
        
        # 建立APP到FileBot应用ID的映射
        app_to_filebot = self.mappings['app']
        
        folds_data = self.tables_data['FOLD']
        imported_count = 0
        
        for fold_row in folds_data:
            # FOLD表结构: ID, PARENT_ID, NAME, CREATE_DATE, ADMIN_ID, DELETED, REPORTS
            if len(fold_row) < 7:
                continue
                
            fold_id, parent_id, name, create_date, admin_id, deleted, reports = fold_row
            
            # 找到对应的APP ID
            app_id = None
            if parent_id in draw_to_app:
                app_id = draw_to_app[parent_id]
            else:
                # 如果没有DRAW映射，使用第一个可用的APP
                if app_to_filebot:
                    app_id = list(app_to_filebot.keys())[0]
            
            if not app_id or app_id not in app_to_filebot:
                # 跳过没有对应APP的文件夹
                continue
                
            filebot_app_id = app_to_filebot[app_id]
            
            # 获取应用slug
            self.filebot_cursor.execute("SELECT slug FROM apps WHERE id = ?", (filebot_app_id,))
            app_slug_row = self.filebot_cursor.fetchone()
            if not app_slug_row:
                continue
                
            app_slug = app_slug_row[0]
            folder_path = f"/{app_slug}/{name.lower().replace(' ', '-')}"
            
            folder_uuid = str(uuid.uuid4())
            
            # 插入文件夹
            try:
                self.filebot_cursor.execute("""
                    INSERT INTO folders (id, app_id, name, path, description, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), 'smarti-importer')
                """, (
                    folder_uuid,
                    filebot_app_id,
                    name,
                    folder_path,
                    f"从Smarti导入的文件夹: {name} (原ID: {fold_id}, 应用: {app_id})"
                ))
                
                # 保存映射
                self.filebot_cursor.execute("""
                    INSERT INTO smarti_import_mapping 
                    (smarti_table, smarti_id, filebot_table, filebot_id, original_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    'FOLD',
                    str(fold_id),
                    'folders',
                    folder_uuid,
                    json.dumps(fold_row)
                ))
                
                self.mappings['fold'][fold_id] = folder_uuid
                imported_count += 1
                
            except sqlite3.Error as e:
                print(f"  ⚠️  文件夹 {name} 导入失败: {e}")
                continue
        
        self.filebot_conn.commit()
        print(f"✅ 文件夹导入完成: {imported_count}/{len(folds_data)} 个")
        
    def import_documents(self):
        """导入文档元数据"""
        print("\n📄 导入文档元数据...")
        
        if 'DOC' not in self.tables_data:
            print("  ❌ 没有找到DOC表数据")
            return
        
        # 获取admin用户ID
        self.filebot_cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_user_row = self.filebot_cursor.fetchone()
        admin_user_id = admin_user_row[0] if admin_user_row else '4dad6fa1-d521-417f-8877-efe95fcf1f04'
        
        # 需要EXTERNAL_FILE和PAGES表来获取文件信息
        external_files = {}
        if 'EXTERNAL_FILE' in self.tables_data:
            for row in self.tables_data['EXTERNAL_FILE']:
                if len(row) > 0:
                    external_files[row[0]] = row
        
        docs_data = self.tables_data['DOC']
        imported_count = 0
        
        for doc_row in docs_data:
            # DOC表结构: ID, PARENT_ID, NAME, CREATE_DATE, ADMIN_ID, DELETED, REPORTS
            if len(doc_row) < 7:
                continue
                
            doc_id, parent_id, name, create_date, admin_id, deleted, reports = doc_row
            
            # 查找对应的文件夹
            if parent_id not in self.mappings['fold']:
                # 如果没有文件夹映射，跳过
                continue
                
            folder_id = self.mappings['fold'][parent_id]
            
            # 查找对应的外部文件（如果有）
            file_info = None
            if doc_id in external_files:
                file_info = external_files[doc_id]
            
            # 确定文件名和文件类型
            original_filename = f"{name}.tif"
            file_type = 'tiff'
            mime_type = 'image/tiff'
            file_size = 0
            
            if file_info and len(file_info) > 4:
                # EXTERNAL_FILE结构: ID, VOLUME_ID, DISPOSITIONID, REPORT_ID, PATH, IS_IMAGE, IROWS, ICOLS, CREATE_DATE, FILE_SIZE, ...
                path = file_info[4]  # PATH字段
                if path and isinstance(path, str):
                    original_filename = Path(path).name
                    # 根据扩展名确定文件类型
                    ext = Path(path).suffix.lower()
                    if ext in ['.tif', '.tiff']:
                        file_type = 'tiff'
                        mime_type = 'image/tiff'
                    elif ext in ['.pdf']:
                        file_type = 'pdf'
                        mime_type = 'application/pdf'
                    elif ext in ['.jpg', '.jpeg']:
                        file_type = 'jpeg'
                        mime_type = 'image/jpeg'
                    elif ext in ['.png']:
                        file_type = 'png'
                        mime_type = 'image/png'
                    elif ext in ['.txt']:
                        file_type = 'txt'
                        mime_type = 'text/plain'
                    elif ext in ['.html', '.htm']:
                        file_type = 'html'
                        mime_type = 'text/html'
                
                # 文件大小
                if len(file_info) > 9:
                    file_size_val = file_info[9]  # FILE_SIZE字段
                    if file_size_val:
                        try:
                            file_size = int(float(file_size_val))
                        except:
                            file_size = 0
            
            # 构建元数据
            metadata = {
                'smarti_doc_id': doc_id,
                'original_name': name,
                'create_date': str(create_date),
                'admin_id': admin_id,
                'deleted': deleted,
                'reports': reports,
                'import_source': 'smarti',
                'import_time': datetime.now().isoformat()
            }
            
            # 添加外部文件信息（如果存在）
            if file_info:
                metadata['external_file_info'] = {
                    'id': file_info[0],
                    'volume_id': file_info[1],
                    'disposition_id': file_info[2],
                    'report_id': file_info[3],
                    'path': file_info[4] if len(file_info) > 4 else None,
                    'is_image': file_info[5] if len(file_info) > 5 else None,
                    'rows': file_info[6] if len(file_info) > 6 else None,
                    'cols': file_info[7] if len(file_info) > 7 else None,
                    'file_size': file_info[9] if len(file_info) > 9 else None
                }
            
            # 插入文档
            try:
                self.filebot_cursor.execute("""
                    INSERT INTO documents (
                        id, folder_id, title, original_filename, stored_filename,
                        file_size, file_type, mime_type, document_metadata,
                        uploaded_by, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'smarti-importer')
                """, (
                    str(uuid.uuid4()),
                    folder_id,
                    name,
                    original_filename,
                    f"{uuid.uuid4()}{Path(original_filename).suffix}",  # 存储文件名
                    file_size,
                    file_type,
                    mime_type,
                    json.dumps(metadata),
                    admin_user_id  # 上传者ID
                ))
                
                # 保存映射（需要获取最后插入的ID）
                self.filebot_cursor.execute("SELECT last_insert_rowid()")
                last_rowid = self.filebot_cursor.fetchone()[0]
                self.filebot_cursor.execute("SELECT id FROM documents WHERE rowid = ?", (last_rowid,))
                doc_uuid = self.filebot_cursor.fetchone()[0]
                
                self.filebot_cursor.execute("""
                    INSERT INTO smarti_import_mapping 
                    (smarti_table, smarti_id, filebot_table, filebot_id, original_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    'DOC',
                    str(doc_id),
                    'documents',
                    doc_uuid,
                    json.dumps(doc_row)
                ))
                
                self.mappings['doc'][doc_id] = doc_uuid
                imported_count += 1
                
            except sqlite3.Error as e:
                print(f"  ⚠️  文档 {name} 导入失败: {e}")
                continue
        
        self.filebot_conn.commit()
        print(f"✅ 文档导入完成: {imported_count}/{len(docs_data)} 个")
        
    def import_permissions(self):
        """导入权限数据"""
        print("\n🔐 导入权限数据...")
        
        # 导入AUTHORITY表
        if 'AUTHORITY' in self.tables_data:
            authority_data = self.tables_data['AUTHORITY']
            print(f"  👥 找到 {len(authority_data)} 条权限记录")
            
            # 将权限数据保存到设置中或单独的表
            for auth_row in authority_data:
                if len(auth_row) >= 2:
                    role_name, user_name = auth_row[0], auth_row[1]
                    # 保存到映射表供后续使用
                    self.filebot_cursor.execute("""
                        INSERT INTO smarti_import_mapping 
                        (smarti_table, smarti_id, filebot_table, filebot_id, original_data)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        'AUTHORITY',
                        f"{role_name}:{user_name}",
                        'permissions',
                        'smarti-authority',
                        json.dumps(auth_row)
                    ))
        
        # 导入RECORD_CLASS_SECURITY表
        if 'RECORD_CLASS_SECURITY' in self.tables_data:
            security_data = self.tables_data['RECORD_CLASS_SECURITY']
            print(f"  🔒 找到 {len(security_data)} 条记录类安全设置")
            
            for sec_row in security_data:
                if len(sec_row) >= 2:
                    user_name, record_class_id = sec_row[0], sec_row[1]
                    self.filebot_cursor.execute("""
                        INSERT INTO smarti_import_mapping 
                        (smarti_table, smarti_id, filebot_table, filebot_id, original_data)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        'RECORD_CLASS_SECURITY',
                        f"{user_name}:{record_class_id}",
                        'permissions',
                        'smarti-security',
                        json.dumps(sec_row)
                    ))
        
        self.filebot_conn.commit()
        print("✅ 权限数据导入完成")
        
    def save_mapping_file(self):
        """保存映射数据到JSON文件"""
        print("\n💾 保存映射数据...")
        
        mapping_data = {
            'import_time': datetime.now().isoformat(),
            'smarti_source': str(SMARTI_SCRIPT),
            'mappings': self.mappings,
            'table_counts': {table: len(data) for table, data in self.tables_data.items()}
        }
        
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 映射数据已保存到: {MAPPING_FILE}")
        
    def generate_import_report(self):
        """生成导入报告"""
        print("\n" + "="*60)
        print("📊 Smarti数据库导入报告")
        print("="*60)
        
        # 统计导入数量
        total_smarti_rows = sum(len(data) for data in self.tables_data.values())
        print(f"Smarti数据总量: {total_smarti_rows:,} 行")
        
        # 检查导入结果
        self.filebot_cursor.execute("SELECT COUNT(*) FROM smarti_import_mapping")
        mapping_count = self.filebot_cursor.fetchone()[0]
        print(f"导入映射记录: {mapping_count:,} 条")
        
        # 各类型统计
        print("\n导入统计:")
        for map_type, mapping in self.mappings.items():
            if mapping:
                print(f"  {map_type:15} {len(mapping):6} 条")
        
        # 建议下一步
        print("\n🚀 下一步建议:")
        print("1. 检查导入的数据完整性")
        print("2. 处理实际文件（将Smarti备份文件复制到FileBot存储）")
        print("3. 测试导出功能（使用保存的映射数据）")
        print("4. 验证权限和数据访问控制")
        
    def run(self):
        """运行导入流程"""
        print("="*60)
        print("🚀 Smarti数据库导入工具 - 混合策略导入")
        print("="*60)
        
        try:
            # 1. 加载数据
            self.load_smarti_script()
            self.parse_insert_statements()
            
            # 2. 连接数据库
            self.connect_filebot()
            self.create_mapping_table()
            
            # 3. 分步导入
            self.import_apps()
            self.import_folders()
            self.import_documents()
            self.import_permissions()
            
            # 4. 保存结果
            self.save_mapping_file()
            self.generate_import_report()
            
            print("\n🎉 导入完成！")
            
        except Exception as e:
            print(f"\n❌ 导入过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            if self.filebot_conn:
                self.filebot_conn.close()
                print("\n🔌 数据库连接已关闭")

if __name__ == "__main__":
    importer = SmartiImporter()
    importer.run()