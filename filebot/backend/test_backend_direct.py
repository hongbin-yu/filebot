#!/usr/bin/env python3
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入后端模块测试
from app.routers.folders import get_folders, get_folder
from app.models.user import User
from unittest.mock import Mock
import uuid

def test_get_folders():
    """测试get_folders函数的文档计数逻辑"""
    print("测试 get_folders 函数...")
    
    # 创建模拟的数据库会话
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.database import SQLALCHEMY_DATABASE_URL
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 创建模拟用户
        mock_user = Mock(spec=User)
        mock_user.username = "testuser"
        mock_user.is_superuser = True
        
        # 获取canada-site应用
        from app.models.app import App
        app = db.query(App).filter(App.slug == "canada-site").first()
        if not app:
            # 如果找不到，尝试找任何应用
            app = db.query(App).first()
        
        if not app:
            print("找不到测试应用")
            return
        
        print(f"测试应用: {app.name} (slug: {app.slug})")
        
        # 使用app_id参数调用get_folders
        # 注意：这里需要模拟FastAPI的依赖注入
        # 我们直接调用数据库查询逻辑进行测试
        
        from sqlalchemy import func
        from app.models.folder import Folder
        from app.models.document import Document
        
        # 复制get_folders中的查询逻辑
        query = db.query(Folder).filter(Folder.app_id == app.id)
        
        # 创建文档计数的子查询
        doc_count_subquery = db.query(
            Document.folder_id,
            func.count(Document.id).label('document_count')
        ).group_by(Document.folder_id).subquery()
        
        # 修改查询以左连接文档计数
        folders_with_counts = query.outerjoin(
            doc_count_subquery,
            Folder.id == doc_count_subquery.c.folder_id
        ).with_entities(
            Folder,
            func.coalesce(doc_count_subquery.c.document_count, 0).label('document_count')
        ).order_by(Folder.name).all()
        
        print(f"查询到 {len(folders_with_counts)} 个文件夹")
        
        # 检查是否有文件夹包含文档
        has_docs = False
        for i, (folder_obj, doc_count) in enumerate(folders_with_counts[:10]):  # 检查前10个
            if doc_count > 0:
                has_docs = True
                print(f"  ✓ 文件夹 '{folder_obj.name}' 有 {doc_count} 个文档")
        
        if not has_docs:
            print("  ✗ 没有找到包含文档的文件夹（可能所有文件夹都没有文档）")
        
        # 测试转换逻辑
        print(f"\n测试文件夹对象转换...")
        test_folders = []
        for folder_obj, doc_count in folders_with_counts[:3]:
            # 复制get_folders中的转换逻辑
            folder_dict = {c.name: getattr(folder_obj, c.name) for c in folder_obj.__table__.columns}
            folder_dict['document_count'] = doc_count
            test_folders.append(folder_dict)
            
            print(f"  文件夹: {folder_dict.get('name')}")
            print(f"    包含字段: {', '.join(sorted(folder_dict.keys()))}")
            print(f"    document_count值: {folder_dict.get('document_count')}")
        
    finally:
        db.close()

def test_schema():
    """测试Schema是否包含document_count字段"""
    print(f"\n测试 Schema 模型...")
    
    from app.schemas.app import FolderResponse
    import inspect
    
    # 检查FolderResponse模型的字段
    fields = FolderResponse.__fields__
    field_names = list(fields.keys())
    
    print(f"FolderResponse 字段: {', '.join(sorted(field_names))}")
    
    if 'document_count' in field_names:
        print("  ✓ 包含 document_count 字段")
        field_info = fields['document_count']
        print(f"    类型: {field_info.type_}")
        print(f"    默认值: {field_info.default}")
    else:
        print("  ✗ 不包含 document_count 字段")

if __name__ == "__main__":
    print("=" * 60)
    print("直接测试后端文档计数功能")
    print("=" * 60)
    
    test_schema()
    test_get_folders()