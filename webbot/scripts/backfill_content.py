#!/usr/bin/env python3
"""Backfill webbot_page.content from saved HTML files on disk."""
import sqlite3, os, sys

FILEBOT_DATA_DIR = "/home/hongb/.openclaw/workspace/filebot/backend/data"
WEBBOT_DB_PATH = "/home/hongb/.openclaw/workspace/webbot/app/webbot.db"

path_filter = sys.argv[1] if len(sys.argv) > 1 else None

wb = sqlite3.connect(WEBBOT_DB_PATH)
wc = wb.cursor()

if path_filter:
    rows = wc.execute("SELECT path FROM webbot_page WHERE (content IS NULL OR content = '') AND path LIKE ?",
                      ('%' + path_filter + '%',)).fetchall()
else:
    rows = wc.execute("SELECT path FROM webbot_page WHERE (content IS NULL OR content = '')").fetchall()

print(f'Found {len(rows)} pages with empty content')

fixed = 0
not_found = 0

for (path,) in rows:
    rel = os.path.join("boarding", path.lstrip("/"))
    filepath = os.path.join(FILEBOT_DATA_DIR, f"{rel}.html")
    
    if os.path.isfile(filepath):
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        wc.execute("UPDATE webbot_page SET content = ? WHERE path = ? AND (content IS NULL OR content = '')",
                   (content, path))
        fixed += wc.rowcount
    else:
        # also try with subfolder structure
        filepath2 = os.path.join(FILEBOT_DATA_DIR, rel)
        html_files = []
        if os.path.isdir(filepath2):
            for fname in os.listdir(filepath2):
                if fname.endswith('.html'):
                    html_files.append(fname)
        if html_files:
            # pick the first html file in that folder (the one named after the folder)
            name = path.rstrip('/').split('/')[-1]
            candidates = [f for f in html_files if f.startswith(name)]
            if candidates:
                fp = os.path.join(filepath2, candidates[0])
            else:
                fp = os.path.join(filepath2, html_files[0])
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            wc.execute("UPDATE webbot_page SET content = ? WHERE path = ? AND (content IS NULL OR content = '')",
                       (content, path))
            fixed += wc.rowcount
        else:
            not_found += 1

wb.commit()
wb.close()

print(f'Backfilled: {fixed} pages')
if not_found:
    print(f'No HTML file found for: {not_found} pages (likely folder nodes)')
