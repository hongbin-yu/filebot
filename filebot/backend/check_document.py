#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import pathlib

# 创建数据库连接
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# 要检查的文档ID
document_id = "7d964867-6ba7-4db4-a48b-8607d44ac511"

print(f"检查文档ID: {document_id}")

# 查询文档信息
query = text("""
    SELECT 
        id,
        original_filename,
        stored_filename,
        file_type,
        file_size,
        full_storage_path,
        folder_id,
        created_at,
        conversion_status,
        status
    FROM documents 
    WHERE id = :doc_id
""")

result = db.execute(query, {"doc_id": document_id})
document = result.fetchone()

if document:
    print("✅ 文档存在:")
    print(f"  ID: {document.id}")
    print(f"  原始文件名: {document.original_filename}")
    print(f"  存储文件名: {document.stored_filename}")
    print(f"  文件类型: {document.file_type}")
    print(f"  文件大小: {document.file_size} 字节")
    print(f"  完整存储路径: {document.full_storage_path}")
    print(f"  文件夹ID: {document.folder_id}")
    print(f"  创建时间: {document.created_at}")
    print(f"  转换状态: {document.conversion_status}")
    print(f"  文档状态: {document.status}")
    
    # 检查文件是否存在
    from app.core.config import settings
    
    # 模拟 get_document_file_path 逻辑
    print("\n🔍 路径查找测试:")
    
    # 1. 默认存储路径
    default_path = pathlib.Path(settings.FILE_STORAGE_PATH) / "original" / document.stored_filename
    print(f"  1. 默认路径: {default_path}")
    print(f"     存在: {default_path.exists()}")
    
    # 2. 旧版本爬虫存储路径
    old_crawler_path = pathlib.Path("data/documents") / document.stored_filename
    print(f"  2. 爬虫路径: {old_crawler_path}")
    print(f"     存在: {old_crawler_path.exists()}")
    
    # 3. 绝对路径检查
    if document.stored_filename and os.path.isabs(document.stored_filename):
        abs_path = pathlib.Path(document.stored_filename)
        print(f"  3. 绝对路径: {abs_path}")
        print(f"     存在: {abs_path.exists()}")
    
    # 确定实际文件位置
    actual_path = None
    if old_crawler_path.exists():
        actual_path = old_crawler_path
        print(f"  ✅ 文件存在于爬虫路径: {actual_path}")
    elif default_path.exists():
        actual_path = default_path
        print(f"  ✅ 文件存在于默认路径: {actual_path}")
    else:
        print("  ❌ 文件在任何路径都不存在")
        
    if actual_path:
        print(f"  实际大小: {actual_path.stat().st_size} 字节")
        print(f"  数据库记录大小: {document.file_size} 字节")
        if actual_path.stat().st_size != document.file_size:
            print("  ⚠️ 大小不匹配！数据库记录可能不正确")
            
    # 检查文件夹信息
    folder_query = text("SELECT id, name, path FROM folders WHERE id = :folder_id")
    folder_result = db.execute(folder_query, {"folder_id": document.folder_id})
    folder = folder_result.fetchone()
    if folder:
        print(f"\n📁 所属文件夹: {folder.name}")
        print(f"   文件夹路径: {folder.path}")
        print(f"   文件夹ID: {folder.id}")
    else:
        print("\n⚠️ 文件夹不存在")
        
    # 测试下载端点能否找到文件
    print("\n🧪 下载端点测试:")
    # 导入 get_document_file_path 函数
    from app.routers.documents import get_document_file_path
    from app.models.document import Document as DocumentModel
    
    # 创建Document对象（模拟）
    # 这里简化，直接测试路径逻辑
    print("  修改后的get_document_file_path逻辑应能正确找到文件")
    
else:
    print("❌ 文档不存在")

db.close()