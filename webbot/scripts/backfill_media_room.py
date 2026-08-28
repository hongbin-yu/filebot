#!/usr/bin/env python3
"""
backfill_media_room.py — 从 media-room 列表页的 data-wb-tags 反向回填媒体页的
media_type / report_type / issue_year / tabling_date。

背景（关键数据源）：
  media-room 列表页里，每个媒体条目是这样一个结构：

    <div class="col-xs-12 col-md-6 listing-card"
         data-wb-tags="news-release northern-legislative-assemblies-reports 2026 ">
      <article class="oag-card ...">
        <div class="mb-3">
          <span class="label label-primary article-type">News release</span>
          <time datetime="2026-05-28" class="small">May 28, 2026</time>
        </div>
        <h3><a href="/en/auditor-general/media-room/....html">...</a></h3>
      </article>
    </div>

  data-wb-tags 的值是空格分隔的 token，语义为：
    token[0] = media_type slug     (news-release|media-advisory|opening-statement)
    token[1] = report_type slug    (可空！opening-statement 条目没有 report_type)
    token[2] = issue_year          (纯数字，如 2026)

  因此直接从 data-wb-tags 拿 slug，无需再做「列表页显示文本 → slug」的反查映射。

  三个 tag 分类（均属 OAG custom tag）：
    media_type  -> /canadasite/tags/custom/oag-bvg/media-type
    report_type -> /canadasite/tags/custom/oag-bvg/report-type
    issue_year  -> /canadasite/tags/custom/oag-bvg/issue-year

  写回 metadata（与 audit-reports imported 页对齐的双字段模式）：
    media_type_key   = [slug, ...]
    media_type       = [tag title_en/fr, ...]
    report_type_key  = [slug, ...]
    report_type      = [tag title_en/fr, ...]
    issue_year_key   = [year, ...]
    issue_year       = [year, ...]
    tabling_date_iso = "YYYY-MM-DD"
    tabling_date     = "May 28, 2026"（展示文本）

  slug 与 title 的映射从 webbot_tag 表动态读取（按 lang 取 title_en/title_fr）。

英文列表页: /canadasite/en/auditor-general/media-room
法文列表页: /canadasite/fr/verificateur-general/salle-medias

用法：
  python3 backfill_media_room.py --list-page <path> --dry-run
  python3 backfill_media_room.py --list-page <path> --commit [--overwrite]
"""
import argparse
import json
import re
import sqlite3
import sys

DB_PATH = "/opt/webfilebot/webbot/data/webbot.db"
PATH_PREFIX = "/canadasite"
HREF_SUFFIX = ".html"

# 三个 OAG tag 分类路径
MEDIA_TYPE_CAT = "/canadasite/tags/custom/oag-bvg/media-type"
REPORT_TYPE_CAT = "/canadasite/tags/custom/oag-bvg/report-type"
ISSUE_YEAR_CAT = "/canadasite/tags/custom/oag-bvg/issue-year"


def load_slug_to_title(conn, cat_path):
    """读取某分类下 tag，建立 {slug: {"en": title_en, "fr": title_fr}} 映射。"""
    result = {}
    rows = conn.execute(
        "SELECT path, title_en, title_fr FROM webbot_tag WHERE path LIKE ?",
        (cat_path + "/%",),
    ).fetchall()
    for path, title_en, title_fr in rows:
        slug = path.rsplit("/", 1)[-1]
        result[slug] = {"en": title_en or "", "fr": title_fr or ""}
    return result


def detect_language(list_page_path):
    return "fr" if "/fr/" in list_page_path else "en"


def parse_listing_blocks(content: str, path_prefix: str = PATH_PREFIX):
    """解析列表页，返回 [(media_slug, report_slug, year, date_iso, date_display, page_path), ...]

    从 <div class="listing-card" data-wb-tags="..."> 块解析，比 <article> 更完整
    （因为 data-wb-tags 在外层 div，而非 <article> 上）。
    """
    items = []
    # 匹配整个 listing-card div（含 data-wb-tags）到其闭合 </div>
    # 使用非贪婪直到 </article>\s*</div>
    block_re = re.compile(
        r'<div[^>]*\blisting-card\b[^>]*\bdata-wb-tags="([^"]*)"[^>]*>.*?</article>\s*</div>',
        re.S | re.I,
    )
    for m in block_re.finditer(content):
        block = m.group(0)
        tags_raw = m.group(1).strip()
        tokens = tags_raw.split()

        media_slug = None
        report_slug = None
        year = None

        # token 语义：media_type [report_type] year
        if tokens:
            media_slug = tokens[0]
        # year = 纯数字的 token
        for t in tokens[1:]:
            if t.isdigit():
                year = t
        # report_type = 中间非数字 token（第一个非 year 的，若有）
        for t in tokens[1:]:
            if not t.isdigit():
                report_slug = t
                break

        # href
        href = re.search(r'<a[^>]*\bhref="([^"]*\.html)', block, re.I)
        if not href:
            continue
        href_path = href.group(1).strip()
        if href_path.endswith(HREF_SUFFIX):
            href_path = href_path[: -len(HREF_SUFFIX)]
        else:
            href_path = href_path.rsplit(".", 1)[0]
        if not href_path.startswith(path_prefix):
            href_path = path_prefix.rstrip("/") + "/" + href_path.lstrip("/")

        # 日期
        date_iso = None
        date_display = None
        mt = re.search(r'<time[^>]*\bdatetime="([^"]+)"[^>]*>\s*(.*?)\s*</time>', block, re.S | re.I)
        if mt:
            date_iso = mt.group(1).strip()
            date_display = re.sub(r"<[^>]+>", "", mt.group(2)).strip()

        items.append((media_slug, report_slug, year, date_iso, date_display, href_path))
    return items


def put_if_changed(pending, metadata, key, value, overwrite):
    """仅在字段缺失、或 overwrite、或值不同时，把 key=value 放入 pending。"""
    old = metadata.get(key)
    if (not old or overwrite) and old != value:
        pending[key] = value


def main():
    ap = argparse.ArgumentParser(description="从 media-room 列表页 data-wb-tags 回填媒体页 OAG tags")
    ap.add_argument("--list-page", required=True)
    ap.add_argument("--path-prefix", default=PATH_PREFIX)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--overwrite", action="store_true",
                    help="覆盖已有的字段值（默认不覆盖）")
    args = ap.parse_args()

    if not args.dry_run and not args.commit:
        print("请指定 --dry-run 或 --commit", file=sys.stderr)
        sys.exit(2)

    lang = detect_language(args.list_page)
    path_prefix = args.path_prefix

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    media_title = load_slug_to_title(conn, MEDIA_TYPE_CAT)
    report_title = load_slug_to_title(conn, REPORT_TYPE_CAT)

    row = conn.execute(
        "SELECT path, content FROM webbot_page WHERE path = ?", (args.list_page,)
    ).fetchone()
    if row is None:
        print(f"未找到列表页: {args.list_page}", file=sys.stderr)
        sys.exit(3)

    items = parse_listing_blocks(row["content"] or "", path_prefix)
    print(f"列表页 {args.list_page} 解析到 {len(items)} 个 listing-card (lang={lang})")

    updated = 0
    no_change = 0
    missing_page = 0
    unresolved = {"media": set(), "report": set()}

    for media_slug, report_slug, year, date_iso, date_display, page_path in items:
        prow = conn.execute(
            "SELECT id, metadata FROM webbot_page WHERE path = ?", (page_path,)
        ).fetchone()
        if prow is None:
            missing_page += 1
            print(f"  [MISS] 目标页不存在: {page_path}")
            continue

        page_id = prow["id"]
        raw = prow["metadata"] or ""
        try:
            metadata = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            metadata = {}

        pending = {}

        # media_type
        if media_slug:
            if media_slug in media_title:
                t = media_title[media_slug][lang] or media_slug
                put_if_changed(pending, metadata, "media_type_key", [media_slug], args.overwrite)
                put_if_changed(pending, metadata, "media_type", [t], args.overwrite)
            else:
                unresolved["media"].add(media_slug)

        # report_type（可空）
        if report_slug:
            if report_slug in report_title:
                t = report_title[report_slug][lang] or report_slug
                put_if_changed(pending, metadata, "report_type_key", [report_slug], args.overwrite)
                put_if_changed(pending, metadata, "report_type", [t], args.overwrite)
            else:
                unresolved["report"].add(report_slug)

        # issue_year
        if year and year.isdigit():
            put_if_changed(pending, metadata, "issue_year_key", [year], args.overwrite)
            put_if_changed(pending, metadata, "issue_year", [year], args.overwrite)

        # 日期
        if date_iso:
            put_if_changed(pending, metadata, "tabling_date_iso", date_iso, args.overwrite)
        if date_display:
            put_if_changed(pending, metadata, "tabling_date", date_display, args.overwrite)

        if not pending:
            no_change += 1
            continue

        metadata.update(pending)
        new_raw = json.dumps(metadata, ensure_ascii=False)
        detail = ", ".join(f"{k}={v}" for k, v in pending.items())

        if args.dry_run:
            updated += 1
            print(f"  [SET] {page_path}\n        {detail}")
        else:
            conn.execute("UPDATE webbot_page SET metadata = ? WHERE id = ?", (new_raw, page_id))
            updated += 1
            print(f"  [SET] {page_path}  {detail}")

    if args.commit:
        conn.commit()

    print("-" * 60)
    print(f"更新: {updated} | 无变化: {no_change} | 目标页缺失: {missing_page}")
    if unresolved["media"]:
        print("未匹配的 media_type slug:", sorted(unresolved["media"]))
    if unresolved["report"]:
        print("未匹配的 report_type slug:", sorted(unresolved["report"]))
    conn.close()


if __name__ == "__main__":
    main()
