#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.document import FileType
from app.schemas.document import DocumentCreate
import uuid
from app.ai.website_crawler import create_document

# 创建数据库连接
engine = create_engine('sqlite:///filebot.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# 测试数据
folder_id = "a72ab8c7-b6f4-46b8-8ef9-29cceab6176b"  # 使用现有的文件夹ID
document_data = DocumentCreate(
    title="测试文档",
    description="测试create_document函数",
    original_filename="test-create-document.html",
    file_size=100,
    file_type=FileType.HTML,
    mime_type="text/html",
    folder_id=folder_id,
    uploaded_by=uuid.UUID("4dad6fa1-d521-417f-8877-efe95fcf1f04"),
    original_url="https://example.com/test",
    document_metadata={"test": True}
)

# 测试1：正常HTML内容
print("=== 测试1：正常HTML内容 ===")
html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Test Content</h1>
    <p>This is a test paragraph.</p>
</body>
</html>"""

try:
    doc = create_document(db, document_data, folder_id, html_content)
    print(f"文档创建成功: ID={doc.id}")
    
    # 检查文件
    file_path = f"data/documents/{folder_id}/test-create-document.html"
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print(f"文件大小: {size} 字节")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"文件内容长度: {len(content)} 字符")
            if size > 0:
                print("✓ 文件非空")
            else:
                print("✗ 文件为空")
    else:
        print(f"✗ 文件不存在: {file_path}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

# 测试2：空内容
print("\n=== 测试2：空内容 ===")
document_data2 = DocumentCreate(
    title="测试空文档",
    description="测试空内容",
    original_filename="test-empty.html",
    file_size=0,
    file_type=FileType.HTML,
    mime_type="text/html",
    folder_id=folder_id,
    uploaded_by=uuid.UUID("4dad6fa1-d521-417f-8877-efe95fcf1f04"),
    original_url="https://example.com/test-empty",
    document_metadata={"test": True}
)

try:
    doc2 = create_document(db, document_data2, folder_id, "")
    print(f"文档创建成功: ID={doc2.id}")
    
    file_path2 = f"data/documents/{folder_id}/test-empty.html"
    if os.path.exists(file_path2):
        size = os.path.getsize(file_path2)
        print(f"文件大小: {size} 字节")
        if size == 0:
            print("✓ 文件为空（符合预期）")
        else:
            print(f"✗ 文件非空: {size} 字节")
except Exception as e:
    print(f"错误: {e}")

# 测试3：None内容
print("\n=== 测试3：None内容 ===")
document_data3 = DocumentCreate(
    title="测试None文档",
    description="测试None内容",
    original_filename="test-none.html",
    file_size=0,
    file_type=FileType.HTML,
    mime_type="text/html",
    folder_id=folder_id,
    uploaded_by=uuid.UUID("4dad6fa1-d521-417f-8877-efe95fcf1f04"),
    original_url="https://example.com/test-none",
    document_metadata={"test": True}
)

try:
    doc3 = create_document(db, document_data3, folder_id, None)
    print(f"文档创建成功: ID={doc3.id}")
    
    file_path3 = f"data/documents/{folder_id}/test-none.html"
    if os.path.exists(file_path3):
        size = os.path.getsize(file_path3)
        print(f"文件大小: {size} 字节")
except Exception as e:
    print(f"错误: {e}")

# 清理测试文件
for filename in ["test-create-document.html", "test-empty.html", "test-none.html"]:
    path = f"data/documents/{folder_id}/{filename}"
    if os.path.exists(path):
        os.remove(path)
        print(f"已清理: {path}")

db.close()