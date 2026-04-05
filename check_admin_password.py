#!/usr/bin/env python3
"""
检查admin用户密码哈希
"""

import sys
sys.path.insert(0, '/home/hongb/.openclaw/workspace/filebot/backend')

from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password

def check_user_password():
    """检查用户密码哈希"""
    db = SessionLocal()
    
    try:
        # 获取admin用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("未找到admin用户")
            return
        
        print(f"找到admin用户: {admin_user.username} ({admin_user.email})")
        print(f"密码哈希: {admin_user.password_hash}")
        print(f"哈希长度: {len(admin_user.password_hash)}")
        
        # 尝试常见密码
        common_passwords = [
            "admin",
            "password",
            "admin123",
            "123456",
            "filebot",
            "Admin123!",
            "",
        ]
        
        print("\n尝试常见密码:")
        for password in common_passwords:
            try:
                if verify_password(password, admin_user.password_hash):
                    print(f"  ✅ 密码匹配: '{password}'")
                    return password
                else:
                    print(f"  ❌ 不匹配: '{password}'")
            except Exception as e:
                print(f"  ⚠️  验证错误 '{password}': {e}")
        
        print("\n未找到匹配的密码，建议重置密码或创建新用户")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_user_password()