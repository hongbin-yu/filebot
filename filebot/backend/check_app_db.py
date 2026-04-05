#!/usr/bin/env python3
"""
直接检查数据库中的App字段
"""
import sqlite3

db_path = 'filebot.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查表结构
cursor.execute('PRAGMA table_info(apps)')
columns = cursor.fetchall()
print('📊 Apps表结构:')
for col in columns:
    print(f'  {col[1]:20} {col[2]:15} {"NOT NULL" if col[3] else "NULLABLE"}')

# 检查前3个应用的数据
print('\n📋 应用数据:')
cursor.execute('SELECT id, name, redirect_url, icon FROM apps LIMIT 3')
apps = cursor.fetchall()
for app_id, name, redirect_url, icon in apps:
    print(f'\n  {name}:')
    print(f'    ID: {app_id}')
    print(f'    重定向URL: {redirect_url if redirect_url else "NULL"}')
    print(f'    图标: {icon if icon else "NULL"}')

conn.close()