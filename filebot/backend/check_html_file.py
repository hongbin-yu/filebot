#!/usr/bin/env python3
import sys
sys.path.append('/home/hongb/.openclaw/workspace/filebot/backend')

from app.database import SessionLocal
from app.models.document import Document
from sqlalchemy import or_
import os

def main():
    db = SessionLocal()
    try:
        # 查找文件名包含government-communications的文档
        docs = db.query(Document).filter(
            Document.original_filename.like('%government-communications%')
        ).all()
        
        print(f"找到 {len(docs)} 个文档:")
        for doc in docs:
            print(f"ID: {doc.id}")
            print(f"原始文件名: {doc.original_filename}")
            print(f"存储文件名: {doc.stored_filename}")
            print(f"文件类型: {doc.file_type}")
            print(f"文件大小: {doc.file_size}")
            print(f"文件夹ID: {doc.folder_id}")
            print(f"状态: {doc.status}")
            print(f"元数据: {doc.document_metadata}")
            print("-" * 50)
            
            # 检查文件是否存在
            possible_paths = [
                os.path.join("data/documents", doc.stored_filename),
                os.path.join("data/files/original", doc.stored_filename),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    actual_size = os.path.getsize(path)
                    print(f"文件路径: {path}")
                    print(f"实际文件大小: {actual_size} 字节")
                    print(f"数据库大小 vs 实际大小: {doc.file_size} vs {actual_size}")
                    if actual_size == 0:
                        print("⚠️  警告：实际文件大小为0字节！")
                    break
            else:
                print("❌ 文件未找到在任何路径")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()