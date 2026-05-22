#!/usr/bin/env python3
"""
配对 webbot_page 中的 EN/FR 页面。

配对来源（顺序 fallback）：
1. document_metadata 中的 alternate_fr_url / alternate_en_url
2. 已爬取的 HTML 文件中的 <a lang="fr/en"> 语言切换链接（#wb-lng）

用法:
  python3 scripts/link_alternates.py                  # 正常执行
  python3 scripts/link_alternates.py --dry-run        # 只预览，不写入
"""

import argparse
import html.parser
import json
import os
import re
import sqlite3
import sys
from urllib.parse import urlparse

FILEBOT_DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
WEBBOT_DB_PATH = "/home/hongb/.openclaw/workspace/webbot/app/webbot.db"
FILEBOT_DATA_DIR = "/home/hongb/.openclaw/workspace/filebot/backend/data"


class WbLngParser(html.parser.HTMLParser):
    """从 HTML 中提取 #wb-lng 里的语言切换链接。

    匹配：
      <section id="wb-lng"> ... <a lang="fr" href="/fr/xxx.html"> ... </section>
    """
    def __init__(self):
        super().__init__()
        self.alt_href = None
        self._in_wb_lng = False
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # 进入 #wb-lng section
        if tag == 'section' and attrs_dict.get('id') == 'wb-lng':
            self._in_wb_lng = True
            self._depth = 1
            return
        if self._in_wb_lng:
            self._depth += 1
            # 在 #wb-lng 内部找 <a lang="en" ...> 或 <a lang="fr" ...>
            if tag == 'a' and attrs_dict.get('lang') in ('en', 'fr') and attrs_dict.get('href'):
                self.alt_href = attrs_dict['href']

    def handle_endtag(self, tag):
        if self._in_wb_lng:
            self._depth -= 1
            if self._depth <= 0:
                self._in_wb_lng = False

    @classmethod
    def extract(cls, html_content: str) -> str | None:
        """解析 HTML 内容，返回 alternate href (如 /fr/services/emplois.html) 或 None"""
        parser = cls()
        try:
            parser.feed(html_content)
        except Exception:
            return None
        return parser.alt_href


def extract_alternate_from_metadata(meta: dict, lang: str) -> str | None:
    """从 document_metadata 提取 alternate URL"""
    alt_field = 'alternate_fr_url' if lang == 'en' else 'alternate_en_url'
    alt_url = meta.get(alt_field)
    if alt_url:
        try:
            return urlparse(alt_url).path
        except Exception:
            pass
    return None


def read_html_file(this_doc_path: str, storage_path: str | None) -> str | None:
    """根据文档的 storage_path 读取 HTML 文件内容"""
    if storage_path:
        filepath = os.path.join(FILEBOT_DATA_DIR, storage_path)
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except (OSError, UnicodeDecodeError):
                pass

    # 尝试从 path 推导
    rel = this_doc_path.lstrip('/')  # e.g. boarding/canadasite/en/services/jobs
    candidates = [
        os.path.join(FILEBOT_DATA_DIR, f'{rel}.html'),
        os.path.join(FILEBOT_DATA_DIR, rel, 'index.html'),
    ]
    for c in candidates:
        if os.path.isfile(c):
            try:
                with open(c, 'r', encoding='utf-8') as f:
                    return f.read()
            except (OSError, UnicodeDecodeError):
                pass
    return None


def html_href_to_candidates(alt_href: str) -> list[str]:
    """将 HTML 中的 alternate href 转为 webbot_page 候选路径

    HTML 中的 href 是生产路径: /fr/services/emplois.html
    webbot_page 用的是 /canadasite/fr/services/emplois (无 .html 后缀)
    """
    # 去 .html 后缀
    base = alt_href[:-5] if alt_href.endswith('.html') else alt_href

    candidates = []
    # 生产路径: /fr/services/emplois → /canadasite/fr/services/emplois
    candidates.append(f'/canadasite{base}')
    candidates.append(f'/boarding/canadasite{base}')
    # staging 路径: /content/canadasite/fr/xxx → /canadasite/fr/xxx
    if '/content/canadasite/' in base:
        rest = base.split('/content/canadasite', 1)[1]
        candidates.append(f'/canadasite{rest}')
        candidates.append(f'/boarding/canadasite{rest}')
    # 裸路径 (生产环境不带 canadasite 前缀)
    candidates.append(base)

    # 去重保留顺序
    seen = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]


def resolve_webbot_page(cur, alt_href: str, this_lang: str):
    """尝试在 webbot_page 中找到 alternate 页面"""
    candidates = html_href_to_candidates(alt_href)
    expected_lang = 'fr' if this_lang == 'en' else 'en'
    for c in candidates:
        row = cur.execute(
            'SELECT id, path, language FROM webbot_page WHERE path = ?',
            (c,)
        ).fetchone()
        if row:
            if row['language'] != expected_lang:
                # 存在但语言不匹配 — 可能是同语言自我引用
                return None
            return row
    return None


def doc_path_to_wb_path(doc_path: str) -> str:
    """将 documents 的 path (/boarding/canadasite/...) 转为 webbot_page 的 path (/canadasite/...)"""
    if doc_path.startswith('/boarding/'):
        return doc_path[len('/boarding'):]
    return doc_path


def main():
    parser = argparse.ArgumentParser(description='EN/FR 页面配对')
    parser.add_argument('--dry-run', action='store_true', help='只预览不写入')
    args = parser.parse_args()

    # 两个数据库：filebot.db（读 documents）+ webbot.db（读写 webbot_page）
    fb_conn = sqlite3.connect(FILEBOT_DB_PATH)
    fb_conn.row_factory = sqlite3.Row
    fb_cur = fb_conn.cursor()

    wb_conn = sqlite3.connect(WEBBOT_DB_PATH)
    wb_conn.row_factory = sqlite3.Row
    wb_cur = wb_conn.cursor()

    # 读取所有 boarding HTML 文档（含 storage_path 用于读 HTML 文件）
    fb_cur.execute("""
        SELECT path, document_metadata, storage_path
        FROM documents
        WHERE path LIKE '/boarding/%'
          AND (file_type = 'HTML' OR mime_type = 'text/html')
          AND document_metadata IS NOT NULL
          AND document_metadata != ''
    """)
    docs = fb_cur.fetchall()
    print(f"📄 检查 {len(docs)} 个文档 (filebot.db)")

    stats = {"meta_paired": 0, "html_paired": 0, "skipped": 0, "errors": 0}

    for doc in docs:
        doc_path = doc['path'] or ''
        storage_path = doc['storage_path']
        raw = doc['document_metadata']

        # 解析 metadata
        meta = {}
        if raw:
            try:
                meta = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                pass

        # 判断当前语言
        this_lang = 'fr' if '/fr/' in doc_path else 'en'

        # === 来源 1: 从 document_metadata 提取 ===
        alt_href = extract_alternate_from_metadata(meta, this_lang)
        src = 'meta' if alt_href else None

        # === 来源 2 (fallback): 从 HTML 正文提取 ===
        if not alt_href:
            html_content = read_html_file(doc_path, storage_path)
            if html_content:
                alt_href = WbLngParser.extract(html_content)
            if alt_href:
                src = 'html'

        if not alt_href or not src:
            stats["skipped"] += 1
            continue

        # 在 webbot_page 找对应页面（针对 webbot_page 路径）
        alt_row = resolve_webbot_page(wb_cur, alt_href, this_lang)
        if not alt_row:
            stats["skipped"] += 1
            continue

        # 找本页面在 webbot_page 中的记录（doc_path 需要转为 webbot path）
        wb_path = doc_path_to_wb_path(doc_path)
        my_row = wb_cur.execute(
            'SELECT id, path, language, other_language_path FROM webbot_page WHERE path = ?',
            (wb_path,)
        ).fetchone()
        if not my_row:
            stats["skipped"] += 1
            continue

        if not alt_row['id']:
            stats["errors"] += 1
            continue

        # 已配对跳过
        if my_row['other_language_path'] == alt_row['path']:
            continue

        # 写入
        if args.dry_run:
            print(f"  [{src}] {my_row['path']} ↔ {alt_row['path']}")
        else:
            wb_cur.execute("UPDATE webbot_page SET other_language_path = ? WHERE id = ?",
                        (alt_row['path'], my_row['id']))
            wb_cur.execute("UPDATE webbot_page SET other_language_path = ? WHERE id = ?",
                        (my_row['path'], alt_row['id']))

        stats[f"{src}_paired"] += 1

        if (stats["meta_paired"] + stats["html_paired"]) % 50 == 0:
            print(f"  进度: {stats['meta_paired'] + stats['html_paired']} 对...")

    if not args.dry_run:
        wb_conn.commit()
    fb_conn.close()
    wb_conn.close()

    print(f"\n{'='*40}")
    print(f"✅ 完成{'（预览模式）' if args.dry_run else ''}")
    print(f"   metadata 配对: {stats['meta_paired']} 对")
    print(f"   HTML 解析配对: {stats['html_paired']} 对")
    print(f"   未匹配: {stats['skipped']}")
    print(f"   错误: {stats['errors']}")


if __name__ == '__main__':
    main()
