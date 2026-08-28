#!/usr/bin/env python3
"""
Incremental sync from canada.ca sitemap.

用法:
  # dev 环境（默认）
  python3 scripts/incremental_sync.py --sitemap https://www.canada.ca/en/services.sitemap.xml

  # prod 环境（使用 PostgreSQL + prod 路径）
  python3 scripts/incremental_sync.py --env prod --sitemap https://www.canada.ca/en/services.sitemap.xml

  # 预览变化（不爬取）
  python3 scripts/incremental_sync.py --env prod --sitemap ... --dry-run

  # 强制全量重爬
  python3 scripts/incremental_sync.py --env prod --sitemap ... --force

  # 限制数量
  python3 scripts/incremental_sync.py --env prod --sitemap ... --limit 20

原理:
  1. 抓取 sitemap XML，解析 <loc> 和 <lastmod>
  2. 与本地快照文件对比 (sitemap_snapshots/{slug}.json)
  3. 只爬取: 新增 URL + lastmod 更新的 URL
  4. 爬取后更新快照
"""

import argparse
import html.parser
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

# ── 环境配置 ──────────────────────────────────────────────────────────────

ENV_CONFIGS = {
    'dev': {
        'webbot_db': 'PLACEHOLDER',  # resolved relative to PROJECT_DIR
        'filebot_data': 'PLACEHOLDER',
        'filebot_db': '/home/hongb/.openclaw/workspace/filebot/backend/filebot.db',
        'filebot_mode': 'sqlite',
        'snapshot_dir': 'PLACEHOLDER',  # resolved relative to SCRIPT_DIR
    },
    'prod': {
        'webbot_db': '/opt/webfilebot/webbot/data/webbot.db',
        'filebot_data': '/opt/webfilebot/filebot-backend/data',
        'filebot_pg_url': 'postgresql://filebot:filebot@localhost:5432/filebot',
        'filebot_mode': 'postgres',
        'snapshot_dir': '/opt/webfilebot/sitemap_snapshots',
        'admin_user_id': '4dad6fa1-d521-417f-8877-efe95fcf1f04',
        'app_id': '25801434-c253-4e77-8261-fa4d341e0830',  # Boarding app
    },
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
CANADA_CA_BASE = "https://www.canada.ca"

# 实际值在 main() 中根据 env 参数解析
_config = {}


# ── Sitemap 获取与解析 ──────────────────────────────────────────────────

def fetch_sitemap(url: str) -> str | None:
    """获取 sitemap XML"""
    user_agents = [
        'Mozilla/5.0 (compatible; WebBot/1.0)',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    ]
    for ua in user_agents:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': ua})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except Exception:
            continue
    print(f"  ❌ 所有 UA 都无法获取 sitemap: {url}")
    return None


def parse_sitemap_entries(xml_content: str) -> list[dict]:
    """解析 sitemap XML，返回 [{loc, lastmod, lastmod_dt}]"""
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    root = ET.fromstring(xml_content)
    urls = root.findall(f'{ns}url')
    entries = []
    for u in urls:
        loc_el = u.find(f'{ns}loc')
        if loc_el is None or not loc_el.text:
            continue
        loc = loc_el.text.strip().rstrip('/')
        lm_el = u.find(f'{ns}lastmod')
        lastmod = lm_el.text.strip() if lm_el is not None and lm_el.text else ''
        entries.append({'loc': loc, 'lastmod': lastmod})
    return entries


# ── 快照管理 ────────────────────────────────────────────────────────────

def snapshot_path(sitemap_url: str) -> str:
    """从 sitemap URL 生成快照文件名"""
    parsed = urllib.parse.urlparse(sitemap_url)
    path = parsed.path.rstrip('/')
    parts = path.split('/')
    slug = parts[-1].replace('.sitemap.xml', '').replace('.xml', '')
    lang = 'en'
    for p in parts:
        if p in ('en', 'fr'):
            lang = p
    return os.path.join(_config['snapshot_dir'], f'{slug}_{lang}.sitemap.json')


def load_snapshot(sitemap_url: str) -> dict:
    """加载上一次的快照：{url: lastmod_string}"""
    spath = snapshot_path(sitemap_url)
    if os.path.isfile(spath):
        with open(spath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_snapshot(sitemap_url: str, snapshot: dict):
    """保存快照"""
    spath = snapshot_path(sitemap_url)
    os.makedirs(os.path.dirname(spath), exist_ok=True)
    with open(spath, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    print(f"  💾 快照已保存: {spath} ({len(snapshot)} 个 URL)")


# ── URL 路径转换 ────────────────────────────────────────────────────────

def url_to_doc_path(url: str) -> str | None:
    """将 canada.ca URL 转为 filebot document path"""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.rstrip('/')
    if path.endswith('.html'):
        path = path[:-5]

    if '/content/canadasite/' in path:
        path = re.sub(r'^/content/canadasite', '', path)

    m = re.match(r'^/(en|fr)/(.*)', path)
    if not m:
        return None
    return f'/boarding/canadasite/{m.group(1)}/{m.group(2)}'


def doc_path_to_wb_path(doc_path: str) -> str:
    """filebot doc path → webbot page path"""
    if doc_path.startswith('/boarding/'):
        return doc_path[len('/boarding'):]
    return doc_path


def detect_lang(doc_path: str) -> str:
    rest = doc_path.replace('/boarding', '', 1)
    if '/fr/' in rest:
        return 'fr'
    return 'en'


def build_canada_url(doc_path: str) -> str:
    m = re.search(r'/canadasite/(en|fr)/(.+)$', doc_path)
    if not m:
        return ''
    return f'{CANADA_CA_BASE}/{m.group(1)}/{m.group(2)}.html'


# ── 页面内容爬取 ────────────────────────────────────────────────────────

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
                print(f"    ⏳ 重试 ({attempt + 1}/{retries}): {e}, {wait}s 后...")
                time.sleep(wait)
            else:
                print(f"    ❌ 抓取失败: {e}")
                return None


def save_html_file(doc_path: str, html_content: str) -> str:
    rel = doc_path.lstrip('/')
    filepath = os.path.join(_config['filebot_data'], f"{rel}.html")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return f"{rel}.html"


# ── #wb-lng 解析 ───────────────────────────────────────────────────────

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
        lang = p.alt_lang
        return f'/canadasite{href}'
    return None


# ── FileBot 连接管理 ────────────────────────────────────────────────────

def open_filebot():
    """根据环境打开 FileBot DB 连接（SQLite 或 PostgreSQL）"""
    mode = _config['filebot_mode']
    if mode == 'postgres':
        import psycopg2  # lazy import, only on prod
        conn = psycopg2.connect(_config['filebot_pg_url'])
        return conn
    else:
        return sqlite3.connect(_config['filebot_db'])


def ensure_filebot_tables(conn):
    """确保 FileBot DB 有必要的表（仅 SQLite 需要，PG 已有）"""
    mode = _config['filebot_mode']
    if mode == 'postgres':
        return  # PG 表已存在

    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
    if cur.fetchone():
        return

    print('  ⚠️  创建 documents 表 (FileBot DB)...')
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            path VARCHAR(500) PRIMARY KEY,
            folder_path VARCHAR(500) NOT NULL DEFAULT '',
            document_number VARCHAR(100) UNIQUE,
            title VARCHAR(255),
            description VARCHAR(1000),
            status VARCHAR(20) DEFAULT 'ACTIVE',
            type VARCHAR(20) DEFAULT 'GENERAL',
            comments VARCHAR(2000),
            publish_status VARCHAR(20) DEFAULT 'UNPUBLISHED',
            original_filename VARCHAR(255) NOT NULL DEFAULT '',
            stored_filename VARCHAR(255) NOT NULL DEFAULT '',
            file_size BIGINT DEFAULT 0,
            file_type VARCHAR(20) DEFAULT 'HTML',
            mime_type VARCHAR(100) DEFAULT 'text/html',
            storage_subfolder VARCHAR(255),
            full_storage_path VARCHAR(500),
            storage_path VARCHAR(500),
            parent_folder_path VARCHAR(500),
            document_metadata TEXT DEFAULT '{}',
            uploaded_by VARCHAR(36) DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100) DEFAULT 'incremental-sync',
            updated_at TIMESTAMP,
            updated_by VARCHAR(100)
        )
    """)
    conn.commit()
    print('  ✅ documents 表已创建')


def filebot_doc_exists(cur, doc_path: str) -> bool:
    """检查 FileBot 是否有此文档"""
    mode = _config['filebot_mode']
    if mode == 'postgres':
        cur.execute("SELECT path FROM documents WHERE path = %s", (doc_path,))
    else:
        cur.execute("SELECT path FROM documents WHERE path = ?", (doc_path,))
    return cur.fetchone() is not None


def pg_ensure_folder(cur, folder_path: str, conn=None):
    """确保 PostgreSQL 文件夹记录存在（递归）"""
    if not folder_path or folder_path == '/':
        return
    cur.execute("SELECT path FROM folders WHERE path = %s", (folder_path,))
    if cur.fetchone():
        return
    parent = os.path.dirname(folder_path.rstrip('/'))
    if parent and parent != folder_path:
        pg_ensure_folder(cur, parent, conn)
    name = folder_path.rstrip('/').split('/')[-1]
    admin_id = _config['admin_user_id']
    app_id = _config['app_id']
    cur.execute("""
        INSERT INTO folders
            (path, app_id, parent_folder_path, name, created_by)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (path) DO NOTHING
    """, (folder_path, app_id, parent or None, name, admin_id))
    if conn:
        conn.commit()


def filebot_create(cur, doc_path: str, stored_filename: str,
                   source_url: str, sitemap_lastmod: str = '',
                   conn=None):
    """新建 FileBot 文档记录"""
    folder_path = os.path.dirname(doc_path)
    name = os.path.splitext(stored_filename)[0]
    meta = json.dumps({
        'source_url': source_url,
        'imported_at': datetime_now(),
        'sitemap_lastmod': sitemap_lastmod,
    })
    mode = _config['filebot_mode']
    if mode == 'postgres':
        pg_ensure_folder(cur, folder_path, conn)
        admin_id = _config['admin_user_id']
        cur.execute("""
            INSERT INTO documents 
                (path, folder_path, title, description, status, type,
                 publish_status, original_filename, stored_filename,
                 file_size, file_type, mime_type, storage_path, document_metadata,
                 uploaded_by)
            VALUES (%s, %s, %s, %s, 'ACTIVE', 'GENERAL',
                    'UNPUBLISHED', %s, %s, 0, 'HTML', 'text/html', %s, %s, %s)
            ON CONFLICT (path) DO NOTHING
        """, (doc_path, folder_path, name,
              f'Webpage from {source_url}',
              stored_filename, stored_filename, '', meta, admin_id))
    else:
        cur.execute("""
            INSERT OR IGNORE INTO documents 
                (path, folder_path, title, description, status, type,
                 publish_status, original_filename, stored_filename, 
                 file_type, mime_type, storage_path, document_metadata)
            VALUES (?, ?, ?, ?, 'ACTIVE', 'GENERAL',
                    'UNPUBLISHED', ?, ?, 'HTML', 'text/html', ?, ?)
        """, (doc_path, folder_path, name,
              f'Webpage from {source_url}',
              stored_filename, stored_filename, '', meta))


def filebot_update(cur, doc_path: str, stored_filename: str,
                   source_url: str, sitemap_lastmod: str = ''):
    """更新已有 FileBot 记录的 metadata"""
    meta = json.dumps({
        'source_url': source_url,
        'imported_at': datetime_now(),
        'sitemap_lastmod': sitemap_lastmod,
    })
    mode = _config['filebot_mode']
    if mode == 'postgres':
        cur.execute(
            "UPDATE documents SET document_metadata = %s, stored_filename = %s WHERE path = %s",
            (meta, stored_filename, doc_path))
    else:
        cur.execute(
            "UPDATE documents SET document_metadata = ?, stored_filename = ? WHERE path = ?",
            (meta, stored_filename, doc_path))


# ── WebBot 写入 ────────────────────────────────────────────────────────

def ensure_webbot_parent(cur, parent_path: str, language: str,
                          other_lang_parent_path: str | None = None):
    if not parent_path or parent_path == '/':
        return
    cur.execute("SELECT id FROM webbot_page WHERE path = ?", (parent_path,))
    if cur.fetchone():
        if other_lang_parent_path:
            cur.execute(
                "UPDATE webbot_page SET other_language_path = ? WHERE path = ? AND other_language_path IS NULL",
                (other_lang_parent_path, parent_path))
        return
    grandparent = os.path.dirname(parent_path.rstrip('/'))
    grandparent_other = None
    if grandparent and grandparent != parent_path and other_lang_parent_path:
        grandparent_other = os.path.dirname(other_lang_parent_path.rstrip('/'))
    if grandparent and grandparent != parent_path:
        ensure_webbot_parent(cur, grandparent, language, grandparent_other)
    name = parent_path.rstrip('/').split('/')[-1]
    cur.execute("""
        INSERT INTO webbot_page (id, path, title, language, parent_path, other_language_path,
                                 created_at, last_modified)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (parent_path, parent_path, name, language, grandparent or '/', other_lang_parent_path))


def import_to_webbot(cur, doc_path: str, stored_filename: str, language: str,
                     other_language_path: str | None = None,
                     html_content: str | None = None,
                     sitemap_lastmod: str = '') -> str:
    """导入/更新到 WebBot。返回 'created' | 'updated'"""
    wb_path = doc_path_to_wb_path(doc_path)

    cur.execute('SELECT id, metadata FROM webbot_page WHERE path = ?', (wb_path,))
    existing = cur.fetchone()
    now = datetime_now()

    title = os.path.splitext(stored_filename)[0].replace('-', ' ').title()
    parent = os.path.dirname(wb_path.rstrip('/'))
    if parent and parent != wb_path:
        parent_other = None
        if other_language_path:
            parent_other = os.path.dirname(other_language_path.rstrip('/'))
        ensure_webbot_parent(cur, parent, language, parent_other)

    # 构建 metadata（保留已有字段 + sitemap_lastmod）
    meta = {}
    if existing:
        try:
            existing_meta = json.loads(existing[1]) if existing[1] else {}
            if isinstance(existing_meta, dict):
                meta = existing_meta
        except (json.JSONDecodeError, TypeError):
            pass

    meta['sitemap_lastmod'] = sitemap_lastmod
    meta['last_synced'] = now

    if existing:
        # last_modified 只由用户 save/import 控制（它作为 date modified 显示在页面上）。
        # daily_sync 是自动任务，无论内容是否变化都不得 touch last_modified，
        # 否则会把 lm 推到 last_published 之后导致 is_republish 全站误报。
        cur.execute("""
            UPDATE webbot_page 
            SET title = ?, content = ?, metadata = ?,
                other_language_path = COALESCE(?, other_language_path)
            WHERE path = ?
        """, (title, html_content or '', json.dumps(meta, ensure_ascii=False),
              other_language_path, wb_path))
        return 'updated'
    else:
        cur.execute("""
            INSERT INTO webbot_page (id, path, title, content, language, parent_path, 
                                     other_language_path, metadata, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (wb_path, wb_path, title, html_content or '', language, parent,
              other_language_path, json.dumps(meta, ensure_ascii=False), now, now))
        return 'created'


def datetime_now() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


# ── 主流程 ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='增量同步：从 sitemap 抓取变更的页面')
    parser.add_argument('--env', default='dev', choices=['dev', 'prod'],
                        help='环境: dev (默认, SQLite) 或 prod (PostgreSQL)')
    parser.add_argument('--sitemap', '-s', required=True,
                        help='Sitemap URL')
    parser.add_argument('--dry-run', action='store_true',
                        help='只预览变化，不爬取')
    parser.add_argument('--force', action='store_true',
                        help='强制全量重新爬取（忽略快照）')
    parser.add_argument('--limit', type=int, default=0,
                        help='最多处理 N 个变化页面')
    parser.add_argument('--skip', type=int, default=0,
                        help='跳过前 N 个变化页面（用于断点续跑）')
    parser.add_argument('--delay', type=float, default=0.3,
                        help='请求间隔秒数')
    args = parser.parse_args()

    # ── 加载环境配置 ──
    global _config
    base_cfg = ENV_CONFIGS[args.env]
    _config = dict(base_cfg)

    if args.env == 'dev':
        _config['webbot_db'] = os.path.join(PROJECT_DIR, 'app', 'webbot.db')
        _config['filebot_data'] = '/home/hongb/.openclaw/workspace/filebot/backend/data'
        _config['snapshot_dir'] = os.path.join(SCRIPT_DIR, 'sitemap_snapshots')

    os.makedirs(_config['snapshot_dir'], exist_ok=True)

    sitemap_url = args.sitemap
    force_full = args.force

    print(f'🌐 环境: {args.env}')
    print(f'   WebBot DB: {_config.get("webbot_db", "N/A")}')
    print(f'   FileBot:   {_config["filebot_mode"]} ({_config.get("filebot_db", _config.get("filebot_pg_url", "?"))})')
    print(f'   FileBot数据: {_config["filebot_data"]}')
    print(f'   快照目录: {_config["snapshot_dir"]}')
    print()

    # ── 1. 获取 sitemap ──
    print(f'📡 获取 sitemap: {sitemap_url}')
    xml = fetch_sitemap(sitemap_url)
    if not xml:
        print('❌ 无法获取 sitemap，退出')
        return

    try:
        remote_entries = parse_sitemap_entries(xml)
    except ET.ParseError as e:
        print(f'❌ Sitemap XML 解析失败: {e}')
        return

    if not remote_entries:
        print('❌ Sitemap 中没有 URL')
        return

    remote_snapshot = {e['loc']: e['lastmod'] for e in remote_entries}
    print(f'📄 Sitemap 包含 {len(remote_entries)} 个 URL, {sum(1 for v in remote_snapshot.values() if v)} 个有 lastmod')

    # ── 2. 加载本地快照 ──
    local_snapshot = load_snapshot(sitemap_url)
    if not local_snapshot:
        print(f'📋 无本地快照（首次运行），将全量处理')
    else:
        print(f'📋 本地快照有 {len(local_snapshot)} 个 URL')

    # ── 3. 计算差异 ──
    to_crawl = []
    skipped = 0
    errors = 0

    for entry in remote_entries:
        loc = entry['loc']
        lastmod = entry['lastmod']

        dp = url_to_doc_path(loc)
        if not dp:
            errors += 1
            continue

        if force_full:
            needs_crawl = True
            reason = '强制全量'
        elif loc not in local_snapshot:
            needs_crawl = True
            reason = '新增页面'
        elif lastmod and lastmod != local_snapshot.get(loc, ''):
            old_lm = local_snapshot.get(loc, '')
            reason = f'lastmod 变更: {old_lm} → {lastmod}'
            needs_crawl = True
        else:
            needs_crawl = False
            reason = '无变化'

        if needs_crawl:
            to_crawl.append((loc, lastmod, dp, reason))
        else:
            skipped += 1

    print(f'\n📊 统计:')
    print(f'   需爬取: {len(to_crawl)}')
    if errors:
        print(f'   路径解析失败: {errors}')
    print(f'   跳过(无变化): {skipped}')

    if args.limit and args.limit < len(to_crawl):
        print(f'   (限制为 {args.limit})')
        to_crawl = to_crawl[:args.limit]

    if args.skip > 0:
        skipped_count = min(args.skip, len(to_crawl))
        to_crawl = to_crawl[skipped_count:]
        print(f'   (跳过前 {skipped_count} 个，断点续跑)')

    def sort_key(item):
        lm = item[1]
        if lm:
            try:
                return lm
            except Exception:
                return ''
        return ''

    to_crawl.sort(key=sort_key, reverse=True)

    print(f'\n📋 变化预览:')
    for loc, lastmod, dp, reason in to_crawl[:20]:
        lm_short = lastmod[:19] if lastmod else '(无 lastmod)'
        print(f'  [{lm_short}] {reason}')
        print(f'           {loc[:80]}')
    if len(to_crawl) > 20:
        print(f'           ... 还有 {len(to_crawl) - 20} 个')

    if args.dry_run:
        print('\n🏁 Dry-run 完成，未爬取任何页面')
        return

    if not to_crawl:
        print('\n✅ 没有需要同步的页面，系统已是最新')
        save_snapshot(sitemap_url, remote_snapshot)
        return

    # ── 4. 开始增量爬取 ──
    print(f'\n🚀 开始爬取 {len(to_crawl)} 个页面 (间隔 {args.delay}s)...')

    # 导入包
    if _config['filebot_mode'] == 'postgres':
        import psycopg2

    import sqlite3

    fb_conn = open_filebot()
    ensure_filebot_tables(fb_conn)
    fb_cur = fb_conn.cursor()

    wb_conn = sqlite3.connect(_config['webbot_db'])
    wb_cur = wb_conn.cursor()

    stats = {
        'crawled': 0, 'failed': 0,
        'fb_created': 0, 'fb_updated': 0,
        'wb_created': 0, 'wb_updated': 0,
    }

    start_time = time.time()

    for i, (target_url, lastmod, doc_path, reason) in enumerate(to_crawl, 1):
        filename = doc_path.rstrip('/').split('/')[-1] + '.html'
        lang = detect_lang(doc_path)

        print(f'\n[{i}/{len(to_crawl)}] [{lang.upper()}] {reason}')
        print(f'   {doc_path[:80]}')
        print(f'   {target_url[:80]}')

        html = fetch_html(target_url)
        if not html:
            stats['failed'] += 1
            continue

        stats['crawled'] += 1

        other_lang_path = extract_other_lang_path_from_html(html)

        storage_path = save_html_file(doc_path, html)

        already_in_fb = filebot_doc_exists(fb_cur, doc_path)

        if not already_in_fb:
            filebot_create(fb_cur, doc_path, filename, target_url, lastmod, conn=fb_conn)
            stats['fb_created'] += 1
        else:
            filebot_update(fb_cur, doc_path, filename, target_url, lastmod)
            stats['fb_updated'] += 1

        result = import_to_webbot(
            wb_cur, doc_path, filename, lang,
            other_language_path=other_lang_path,
            html_content=html,
            sitemap_lastmod=lastmod
        )
        if result == 'created':
            stats['wb_created'] += 1
        elif result == 'updated':
            stats['wb_updated'] += 1

        print(f'   ✅ FileBot: {"新建" if not already_in_fb else "更新"} | WebBot: {result}')

        if i % 20 == 0:
            fb_conn.commit()
            wb_conn.commit()
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(to_crawl) - i) / rate if rate > 0 else 0
            print(f'\n--- 进度: {i}/{len(to_crawl)} ({rate:.1f}/s) ETA: {eta:.0f}s ---')

        time.sleep(args.delay)

    fb_conn.commit()
    wb_conn.commit()
    fb_conn.close()
    wb_conn.close()
    total_time = time.time() - start_time

    save_snapshot(sitemap_url, remote_snapshot)

    print(f'\n{"="*50}')
    print(f'✅ 增量同步完成 (耗时 {total_time:.0f}s)')
    print(f'   环境: {args.env}')
    print(f'   抓取成功: {stats["crawled"]}')
    print(f'   抓取失败: {stats["failed"]}')
    print(f'   FileBot 新建: {stats["fb_created"]}')
    print(f'   FileBot 更新: {stats["fb_updated"]}')
    print(f'   WebBot 新建: {stats["wb_created"]}')
    print(f'   WebBot 更新: {stats["wb_updated"]}')


if __name__ == '__main__':
    main()
