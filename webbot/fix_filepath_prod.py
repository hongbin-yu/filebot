#!/usr/bin/env python3
"""生产修复: webbot_page.metadata.file_path 错误绝对路径 -> /canadasite/... (2026-08-09)
先备份 DB, 再修复, 最后统计验证。"""
import json, shutil, sqlite3, time

DB = '/opt/webfilebot/webbot/data/webbot.db'
bak = DB + '.bak-20260809-filepath'
shutil.copy2(DB, bak)
print('backup ->', bak)

def strip_html(p):
    if p.endswith('.html'): return p[:-5]
    if p.endswith('.htm'): return p[:-4]
    return p

conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT id, path, metadata FROM webbot_page WHERE metadata LIKE '%file_path%'"
).fetchall()
changed, skipped, errors = 0, 0, []
for pid, path, meta_raw in rows:
    try:
        m = json.loads(meta_raw)
    except (json.JSONDecodeError, TypeError):
        errors.append((path, 'bad json')); continue
    fp = m.get('file_path')
    if not fp or not isinstance(fp, str) or '/boarding/' not in fp:
        continue
    rel = '/' + fp.split('/boarding/', 1)[1]
    rel = rel.replace('.html/', '/').replace('.htm/', '/')
    rel = strip_html(rel)
    norm_path = strip_html(path)
    if not (rel == norm_path or rel.startswith(norm_path + '/')):
        skipped += 1
        errors.append((path, 'skip: ' + fp[:100]))
        continue
    if m.get('file_path') == norm_path:
        continue
    m['file_path'] = norm_path
    conn.execute(
        "UPDATE webbot_page SET metadata=? WHERE id=?",
        (json.dumps(m, ensure_ascii=False), pid),
    )
    changed += 1
conn.commit()
print('changed:', changed, 'skipped:', skipped)

# 统计残留
rows = conn.execute(
    "SELECT path, metadata FROM webbot_page WHERE metadata LIKE '%file_path%'"
).fetchall()
from collections import Counter
c = Counter()
for r in rows:
    try: m = json.loads(r[1])
    except: continue
    fp = m.get('file_path') or ''
    if fp.startswith('/opt/'): c['opt_abs'] += 1
    elif fp.startswith('/home/'): c['home_abs'] += 1
    elif fp.startswith('/boarding') or fp.startswith('boarding'): c['boarding'] += 1
    elif fp.startswith('/canadasite'): c['canadasite'] += 1
    elif fp.startswith('/content/dam'): c['dam'] += 1
    else: c['other:' + fp[:30]] += 1
print('after fix distribution:', dict(c))
for e in errors[:10]: print(' !', e)
conn.close()
