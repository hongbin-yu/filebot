#!/usr/bin/env python3
"""
FileBot → Webbot 独立导入工具

从 FileBot documents 表导入 HTML 文档到 webbot_page 表（两表在同一 SQLite 数据库中），
支持自动创建目录层级节点和 EN/FR 多语言配对。

用法:
  export_filebot_to_webbot.py import [选项]           # 导入文档
  export_filebot_to_webbot.py link [--dry-run]       # 仅配对（独立运行）
  export_filebot_to_webbot.py import --prefix /boarding

示例:
  cd /home/hongb/.openclaw/workspace/webbot
  python3 scripts/export_filebot_to_webbot.py --dry-run import
  python3 scripts/export_filebot_to_webbot.py import
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_FILEBOT_DB = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
DEFAULT_FILEBOT_DATA = "/home/hongb/.openclaw/workspace/filebot/backend/data"
DEFAULT_PREFIX = "/boarding"
DEFAULT_BATCH_SIZE = 200

# 已知的语言代码前缀
LANG_CODES = frozenset({'en', 'cn', 'fr', 'zh'})

# document_metadata 中 alternate 字段名
ALTERNATE_MAP = {"fr": "alternate_fr_url", "en": "alternate_en_url"}


def get_conn(db_path=None):
    """获取数据库连接"""
    conn = sqlite3.connect(db_path or DEFAULT_FILEBOT_DB)
    conn.row_factory = sqlite3.Row
    return conn


def strip_prefix(path, prefix):
    """去掉 FileBot 路径前缀 → 得到 webboot 相对路径"""
    if path.startswith(prefix):
        rest = path[len(prefix):]
        return rest if rest.startswith('/') else ('/' + rest)
    return path


def extract_lang(path):
    """从路径中提取语言代码。扫描所有 path 段，找到 en/fr 即返回。"""
    parts = path.strip('/').split('/')
    for p in parts:
        if p in LANG_CODES:
            return p
    # 特殊处理：如果路径包含 /etc/designs/canada/ 可能是设计文件
    if 'etc/designs/canada' in path:
        return 'other'
    return 'en'


def read_file(storage_path, data_dir=None):
    """读取文件内容"""
    if data_dir is None:
        data_dir = DEFAULT_FILEBOT_DATA
    full_path = os.path.join(data_dir, storage_path)
    if not os.path.isfile(full_path):
        return None
    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return None


def extract_meta_tags(html):
    """
    从 HTML 中提取 <meta name="description">、<meta name="keywords">
    和 <meta name="dcterms.modified">。
    返回 (description, keywords, dcterms_modified) 元组。
    """
    desc = ''
    kw = ''
    modified = None
    if not html:
        return desc, kw, modified
    
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
                  html, re.I)
    if m:
        desc = m.group(1).strip()

    m = re.search(r'<meta\s+name=["\']keywords["\']\s+content=["\']([^"\']+)["\']',
                  html, re.I)
    if m:
        kw = m.group(1).strip()
    
    # 提取 dcterms.modified (W3CDTF date, e.g. "2026-05-15")
    m = re.search(r'<meta\s+name=["\']dcterms\.modified["\']\s+title=["\']W3CDTF["\']\s+content=["\']([^"\']+)["\']',
                  html, re.I)
    if m:
        modified = m.group(1).strip()
    
    return desc, kw, modified

    return desc, kw


def extract_other_language_path(meta: dict, lang: str) -> str | None:
    """
    从 document metadata 中提取 other_language_path。
    
    EN 页面取 alternate_fr_url，FR 页面取 alternate_en_url，
    去除 https://www.canada.ca 前缀和 .html 后缀得到路径。
    
    示例:
      "alternate_fr_url": "https://www.canada.ca/fr/patrimoine-canadien/campagnes/laissez-passer-canada/ressources-entreprises.html"
      → "/fr/patrimoine-canadien/campagnes/laissez-passer-canada/ressources-entreprises"
    """
    if not meta or not isinstance(meta, dict):
        return None

    # EN 页面找 alternate_fr_url, FR 页面找 alternate_en_url
    alt_field = 'alternate_fr_url' if lang == 'en' else 'alternate_en_url'
    alt_url = meta.get(alt_field)

    if not alt_url or not isinstance(alt_url, str) or not alt_url.startswith('http'):
        return None

    # 解析 URL 获取路径部分
    parsed = urlparse(alt_url)
    path = parsed.path.rstrip('/')

    # 去除 .html 后缀
    if path.endswith('.html'):
        path = path[:-5]

    return path if path else None


def guess_webbot_paths(alternate_url):
    """
    将 alternate URL 转为 webbot_page 路径候选。
    webbot_page 路径格式为 /canadasite/fr/xxx 或 /canadasite/en/xxx。
    
    规则（按用户要求）：
      other_language_path = alternate_url
          .remove_prefix('https://www.canada.ca')
          .remove_suffix('.html')
      → 再套上 /canadasite 查表
    
    返回候选列表，按优先级排列，同时包含 .html 和无 .html 版本。
    """
    if not alternate_url or not alternate_url.startswith('http'):
        return []

    parsed = urlparse(alternate_url)
    url_path = parsed.path.rstrip('/')

    candidates = []
    # Case 1: AEM-style URL with /content/canadasite prefix
    # e.g. https://www.canada.ca/content/canadasite/fr/gouvernement/min.html
    if '/content/canadasite' in url_path:
        parts = url_path.split('/content/canadasite', 1)
        if len(parts) > 1:
            alt = parts[1]
            candidates.append(f'/canadasite{alt}')
            # Also try without .html
            if alt.endswith('.html'):
                candidates.append(f'/canadasite{alt[:-5]}')

    # Case 2: Direct canada.ca URL with language prefix
    # e.g. https://www.canada.ca/fr/gouvernement/min.html  
    # → /canadasite/fr/gouvernement/min.html
    for p in ('/fr/', '/en/'):
        if p in url_path:
            full = f'/canadasite{url_path}'
            candidates.append(full)
            # Also try without .html (dedup'd pages)
            if full.endswith('.html'):
                candidates.append(full[:-5])
            break

    # Case 3: Bare path as fallback (also with/without .html)
    candidates.append(url_path)
    if url_path.endswith('.html'):
        candidates.append(url_path[:-5])

    # Deduplicate while preserving order
    seen = set()
    result = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def insert_page(cursor, page_id, parent_path, path, title, content,
                language, description="", keywords="", status="published",
                metadata=None, created_by="system", hide_in_nav=False,
                other_language_path=None, last_modified=None):
    """
    插入页面。如果 path 已存在，则跳过。
    使用 path 的唯一性来判断重复。
    
    other_language_path: 其他语言对应页面路径（导入时必填）。
    last_modified: 可选的修改时间（默认使用当前时间）。
                   导入时从 <meta name="dcterms.modified"> 提取。
    """
    now = datetime.now().isoformat()
    lm = last_modified if last_modified else now
    meta = json.dumps(metadata or {})

    # Check if path already exists
    cursor.execute('SELECT id, path FROM webbot_page WHERE path = ?', (path,))
    existing = cursor.fetchone()
    if existing:
        return False, existing['id']

    try:
        cursor.execute("""
            INSERT INTO webbot_page 
                (id, title, description, keywords, content, language, parent_path, 
                 other_language_path, status, metadata, hide_in_navigation,
                 created_by, created_at, last_modified, path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page_id, title, description, keywords, content, language, parent_path,
            other_language_path, status, meta, hide_in_nav,
            created_by, now, lm, path
        ))
        return True, page_id
    except sqlite3.IntegrityError as e:
        print(f"  ⚠️  IntegrityError: {e}")
        return False, None
    except Exception as e:
        print(f"  ❌ Error inserting page: {e}")
        return False, None


def cmd_import(args):
    """导入文档到 webbot_page"""
    conn = get_conn(args.filebot_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    prefix = args.prefix.rstrip('/')
    data_dir = args.filebot_data
    batch_size = args.batch_size
    dry_run = args.dry_run

    print(f"📄 FileBot {prefix} 文档导入到 webbot_page...")
    if dry_run:
        print("  🏃 dry-run 模式（不写入）")

    # 查询 HTML 文档
    cursor.execute("""
        SELECT id, title, description, path, storage_path, parent_folder_path,
               document_metadata, created_by, file_size
        FROM documents
        WHERE path LIKE ?
          AND (file_type = 'HTML' OR mime_type = 'text/html')
        ORDER BY path
    """, (prefix + '/%',))

    docs = cursor.fetchall()
    total = len(docs)
    print(f"  找到 {total} 个 HTML 文档")

    # 收集已存在的 path
    cursor.execute('SELECT path FROM webbot_page')
    existing = {r['path'] for r in cursor.fetchall()}
    print(f"  webbot_page 已有 {len(existing)} 条记录")

    inserted = 0
    skipped = 0

    for idx, doc in enumerate(docs):
        doc_id = doc['id']
        doc_title = doc['title'] or ''
        doc_path = doc['path'] or ''
        storage_path = doc['storage_path'] or ''
        parent_folder = doc['parent_folder_path'] or ''
        doc_meta_raw = doc['document_metadata']
        created_by = doc['created_by'] or 'system'

        # 转换为 webbot_page 路径（去掉 /boarding 前缀）
        if doc_path.startswith(prefix):
            wb_path = doc_path[len(prefix):]
            if not wb_path.startswith('/'):
                wb_path = '/' + wb_path
        else:
            wb_path = doc_path

        # 解析 metadata
        meta = {}
        if doc_meta_raw:
            try:
                if isinstance(doc_meta_raw, str):
                    meta = json.loads(doc_meta_raw)
                elif isinstance(doc_meta_raw, dict):
                    meta = doc_meta_raw
            except (json.JSONDecodeError, TypeError):
                meta = {}

        # 读取文件内容
        content = read_file(storage_path, data_dir)
        if content is None:
            print(f"  ⚠️  无法读取文件: {storage_path}")
            content = ""

        # 从 HTML 提取 meta description、keywords 和 dcterms.modified
        meta_desc, meta_keywords, dcterms_modified = extract_meta_tags(content)
        # description 优先级: HTML meta > documents.description
        page_desc = meta_desc if meta_desc else (doc['description'] or '')

        # 构造目录层级
        path_parts = [p for p in wb_path.strip('/').split('/') if p]
        if len(path_parts) < 2:
            print(f"  ⚠️  路径太短，跳过: {wb_path}")
            skipped += 1
            continue

        lang = extract_lang(wb_path)

        # 创建目录层级节点
        parent_path = ''
        cum = ''
        for i, seg in enumerate(path_parts):
            if seg in LANG_CODES:
                cum += '/' + seg
                # 语言段（如 en/fr）也创建目录页 + 更新父路径
                lang_seg_path = cum
                if i < len(path_parts) - 1 and lang_seg_path not in existing:
                    lang_seg_id = f"lang-{seg}-{doc_id[:8]}"
                    if not dry_run:
                        ok, _ = insert_page(
                            cursor, lang_seg_id, parent_path,
                            lang_seg_path, seg, "", lang,
                            description="", status="draft",
                            metadata={"is_folder": True, "is_language_root": True},
                            created_by=created_by, hide_in_nav=True
                        )
                        if ok:
                            existing.add(lang_seg_path)
                parent_path = lang_seg_path
                continue
            cum += '/' + seg
            if i == len(path_parts) - 1:
                # 叶子节点 - 就是文档本身
                break
            # 非叶子节点 - 创建目录页面
            seg_path = cum
            if seg_path not in existing:
                seg_id = f"folder-{seg}-{doc_id[:8]}"
                if not dry_run:
                    ok, _ = insert_page(
                        cursor, seg_id, parent_path,
                        seg_path, seg, "", "dir", 
                        description="", status="draft",
                        metadata={"is_folder": True},
                        created_by=created_by, hide_in_nav=True
                    )
                    if ok:
                        existing.add(seg_path)
                parent_path = seg_path
            else:
                parent_path = seg_path

        # 插入文档页面
        leaf_path = wb_path
        if leaf_path not in existing:
            page_id = doc_id  # 使用相同的ID
            # 从 document metadata 提取 other_language_path（必填）
            other_lang_path = extract_other_language_path(meta, lang)

            if not dry_run:
                ok, pid = insert_page(
                    cursor, page_id, parent_path,
                    leaf_path, doc_title, content, lang,
                    description=page_desc, keywords=meta_keywords,
                    status="published", metadata=meta,
                    created_by=created_by, hide_in_nav=len(path_parts) <= 2,
                    other_language_path=other_lang_path,
                    last_modified=dcterms_modified
                )
                if ok:
                    inserted += 1
                    existing.add(leaf_path)
                else:
                    skipped += 1
            else:
                inserted += 1
                existing.add(leaf_path)
        else:
            skipped += 1

        if (idx + 1) % 100 == 0:
            print(f"  进度: {idx + 1}/{total} (已导入: {inserted}, 跳过: {skipped})")

    if not dry_run:
        conn.commit()

    conn.close()
    print(f"\n✅ 完成! 导入: {inserted}, 跳过: {skipped}, 总计: {total}")
    
    # Post-import cleanup: merge .html ↔ dir conflicts, strip remaining .html, fix root parent_path
    if not dry_run:
        cmd_dedup_html_dir_conflicts(args)
        cmd_strip_html_pages(args)
        cmd_fix_root_parent(args)
    
    return inserted


def cmd_dedup_html_dir_conflicts(args):
    """
    Post-import cleanup: merge .html pages into their stem dir entries.
    
    When a dir at `/canadasite/en/xxx` and a page at `/canadasite/en/xxx.html` both exist,
    the .html page's content is merged into the dir (which becomes a real page),
    and the .html record is deleted.
    """
    conn = get_conn(args.filebot_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    dry_run = getattr(args, 'dry_run', False)
    
    # Find all dirs
    cursor.execute("SELECT path FROM webbot_page WHERE language = 'dir'")
    dirs = {r['path'] for r in cursor.fetchall()}
    
    # Find all .html pages
    cursor.execute("SELECT path, id, language, title, content, description, metadata FROM webbot_page WHERE language IN ('en', 'fr') AND path LIKE '%.html'")
    html_pages = cursor.fetchall()
    
    conflicts = []
    for p in html_pages:
        stem = p['path'][:-5]
        if stem in dirs:
            conflicts.append((stem, p))
    
    if conflicts:
        print(f"🔧 修复 {len(conflicts)} 个 .html/目录冲突...")
    
    fixed = 0
    for stem, page in conflicts:
        if dry_run:
            fixed += 1
            continue
            
        # Get the dir entry
        cursor.execute('SELECT id, language FROM webbot_page WHERE path = ? AND language = "dir"', (stem,))
        dir_row = cursor.fetchone()
        if not dir_row:
            continue
            
        dir_id = dir_row['id']
        
        # Update dir: copy .html page content, promote language
        meta = page['metadata'] or '{}'
        if isinstance(meta, str):
            try:
                meta_obj = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta_obj = {}
        else:
            meta_obj = meta
        meta_obj['upgraded_from_dir'] = True
        meta_obj['merged_html_page'] = page['path']
        
        cursor.execute('''
            UPDATE webbot_page 
            SET title = ?, content = ?, description = ?, language = ?,
                status = 'published', hide_in_navigation = 0,
                metadata = ?
            WHERE id = ?
        ''', (
            page['title'], page['content'], page['description'], page['language'],
            json.dumps(meta_obj), dir_id
        ))
        
        # Delete the .html page
        cursor.execute('DELETE FROM webbot_page WHERE id = ?', (page['id'],))
        fixed += 1
    
    if not dry_run:
        conn.commit()
    
    conn.close()
    if conflicts:
        print(f"  ✅ 合并完成: {fixed} 个")
    return fixed


def cmd_strip_html_pages(args):
    """
    Post-dedup cleanup: rename remaining .html pages (those without dir counterparts).
    These have no dir at the same stem path, so a simple path rename is safe.
    """
    conn = get_conn(args.filebot_db)
    cursor = conn.cursor()

    dry_run = getattr(args, 'dry_run', False)

    # Find .html pages that have no dir at their stem (all remaining ones after dedup)
    cursor.execute("SELECT path FROM webbot_page WHERE path LIKE '%.html'")
    html_paths = [r['path'] for r in cursor.fetchall()]

    if not html_paths:
        conn.close()
        return 0

    stems = {p[:-5] for p in html_paths}
    placeholders = ','.join('?' for _ in stems)
    cursor.execute(f'SELECT path FROM webbot_page WHERE path IN ({placeholders}) AND path NOT LIKE "%.html"', list(stems))
    existing = {r['path'] for r in cursor.fetchall()}
    conflicts = stems & existing
    safe_paths = [p for p in html_paths if p[:-5] not in conflicts]

    if not dry_run:
        for old_path in safe_paths:
            new_path = old_path[:-5]
            cursor.execute('UPDATE webbot_page SET path = ? WHERE path = ?', (new_path, old_path))

        if conflicts:
            for old_path in [p for p in html_paths if p[:-5] in conflicts]:
                new_path = old_path[:-5]
                # Merge content into existing, then delete the .html page
                cursor.execute('SELECT id, title, content, description, language, keywords, metadata FROM webbot_page WHERE path = ?', (old_path,))
                html_row = cursor.fetchone()
                if html_row:
                    meta = html_row['metadata'] or '{}'
                    if isinstance(meta, str):
                        try:
                            meta_obj = json.loads(meta)
                        except:
                            meta_obj = {}
                    else:
                        meta_obj = meta
                    meta_obj['merged_html_page'] = old_path
                    cursor.execute('''
                        UPDATE webbot_page SET title = COALESCE(NULLIF(?, ''), title),
                            content = COALESCE(NULLIF(?, ''), content),
                            description = COALESCE(NULLIF(?, ''), description),
                            keywords = COALESCE(NULLIF(?, ''), keywords),
                            metadata = ?
                        WHERE path = ?
                    ''', (html_row['title'], html_row['content'], html_row['description'],
                          html_row['keywords'], json.dumps(meta_obj), new_path))
                    cursor.execute('DELETE FROM webbot_page WHERE path = ?', (old_path,))

    conn.commit()
    conn.close()

    total = len(safe_paths) + len(conflicts)
    print(f"  ✅ 去除 .html 后缀: {len(safe_paths)} 页重命名, {len(conflicts)} 页合并, 共 {total}")
    return total


def cmd_fix_root_parent(args):
    """
    Post-import fix: root `/canadasite` should have parent_path = '/' not ''
    """
    conn = get_conn(args.filebot_db)
    cursor = conn.cursor()
    
    dry_run = getattr(args, 'dry_run', False)
    
    cursor.execute("SELECT COUNT(*) FROM webbot_page WHERE path = '/canadasite' AND (parent_path IS NULL OR parent_path = '')")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"🔧 修复根节点 parent_path（{count} 条: '' → '/'）")
        if not dry_run:
            cursor.execute("UPDATE webbot_page SET parent_path = '/' WHERE path = '/canadasite' AND (parent_path IS NULL OR parent_path = '')")
            conn.commit()
    
    conn.close()
    return count


def cmd_export_folder(args):
    """导出选中文件夹的页面（JSON 格式输出）。

    根据指定的文件夹路径和深度，导出 webbot_page 中的页面。
    depth=1 仅当前路径，depth=2 包含直接子页，以此类推。
    """
    conn = get_conn(args.filebot_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    path = args.path.rstrip('/')
    depth = args.depth

    if not path:
        path = '/'
    if not path.startswith('/'):
        path = '/' + path

    print(f"📁 导出文件夹: {path} (depth={depth})", file=sys.stderr)

    # 获取所有 webboot 页面
    cursor.execute("""
        SELECT id, parent_path, path, title, language, description, keywords,
               content, status, metadata, hide_in_navigation, other_language_path
        FROM webbot_page
        ORDER BY path
    """)
    all_pages = cursor.fetchall()
    conn.close()

    base_parts = path.strip('/').split('/') if path != '/' else []
    base_depth = len(base_parts)

    result = []
    for page in all_pages:
        page_path = page['path']
        page_parts = page_path.strip('/').split('/')

        if page_path == path:
            # 精确匹配
            result.append(dict(page))
        elif page_path.startswith(path + '/'):
            # 在子路径中：检查深度
            additional_levels = len(page_parts) - base_depth
            if additional_levels <= depth - 1:
                result.append(dict(page))

    # 输出 JSON 到 stdout
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"✅ 共导出 {len(result)} 条记录", file=sys.stderr)
    return len(result)


def cmd_link(args):
    """配对 EN/FR 页面（通过 alternate_fr_url / alternate_en_url）
    
    会在 webbot_page 的 other_language_path 列中存储配对页面的 PATH（而非 ID）。
    """
    conn = get_conn(args.filebot_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    prefix = args.prefix.rstrip('/')
    dry_run = getattr(args, 'dry_run', False)

    print("🔗 配对 EN/FR 页面...")
    if dry_run:
        print("  🏃 dry-run 模式")

    # 查询所有 boarding HTML 文档
    cursor.execute("""
        SELECT id, path, document_metadata
        FROM documents
        WHERE path LIKE ?
          AND (file_type = 'HTML' OR mime_type = 'text/html')
        ORDER BY path
    """, (prefix + '/%',))

    docs = cursor.fetchall()
    print(f"  检查 {len(docs)} 个文档")

    pairs = 0
    errors = 0

    for doc in docs:
        doc_id = doc['id']
        doc_path = doc['path'] or ''
        raw = doc['document_metadata']

        meta = {}
        if raw:
            try:
                if isinstance(raw, str):
                    meta = json.loads(raw)
                elif isinstance(raw, dict):
                    meta = raw
            except (json.JSONDecodeError, TypeError):
                continue

        # 提取 webbot_path
        wb_path = strip_prefix(doc_path, prefix)

        # 检测语言
        lang = extract_lang(wb_path)

        # 查找 alternate URL
        alt_field = ALTERNATE_MAP.get(lang)
        alt_url = meta.get(alt_field) if alt_field else None

        if not alt_url:
            # 尝试反向查找
            if lang == 'fr':
                alt_field = 'alternate_fr_url'
            elif lang == 'en':
                alt_field = 'alternate_fr_url'
            alt_url = meta.get(alt_field)

        if not alt_url:
            continue

        # 猜测 alternate webbot 路径
        candidates = guess_webbot_paths(alt_url)
        if not candidates:
            continue

        # 查找 webbot_page 中的对应页面
        matched = False
        for c in candidates:
            cursor.execute('SELECT id, path, language FROM webbot_page WHERE path = ?', (c,))
            alt_row = cursor.fetchone()
            if alt_row:
                alt_path = alt_row['path']
                alt_lang = alt_row['language']

                # 存储配对页面的 PATH（而非 ID）
                if not dry_run:
                    cursor.execute(
                        'UPDATE webbot_page SET other_language_path = ? WHERE path = ?',
                        (alt_path, wb_path)
                    )
                    cursor.execute(
                        'UPDATE webbot_page SET other_language_path = ? WHERE path = ?',
                        (wb_path, alt_path)
                    )
                    conn.commit()

                pairs += 1
                matched = True
                break

        if not matched:
            errors += 1

    conn.close()
    print(f"\n✅ 配对完成! 已配对: {pairs}, 错误: {errors}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="FileBot → Webbot 文档导入工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    p.add_argument('--filebot-db', default=DEFAULT_FILEBOT_DB)
    p.add_argument('--filebot-data', default=DEFAULT_FILEBOT_DATA)
    p.add_argument('--prefix', default=DEFAULT_PREFIX)
    p.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument('--dry-run', action='store_true', default=False)

    sub = p.add_subparsers(dest='command')
    imp = sub.add_parser('import', help='导入文档到 webbot_page')
    lnk = sub.add_parser('link', help='配对 EN/FR 页面')
    sub.add_parser('dedup', help='合并 .html/目录冲突')
    sub.add_parser('strip-html', help='去掉剩余 .html 后缀')
    sub.add_parser('fix-root', help='修复根节点 parent_path')

    exp = sub.add_parser('export', help='导出选中文件夹的页面（JSON 格式输出）')
    exp.add_argument('--path', default='/canadasite', help='要导出的文件夹路径（默认: /canadasite）')
    exp.add_argument('--depth', type=int, default=1, help='导出深度: 1=仅当前页, 2=包含子页（默认: 1）')

    return p.parse_args(argv)


def main():
    args = parse_args()
    command = args.command

    if command == 'import':
        cmd_import(args)
    elif command == 'link':
        cmd_link(args)
    elif command == 'dedup':
        cmd_dedup_html_dir_conflicts(args)
    elif command == 'strip-html':
        cmd_strip_html_pages(args)
    elif command == 'fix-root':
        cmd_fix_root_parent(args)
    elif command == 'export':
        cmd_export_folder(args)
    else:
        print(f"未知命令: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
