#!/usr/bin/env python3
"""
爬取 WebBot 中缺失的 EN/FR 页面。

检测 filebot.db 中已有 HTML 文档，解析 #wb-lng 中的语言切换链接，
若对方语言页面在 webbot_page 中不存在，则从 canada.ca 爬取并导入。

用法:
  # FR → EN：爬取 FR 文档指向但缺失的 EN 页面
  python3 scripts/crawl_missing_en.py --direction fr2en

  # EN → FR：爬取 EN 文档指向但缺失的 FR 页面（主要缺口）
  python3 scripts/crawl_missing_en.py --direction en2fr [--limit 100]

  # 预览
  python3 scripts/crawl_missing_en.py --direction en2fr --dry-run
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import html.parser

FILEBOT_DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
WEBBOT_DB_PATH = "/home/hongb/.openclaw/workspace/webbot/app/webbot.db"
FILEBOT_DATA_DIR = "/home/hongb/.openclaw/workspace/filebot/backend/data"
CANADA_CA_BASE = "https://www.canada.ca"


class WbLngParser(html.parser.HTMLParser):
    """解析 #wb-lng 中的语言切换链接"""
    def __init__(self):
        super().__init__()
        self.alt_href = None
        self._in_wb_lng = False
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'section' and d.get('id') == 'wb-lng':
            self._in_wb_lng = True
            self._depth = 1
            return
        if self._in_wb_lng:
            self._depth += 1
            if tag == 'a' and d.get('lang') in ('en', 'fr') and d.get('href'):
                self.alt_href = d['href']

    def handle_endtag(self, tag):
        if self._in_wb_lng:
            self._depth -= 1
            if self._depth <= 0:
                self._in_wb_lng = False


def extract_wb_lng_href(filepath: str) -> str | None:
    """从 HTML 文件提取 #wb-lng 中的语言切换 href"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(500000)
        p = WbLngParser()
        p.feed(content)
        return p.alt_href
    except FileNotFoundError:
        return None


def read_html_file(doc_path: str, storage_path: str | None) -> str | None:
    """读取文档 HTML 文件"""
    if storage_path:
        filepath = os.path.join(FILEBOT_DATA_DIR, storage_path)
        if os.path.isfile(filepath):
            return filepath
    rel = doc_path.lstrip('/')
    filepath = os.path.join(FILEBOT_DATA_DIR, f"{rel}.html")
    if os.path.isfile(filepath):
        return filepath
    return None


def fetch_url(url: str, retries: int = 3) -> str | None:
    """从 canada.ca 抓取 HTML 内容"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; WebBot/1.0)',
                    'Accept': 'text/html,application/xhtml+xml',
                    'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8',
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
                charset = resp.headers.get_content_charset() or 'utf-8'
                return content.decode(charset, errors='replace')
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"    ⏳ 重试 ({attempt + 1}/{retries}): {e}, {wait}s 后重试...")
                time.sleep(wait)
            else:
                print(f"    ❌ 抓取失败: {e}")
                return None


def save_html_file(doc_path: str, html_content: str) -> str:
    """保存 HTML 到 filebot 数据目录，返回 storage_path"""
    rel = doc_path.lstrip('/')
    filepath = os.path.join(FILEBOT_DATA_DIR, f"{rel}.html")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return f"{rel}.html"


def create_document_record(fb_cur, doc_path: str, storage_path: str,
                           stored_filename: str):
    """在 filebot documents 表创建记录"""
    folder_path = os.path.dirname(doc_path)
    name = os.path.splitext(stored_filename)[0]
    fb_cur.execute("""
        INSERT OR IGNORE INTO documents 
            (path, folder_path, title, description, status, type,
             publish_status, original_filename, stored_filename, 
             file_type, mime_type, storage_path, document_metadata)
        VALUES (?, ?, ?, ?, 'ACTIVE', 'GENERAL',
                'UNPUBLISHED', ?, ?, 'HTML', 'text/html', ?, '{}')
    """, (doc_path, folder_path, name,
           f'Webpage from {doc_path}',
           stored_filename, stored_filename, storage_path))


def derive_other_lang_path(path: str) -> str | None:
    """通过交换 /en/ ↔ /fr/ 推导另一种语言的路径"""
    if '/en/' in path:
        return path.replace('/en/', '/fr/', 1)
    if '/fr/' in path:
        return path.replace('/fr/', '/en/', 1)
    return None


def import_to_webbot(wb_cur, doc_path: str, stored_filename: str, language: str,
                     other_language_path: str | None = None,
                     html_content: str | None = None):
    """导入到 webbot_page 表"""
    wb_path = doc_path[len('/boarding'):] if doc_path.startswith('/boarding/') else doc_path

    wb_cur.execute('SELECT id FROM webbot_page WHERE path = ?', (wb_path,))
    if wb_cur.fetchone():
        # 已有但可能缺 content
        if html_content:
            wb_cur.execute(
                "UPDATE webbot_page SET content = ? WHERE path = ? AND (content IS NULL OR content = '')",
                (html_content, wb_path)
            )
        return 'exists'

    title = os.path.splitext(stored_filename)[0].replace('-', ' ').title()

    parent = os.path.dirname(wb_path.rstrip('/'))
    if parent and parent != wb_path:
        # 父路径的 other_language_path = other_language_path 去掉末尾一段
        parent_other_lang = None
        if other_language_path:
            parent_other_lang = os.path.dirname(other_language_path.rstrip('/'))
        ensure_webbot_parent(wb_cur, parent, language, parent_other_lang)

    wb_cur.execute("""
        INSERT INTO webbot_page (id, path, title, content, language, parent_path, other_language_path,
                                 created_at, last_modified)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (wb_path, wb_path, title, html_content or '', language, parent, other_language_path))

    return 'created'


def ensure_webbot_parent(wb_cur, parent_path: str, language: str,
                          other_lang_parent_path: str | None = None):
    """确保 webbot_page 中有父路径节点，同时设置 other_language_path"""
    if not parent_path or parent_path == '/':
        return
    wb_cur.execute("SELECT id FROM webbot_page WHERE path = ?", (parent_path,))
    if wb_cur.fetchone():
        # 已存在但可能没有 other_language_path，如果传了就更新
        if other_lang_parent_path:
            wb_cur.execute(
                "UPDATE webbot_page SET other_language_path = ? WHERE path = ? AND other_language_path IS NULL",
                (other_lang_parent_path, parent_path)
            )
        return
    # 递归先创建祖父路径
    grandparent = os.path.dirname(parent_path.rstrip('/'))
    grandparent_other = None
    if grandparent and grandparent != parent_path and other_lang_parent_path:
        grandparent_other = os.path.dirname(other_lang_parent_path.rstrip('/'))
    if grandparent and grandparent != parent_path:
        ensure_webbot_parent(wb_cur, grandparent, language, grandparent_other)
    name = parent_path.rstrip('/').split('/')[-1]
    wb_cur.execute("""
        INSERT INTO webbot_page (id, path, title, language, parent_path, other_language_path,
                                 created_at, last_modified)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (parent_path, parent_path, name, language, grandparent or '/', other_lang_parent_path))


def href_to_canada_url(href: str) -> str:
    """将 #wb-lng href 转为完整的 CANADA.CA URL"""
    href = href.strip()
    if href.startswith('http'):
        return href
    if href.startswith('/'):
        return f"{CANADA_CA_BASE}{href}"
    return f"{CANADA_CA_BASE}/{href}"


def href_to_wb_candidates(href: str) -> list[str]:
    """将 #wb-lng href 转为候选 webbot_page 路径（去重）"""
    # 去 .html 后缀
    base = href[:-5] if href.endswith('.html') else href

    candidates = [f'/canadasite{base}', f'/boarding/canadasite{base}']

    # 如果包含 staging 路径 /content/canadasite/
    if '/content/canadasite/' in base:
        rest = base.split('/content/canadasite', 1)[1]
        candidates.insert(0, f'/canadasite{rest}')
        candidates.insert(1, f'/boarding/canadasite{rest}')

    # 去重保留顺序
    seen = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]


def detect_language_from_path(path: str) -> str:
    """从路径检测语言"""
    rest = path.replace('/boarding', '', 1)
    for pfx in ('/canadasite/', '/content/canadasite/'):
        idx = rest.find(pfx)
        if idx >= 0:
            sub = rest[idx + len(pfx):]
            if sub.startswith('en/'):
                return 'en'
            if sub.startswith('fr/'):
                return 'fr'
    if '/en/' in rest:
        return 'en'
    if '/fr/' in rest:
        return 'fr'
    return 'en'  # default


def find_missing_pages(fb_cur, wb_cur, direction: str, limit: int):
    """
    查找缺失的响应式页面。
    direction='fr2en': 从 FR 文档的 #wb-lng 找缺失的 EN
    direction='en2fr': 从 EN 文档的 #wb-lng 找缺失的 FR
    """
    source_lang = 'en' if direction == 'en2fr' else 'fr'
    target_lang = 'fr' if direction == 'en2fr' else 'en'
    lang_code = 'fr' if target_lang == 'fr' else 'en'  # #wb-lng a 标签的 lang 值

    fb_cur.execute("""
        SELECT path, storage_path
        FROM documents
        WHERE path LIKE '/boarding/canadasite/{}/%'
          AND (file_type = 'HTML' OR mime_type = 'text/html')
          AND storage_path IS NOT NULL AND storage_path != ''
        ORDER BY path
    """.format(source_lang))

    docs = fb_cur.fetchall()
    print(f"📄 检查 {len(docs)} 个 {source_lang.upper()} 文档")

    missing = []  # (target_url, source_path, source_storage)

    for r in docs:
        doc_path = r[0]
        storage = r[1]

        filepath = read_html_file(doc_path, storage)
        if not filepath:
            continue

        href = extract_wb_lng_href(filepath)
        if not href:
            continue

        # 确认 href 指向目标语言
        if target_lang not in href.split('/'):
            continue

        candidates = href_to_wb_candidates(href)
        exists = any(
            wb_cur.execute('SELECT 1 FROM webbot_page WHERE path = ?', (c,)).fetchone()
            for c in candidates
        )
        if not exists:
            target_url = href_to_canada_url(href)
            missing.append((target_url, doc_path, storage))

    print(f"🔍 发现 {len(missing)} 个缺失的 {target_lang.upper()} 页面")
    if limit:
        missing = missing[:limit]
        print(f"   (限制 {limit} 个)")

    return missing, source_lang, target_lang


def build_target_doc_path(target_url: str) -> str:
    """
    从 canada.ca URL 构建 filebot document path。
    例: https://www.canada.ca/fr/services/emplois.html
      → /boarding/canadasite/fr/services/emplois
    """
    parsed = urllib.parse.urlparse(target_url)
    path = parsed.path.rstrip('/')
    if path.endswith('.html'):
        path = path[:-5]

    # 去掉 /content/canadasite 前缀
    path = re.sub(r'^/content/canadasite', '', path)

    # 确保以 /en/ 或 /fr/ 开头（相对于 /canadasite 根）
    if path.startswith('/en/') or path.startswith('/fr/'):
        return f'/boarding/canadasite{path}'
    # 没有语言代码
    return f'/boarding/canadasite{path}'


def main():
    parser = argparse.ArgumentParser(description='爬取缺失的 EN/FR 页面')
    parser.add_argument('--direction', choices=['fr2en', 'en2fr'], default='en2fr',
                        help='爬取方向: fr2en=从FR找缺的EN, en2fr=从EN找缺的FR')
    parser.add_argument('--dry-run', action='store_true', help='只预览不爬取')
    parser.add_argument('--limit', type=int, default=0, help='限制爬取数量（0=不限制）')
    parser.add_argument('--retries', type=int, default=3, help='抓取重试次数')
    parser.add_argument('--delay', type=float, default=0.3, help='请求间隔秒数')
    args = parser.parse_args()

    fb_conn = sqlite3.connect(FILEBOT_DB_PATH)
    fb_cur = fb_conn.cursor()
    wb_conn = sqlite3.connect(WEBBOT_DB_PATH)
    wb_cur = wb_conn.cursor()

    missing, src_lang, tgt_lang = find_missing_pages(
        fb_cur, wb_cur, args.direction, args.limit
    )

    if not missing:
        print("✅ 没有缺失的页面需要爬取")
        fb_conn.close()
        wb_conn.close()
        return

    if args.dry_run:
        print(f"\n📋 Dry-run: 将会从 canada.ca 爬取 {len(missing)} 个 {tgt_lang.upper()} 页面:")
        for url, src_path, _ in missing[:30]:
            doc_path = build_target_doc_path(url)
            print(f"   {url}")
            print(f"     → doc: {doc_path}  (来源: {src_path})")
        if len(missing) > 30:
            print(f"   ... 还有 {len(missing) - 30} 个")
        fb_conn.close()
        wb_conn.close()
        return

    # === 开始爬取 ===
    stats = {'crawled': 0, 'failed': 0, 'imported': 0, 'existed': 0, 'saved': 0}

    print(f"\n🌐 开始爬取 {len(missing)} 个 {tgt_lang.upper()} 页面...")
    start_time = time.time()

    for i, (target_url, src_path, src_storage) in enumerate(missing, 1):
        doc_path = build_target_doc_path(target_url)
        wb_path = doc_path[len('/boarding'):]
        filename = doc_path.rstrip('/').split('/')[-1] + '.html'

        print(f"\n[{i}/{len(missing)}] {target_url}")
        print(f"   doc: {doc_path}")

        # 1. 先检查 filebot 是否已有
        fb_cur.execute('SELECT path FROM documents WHERE path = ?', (doc_path,))
        existing_doc = fb_cur.fetchone()
        if existing_doc:
            print(f"   ⏭️   filebot 已有记录")
            stats['existed'] += 1
            # 仍然检查 webbot（尝试从事先保存的 HTML 读取 content）
            src_wb_path = src_path[len('/boarding'):] if src_path.startswith('/boarding/') else src_path
            # 从磁盘读已有内容
            existing_html = read_html_file(doc_path, None)
            result = import_to_webbot(wb_cur, doc_path, filename, tgt_lang,
                                      other_language_path=src_wb_path,
                                      html_content=existing_html)
            if result == 'created':
                stats['imported'] += 1
                print(f"   ✅ 导入到 webbot")
            continue

        # 2. 抓取 HTML
        html = fetch_url(target_url, retries=args.retries)
        if not html:
            stats['failed'] += 1
            continue

        stats['crawled'] += 1

        # 3. 保存 HTML 文件
        save_html_file(doc_path, html)
        stats['saved'] += 1

        # 4. 在 filebot documents 表创建记录
        create_document_record(fb_cur, doc_path, None, filename)

        # 5. 导入到 webbot_page（带上 content）
        src_wb_path = src_path[len('/boarding'):] if src_path.startswith('/boarding/') else src_path
        result = import_to_webbot(wb_cur, doc_path, filename, tgt_lang,
                                  other_language_path=src_wb_path,
                                  html_content=html)
        if result == 'created':
            stats['imported'] += 1
        else:
            stats['existed'] += 1

        # 定期提交
        if i % 20 == 0:
            fb_conn.commit()
            wb_conn.commit()
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(missing) - i) / rate if rate > 0 else 0
            print(f"\n--- 进度: {i}/{len(missing)} ({rate:.1f}/s) ETA: {eta:.0f}s ---")

        time.sleep(args.delay)

    # 最终提交
    fb_conn.commit()
    wb_conn.commit()
    total_time = time.time() - start_time

    print(f"\n{'='*50}")
    print(f"✅ 完成 (耗时 {total_time:.0f}s)")
    print(f"   抓取成功: {stats['crawled']}")
    print(f"   抓取失败: {stats['failed']}")
    print(f"   文件保存: {stats['saved']}")
    print(f"   导入 webbot: {stats['imported']}")
    print(f"   已存在跳过: {stats['existed']}")

    fb_conn.close()
    wb_conn.close()


if __name__ == '__main__':
    main()
