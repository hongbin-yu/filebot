#!/usr/bin/env python3
"""
测试FileBot数据库连接和查询
"""

import sys
sys.path.insert(0, '/home/hongb/.openclaw/workspace/filebot/backend')

from app.db.database import SessionLocal, engine
from app.models.app import App
from app.models.drawer import Drawer
from app.models.folder import Folder
from app.models.document import Document
from app.models.user import User
from sqlalchemy import select
import json

def test_database():
    """测试数据库连接和查询"""
    db = SessionLocal()
    
    try:
        # 查询应用
        apps = db.query(App).all()
        print(f"数据库中的App数量: {len(apps)}")
        for app in apps:
            print(f"  App: {app.id} - {app.name} (所有者: {app.owner_id})")
            if app.settings:
                print(f"    设置: {json.dumps(app.settings, indent=2)}")
        
        # 查询用户
        users = db.query(User).all()
        print(f"\n数据库中的用户数量: {len(users)}")
        for user in users:
            print(f"  用户: {user.id} - {user.username} - {user.email}")
        
        # 查询文档
        documents = db.query(Document).all()
        print(f"\n数据库中的文档数量: {len(documents)}")
        for doc in documents[:5]:  # 只显示前5个
            print(f"  文档: {doc.id} - {doc.name} - {doc.file_type}")
        
        if len(documents) > 5:
            print(f"  ... 和 {len(documents) - 5} 个更多文档")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_database()