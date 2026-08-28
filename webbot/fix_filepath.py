#!/usr/bin/env python3
"""修复 webbot_page.metadata.file_path 错误绝对路径。

错误格式（Import Page bookmarklet 产生）:
  /opt/webfilebot/data/files/boarding/canadasite/en/services/jobs.html
  /home/hongb/.openclaw/workspace/filebot/backend/data/files/boarding/canadasite/...html
  boarding/canadasite/etc/designs/.../page-feedback-fr.html

正确格式（与 320 条正常记录一致）:
  /canadasite/en/services/jobs

转换规则: 取 '/boarding/' 之后的部分，去掉 .html/.htm 后缀。
校验: 转换结果必须等于页面 path 列，否则跳过并报告。
用法: python3 fix_filepath.py <db_path> [--dry-run]
"""
import json
import sqlite3
import sys

DB = 'app/webbot.db'
DRY = True

conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT id, path, metadata FROM webbot_page WHERE metadata LIKE '%file_path%'"
).fetchall()

changed, skipped, errors = 0, 0, []
for pid, path, meta_raw in rows:
    try:
        m = json.loads(meta_raw)
    except (json.JSONDecodeError, TypeError):
        errors.append((path, 'bad json'))
        continue
    fp = m.get('file_path')
    if not fp or not isinstance(fp, str):
        continue
    # 只在含 /boarding/ 的绝对/相对路径上转换
    if '/boarding/' not in fp:
        continue
    new_fp = '/' + fp.split('/boarding/', 1)[1]
    if new_fp.endswith('.html'):
        new_fp = new_fp[:-5]
    elif new_fp.endswith('.htm'):
        new_fp = new_fp[:-4]
    # 校验: 转换结果必须与页面路径一致（导入时 webbot_path 即页面 path）
    if new_fp != path:
        errors.append((path, f'mismatch: {fp[:90]} -> {new_fp}'))
        skipped += 1
        continue
    if new_fp == fp:
        continue
    m['file_path'] = new_fp
    if not DRY:
        conn.execute(
            "UPDATE webbot_page SET metadata=? WHERE id=?",
            (json.dumps(m, ensure_ascii=False), pid),
        )
    changed += 1

if not DRY:
    conn.commit()
conn.close()
print(f'DB={DB} dry_run={DRY} changed={changed} skipped={skipped} errors={len(errors)}')
for e in errors[:15]:
    print('  !', e)
