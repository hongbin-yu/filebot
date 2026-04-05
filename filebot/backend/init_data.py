#!/usr/bin/env python3
"""初始化测试数据"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.core.security import create_first_superuser, get_password_hash
from app.models.user import User
from app.models.app import App
import uuid

def init_test_data():
    db = SessionLocal()
    
    try:
        # 1. 创建超级用户（如果不存在）
        print("1. 检查/创建超级用户...")
        admin = db.query(User).filter(
            (User.username == "admin") | (User.email == "admin@filebot.com")
        ).first()
        
        if not admin:
            admin = User(
                id=str(uuid.uuid4()),
                username="admin",
                email="admin@filebot.com",
                password_hash=get_password_hash("admin123"),
                full_name="系统管理员",
                is_active=True,
                is_superuser=True,
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("   ✓ 创建管理员用户: admin/admin123")
        else:
            print(f"   ✓ 管理员已存在: {admin.username}")
        
        # 2. 创建测试应用（如果不存在）
        print("\n2. 检查/创建测试应用...")
        app = db.query(App).filter(App.slug == "test-admin").first()
        
        if not app:
            app = App(
                id=str(uuid.uuid4()),
                name="Admin测试应用",
                slug="test-admin",
                description="用于Admin功能测试的应用",
                owner_id=admin.id,
                created_by=admin.username,
                settings={"indices": ["Department", "DocumentType"]}
            )
            db.add(app)
            db.commit()
            print("   ✓ 创建测试应用: Admin测试应用")
        else:
            print(f"   ✓ 测试应用已存在: {app.name}")
        
        # 3. 列出所有应用
        print("\n3. 应用列表:")
        apps = db.query(App).all()
        for a in apps:
            print(f"   - {a.name} (ID: {a.id})")
        
        # 4. 列出所有用户
        print("\n4. 用户列表:")
        users = db.query(User).all()
        for u in users:
            print(f"   - {u.username} ({u.email}) - 超级用户: {u.is_superuser}")
        
        print("\n✅ 数据初始化完成")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_test_data()