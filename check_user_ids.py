#!/usr/bin/env python3
"""检查用户ID格式"""

import sqlite3
import sys
import os

DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"

def check_user_ids():
    """检查用户ID格式"""
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查users表
    print("检查users表...")
    cursor.execute("SELECT id, username, created_at FROM users")
    users = cursor.fetchall()
    
    print(f"找到 {len(users)} 个用户:")
    for user_id, username, created_at in users:
        print(f"  - 用户名: {username}")
        print(f"    ID: {user_id}")
        print(f"    ID长度: {len(user_id)} 字符")
        print(f"    包含连字符: {'-' in user_id}")
        print()
    
    # 检查devices表是否存在
    print("\n检查devices表...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
    if cursor.fetchone():
        cursor.execute("SELECT id, name, type FROM devices")
        devices = cursor.fetchall()
        print(f"找到 {len(devices)} 个设备:")
        for device_id, name, type_ in devices:
            print(f"  - 设备名: {name}, 类型: {type_}")
            print(f"    ID: {device_id}")
            print(f"    ID长度: {len(device_id)} 字符")
    else:
        print("devices表不存在")
    
    # 检查file_naming_rules表是否存在
    print("\n检查file_naming_rules表...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_naming_rules'")
    if cursor.fetchone():
        cursor.execute("SELECT id, basename, subfolder_name FROM file_naming_rules")
        rules = cursor.fetchall()
        print(f"找到 {len(rules)} 个命名规则:")
        for rule_id, basename, subfolder_name in rules:
            print(f"  - 基础名: {basename}, 子文件夹: {subfolder_name}")
    else:
        print("file_naming_rules表不存在")
    
    conn.close()

if __name__ == "__main__":
    check_user_ids()