"""
WebBot Analytics API — 页面数据分析面板
聚合统计数据，用于 Data Analysis 仪表盘展示
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

import os

DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class AnalyticsResponse(BaseModel):
    overview: dict
    language: dict
    status: dict
    translation_gaps: dict
    redirects: dict
    templates: list
    tag_usage: dict
    recent_activity: dict


@router.get("")
async def get_analytics():
    """Aggregate all analytics data for the dashboard."""
    conn = get_db()
    c = conn.cursor()

    # === Overview ===
    c.execute("SELECT COUNT(*) FROM webbot_page")
    total_pages = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM webbot_tag")
    total_tags = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT page_id) FROM webbot_page_tags")
    tagged_pages = c.fetchone()[0]

    # === Language ===
    c.execute("SELECT COUNT(*) FROM webbot_page WHERE path LIKE '/canadasite/en/%'")
    en = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM webbot_page WHERE path LIKE '/canadasite/fr/%'")
    fr = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM webbot_page WHERE path NOT LIKE '/canadasite/en/%' AND path NOT LIKE '/canadasite/fr/%'")
    other = c.fetchone()[0]

    # === Status ===
    c.execute("SELECT status, COUNT(*) as cnt FROM webbot_page GROUP BY status ORDER BY cnt DESC")
    status_data = {r["status"]: r["cnt"] for r in c.fetchall()}

    # === Translation gaps ===
    c.execute("SELECT COUNT(*) FROM webbot_page WHERE other_language_path IS NOT NULL AND other_language_path != '' AND status = 'published'")
    paired = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM webbot_page WHERE path LIKE '/canadasite/en/%' AND (other_language_path IS NULL OR other_language_path = '') AND status = 'published' AND (json_extract(metadata, '$.redirect_to') IS NULL OR json_extract(metadata, '$.redirect_to') = '')")
    en_missing_fr = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM webbot_page WHERE path LIKE '/canadasite/fr/%' AND (other_language_path IS NULL OR other_language_path = '') AND status = 'published' AND (json_extract(metadata, '$.redirect_to') IS NULL OR json_extract(metadata, '$.redirect_to') = '')")
    fr_missing_en = c.fetchone()[0]

    # Top pages missing FR (for detail)
    c.execute("""
        SELECT id, title, path, last_modified
        FROM webbot_page
        WHERE path LIKE '/canadasite/en/%'
          AND (other_language_path IS NULL OR other_language_path = '')
          AND status = 'published'
          AND (json_extract(metadata, '$.redirect_to') IS NULL OR json_extract(metadata, '$.redirect_to') = '')
        ORDER BY last_modified DESC
        LIMIT 20
    """)
    missing_fr_list = [
        {"id": r["id"], "title": r["title"], "path": r["path"], "last_modified": r["last_modified"]}
        for r in c.fetchall()
    ]

    # Top pages missing EN (for detail)
    c.execute("""
        SELECT id, title, path, last_modified
        FROM webbot_page
        WHERE path LIKE '/canadasite/fr/%'
          AND (other_language_path IS NULL OR other_language_path = '')
          AND status = 'published'
          AND (json_extract(metadata, '$.redirect_to') IS NULL OR json_extract(metadata, '$.redirect_to') = '')
        ORDER BY last_modified DESC
        LIMIT 20
    """)
    missing_en_list = [
        {"id": r["id"], "title": r["title"], "path": r["path"], "last_modified": r["last_modified"]}
        for r in c.fetchall()
    ]

    # === Broken alternate-language references (other_language_path points to a page that does not exist) ===
    c.execute("""
        SELECT COUNT(*)
        FROM webbot_page p
        LEFT JOIN webbot_page q ON q.path = p.other_language_path
        WHERE p.other_language_path IS NOT NULL AND p.other_language_path != ''
          AND q.id IS NULL
          AND p.status = 'published'
    """)
    broken_reference_count = c.fetchone()[0]

    c.execute("""
        SELECT p.path, p.title, p.other_language_path, p.last_modified
        FROM webbot_page p
        LEFT JOIN webbot_page q ON q.path = p.other_language_path
        WHERE p.other_language_path IS NOT NULL AND p.other_language_path != ''
          AND q.id IS NULL
          AND p.status = 'published'
        ORDER BY p.last_modified DESC
        LIMIT 20
    """)
    broken_references = [
        {"path": r["path"], "title": r["title"], "other_language_url": _strip_site_prefix(r["other_language_path"]), "last_modified": r["last_modified"]}
        for r in c.fetchall()
    ]

    # === Redirect pages (metadata.redirect_to set) ===
    c.execute("""
        SELECT COUNT(*)
        FROM webbot_page
        WHERE json_extract(metadata, '$.redirect_to') IS NOT NULL
          AND json_extract(metadata, '$.redirect_to') != ''
    """)
    redirect_count = c.fetchone()[0]

    c.execute("""
        SELECT id, title, path, last_modified,
               json_extract(metadata, '$.redirect_to') AS redirect_to
        FROM webbot_page
        WHERE json_extract(metadata, '$.redirect_to') IS NOT NULL
          AND json_extract(metadata, '$.redirect_to') != ''
        ORDER BY last_modified DESC
        LIMIT 20
    """)
    redirect_pages = [
        {"id": r["id"], "title": r["title"], "path": r["path"],
         "redirect_to": r["redirect_to"], "last_modified": r["last_modified"]}
        for r in c.fetchall()
    ]

    # === Templates ===
    c.execute("""
        SELECT COALESCE(NULLIF(publish_template, ''), '(Default page template)') AS publish_template, COUNT(*) as cnt
        FROM webbot_page
        GROUP BY COALESCE(NULLIF(publish_template, ''), '(Default page template)')
        ORDER BY cnt DESC
        LIMIT 20
    """)
    template_data = [
        {"template": r["publish_template"], "count": r["cnt"]}
        for r in c.fetchall()
    ]

    # === Tags ===
    c.execute("SELECT type, COUNT(*) as cnt FROM webbot_tag GROUP BY type")
    tag_type_counts = {r["type"]: r["cnt"] for r in c.fetchall()}

    # Tag usage by depth (tags with children)
    c.execute("SELECT COUNT(*) FROM webbot_tag WHERE parent_id IS NOT NULL AND parent_id != ''")
    tags_with_parent = c.fetchone()[0]

    # Paged untagged
    c.execute("SELECT COUNT(*) FROM webbot_page")
    all_p = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT page_id) FROM webbot_page_tags")
    tagged_p = c.fetchone()[0]

    # Top used tags
    c.execute("""
        SELECT t.id, t.type, t.label_fr, COUNT(pt.tag_id) as usage_count
        FROM webbot_tag t
        LEFT JOIN webbot_page_tags pt ON t.id = pt.tag_id
        GROUP BY t.id
        HAVING usage_count > 0
        ORDER BY usage_count DESC
        LIMIT 10
    """)
    top_tags = [
        {"id": r["id"], "type": r["type"], "label_fr": r["label_fr"], "usage_count": r["usage_count"]}
        for r in c.fetchall()
    ]

    # === Activity ===
    c.execute("SELECT COUNT(*) FROM webbot_page WHERE last_modified IS NOT NULL")
    mod_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM webbot_page WHERE last_published IS NOT NULL")
    pub_count = c.fetchone()[0]

    # Last 24h modified
    threshold = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    c.execute("SELECT COUNT(*) FROM webbot_page WHERE last_modified > ?", (threshold,))
    recently_modified = c.fetchone()[0]

    conn.close()

    return AnalyticsResponse(
        overview={
            "total_pages": total_pages,
            "total_tags": total_tags,
            "tagged_pages": tagged_pages,
            "tagged_percent": round(tagged_pages / total_pages * 100, 1) if total_pages else 0,
        },
        language={
            "en": en,
            "fr": fr,
            "other": other,
            "en_percent": round(en / total_pages * 100, 1) if total_pages else 0,
            "fr_percent": round(fr / total_pages * 100, 1) if total_pages else 0,
        },
        status=status_data,
        translation_gaps={
            "paired_pages": paired,
            "en_missing_fr": en_missing_fr,
            "en_missing_fr_percent": round(en_missing_fr / en * 100, 1) if en else 0,
            "fr_missing_en": fr_missing_en,
            "fr_missing_en_percent": round(fr_missing_en / fr * 100, 1) if fr else 0,
            "recent_missing_fr": missing_fr_list,
            "recent_missing_en": missing_en_list,
            "broken_reference_count": broken_reference_count,
            "broken_references": broken_references,
        },
        redirects={
            "count": redirect_count,
            "pages": redirect_pages,
        },
        templates=template_data,
        tag_usage={
            "by_type": tag_type_counts,
            "tags_with_parent": tags_with_parent,
            "untagged_pages": all_p - tagged_p,
            "untagged_percent": round((all_p - tagged_p) / all_p * 100, 1) if all_p else 0,
            "top_tags": top_tags,
        },
        recent_activity={
            "last_modified_set": mod_count,
            "last_published_set": pub_count,
            "last_24h_modified": recently_modified,
            "threshold_is": threshold,
        },
    )


@router.get("/broken-links")
async def get_broken_links(prefix: str = "", limit: int = 50, offset: int = 0):
    """List pages whose other_language_path points to a page that does not exist in the DB.
    Optional `prefix` filters by page path prefix (e.g. /canadasite/en/)."""
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    conn = get_db()
    c = conn.cursor()
    # Escape LIKE wildcards so the prefix is matched literally
    esc_prefix = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_pattern = esc_prefix + "%"

    c.execute("""
        SELECT COUNT(*)
        FROM webbot_page p
        LEFT JOIN webbot_page q ON q.path = p.other_language_path
        WHERE p.other_language_path IS NOT NULL AND p.other_language_path != ''
          AND q.id IS NULL
          AND p.status = 'published'
          AND p.path LIKE ? ESCAPE '\\'
    """, (like_pattern,))
    total = c.fetchone()[0]

    c.execute("""
        SELECT p.path, p.title, p.other_language_path, p.last_modified, p.status
        FROM webbot_page p
        LEFT JOIN webbot_page q ON q.path = p.other_language_path
        WHERE p.other_language_path IS NOT NULL AND p.other_language_path != ''
          AND q.id IS NULL
          AND p.status = 'published'
          AND p.path LIKE ? ESCAPE '\\'
        ORDER BY p.path
        LIMIT ? OFFSET ?
    """, (like_pattern, limit, offset))
    rows = [
        {"path": r["path"], "title": r["title"], "other_language_url": _strip_site_prefix(r["other_language_path"]),
         "last_modified": r["last_modified"], "status": r["status"]}
        for r in c.fetchall()
    ]
    return {
        "prefix": prefix,
        "total": total,
        "limit": limit,
        "offset": offset,
        "broken_links": rows,
    }

def _strip_site_prefix(path):
    """Remove the /canadasite prefix from a path (e.g. /canadasite/en/x -> /en/x)."""
    if path and path.startswith('/canadasite'):
        return path[len('/canadasite'):]
    return path
