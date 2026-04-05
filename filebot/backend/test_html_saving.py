#!/usr/bin/env python3
"""
测试HTML保存功能：确保保存的是原始HTML，而不是提取的文本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.schemas.document import DocumentCreate
from app.models.document import FileType
from app.ai.website_crawler import create_document
import uuid

# 创建内存数据库引擎（用于测试）
from app.models.base import Base
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def test_html_saving():
    """测试HTML保存功能"""
    db = SessionLocal()
    
    try:
        # 创建一个测试文件夹记录（需要Folder模型）
        from app.models.folder import Folder
        from app.models.application import Application
        
        # 创建测试应用
        app_id = str(uuid.uuid4())
        app = Application(
            id=app_id,
            name="Test App",
            slug="test-app",
            description="Test application",
            created_by="test-user"
        )
        db.add(app)
        db.commit()
        
        # 创建测试文件夹
        folder_id = str(uuid.uuid4())
        folder = Folder(
            id=folder_id,
            name="Test Folder",
            description="Test folder",
            app_id=app_id,
            created_by="test-user",
            path="/test"
        )
        db.add(folder)
        db.commit()
        
        # 测试1：使用原始HTML内容
        print("测试1：使用原始HTML内容")
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World</h1>
    <p>This is a test paragraph with <b>bold</b> text.</p>
</body>
</html>"""
        
        document_data = DocumentCreate(
            title="Test HTML Page",
            description="A test HTML page",
            original_filename="test.html",
            file_size=len(html_content.encode('utf-8')),
            file_type=FileType.HTML,
            mime_type="text/html",
            folder_id=folder_id,
            uploaded_by=uuid.UUID("4dad6fa1-d521-417f-8877-efe95fcf1f04"),
            original_url="http://example.com/test.html",
            document_metadata={
                'extracted_text': 'Hello World This is a test paragraph with bold text.',
                'original_html': html_content[:5000]
            }
        )
        
        # 调用create_document
        import tempfile
        import shutil
        
        # 临时目录用于测试文件保存
        test_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        os.chdir(test_dir)
        
        try:
            # 确保data/documents目录存在
            os.makedirs("data/documents", exist_ok=True)
            
            doc = create_document(db, document_data, folder_id, html_content=html_content)
            print(f"  文档创建成功: {doc.id}")
            
            # 检查保存的文件
            file_path = os.path.join("data/documents", folder_id, "test.html")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    saved_content = f.read()
                
                # 验证保存的是HTML，不是纯文本
                if '<html>' in saved_content and '<body>' in saved_content:
                    print("  ✓ 文件保存为HTML格式")
                else:
                    print("  ✗ 文件不是HTML格式（可能是纯文本）")
                    print(f"  内容预览: {saved_content[:200]}")
                
                # 检查是否包含原始HTML的特定标记
                if '<b>bold</b>' in saved_content:
                    print("  ✓ 包含原始HTML标记")
                else:
                    print("  ✗ 原始HTML标记丢失")
            else:
                print("  ✗ 文件未保存")
        
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(test_dir)
        
        # 测试2：不使用html_content参数，依赖元数据中的original_html
        print("\n测试2：依赖元数据中的original_html")
        document_data2 = DocumentCreate(
            title="Test HTML Page 2",
            description="Another test HTML page",
            original_filename="test2.html",
            file_size=len(html_content.encode('utf-8')),
            file_type=FileType.HTML,
            mime_type="text/html",
            folder_id=folder_id,
            uploaded_by=uuid.UUID("4dad6fa1-d521-417f-8877-efe95fcf1f04"),
            original_url="http://example.com/test2.html",
            document_metadata={
                'extracted_text': 'Hello World This is a test paragraph with bold text.',
                'original_html': html_content[:5000]
            }
        )
        
        test_dir2 = tempfile.mkdtemp()
        os.chdir(test_dir2)
        os.makedirs("data/documents", exist_ok=True)
        
        try:
            # 不传递html_content参数
            doc2 = create_document(db, document_data2, folder_id, html_content=None)
            print(f"  文档创建成功: {doc2.id}")
            
            file_path2 = os.path.join("data/documents", folder_id, "test2.html")
            if os.path.exists(file_path2):
                with open(file_path2, 'r', encoding='utf-8') as f:
                    saved_content2 = f.read()
                
                if '<html>' in saved_content2:
                    print("  ✓ 文件从original_html保存为HTML格式")
                else:
                    print("  ✗ 文件不是HTML格式")
                    print(f"  内容预览: {saved_content2[:200]}")
            else:
                print("  ✗ 文件未保存")
        
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(test_dir2)
        
        # 测试3：只有extracted_text（纯文本）的情况
        print("\n测试3：只有extracted_text（纯文本）")
        document_data3 = DocumentCreate(
            title="Test Text Page",
            description="A text-only page",
            original_filename="test3.html",
            file_size=100,
            file_type=FileType.HTML,
            mime_type="text/html",
            folder_id=folder_id,
            uploaded_by=uuid.UUID("4dad6fa1-d521-417f-8877-efe95fcf1f04"),
            original_url="http://example.com/test3.html",
            document_metadata={
                'extracted_text': 'This is plain text content without HTML tags.'
            }
        )
        
        test_dir3 = tempfile.mkdtemp()
        os.chdir(test_dir3)
        os.makedirs("data/documents", exist_ok=True)
        
        try:
            doc3 = create_document(db, document_data3, folder_id, html_content=None)
            print(f"  文档创建成功: {doc3.id}")
            
            file_path3 = os.path.join("data/documents", folder_id, "test3.html")
            if os.path.exists(file_path3):
                with open(file_path3, 'r', encoding='utf-8') as f:
                    saved_content3 = f.read()
                
                if '<!DOCTYPE html>' in saved_content3:
                    print("  ✓ 纯文本被包装为HTML格式")
                else:
                    print("  ✗ 纯文本未被包装为HTML")
                    print(f"  内容预览: {saved_content3[:200]}")
            else:
                print("  ✗ 文件未保存")
        
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(test_dir3)
        
        print("\n所有测试完成")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_html_saving()