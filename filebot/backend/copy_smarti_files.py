#!/usr/bin/env python3
"""
从Smarti备份复制实际文件到FileBot存储
"""

import os
import shutil
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# 路径配置
BACKUP_ROOT = Path("/home/hongb/.openclaw/workspace/filebot/backups/production_migration_20260321_175924")
FILEBOT_DB = Path("filebot.db")
STORAGE_BASE = Path("backend/data/files/original")

class FileCopier:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.stats = {
            'total': 0,
            'found': 0,
            'copied': 0,
            'skipped': 0,
            'errors': 0,
            'size_updated': 0
        }
        
    def connect_db(self):
        """连接数据库"""
        self.conn = sqlite3.connect(FILEBOT_DB)
        self.cursor = self.conn.cursor()
        
    def close_db(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            
    def find_backup_file(self, original_filename):
        """在备份目录中查找文件（改进版：使用文件名匹配）"""
        # 从原始文件名提取目标文件名
        # 格式如 "smarti.002\\00000002.CLD" 或 "smarti.002\\IDX00034.CLD"
        if '\\' in original_filename:
            target_filename = original_filename.split('\\')[1]
        else:
            target_filename = original_filename
        
        # 清理文件名：移除可能的特殊字符
        target_filename = target_filename.strip()
        
        # 递归搜索所有备份子目录
        for root, dirs, files in os.walk(BACKUP_ROOT):
            for file in files:
                if file == target_filename:
                    return Path(root) / file
        
        # 如果没有找到完全匹配，尝试大小写不敏感匹配
        target_lower = target_filename.lower()
        for root, dirs, files in os.walk(BACKUP_ROOT):
            for file in files:
                if file.lower() == target_lower:
                    return Path(root) / file
        
        # 如果还是找不到，尝试部分匹配（对于有特殊前缀的文件）
        # 例如，数据库中是 "....00000004.pdf" 但实际文件是 "00000004.pdf"
        if target_filename.startswith('....'):
            simplified = target_filename[4:]  # 移除前导的"...."
            for root, dirs, files in os.walk(BACKUP_ROOT):
                for file in files:
                    if file == simplified:
                        return Path(root) / file
        
        # 记录找不到的文件
        print(f"  ⚠️  警告: 在备份中找不到文件: {target_filename} (原始: {original_filename})")
        return None
    
    def copy_file_for_document(self, doc_id, stored_filename, original_filename):
        """为单个文档复制文件"""
        # 检查目标文件是否已存在
        target_dir = STORAGE_BASE
        target_path = target_dir / stored_filename
        
        # 确保目标目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 如果目标文件已存在，跳过
        if target_path.exists():
            file_size = target_path.stat().st_size
            self.stats['skipped'] += 1
            return True, file_size, "文件已存在"
        
        # 在备份中查找源文件
        source_path = self.find_backup_file(original_filename)
        if not source_path:
            return False, 0, f"找不到源文件: {original_filename}"
        
        # 复制文件
        try:
            shutil.copy2(source_path, target_path)
            file_size = target_path.stat().st_size
            
            # 更新数据库中的文件大小
            self.cursor.execute(
                "UPDATE documents SET file_size = ?, updated_at = datetime('now') WHERE id = ?",
                (file_size, doc_id)
            )
            
            self.stats['copied'] += 1
            self.stats['size_updated'] += 1
            return True, file_size, f"复制成功: {source_path} -> {target_path}"
            
        except Exception as e:
            return False, 0, f"复制失败: {e}"
    
    def process_documents(self, limit=None):
        """处理所有需要文件的文档"""
        print("🔍 查找需要复制文件的文档...")
        
        # 查询所有Smarti导入的文档，优先处理那些还没有文件大小的
        self.cursor.execute("""
            SELECT d.id, d.stored_filename, d.original_filename, d.file_size
            FROM documents d
            WHERE d.original_filename IS NOT NULL 
              AND d.original_filename != ''
              AND (d.file_size IS NULL OR d.file_size = 0)
              AND (d.original_filename LIKE '%smarti.%' OR d.original_filename LIKE '%.CLD' OR d.original_filename LIKE '%.cld' OR d.original_filename LIKE '%.pcl' OR d.original_filename LIKE '%.afp' OR d.original_filename LIKE '%.tif')
            ORDER BY 
              CASE 
                WHEN d.original_filename LIKE '%smarti.%' THEN 1
                ELSE 2
              END,
              d.created_at
        """)
        
        documents = self.cursor.fetchall()
        
        if limit:
            documents = documents[:limit]
        
        self.stats['total'] = len(documents)
        print(f"  找到 {len(documents)} 个需要文件的文档")
        
        if not documents:
            return
        
        # 处理每个文档
        for i, (doc_id, stored_filename, original_filename, current_size) in enumerate(documents, 1):
            print(f"\n[{i}/{len(documents)}] 处理: {original_filename}")
            
            if not stored_filename:
                print("  ⚠️  没有stored_filename，跳过")
                self.stats['errors'] += 1
                continue
            
            # 检查存储文件名是否有扩展名，如果没有则添加
            if '.' not in stored_filename:
                # 从原始文件名获取扩展名
                ext = Path(original_filename).suffix
                stored_filename = stored_filename + ext
            
            success, file_size, message = self.copy_file_for_document(
                doc_id, stored_filename, original_filename
            )
            
            if success:
                print(f"  ✅ {message}")
                if file_size:
                    print(f"     文件大小: {file_size} 字节 ({file_size/1024:.1f} KB)")
                self.stats['found'] += 1
            else:
                print(f"  ❌ {message}")
                self.stats['errors'] += 1
            
            # 每处理10个文档提交一次
            if i % 10 == 0:
                self.conn.commit()
                print(f"  💾 已提交 {i} 个文档")
        
        # 最终提交
        self.conn.commit()
        
    def verify_files(self):
        """验证文件复制结果"""
        print("\n🔍 验证文件复制结果...")
        
        # 查询文件大小更新情况
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN file_size IS NOT NULL AND file_size > 0 THEN 1 ELSE 0 END) as has_size
            FROM documents
            WHERE original_filename IS NOT NULL AND original_filename != ''
        """)
        
        total, has_size = self.cursor.fetchone()
        
        print(f"  总文档数: {total}")
        print(f"  有文件大小的: {has_size} ({has_size/total*100:.1f}%)")
        
        # 检查实际文件存在情况
        self.cursor.execute("""
            SELECT stored_filename FROM documents 
            WHERE file_size > 0 
            LIMIT 5
        """)
        
        sample_files = self.cursor.fetchall()
        
        print("\n  文件存在检查（抽样）:")
        for (stored_filename,) in sample_files:
            if stored_filename:
                file_path = STORAGE_BASE / stored_filename
                if file_path.exists():
                    size = file_path.stat().st_size
                    print(f"    ✅ {stored_filename}: {size} 字节")
                else:
                    print(f"    ❌ {stored_filename}: 文件不存在")
        
    def run(self, limit=None):
        """运行文件复制"""
        print("=" * 60)
        print("Smarti文件复制工具")
        print("=" * 60)
        
        # 检查备份目录
        if not BACKUP_ROOT.exists():
            print(f"❌ 备份目录不存在: {BACKUP_ROOT}")
            return
        
        # 检查存储目录
        STORAGE_BASE.mkdir(parents=True, exist_ok=True)
        
        # 连接数据库
        self.connect_db()
        
        try:
            # 处理文档
            self.process_documents(limit)
            
            # 验证结果
            self.verify_files()
            
            # 打印统计信息
            print("\n" + "=" * 60)
            print("📊 复制统计")
            print("=" * 60)
            print(f"  总文档数: {self.stats['total']}")
            print(f"  找到源文件: {self.stats['found']}")
            print(f"  已复制文件: {self.stats['copied']}")
            print(f"  已跳过（已存在）: {self.stats['skipped']}")
            print(f"  错误: {self.stats['errors']}")
            print(f"  更新文件大小: {self.stats['size_updated']}")
            
            if self.stats['errors'] > 0:
                print(f"\n⚠️  有 {self.stats['errors']} 个错误，请检查日志")
            
        finally:
            self.close_db()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='复制Smarti备份文件到FileBot存储')
    parser.add_argument('--limit', type=int, help='限制处理的文档数量（用于测试）')
    args = parser.parse_args()
    
    copier = FileCopier()
    copier.run(limit=args.limit)

if __name__ == "__main__":
    main()