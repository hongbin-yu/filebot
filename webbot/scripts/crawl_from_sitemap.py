#!/usr/bin/env python3
"""
从 canada.ca sitemap.xml 爬取某个 department 的页面并导入 FileBot + WebBot。

用法:
  # 预览（不爬取）
  python3 scripts/crawl_from_sitemap.py --department intelligence-commissioner --dry-run

  # 爬取 EN 页面
  python3 scripts/crawl_from_sitemap.py --department intelligence-commissioner --lang en --limit 10

  # 爬取双语
  python3 scripts/crawl_from_sitemap.py --department intelligence-commissioner --both --limit 30
"""

import argparse
import html.parser
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

FILEBOT_DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
WEBBOT_DB_PATH = "/home/hongb/.openclaw/workspace/webbot/app/webbot.db"
FILEBOT_DATA_DIR = "/home/hongb/.openclaw/workspace/filebot/backend/data"
CANADA_CA_BASE = "https://www.canada.ca"


def fetch_xml(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'WebBot/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  ❌ 获取 sitemap 失败: {e}")
        return None


def parse_sitemap_urls(xml_content: str) -> list[str]:
    """从 sitemap XML 中提取所有 <loc> URL（仅 .html 或无后缀的页面）"""
    urls = re.findall(r'<loc>\s*(https?://[^<]+?)\s*</loc>', xml_content)
    out = []
    for u in urls:
        u = u.rstrip('/')
        # 跳过非页面资源
        skip_ext = ('.pdf', '.jpg', '.png', '.gif', '.xml', '.rss', '.atom', '.json', '.csv', '.zip')
        if any(u.lower().endswith(ext) for ext in skip_ext):
            continue
        out.append(u)
    return out


def url_to_doc_path(url: str) -> str | None:
    """将 canada.ca URL 转为 filebot document path"""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.rstrip('/')
    if path.endswith('.html'):
        path = path[:-5]

    if '/content/canadasite/' in path:
        path = re.sub(r'^/content/canadasite', '', path)

    # 必须包含 /en/ 或 /fr/
    m = re.match(r'^/(en|fr)/(.*)', path)
    if not m:
        return None
    return f'/boarding/canadasite/{m.group(1)}/{m.group(2)}'


def detect_lang(doc_path: str) -> str:
    rest = doc_path.replace('/boarding', '', 1)
    if '/fr/' in rest:
        return 'fr'
    return 'en'


def build_canada_url(doc_path: str) -> str:
    """从 doc_path 反向构建 canada.ca URL"""
    m = re.search(r'/canadasite/(en|fr)/(.+)$', doc_path)
    if not m:
        return ''
    return f'{CANADA_CA_BASE}/{m.group(1)}/{m.group(2)}.html'


def derive_other_lang_path(path: str) -> str | None:
    if '/en/' in path:
        return path.replace('/en/', '/fr/', 1)
    if '/fr/' in path:
        return path.replace('/fr/', '/en/', 1)
    return None


class WbLngParser(html.parser.HTMLParser):
    """解析 #wb-lng 中的语言切换链接"""
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
    """从 HTML 的 #wb-lng 段中提取对方语言的路径"""
    p = WbLngParser()
    try:
        p.feed(html_content)
    except Exception:
        return None
    if p.alt_href:
        # href 格式: /fr/commissaire-renseignement/message 或 /fr/commissaire-renseignement/message.html
        href = urllib.parse.urlparse(p.alt_href).path.rstrip('/')
        if href.endswith('.html'):
            href = href[:-5]
        # 转为 webbot 路径: /fr/commissaire-renseignement/message → /canadasite/fr/commissaire-renseignement/message
        lang = p.alt_lang  # 'fr' or 'en'
        return f'/canadasite{href}'
    return None


def fetch_html(url: str, retries: int = 3) -> str | None:
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
    rel = doc_path.lstrip('/')
    filepath = os.path.join(FILEBOT_DATA_DIR, f"{rel}.html")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return f"{rel}.html"


def create_document_record(fb_cur, doc_path: str, storage_path: str, stored_filename: str):
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
           f'Webpage from {build_canada_url(doc_path)}',
           stored_filename, stored_filename, storage_path))


def ensure_webbot_parent(wb_cur, parent_path: str, language: str,
                          other_lang_parent_path: str | None = None):
    if not parent_path or parent_path == '/':
        return
    wb_cur.execute("SELECT id FROM webbot_page WHERE path = ?", (parent_path,))
    if wb_cur.fetchone():
        if other_lang_parent_path:
            wb_cur.execute(
                "UPDATE webbot_page SET other_language_path = ? WHERE path = ? AND other_language_path IS NULL",
                (other_lang_parent_path, parent_path)
            )
        return
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


def import_to_webbot(wb_cur, doc_path: str, stored_filename: str, language: str,
                     other_language_path: str | None = None,
                     html_content: str | None = None):
    wb_path = doc_path[len('/boarding'):] if doc_path.startswith('/boarding/') else doc_path

    wb_cur.execute('SELECT id FROM webbot_page WHERE path = ?', (wb_path,))
    if wb_cur.fetchone():
        # 已有但可能缺 other_language_path
        if other_language_path:
            wb_cur.execute(
                "UPDATE webbot_page SET other_language_path = ? WHERE path = ? AND other_language_path IS NULL",
                (other_language_path, wb_path)
            )
        # 也补一下 content（如果从文件读得到的话）
        if wb_cur.execute('SELECT content FROM webbot_page WHERE path = ?', (wb_path,)).fetchone()[0] is None:
            if html_content:
                wb_cur.execute(
                    "UPDATE webbot_page SET content = ? WHERE path = ? AND content IS NULL",
                    (html_content, wb_path)
                )
        return 'exists'

    title = os.path.splitext(stored_filename)[0].replace('-', ' ').title()

    parent = os.path.dirname(wb_path.rstrip('/'))
    if parent and parent != wb_path:
        parent_other = None
        if other_language_path:
            parent_other = os.path.dirname(other_language_path.rstrip('/'))
        ensure_webbot_parent(wb_cur, parent, language, parent_other)

    wb_cur.execute("""
        INSERT INTO webbot_page (id, path, title, content, language, parent_path, other_language_path,
                                 created_at, last_modified)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (wb_path, wb_path, title, html_content or '', language, parent, other_language_path))

    return 'created'


def main():
    parser = argparse.ArgumentParser(description='从 sitemap.xml 爬取 department 页面')
    parser.add_argument('--department', '-d', required=True,
                        help='Department slug (e.g. intelligence-commissioner)')
    parser.add_argument('--lang', choices=['en', 'fr'], default='en',
                        help='要爬取的语言')
    parser.add_argument('--both', action='store_true',
                        help='同时爬取 EN 和 FR')
    parser.add_argument('--dry-run', action='store_true',
                        help='只预览不爬取')
    parser.add_argument('--limit', type=int, default=0,
                        help='限制爬取数量（每语言）')
    parser.add_argument('--delay', type=float, default=0.3,
                        help='请求间隔秒数')
    args = parser.parse_args()

    # 收集 sitemap URL
    if args.both:
        langs = ['en', 'fr']
    else:
        langs = [args.lang]

    all_pages = []  # [(url, lang, doc_path), ...]

    for lang in langs:
        # 语言到 sitemap slug 的映射
        # EN 和 FR 的 sitemap slug 映射
        fr_slug_map = {
            'intelligence-commissioner': 'commissaire-renseignement',
            'translation-bureau': 'bureau-traduction',
            'copyright-board': 'commision-droit-auteur',
            'correctional-investigator': 'enqueteur-correctionnel',
            'national-battlefields-commission': 'commission-champs-bataille-nationaux',
            'national-film-board': 'office-national-film',
        }
        en_slug = args.department
        fr_slug = fr_slug_map.get(args.department, args.department)
        slug = en_slug if lang == 'en' else fr_slug
        sitemap_url = f'{CANADA_CA_BASE}/{lang}/{slug}.sitemap.xml'

        print(f'📡 获取 {lang.upper()} sitemap: {sitemap_url}')
        xml = fetch_xml(sitemap_url)
        if not xml:
            print(f'  ❌ 无法获取 {lang.upper()} sitemap')
            continue

        urls = parse_sitemap_urls(xml)
        print(f'  📄 {len(urls)} 个 URL')

        for url in urls:
            dp = url_to_doc_path(url)
            if dp:
                all_pages.append((url, lang, dp))

    if not all_pages:
        print('❌ 没有找到可爬取的页面')
        return

    print(f'\n📊 总计 {len(all_pages)} 个页面 (EN: {sum(1 for _, l, _ in all_pages if l=="en")}, '
          f'FR: {sum(1 for _, l, _ in all_pages if l=="fr")})')

    if args.limit:
        # 每语言限制
        en_pages = [(u, l, d) for u, l, d in all_pages if l == 'en']
        fr_pages = [(u, l, d) for u, l, d in all_pages if l == 'fr']
        all_pages = en_pages[:args.limit] + fr_pages[:args.limit]
        print(f'   (限制每语言 {args.limit} 个 = {len(all_pages)} 总计)')

    if args.dry_run:
        print(f'\n📋 Dry-run: 将会爬取 {len(all_pages)} 个页面:')
        for url, lang, dp in all_pages[:20]:
            print(f'  [{lang.upper()}] {url}')
            print(f'           → doc: {dp}')
        if len(all_pages) > 20:
            print(f'           ... 还有 {len(all_pages) - 20} 个')
        return

    # === 开始爬取 ===
    fb_conn = sqlite3.connect(FILEBOT_DB_PATH)
    fb_cur = fb_conn.cursor()
    wb_conn = sqlite3.connect(WEBBOT_DB_PATH)
    wb_cur = wb_conn.cursor()

    stats = {'crawled': 0, 'failed': 0, 'imported': 0, 'existed': 0, 'saved': 0,
             'other_lang_filled': 0}

    start_time = time.time()

    for i, (target_url, lang, doc_path) in enumerate(all_pages, 1):
        filename = doc_path.rstrip('/').split('/')[-1] + '.html'

        # 初始化 other_lang_path（后面从 #wb-lng 解析）
        other_lang_path = None

        print(f'\n[{i}/{len(all_pages)}] [{lang.upper()}] {target_url}')
        print(f'   doc: {doc_path}')

        # 检查 filebot 是否已有
        fb_cur.execute('SELECT path FROM documents WHERE path = ?', (doc_path,))
        in_filebot = fb_cur.fetchone() is not None

        if not in_filebot:
            # 抓取 HTML
            html = fetch_html(target_url)
            if not html:
                stats['failed'] += 1
                continue

            stats['crawled'] += 1

            # 从 #wb-lng 解析对方语言的真实路径
            other_lang_path = extract_other_lang_path_from_html(html)

            # 保存
            save_html_file(doc_path, html)
            stats['saved'] += 1

            # filebot 记录
            create_document_record(fb_cur, doc_path, None, filename)
        else:
            # 从已保存的文件解析 #wb-lng
            rel = doc_path.lstrip('/')
            filepath = os.path.join(FILEBOT_DATA_DIR, f"{rel}.html")
            if os.path.isfile(filepath):
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    existing_html = f.read()
                other_lang_path = extract_other_lang_path_from_html(existing_html)
                html = existing_html
            else:
                html = None

        # 导入 webbot（带上 content + 真实 other_lang_path）
        result = import_to_webbot(wb_cur, doc_path, filename, lang,
                                   other_language_path=other_lang_path,
                                   html_content=html)
        if result == 'created':
            stats['imported'] += 1
        elif result == 'exists' and other_lang_path:
            stats['other_lang_filled'] += 1

        if not in_filebot:
            print(f'   ✅ 已导入')

        # 定期提交
        if i % 20 == 0:
            fb_conn.commit()
            wb_conn.commit()
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(all_pages) - i) / rate if rate > 0 else 0
            print(f'\n--- 进度: {i}/{len(all_pages)} ({rate:.1f}/s) ETA: {eta:.0f}s ---')

        time.sleep(args.delay)

    fb_conn.commit()
    wb_conn.commit()
    fb_conn.close()
    wb_conn.close()
    total_time = time.time() - start_time

    print(f'\n{"="*50}')
    print(f'✅ 完成 (耗时 {total_time:.0f}s)')
    print(f'   抓取成功: {stats["crawled"]}')
    print(f'   抓取失败: {stats["failed"]}')
    print(f'   文件保存: {stats["saved"]}')
    print(f'   导入 webbot: {stats["imported"]}')
    print(f'   已有跳过: {stats["existed"]}')
    print(f'   补充 other_language_path: {stats["other_lang_filled"]}')


if __name__ == '__main__':
    main()
