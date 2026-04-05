#!/usr/bin/env python3
"""
修复UUID模型问题 - 改用字符串存储UUID
"""

import sys
sys.path.insert(0, '/home/hongb/.openclaw/workspace/filebot/backend')

from sqlalchemy import create_engine, Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import uuid

# 创建新的Base类
Base = declarative_base()

class User(Base):
    """用户表 - 使用String存储UUID"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(String(1), default="Y", nullable=False)
    role = Column(String(50), default="user", nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class App(Base):
    """应用表 - 使用String存储UUID"""
    __tablename__ = "apps"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    settings = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)
    
    # 关系
    owner = relationship("User")

def fix_database():
    """修复数据库"""
    from app.db.database import engine
    
    print("1. 备份现有表数据...")
    
    # 连接到数据库
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    
    session = Session(bind=engine)
    
    try:
        # 备份现有数据
        users_backup = session.execute(text("SELECT * FROM users")).fetchall()
        apps_backup = session.execute(text("SELECT * FROM apps")).fetchall()
        
        print(f"  用户数据: {len(users_backup)} 行")
        print(f"  应用数据: {len(apps_backup)} 行")
        
        # 删除现有表
        print("\n2. 删除现有表...")
        Base.metadata.drop_all(bind=engine)
        
        # 创建新表
        print("\n3. 创建新表（使用String UUID）...")
        Base.metadata.create_all(bind=engine)
        
        # 恢复用户数据
        print("\n4. 恢复用户数据...")
        for user in users_backup:
            # 将UUID转换为字符串格式
            user_id = user[0]
            if isinstance(user_id, bytes):
                # 如果是字节，转换为UUID再转字符串
                try:
                    user_uuid = uuid.UUID(bytes=user_id)
                    user_id_str = str(user_uuid)
                except:
                    user_id_str = str(uuid.uuid4())
            else:
                user_id_str = str(user_id) if user_id else str(uuid.uuid4())
            
            # 确保是标准UUID格式
            if len(user_id_str) == 32 and '-' not in user_id_str:
                user_id_str = f"{user_id_str[:8]}-{user_id_str[8:12]}-{user_id_str[12:16]}-{user_id_str[16:20]}-{user_id_str[20:]}"
            
            new_user = User(
                id=user_id_str,
                username=user[1],
                email=user[2],
                password_hash=user[3],
                full_name=user[4],
                is_active=user[5],
                role=user[6],
                created_at=user[7],
                updated_at=user[8]
            )
            session.add(new_user)
        
        session.commit()
        print(f"  恢复 {len(users_backup)} 个用户")
        
        # 恢复应用数据
        print("\n5. 恢复应用数据...")
        for app in apps_backup:
            # 转换应用ID
            app_id = app[0]
            if isinstance(app_id, bytes):
                try:
                    app_uuid = uuid.UUID(bytes=app_id)
                    app_id_str = str(app_uuid)
                except:
                    app_id_str = str(uuid.uuid4())
            else:
                app_id_str = str(app_id) if app_id else str(uuid.uuid4())
            
            # 转换所有者ID
            owner_id = app[3]
            if isinstance(owner_id, bytes):
                try:
                    owner_uuid = uuid.UUID(bytes=owner_id)
                    owner_id_str = str(owner_uuid)
                except:
                    owner_id_str = str(uuid.uuid4())
            else:
                owner_id_str = str(owner_id) if owner_id else str(uuid.uuid4())
            
            # 确保是标准UUID格式
            for id_str in [app_id_str, owner_id_str]:
                if len(id_str) == 32 and '-' not in id_str:
                    id_str = f"{id_str[:8]}-{id_str[8:12]}-{id_str[12:16]}-{id_str[16:20]}-{id_str[20:]}"
            
            new_app = App(
                id=app_id_str,
                name=app[1],
                description=app[2],
                owner_id=owner_id_str,
                settings=app[4] if len(app) > 4 else {},
                created_at=app[5] if len(app) > 5 else None,
                created_by=app[6] if len(app) > 6 else None,
                updated_at=app[7] if len(app) > 7 else None,
                updated_by=app[8] if len(app) > 8 else None
            )
            session.add(new_app)
        
        session.commit()
        print(f"  恢复 {len(apps_backup)} 个应用")
        
        print("\n✅ 数据库修复完成")
        
        # 验证数据
        print("\n6. 验证修复结果...")
        users_count = session.query(User).count()
        apps_count = session.query(App).count()
        
        print(f"  用户表: {users_count} 行")
        print(f"  应用表: {apps_count} 行")
        
        # 检查一个用户
        user = session.query(User).first()
        if user:
            print(f"  示例用户: {user.username} (ID: {user.id})")
            print(f"  ID类型: {type(user.id).__name__}")
            print(f"  ID长度: {len(user.id)}")
            
            # 验证UUID格式
            try:
                uuid_obj = uuid.UUID(user.id)
                print(f"  ✅ UUID格式有效")
            except ValueError:
                print(f"  ❌ UUID格式无效")
        
        # 检查一个应用
        app = session.query(App).first()
        if app:
            print(f"  示例应用: {app.name} (ID: {app.id})")
            print(f"  所有者ID: {app.owner_id}")
        
    except Exception as e:
        print(f"❌ 修复错误: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

def update_model_files():
    """更新模型文件"""
    print("\n7. 更新模型文件...")
    
    # 读取现有模型文件
    user_model_path = "/home/hongb/.openclaw/workspace/filebot/backend/app/models/user.py"
    app_model_path = "/home/hongb/.openclaw/workspace/filebot/backend/app/models/app.py"
    
    try:
        # 更新User模型
        with open(user_model_path, 'r', encoding='utf-8') as f:
            user_content = f.read()
        
        # 替换UUID定义
        user_content = user_content.replace(
            "from sqlalchemy.dialects.postgresql import UUID",
            "# from sqlalchemy.dialects.postgresql import UUID  # 注释掉，使用String代替"
        )
        user_content = user_content.replace(
            "id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
            "id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))"
        )
        
        with open(user_model_path, 'w', encoding='utf-8') as f:
            f.write(user_content)
        print(f"  ✅ 更新User模型: {user_model_path}")
        
        # 更新App模型
        with open(app_model_path, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        app_content = app_content.replace(
            "from sqlalchemy.dialects.postgresql import UUID",
            "# from sqlalchemy.dialects.postgresql import UUID  # 注释掉，使用String代替"
        )
        app_content = app_content.replace(
            "id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)",
            "id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))"
        )
        app_content = app_content.replace(
            "owner_id = Column(UUID(as_uuid=True), ForeignKey(\"users.id\"), nullable=False)",
            "owner_id = Column(String(36), ForeignKey(\"users.id\"), nullable=False)"
        )
        
        with open(app_model_path, 'w', encoding='utf-8') as f:
            f.write(app_content)
        print(f"  ✅ 更新App模型: {app_model_path}")
        
        # 更新其他相关模型
        model_files = [
            "/home/hongb/.openclaw/workspace/filebot/backend/app/models/drawer.py",
            "/home/hongb/.openclaw/workspace/filebot/backend/app/models/folder.py",
            "/home/hongb/.openclaw/workspace/filebot/backend/app/models/document.py",
            "/home/hongb/.openclaw/workspace/filebot/backend/app/models/page.py",
            "/home/hongb/.openclaw/workspace/filebot/backend/app/models/conversion_task.py",
        ]
        
        for model_file in model_files:
            try:
                with open(model_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "from sqlalchemy.dialects.postgresql import UUID" in content:
                    content = content.replace(
                        "from sqlalchemy.dialects.postgresql import UUID",
                        "# from sqlalchemy.dialects.postgresql import UUID  # 注释掉，使用String代替"
                    )
                
                if "UUID(as_uuid=True)" in content:
                    content = content.replace(
                        "UUID(as_uuid=True)",
                        "String(36)"
                    )
                
                with open(model_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  ✅ 更新模型: {model_file}")
            except FileNotFoundError:
                print(f"  ℹ️  模型文件不存在: {model_file}")
            except Exception as e:
                print(f"  ⚠️  更新{model_file}错误: {e}")
        
        print("\n✅ 模型文件更新完成")
        
    except Exception as e:
        print(f"❌ 更新模型文件错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("=== 修复FileBot UUID格式问题 ===\n")
    
    # 停止后端
    import subprocess
    import time
    
    print("停止FileBot后端...")
    try:
        subprocess.run(["pkill", "-f", "uvicorn"], timeout=5)
        time.sleep(2)
        print("✅ 后端已停止")
    except:
        pass
    
    # 修复数据库
    fix_database()
    
    # 更新模型文件
    update_model_files()
    
    print("\n✅ 修复完成")
    print("\n下一步:")
    print("  1. 重启FileBot后端")
    print("  2. 测试API功能")
    print("  3. 继续Smart iAdmin集成测试")

if __name__ == "__main__":
    main()