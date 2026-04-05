#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models.folder import Folder
from app.models.document import Document
from app.models.app import App

# 创建数据库会话
from app.db.database import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# 测试文档计数查询
print("测试文档计数查询...")

# 1. 测试子查询方法（与folders.py中相同）
from sqlalchemy import func

# 创建文档计数的子查询
doc_count_subquery = db.query(
    Document.folder_id,
    func.count(Document.id).label('document_count')
).group_by(Document.folder_id).subquery()

# 查询所有文件夹及其文档计数
folders_with_counts = db.query(
    Folder,
    func.coalesce(doc_count_subquery.c.document_count, 0).label('document_count')
).outerjoin(
    doc_count_subquery,
    Folder.id == doc_count_subquery.c.folder_id
).order_by(Folder.name).limit(10).all()

print(f"\n前10个文件夹的文档计数:")
for folder_obj, doc_count in folders_with_counts:
    print(f"  文件夹: {folder_obj.name} (ID: {folder_obj.id[:8]}...) - 文档数量: {doc_count}")

# 2. 测试特定文件夹（en文件夹）
en_folder_id = '2db73b44-660a-42ed-bc63-c97751dae48b'
print(f"\n测试特定文件夹 (ID: {en_folder_id}):")

# 直接查询该文件夹的文档数量
direct_count = db.query(func.count(Document.id)).filter(Document.folder_id == en_folder_id).scalar()
print(f"  直接文档数量: {direct_count}")

# 使用子查询方法
folder_with_count = db.query(
    Folder,
    func.coalesce(doc_count_subquery.c.document_count, 0).label('document_count')
).outerjoin(
    doc_count_subquery,
    Folder.id == doc_count_subquery.c.folder_id
).filter(Folder.id == en_folder_id).first()

if folder_with_count:
    folder_obj, doc_count = folder_with_count
    print(f"  文件夹名称: {folder_obj.name}")
    print(f"  文件夹路径: {folder_obj.path}")
    print(f"  文档数量 (通过子查询): {doc_count}")
    print(f"  匹配: {'是' if doc_count == direct_count else '否'}")

# 3. 检查数据库中的实际文档
print(f"\n检查数据库中的实际文档分布:")
# 按folder_id分组统计文档
from sqlalchemy import desc

doc_counts = db.query(
    Document.folder_id,
    func.count(Document.id).label('count'),
    func.group_concat(Document.title, '|').label('sample_titles')
).group_by(Document.folder_id).order_by(desc(func.count(Document.id))).limit(5).all()

print("文档最多的5个文件夹:")
for folder_id, count, sample_titles in doc_counts:
    # 获取文件夹名称
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    folder_name = folder.name if folder else f"未知文件夹 ({folder_id[:8]}...)"
    
    # 解析示例标题
    titles = sample_titles.split('|')[:3] if sample_titles else []
    sample = ', '.join([t[:30] + '...' if len(t) > 30 else t for t in titles])
    
    print(f"  文件夹: {folder_name} - 文档数量: {count}")
    if sample:
        print(f"    示例: {sample}")

db.close()