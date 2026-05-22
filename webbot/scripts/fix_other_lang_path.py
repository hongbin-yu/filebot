#!/usr/bin/env python3
"""Fix other_language_path in webbot_page by reading #wb-lng from saved HTML files."""
import sqlite3, os, sys, urllib.parse, html.parser

FILEBOT_DATA_DIR = "/home/hongb/.openclaw/workspace/filebot/backend/data"
WEBBOT_DB_PATH = "/home/hongb/.openclaw/workspace/webbot/app/webbot.db"

path_filter = sys.argv[1] if len(sys.argv) > 1 else None


class WbLngParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.alt_href = None
        self.alt_lang = None
        self._in_wb_lng = False
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'section' and d.get('id') == 'wb-lng':
            self._in_wb_lng = True
            self._depth = 1
            return
        if self._in_wb_lng:
            if tag == 'section':
                self._depth += 1
            if tag == 'a' and d.get('lang') in ('fr', 'en'):
                self.alt_href = d.get('href', '')
                self.alt_lang = d.get('lang')

    def handle_endtag(self, tag):
        if self._in_wb_lng:
            if tag == 'section':
                self._depth -= 1
                if self._depth == 0:
                    self._in_wb_lng = False


def extract_other_lang_path_from_html(html_content: str) -> str | None:
    p = WbLngParser()
    try:
        p.feed(html_content)
    except Exception:
        return None
    if p.alt_href:
        href = urllib.parse.urlparse(p.alt_href).path.rstrip('/')
        if href.endswith('.html'):
            href = href[:-5]
        return f'/canadasite{href}'
    return None


wb = sqlite3.connect(WEBBOT_DB_PATH)
wc = wb.cursor()

# 找出 all pages that have a non-null other_language_path, read the HTML file, and verify
if path_filter:
    rows = wc.execute("SELECT path, other_language_path FROM webbot_page WHERE path LIKE ?",
                      ('%' + path_filter + '%',)).fetchall()
else:
    rows = wc.execute("SELECT path, other_language_path FROM webbot_page WHERE other_language_path IS NOT NULL").fetchall()

fixed = 0
errors = 0
skipped = 0

for (path, current_other) in rows:
    # skip root entries  
    if path in ('/', '/en', '/fr', '/canadasite', '/canadasite/en', '/canadasite/fr'):
        continue
    
    rel = os.path.join("boarding", path.lstrip("/"))
    filepath = os.path.join(FILEBOT_DATA_DIR, f"{rel}.html")
    
    if not os.path.isfile(filepath):
        errors += 1
        continue
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()
    
    correct_other = extract_other_lang_path_from_html(html)
    if not correct_other:
        errors += 1
        continue
    
    if correct_other != current_other:
        wc.execute("UPDATE webbot_page SET other_language_path = ? WHERE path = ?",
                   (correct_other, path))
        fixed += 1
        print(f'  📝 {path}')
        print(f'     old: {current_other}')
        print(f'     new: {correct_other}')

wb.commit()
wb.close()

print(f'\n✅ 修复: {fixed} 页')
print(f'⚠️  无法读取/无链接: {errors} 页')
print(f'⏭️  已正确: {skipped} 页')
