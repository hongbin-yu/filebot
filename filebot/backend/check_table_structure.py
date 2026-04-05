#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('filebot.db')
cursor = conn.cursor()

# 获取documents表结构
cursor.execute("PRAGMA table_info(documents)")
columns = cursor.fetchall()
print("documents表结构:")
for col in columns:
    print(f"  {col[1]} ({col[2]}) - 主键: {col[5]}")
    
# 获取apps表结构
print("\napps表结构:")
cursor.execute("PRAGMA table_info(apps)")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")
    
# 获取folders表结构
print("\nfolders表结构:")
cursor.execute("PRAGMA table_info(folders)")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

conn.close()