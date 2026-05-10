#!/usr/bin/env python3
"""
🇫🇷 法英双语配对工作流

精髓: 所有配对信息先在 FileBot documents 层准备，然后用 export 脚本导入 webbot_page

工作流:
  FileBot documents (带 alternate_fr_url) → export_boarding_canadasite.py → 配对的 webbot_page

步骤:
  1. 从 webbot_page 读 EN 页面 HTML → 提取 FR 语言切换链接（hreflang="fr"）
  2. 爬取 canada.ca 法语页面
  3. 存为 FileBot 文档（与 EN 文档同文件夹）
  4. 在 EN 文档的 document_metadata 写入 alternate_fr_url
  5. 调用 export 脚本 → 自动配对 webbot_page

命令:
  scan <prefix>    扫描未配对的 EN 页面
  pair <path>      完整配对一个页面
  export           执行 export 导入
"""

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import requests

FILEBOT_DB = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
FILEBOT_DATA = "/home/hongb/.openclaw/workspace/filebot/backend/data"
EXPORT_SCRIPT = "/home/hongb/.openclaw/workspace/webbot/scripts/export_filebot_to_webbot.py"
SCPAPER_DELAY = 1.2
TIMEOUT = 30

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CanadaSitePairing/1.0)"
}


def get_db():
    conn = sqlite3.connect(FILEBOT_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def extract_french_alternate_url(html):
    """从 canada.ca 英文页面 HTML 中找到法语语言切换链接。"""
    if not html:
        return None
    patterns = [
        r'<link[^>]*rel="alternate"[^>]*hreflang="fr"[^>]*href="([^"]+)"',
        r'<link[^>]*hreflang="fr"[^>]*rel="alternate"[^>]*href="([^"]+)"',
        r'<a[^>]*lang="fr"[^>]*hreflang="fr"[^>]*href="([^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def find_filebot_doc(cursor, webbot_path):
    """通过 webbot_page 路径反查 FileBot 文档。"""
    filebot_path = webbot_path.replace("/canadasite/", "/boarding/canadasite/", 1)
    if not filebot_path.endswith('.html'):
        filebot_path += '.html'
    cursor.execute(
        "SELECT id, path, folder_id, storage_path, document_metadata, title, original_filename "
        "FROM documents WHERE path = ? AND (file_type = 'HTML' OR mime_type = 'text/html')",
        (filebot_path,)
    )
    return cursor.fetchone()


def filebot_path_from_french_url(fr_url):
    """将 canada.ca 法语 URL 转换为 FileBot 文档路径。"""
    path = fr_url.replace("https://www.canada.ca", "")
    path = path.replace("http://www.canada.ca", "")
    if not path.endswith('.html'):
        path += '.html'
    return path


def webbot_path_from_french_url(fr_url):
    """将 canada.ca 法语 URL 转换为 webbot_page 路径。"""
    path = fr_url.replace("https://www.canada.ca", "")
    path = path.replace("http://www.canada.ca", "")
    return path


def create_french_filebot_doc(cursor, html, fr_url, en_filebot_doc):
    """在 FileBot 中创建法语文档（与 EN 文档同文件夹）。"""
    doc_id = str(uuid.uuid4())
    now = datetime.now()

    fr_path = filebot_path_from_french_url(fr_url)
    fr_webbot_path = webbot_path_from_french_url(fr_url)

    en_folder_id = en_filebot_doc["folder_id"]
    en_folder = cursor.execute("SELECT path FROM folders WHERE id = ?", (en_folder_id,)).fetchone()

    en_folder_path = en_folder["path"] if en_folder else None
    fr_folder_id = en_folder_id  # 保持同文件夹
    fr_folder_path = en_folder_path  # 保持同文件夹路径

    # 安全文件名, 确保 /boarding/canadasite 前缀与 EN 文档一致
    last_seg = fr_path.strip('/').split('/')[-1]
    safe_fn = re.sub(r'[^\w\-.]', '_', last_seg.lower())
    en_doc_path = en_filebot_doc["path"]  # e.g. /boarding/canadasite/en/xxx
    # 从 EN 路径提取前缀 (e.g. /boarding/canadasite)
    if '/canadasite/' in en_doc_path:
        base_prefix = en_doc_path.split('/en/')[0]  # /boarding/canadasite
    else:
        base_prefix = '/boarding'
    the_path = f"{base_prefix}{fr_path}" if not fr_path.startswith(base_prefix) else fr_path
    # storage_path = path without leading /
    storage_path = the_path.lstrip('/')
    # 安全文件名
    full_path = os.path.join(FILEBOT_DATA, storage_path)

    # 写入文件
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(html)
    file_size = os.path.getsize(full_path)

    # 提取标题
    title_m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
    title = title_m.group(1).strip() if title_m else safe_fn.replace('.html', '').replace('_', ' ')

    # 构造 metadata
    en_meta_raw = en_filebot_doc["document_metadata"]
    en_meta = {}
    if en_meta_raw:
        try:
            en_meta = json.loads(en_meta_raw) if isinstance(en_meta_raw, str) else en_meta_raw
        except (json.JSONDecodeError, TypeError):
            pass

    doc_meta = {
        "alternate_en_url": en_meta.get("publish_url", ""),
        "crawl_source": "french_import_pipeline",
        "crawled_at": now.isoformat(),
    }
    if en_meta.get("publish_url"):
        doc_meta["alternate_en_url"] = en_meta["publish_url"]

    # 插入文档
    cursor.execute("""
        INSERT INTO documents (id, path, title, stored_filename, storage_path, file_size, file_type, mime_type,
                               folder_id, parent_folder_path, document_metadata, 
                               original_filename, created_by, created_at, updated_at, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_id, the_path, title, safe_fn, storage_path,
        file_size, "HTML", "text/html",
        fr_folder_id, fr_folder_path if fr_folder_path else None,
        json.dumps(doc_meta),
        safe_fn, "french_import_pipeline", now.isoformat(), now.isoformat(),
        "french_import_pipeline"
    ))

    logger.info(f"  ✅ 创建法语文档: {the_path}")
    return [doc_id, the_path]


def set_alternate_fr_url(cursor, en_doc_id, fr_url):
    """在 EN 文档 metadata 中写入 alternate_fr_url —— 这是配对的关键。"""
    row = cursor.execute("SELECT document_metadata FROM documents WHERE id = ?", (en_doc_id,)).fetchone()
    if not row:
        logger.error(f"  ❌ 找不到 EN 文档: {en_doc_id}")
        return False

    meta = row["document_metadata"]
    if meta:
        try:
            m = json.loads(meta) if isinstance(meta, str) else meta
        except (json.JSONDecodeError, TypeError):
            m = {}
    else:
        m = {}

    # 如果已有 alternate_fr_url 则跳过
    if m.get("alternate_fr_url"):
        logger.info(f"  ℹ️  alternate_fr_url 已存在: {m['alternate_fr_url']}")
        return True

    m["alternate_fr_url"] = fr_url
    m["paired_at"] = datetime.now().isoformat()

    cursor.execute(
        "UPDATE documents SET document_metadata = ?, updated_at = ? WHERE id = ?",
        (json.dumps(m), datetime.now().isoformat(), en_doc_id)
    )
    logger.info(f"  ✅ 写入 alternate_fr_url: {fr_url}")
    return True


def pair_page(en_webbot_path):
    """对一个英文页面执行完整配对流程。"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # 1. 读取 webbot_page 中的 EN 页面
        cursor.execute("SELECT id, path, content FROM webbot_page WHERE path = ?", (en_webbot_path,))
        en_page = cursor.fetchone()
        if not en_page:
            logger.error(f"❌ 找不到 webbot_page EN 页面: {en_webbot_path}")
            return False

        logger.info(f"📄 EN: {en_page['path']}")

        # 2. 从 HTML 中提取 FR 切换链接
        fr_url = extract_french_alternate_url(en_page["content"])
        if not fr_url:
            # 尝试从 FileBot doc metadata 中找
            en_doc = find_filebot_doc(cursor, en_webbot_path)
            if en_doc and en_doc["document_metadata"]:
                try:
                    meta = json.loads(en_doc["document_metadata"]) if isinstance(en_doc["document_metadata"], str) else en_doc["document_metadata"]
                    fr_url = meta.get("alternate_fr_url")
                except (json.JSONDecodeError, TypeError):
                    pass
        else:
            # 从 HTML 找到 FR 链接后获取 FileBot 文档
            en_doc = find_filebot_doc(cursor, en_webbot_path)

        if not fr_url:
            logger.warning(f"  ⚠️ 找不到 FR 切换链接")
            return False

        # 清理 URL
        fr_url = re.sub(r'\.html$', '', fr_url)
        fr_url_orig = fr_url

        # 3. 查找是否已有 FR FileBot 文档
        fr_path = webbot_path_from_french_url(fr_url_orig)
        if not fr_path.endswith('.html'):
            fr_path += '.html'
        existing_fr = cursor.execute(
            "SELECT id FROM documents WHERE path = ? AND (file_type='HTML' OR mime_type='text/html')",
            (f"/boarding{fr_path}",)
        ).fetchone()

        if existing_fr:
            fr_doc_id = existing_fr["id"]
            logger.info(f"  ℹ️  FR 文档已存在: /boarding{fr_path}")
            # 确保 alternate_fr_url 已被设置
            if en_doc:
                set_alternate_fr_url(cursor, en_doc["id"], fr_url_orig)
        else:
            if not en_doc:
                en_doc = find_filebot_doc(cursor, en_webbot_path)
                if not en_doc:
                    logger.error(f"  ❌ 找不到 EN FileBot 文档: {en_webbot_path}")
                    return False

            # 4. 爬取法语页面
            time.sleep(SCPAPER_DELAY)
            logger.info(f"  🌐 爬取: {fr_url_orig}")
            try:
                resp = requests.get(fr_url_orig, headers=REQ_HEADERS, timeout=TIMEOUT)
                resp.raise_for_status()
                fr_html = resp.text
            except Exception as e:
                logger.error(f"  ❌ 爬取失败: {e}")
                return False

            # 5. 创建 FileBot 文档
            result = create_french_filebot_doc(cursor, fr_html, fr_url_orig, en_doc)
            if not result:
                return False
            fr_doc_id = result[0] if isinstance(result, list) else result

            # 6. 设置 alternate_fr_url
            set_alternate_fr_url(cursor, en_doc["id"], fr_url_orig)

        conn.commit()
        logger.info(f"  ✅ 配对完成")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ 配对失败: {e}")
        return False
    finally:
        conn.close()


def scan_unpaired(prefix="/canadasite"):
    """扫描未配对的 EN 页面。"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        rows = cursor.execute("""
            SELECT id, path, LENGTH(COALESCE(content, '')) as content_len
            FROM webbot_page
            WHERE path LIKE ?
              AND language = 'en'
              AND (other_language_path IS NULL OR other_language_path = '')
              AND LENGTH(COALESCE(content, '')) > 2000
            ORDER BY path
        """, (prefix + '%',)).fetchall()

        print(f"\n🔍 扫描未配对的页面: {prefix}")
        print(f"  共 {len(rows)} 个未配对 EN 页面（内容 > 2000 字）\n")

        for i, row in enumerate(rows):
            preview = ""
            if row["content_len"] > 0:
                cursor.execute("SELECT SUBSTR(content, 1, 500) FROM webbot_page WHERE id = ?", (row["id"],))
                html_preview = cursor.fetchone()[0]
                m = re.search(r'hreflang="fr"[^>]*href="([^"]+)"', html_preview or "")
                if m:
                    fr_url_hint = m.group(1)
                    preview = f"  → {fr_url_hint}"
            print(f"  [{i+1}] {row['path']} ({row['content_len']} 字){preview}")

        return rows
    finally:
        conn.close()


def run_export(dry_run=False):
    """运行 export 脚本。"""
    logger.info("🚀 执行 export_boarding_canadasite.py...")
    cmd = f"python3 {EXPORT_SCRIPT} import"
    if dry_run:
        cmd += " --dry-run"
    rc = os.system(cmd)
    if rc == 0:
        logger.info("✅ export 完成")
    else:
        logger.error(f"❌ export 失败 (exit={rc})")
    return rc == 0


def main():
    parser = argparse.ArgumentParser(
        description="🇫🇷 法英双语配对 pipeline: FileBot → export → webbot_page",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command")

    # scan
    p = sub.add_parser("scan", help="扫描未配对的 EN 页面")
    p.add_argument("prefix", nargs="?", default="/canadasite", help="路径前缀（默认 /canadasite）")

    # pair
    p = sub.add_parser("pair", help="完整配对单个页面")
    p.add_argument("path", help="EN webbot_page 路径，如 /canadasite/en/services/jobs.html")

    # pair-all
    p = sub.add_parser("pair-all", help="批量配对未配对页面")
    p.add_argument("--limit", type=int, default=999, help="最多配对数")
    p.add_argument("--skip", type=int, default=0, help="跳过前 N 个")

    # export
    p = sub.add_parser("export", help="执行 export 导入")
    p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    cmd = args.command

    if cmd == "scan":
        scan_unpaired(args.prefix)
    elif cmd == "pair":
        ok = pair_page(args.path)
        sys.exit(0 if ok else 1)
    elif cmd == "pair-all":
        rows = scan_unpaired()
        if not rows:
            print("没有需要配对的页面")
            sys.exit(0)
        skip = getattr(args, "skip", 0)
        limit = getattr(args, "limit", 999)
        to_pair = rows[skip:skip + limit]
        print(f"\n将配对 {len(to_pair)} 个页面...")
        success = 0
        fail = 0
        for i, row in enumerate(to_pair):
            print(f"\n[{i+1}/{len(to_pair)}] ", end="")
            ok = pair_page(row["path"])
            if ok:
                success += 1
            else:
                fail += 1
                time.sleep(3)  # 失败后多等一会儿
        print(f"\n✅ 完成: {success} 成功, {fail} 失败")
    elif cmd == "export":
        run_export(dry_run=args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
