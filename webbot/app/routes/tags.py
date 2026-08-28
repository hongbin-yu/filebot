"""
WebBot Tags API — 通用树形标签系统 (path-based)
所有公共接口使用 path / parent_path，内部 join 表仍用 tag id
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import sqlite3
import json
from datetime import datetime

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])

import os

DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)


TAG_ROOT = "/canadasite/tags"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ============================================================================
# Publish helpers — MUST BE BEFORE path-based routes to avoid conflict
# ============================================================================

@router.get("/page_dcterms")
async def get_page_dcterms(
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/government")
):
    """获取页面标签的 dcterms 元数据（用于发布渲染）"""
    conn = get_db()
    try:
        page_path = path if path.startswith("/") else "/" + path
        page = conn.execute("SELECT id FROM webbot_page WHERE path = ?", (page_path,)).fetchone()
        if not page:
            raise HTTPException(404, f"Page not found: {page_path}")
        rows = conn.execute("""
            SELECT t.title_en, t.title_fr, t.type FROM webbot_tag t
            INNER JOIN webbot_page_tags pt ON pt.tag_id = t.id
            WHERE pt.page_id = ?
        """, (page["id"],)).fetchall()
        result = {}
        subjects = []
        audiences = []
        type_val = None
        for r in rows:
            tag_type = r["type"]
            title_en = r["title_en"]
            if tag_type == "subject":
                subjects.append(title_en)
            elif tag_type == "audience":
                audiences.append(title_en)
            elif tag_type == "type":
                type_val = title_en
        if subjects:
            result["subjects"] = ";".join(subjects)
        if audiences:
            result["audience"] = ";".join(audiences)
        if type_val:
            result["type"] = type_val
        return result
    finally:
        conn.close()


# ============================================================================
# Page-Tag assignment
# ============================================================================

# OAG/BVG 报告 metadata 字段 → 对应 tag 分类路径（用于 slug 计算与反查限定）
OAG_METADATA_FIELDS = {
    "report_type": "/canadasite/tags/custom/oag-bvg/report-type",
    "issue_year": "/canadasite/tags/custom/oag-bvg/issue-year",
    "issues": "/canadasite/tags/custom/oag-bvg/issues",
    "location": "/canadasite/tags/custom/oag-bvg/location",
    "media_type": "/canadasite/tags/custom/oag-bvg/media-type",
    "status": "/canadasite/tags/custom/oag-bvg/status",
    "topics": "/canadasite/tags/custom/oag-bvg/topics",
    "department": "/canadasite/tags/custom/oag-bvg/department",
    "ministers": "/canadasite/tags/custom/oag-bvg/ministers",
    "audited_entities": "/canadasite/tags/institutions",
}


@router.get("/page-properties")
async def get_page_tag_properties_by_query(
    path: str = Query(..., description="Page path, e.g. /canadasite/en/oag/...")
):
    """返回页面中引用的 custom tag 完整属性（query 形式，供 mustache datasource 使用）。"""
    conn = get_db()
    try:
        result = fetch_page_tag_properties(conn, path)
        if result is None:
            raise HTTPException(404, f"Page not found: {path}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Page tag properties failed: {e}")
    finally:
        conn.close()


@router.get("/page/{page_path:path}/properties")
async def get_page_tag_properties(page_path: str):
    """返回页面中引用的 custom tag 完整属性（RESTful path 版本）。"""
    conn = get_db()
    try:
        if not page_path.startswith("/"):
            page_path = "/" + page_path
        result = fetch_page_tag_properties(conn, page_path)
        if result is None:
            raise HTTPException(404, f"Page not found: {page_path}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Page tag properties failed: {e}")
    finally:
        conn.close()


def fetch_page_tag_properties(executor, page_path: str):
    """带继承版本：department/ministers/location 缺失时沿祖先路径向上取（最近优先，到 /canadasite/en 为止）。"""
    result = _load_page_props(executor, page_path)
    if result is None:
        return None
    INHERIT_FIELDS = ("department", "ministers", "location")
    missing = [f for f in INHERIT_FIELDS if not result["tags"].get(f)]
    parts = [p for p in page_path.split("/") if p]
    while len(parts) > 2 and missing:
        parts = parts[:-1]
        parent_path = "/" + "/".join(parts)
        parent = _load_page_props(executor, parent_path)
        if parent is None:
            continue
        still = []
        for f in missing:
            if parent["tags"].get(f):
                result["tags"][f] = parent["tags"][f]
            else:
                still.append(f)
        missing = still
    return result


def _load_page_props(executor, page_path: str):
    """共享查询：返回页面 metadata 中引用的 custom tag 完整属性。

    双通道匹配：
    1. 有 {field}_key → 按 tag id 直接查表（新弹窗保存的数据）
    2. 纯文本（旧自由文本/未补 key）→ 按 title_en 反查（限定在字段对应分类路径内）
    匹配不到的文本进 unresolved 保留原文，模板仍可显示。
    """
    page = executor.execute(
        "SELECT id, path, language, metadata FROM webbot_page WHERE path = ?",
        (page_path,)
    ).fetchone()
    if page is None:
        return None
    meta = {}
    if page["metadata"]:
        try:
            meta = json.loads(page["metadata"])
        except (ValueError, TypeError):
            meta = {}

    tags = {}
    unresolved = {}
    for field, cat_path in OAG_METADATA_FIELDS.items():
        keys = meta.get(field + "_key")
        texts = meta.get(field)
        key_list = keys if isinstance(keys, list) else ([keys] if keys else [])
        text_list = [t for t in (texts if isinstance(texts, list) else ([texts] if texts else [])) if t]

        items = []
        seen_ids = set()

        # 通道 1：按 key 查属性（_key 存的是去前缀 slug，如 'auditor-general-reports'；
        # 也兼容完整 tag id 格式）。slug → path = cat_path + '/' + key。
        if key_list:
            ph = ",".join("?" for _ in key_list)
            path_candidates = [cat_path + "/" + k for k in key_list]
            ph2 = ",".join("?" for _ in path_candidates)
            rows = executor.execute(
                f"SELECT id, path, title_en, title_fr, type FROM webbot_tag "
                f"WHERE id IN ({ph}) OR path IN ({ph2})",
                key_list + path_candidates
            ).fetchall()
            by_id = {r["id"]: r for r in rows}
            by_path = {r["path"]: r for r in rows}
            for k in key_list:
                r = by_id.get(k) or by_path.get(cat_path + "/" + k)
                if r:
                    items.append(_tag_props(r, cat_path, "key"))
                    seen_ids.add(r["id"])
                else:
                    unresolved.setdefault(field, []).append(k)

        # 通道 2：纯文本按 title_en 反查（限定分类路径内，大小写不敏感）
        if text_list:
            ph = ",".join("?" for _ in text_list)
            rows = executor.execute(
                f"SELECT id, path, title_en, title_fr, type FROM webbot_tag "
                f"WHERE LOWER(title_en) IN ({ph}) AND (path = ? OR path LIKE ?)",
                [t.strip().lower() for t in text_list] + [cat_path, cat_path + "/%"]
            ).fetchall()
            by_title = {}
            for r in rows:
                by_title.setdefault(r["title_en"].strip().lower(), r)
            for t in text_list:
                r = by_title.get(t.strip().lower())
                if r and r["id"] not in seen_ids:
                    items.append(_tag_props(r, cat_path, "title"))
                    seen_ids.add(r["id"])
                elif not r:
                    if field in ("department", "ministers", "location"):
                        # 无分类/反查不到的字段：文本透传，模板可直接显示原文
                        items.append({
                            "id": None,
                            "path": "",
                            "slug": t.strip(),
                            "title_en": t.strip(),
                            "title_fr": "",
                            "type": "text",
                            "matched": "text",
                        })
                    else:
                        unresolved.setdefault(field, []).append(t)

        tags[field] = items

    return {
        "path": page["path"],
        "language": page["language"],
        "is_en": page["language"] == "en",
        "tabling_date": _format_tabling_date(meta),
        "tabling_date_iso": meta.get("tabling_date_iso", ""),
        "subjects": meta.get("subjects", ""),
        "tags": tags,
        "unresolved": unresolved,
    }



def _parse_page_meta(raw) -> dict:
    """页面 metadata JSON 字符串 → dict（非法/空 → {}）"""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


def _parse_page_tags(executor, meta):
    """双通道解析页面 metadata 中的 OAG custom tag 属性。

    1. 有 {field}_key → 按 tag id 直接查表（新弹窗保存的数据）
    2. 纯文本（旧自由文本/未补 key）→ 按 title_en 反查（限定在字段对应分类路径内）
    匹配不到的文本进 unresolved 保留原文，模板仍可显示。
    """
    tags = {}
    unresolved = {}
    for field, cat_path in OAG_METADATA_FIELDS.items():
        keys = meta.get(field + "_key")
        texts = meta.get(field)
        key_list = keys if isinstance(keys, list) else ([keys] if keys else [])
        text_list = [t for t in (texts if isinstance(texts, list) else ([texts] if texts else [])) if t]

        items = []
        seen_ids = set()

        # 通道 1：按 key 查属性（_key 存的是去前缀 slug，如 'auditor-general-reports'；
        # 也兼容完整 tag id 格式）。slug → path = cat_path + '/' + key。
        if key_list:
            ph = ",".join("?" for _ in key_list)
            path_candidates = [cat_path + "/" + k for k in key_list]
            ph2 = ",".join("?" for _ in path_candidates)
            rows = executor.execute(
                f"SELECT id, path, title_en, title_fr, type FROM webbot_tag "
                f"WHERE id IN ({ph}) OR path IN ({ph2})",
                key_list + path_candidates
            ).fetchall()
            by_id = {r["id"]: r for r in rows}
            by_path = {r["path"]: r for r in rows}
            for k in key_list:
                r = by_id.get(k) or by_path.get(cat_path + "/" + k)
                if r:
                    items.append(_tag_props(r, cat_path, "key"))
                    seen_ids.add(r["id"])
                else:
                    unresolved.setdefault(field, []).append(k)

        # 通道 2：纯文本按 title_en 反查（限定分类路径内，大小写不敏感）
        if text_list:
            ph = ",".join("?" for _ in text_list)
            rows = executor.execute(
                f"SELECT id, path, title_en, title_fr, type FROM webbot_tag "
                f"WHERE LOWER(title_en) IN ({ph}) AND (path = ? OR path LIKE ?)",
                [t.strip().lower() for t in text_list] + [cat_path, cat_path + "/%"]
            ).fetchall()
            by_title = {}
            for r in rows:
                by_title.setdefault(r["title_en"].strip().lower(), r)
            for t in text_list:
                r = by_title.get(t.strip().lower())
                if r and r["id"] not in seen_ids:
                    items.append(_tag_props(r, cat_path, "title"))
                    seen_ids.add(r["id"])
                elif not r:
                    unresolved.setdefault(field, []).append(t)

        tags[field] = items

    return tags, unresolved


@router.get("/oag-page-properties")
async def get_oag_page_properties(
    path: str = Query(..., description="Parent page path, e.g. /canadasite/en/auditor-general/our-work/audit-reports")
):
    """输入父页面 path，返回其直接子页面的 OAG 属性列表。

    每个 item 包含：path、canada_ca_url（去 /canadasite 前缀的相对 URL）、
    thumbnail（metadata.thumbnail，editor metadata Advanced tab 新增字段）。

    Examples:
    - GET /api/v1/tags/oag-page-properties?path=/canadasite/en/auditor-general/our-work/audit-reports
    """
    conn = get_db()
    try:
        if not path.startswith("/"):
            path = "/" + path
        normalized = path.rstrip("/") or "/"

        # 直接子页面
        rows = conn.execute(
            "SELECT path, language, title, metadata FROM webbot_page WHERE parent_path = ? ORDER BY title ASC",
            (normalized,)
        ).fetchall()
        items = [_oag_page_item(conn, r) for r in rows]

        if not items:
            # path 本身也不存在才 404；页面存在但无子页面 → 空列表
            page = conn.execute(
                "SELECT path FROM webbot_page WHERE path = ?", (normalized,)
            ).fetchone()
            if page is None:
                raise HTTPException(404, f"No pages found for path: {path}")
        return {"path": normalized, "count": len(items), "pages": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAG page properties failed: {e}")
    finally:
        conn.close()


def _oag_page_item(executor, row) -> dict:
    """页面行 → OAG 属性 dict：path / canada_ca_url / thumbnail / language / is_en /
    tabling_date / tabling_date_iso / subjects / tags（8 个 OAG 分类，双通道解析）"""
    p = row["path"]
    meta = _parse_page_meta(row["metadata"])
    tags, _ = _parse_page_tags(executor, meta)
    # id 只需 path 最后一段（slug），如 commentaries-on-financial-audits
    for field_items in tags.values():
        for it in field_items:
            it["id"] = it["path"].rsplit("/", 1)[-1]
    return {
        "path": p,
        "title": row["title"],
        "canada_ca_url": p[len("/canadasite"):] if p.startswith("/canadasite") else None,
        "thumbnail": meta.get("thumbnail", "") or "",
        "language": row["language"],
        "is_en": row["language"] == "en",
        "tabling_date": _format_tabling_date(meta),
        "tabling_date_iso": meta.get("tabling_date_iso", "") or "",
        "subjects": meta.get("subjects", "") or "",
        "tags": tags,
    }


def _format_tabling_date(meta) -> str:
    """tabling date 统一输出 MMM dd, yyyy（如 May 04, 2026）。优先从 iso 解析。"""
    iso = meta.get("tabling_date_iso", "") or ""
    if iso:
        try:
            return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %d, %Y")
        except (ValueError, TypeError):
            pass
    return meta.get("tabling_date", "") or ""


def _tag_props(r, cat_path: str, matched: str) -> dict:
    """tag 行 → 属性 dict（slug = path 去掉分类父路径前缀）"""
    return {
        "id": r["id"],
        "path": r["path"],
        "slug": r["path"][len(cat_path) + 1:],
        "title_en": r["title_en"],
        "title_fr": r["title_fr"],
        "type": r["type"],
        "matched": matched,
    }


@router.get("/page/{page_path:path}/dcterms")
async def get_page_dcterms_by_path(page_path: str):
    """获取页面标签的 dcterms 元数据（RESTful path 版本）"""
    conn = get_db()
    try:
        if not page_path.startswith("/"):
            page_path = "/" + page_path
        page = conn.execute("SELECT id FROM webbot_page WHERE path = ?", (page_path,)).fetchone()
        if not page:
            raise HTTPException(404, f"Page not found: {page_path}")
        rows = conn.execute("""
            SELECT t.title_en, t.title_fr, t.type FROM webbot_tag t
            INNER JOIN webbot_page_tags pt ON pt.tag_id = t.id
            WHERE pt.page_id = ?
        """, (page["id"],)).fetchall()
        result = {}
        subjects = []
        audiences = []
        type_val = None
        for r in rows:
            tag_type = r["type"]
            title_en = r["title_en"]
            if tag_type == "subject":
                subjects.append(title_en)
            elif tag_type == "audience":
                audiences.append(title_en)
            elif tag_type == "type":
                type_val = title_en
        if subjects:
            result["subjects"] = ";".join(subjects)
        if audiences:
            result["audience"] = ";".join(audiences)
        if type_val:
            result["type"] = type_val
        return result
    finally:
        conn.close()


@router.get("/page/{page_path:path}")
async def get_page_tags(page_path: str):
    """获取页面的标签列表"""
    conn = get_db()
    try:
        if not page_path.startswith("/"):
            page_path = "/" + page_path
        page = conn.execute("SELECT id FROM webbot_page WHERE path = ?", (page_path,)).fetchone()
        if not page:
            raise HTTPException(404, f"Page not found: {page_path}")
        rows = conn.execute("""
            SELECT t.* FROM webbot_tag t
            INNER JOIN webbot_page_tags pt ON pt.tag_id = t.id
            WHERE pt.page_id = ?
            ORDER BY t.type, t.id
        """, (page["id"],)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/page/{page_path:path}")
async def set_page_tags(page_path: str, data: dict):
    """设置页面的标签（覆盖式）— body: {tag_paths: ["/canadasite/tags/audience/business", ...]}"""
    tag_paths = data.get("tag_paths", [])
    if not isinstance(tag_paths, list):
        raise HTTPException(400, "tag_paths must be a list of tag paths")
    conn = get_db()
    try:
        if not page_path.startswith("/"):
            page_path = "/" + page_path
        page = conn.execute("SELECT id FROM webbot_page WHERE path = ?", (page_path,)).fetchone()
        if not page:
            raise HTTPException(404, f"Page not found: {page_path}")
        page_id = page["id"]
        valid_ids = set()
        if tag_paths:
            placeholders = ",".join("?" for _ in tag_paths)
            existing = conn.execute(
                f"SELECT id, path FROM webbot_tag WHERE path IN ({placeholders})", tag_paths
            ).fetchall()
            found_paths = {r["path"] for r in existing}
            valid_ids = {r["id"] for r in existing}
            invalid = set(tag_paths) - found_paths
            if invalid:
                raise HTTPException(400, f"Tags not found: {', '.join(sorted(invalid))}")
        conn.execute("DELETE FROM webbot_page_tags WHERE page_id = ?", (page_id,))
        for tid in valid_ids:
            conn.execute(
                "INSERT OR IGNORE INTO webbot_page_tags (page_id, tag_id) VALUES (?, ?)",
                (page_id, tid)
            )
        conn.commit()
        rows = conn.execute("""
            SELECT t.* FROM webbot_tag t
            INNER JOIN webbot_page_tags pt ON pt.tag_id = t.id
            WHERE pt.page_id = ?
            ORDER BY t.type, t.id
        """, (page_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.delete("/page/{page_path:path}")
async def remove_page_tag(page_path: str, tag: str = Query(..., description="Tag path to remove")):
    """从页面移除一个标签"""
    conn = get_db()
    try:
        if not page_path.startswith("/"):
            page_path = "/" + page_path
        page = conn.execute("SELECT id FROM webbot_page WHERE path = ?", (page_path,)).fetchone()
        if not page:
            raise HTTPException(404, f"Page not found: {page_path}")
        tag_row = conn.execute("SELECT id FROM webbot_tag WHERE path = ?", (tag,)).fetchone()
        if not tag_row:
            raise HTTPException(404, f"Tag not found: {tag}")
        conn.execute(
            "DELETE FROM webbot_page_tags WHERE page_id = ? AND tag_id = ?",
            (page["id"], tag_row["id"])
        )
        conn.commit()
        return {"removed": tag}
    finally:
        conn.close()


# ============================================================================
# Tag CRUD — path-based
# ============================================================================

def _path_to_id(path: str) -> str:
    """Derive a short unique ID from a tag path."""
    if path == TAG_ROOT:
        return "tags"
    parts = path.replace(TAG_ROOT + "/", "").split("/")
    return "-".join(parts)


def _id_from_name(name: str) -> str:
    """Convert a display name to a machine ID (lowercase, hyphenated)."""
    return name.lower().replace(" ", "-").replace("_", "-").strip("-")


@router.get("")
async def list_tags(
    type: Optional[str] = Query(None, description="Filter by type (e.g. subject, audience)"),
    parent_path: Optional[str] = Query(None, description="Filter children by parent_path"),
    path: Optional[str] = Query(None, description="Get single tag by path"),
    flat: bool = Query(False, description="Return flat list (no tree)")
):
    """列出标签，可选按 type / parent_path 过滤；传 path 返回单个标签"""
    conn = get_db()
    try:
        # Single tag by path
        if path:
            row = conn.execute(
                "SELECT t.*, "
                "(SELECT COUNT(*) FROM webbot_page_tags WHERE tag_id = t.id) AS page_count "
                "FROM webbot_tag t WHERE t.path = ?",
                (path,)
            ).fetchone()
            if not row:
                raise HTTPException(404, f"Tag not found: {path}")
            tag = dict(row)
            tag["children_count"] = conn.execute(
                "SELECT COUNT(*) FROM webbot_tag WHERE parent_path = ?", (path,)
            ).fetchone()[0]
            return tag

        # List with filters
        sql = """SELECT t.*, 
                  (SELECT COUNT(*) FROM webbot_page_tags WHERE tag_id = t.id) AS page_count 
                 FROM webbot_tag t"""
        params = []
        conditions = []
        if type:
            conditions.append("t.type = ?")
            params.append(type)
        if parent_path is not None:
            conditions.append("t.parent_path = ?")
            params.append(parent_path)
        elif not flat:
            # Default for tree view: show root tags only (children of /canadasite/tags)
            conditions.append("t.parent_path = ?")
            params.append(TAG_ROOT)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY t.type, t.id"
        rows = conn.execute(sql, params).fetchall()
        tags = [dict(r) for r in rows]
        for t in tags:
            t["children_count"] = 0
        if not flat:
            all_rows = conn.execute("SELECT id, parent_path FROM webbot_tag").fetchall()
            children_count = {}
            for r in all_rows:
                p = r["parent_path"]
                if p:
                    children_count[p] = children_count.get(p, 0) + 1
            for t in tags:
                t["children_count"] = children_count.get(t["path"], 0)
        return tags
    finally:
        conn.close()


@router.post("", status_code=201)
async def create_tag(data: dict):
    """创建标签 — body: {path, title_en, title_fr, type, parent_path, ...}"""
    tag_path = data.get("path", "").strip()
    if not tag_path:
        raise HTTPException(400, "path is required (e.g. /canadasite/tags/my-category)")
    if tag_path == TAG_ROOT:
        raise HTTPException(400, "Cannot create the root tag")

    # Derive id from path
    tag_id = data.get("id") or _path_to_id(tag_path)

    # Ensure unique
    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM webbot_tag WHERE id = ?", (tag_id,)).fetchone()
        if existing:
            raise HTTPException(409, f"Tag id '{tag_id}' already exists (try a different path/name)")

        parent_path = data.get("parent_path") or None
        tag_type = data.get("type", "")
        if not tag_type:
            # Auto-detect type: if parent is a root category, use parent's type
            if parent_path:
                parent_row = conn.execute("SELECT type FROM webbot_tag WHERE path = ?", (parent_path,)).fetchone()
                if parent_row and parent_row["type"]:
                    tag_type = parent_row["type"]
            if not tag_type:
                # Use the first segment of path after TAG_ROOT as type
                parts = tag_path.replace(TAG_ROOT + "/", "").split("/")
                tag_type = parts[0] if parts else tag_id

        title_en = data.get("title_en", data.get("id", tag_id))
        title_fr = data.get("title_fr", data.get("label_fr", title_en))
        description = data.get("description", "")
        description_fr = data.get("description_fr", "")

        conn.execute(
            """INSERT INTO webbot_tag 
               (id, title_en, title_fr, type, parent_id, path, parent_path, label_fr, description, description_fr) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tag_id,
                title_en,
                title_fr,
                tag_type,
                None,   # parent_id not used anymore
                tag_path,
                parent_path,
                title_fr,
                description,
                description_fr,
            )
        )
        conn.commit()
        row = conn.execute(
            "SELECT t.*, (SELECT COUNT(*) FROM webbot_page_tags WHERE tag_id = t.id) AS page_count "
            "FROM webbot_tag t WHERE t.id = ?", (tag_id,)
        ).fetchone()
        tag = dict(row)
        tag["children_count"] = 0
        return tag
    finally:
        conn.close()


@router.put("")
async def update_tag(data: dict, path: str = Query(..., description="Tag path to update")):
    """更新标签 — 通过 path 定位"""
    conn = get_db()
    try:
        existing = conn.execute("SELECT * FROM webbot_tag WHERE path = ?", (path,)).fetchone()
        if not existing:
            raise HTTPException(404, f"Tag not found: {path}")
        tag_id = existing["id"]
        field_map = {
            "title_en": "title_en", "title_fr": "title_fr",
            "type": "type", "parent_path": "parent_path",
            "path": "path", "description": "description",
            "description_fr": "description_fr", "label_fr": "label_fr",
        }
        fields = []
        params = []
        for key, sql_col in field_map.items():
            if key in data:
                params.append(data[key])
                fields.append(f"{sql_col} = ?")
        if not fields:
            raise HTTPException(400, "No fields to update")
        params.append(tag_id)
        conn.execute(f"UPDATE webbot_tag SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        row = conn.execute(
            "SELECT t.*, "
            "(SELECT COUNT(*) FROM webbot_page_tags WHERE tag_id = t.id) AS page_count "
            "FROM webbot_tag t WHERE t.id = ?", (tag_id,)
        ).fetchone()
        tag = dict(row)
        tag["children_count"] = conn.execute(
            "SELECT COUNT(*) FROM webbot_tag WHERE parent_path = ?", (path,)
        ).fetchone()[0]
        return tag
    finally:
        conn.close()


@router.delete("")
async def delete_tag(path: str = Query(..., description="Tag path to delete")):
    """删除标签 — 通过 path 定位"""
    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM webbot_tag WHERE path = ?", (path,)).fetchone()
        if not existing:
            raise HTTPException(404, f"Tag not found: {path}")
        tag_id = existing["id"]
        conn.execute("DELETE FROM webbot_page_tags WHERE tag_id = ?", (tag_id,))
        conn.execute("DELETE FROM webbot_tag WHERE id = ?", (tag_id,))
        conn.commit()
        return {"deleted": path}
    finally:
        conn.close()


# ============================================================================
# Tag-based page search
# ============================================================================


@router.get("/search")
async def search_pages_by_tags(
    subjects: Optional[str] = Query(None, description="Comma-separated subject tag names (matches title_en)"),
    audiences: Optional[str] = Query(None, description="Comma-separated audience tag names"),
    types: Optional[str] = Query(None, description="Comma-separated type tag names"),
    tags: Optional[str] = Query(None, description="Comma-separated tag names (any type)"),
    path: Optional[str] = Query(None, description="Page path prefix (LIKE 'path%')"),
    operator: str = Query("AND", description="Matching logic: AND (all tags must match) or OR (any tag matches)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Search pages by tags with optional path prefix filter.

    Supports AND/OR matching across multiple tag types.
    Tag names match against title_en field (case-insensitive ILIKE).

    Examples:
    - GET /api/v1/tags/search?subjects=health,transport&audiences=business
    - GET /api/v1/tags/search?subjects=health&path=/canadasite/en
    - GET /api/v1/tags/search?tags=funding,grants&operator=OR
    """
    conn = get_db()
    try:
        # Collect all tag names
        tag_names = []
        if subjects:
            tag_names.extend([s.strip() for s in subjects.split(",") if s.strip()])
        if audiences:
            tag_names.extend([a.strip() for a in audiences.split(",") if a.strip()])
        if types:
            tag_names.extend([t.strip() for t in types.split(",") if t.strip()])
        if tags:
            tag_names.extend([t.strip() for t in tags.split(",") if t.strip()])

        if not tag_names:
            raise HTTPException(400, "At least one tag filter required (subjects, audiences, types, or tags)")

        # Find matching tag IDs (case-insensitive)
        placeholders = ",".join("?" for _ in tag_names)
        tag_rows = conn.execute(
            f"SELECT id, title_en, type, path FROM webbot_tag WHERE LOWER(title_en) IN ({placeholders})",
            [n.lower() for n in tag_names]
        ).fetchall()

        if not tag_rows:
            return {"total": 0, "pages": [], "matched_tags": [], "not_found": tag_names}

        matched_tag_ids = [r["id"] for r in tag_rows]
        matched_tag_names = [r["title_en"] for r in tag_rows]
        matched_lower = set(n.lower() for n in matched_tag_names)
        not_found = [n for n in tag_names if n.lower() not in matched_lower]
        matched_tag_names = list(dict.fromkeys(matched_tag_names))  # deduplicate

        # Build page query
        if operator.upper() == "AND":
            # All tags must match on the same page
            page_sql = f"""
                SELECT pt.page_id FROM webbot_page_tags pt
                WHERE pt.tag_id IN ({','.join('?' for _ in matched_tag_ids)})
                GROUP BY pt.page_id
                HAVING COUNT(DISTINCT pt.tag_id) = ?
            """
            page_params = matched_tag_ids + [len(matched_tag_ids)]
        else:
            # Any tag matches
            page_sql = f"""
                SELECT DISTINCT pt.page_id FROM webbot_page_tags pt
                WHERE pt.tag_id IN ({','.join('?' for _ in matched_tag_ids)})
            """
            page_params = matched_tag_ids

        # Wrap with page details + path filter
        if path:
            path_prefix = path if path.startswith("/") else "/" + path
            count_sql = f"""
                SELECT COUNT(*) as total FROM webbot_page wp
                WHERE wp.id IN ({page_sql})
                AND wp.path LIKE ?
            """
            data_sql = f"""
                SELECT wp.id, wp.path, wp.title, wp.parent_path, wp.status,
                       wp.description, wp.last_published,
                       wp.created_at, wp.last_modified
                FROM webbot_page wp
                WHERE wp.id IN ({page_sql})
                AND wp.path LIKE ?
                ORDER BY wp.last_published DESC
                LIMIT ? OFFSET ?
            """
            count_params = page_params + [f"{path_prefix}%"]
            data_params = page_params + [f"{path_prefix}%", limit, skip]
        else:
            count_sql = f"""
                SELECT COUNT(*) as total FROM webbot_page wp
                WHERE wp.id IN ({page_sql})
            """
            data_sql = f"""
                SELECT wp.id, wp.path, wp.title, wp.parent_path, wp.status,
                       wp.description, wp.last_published,
                       wp.created_at, wp.last_modified
                FROM webbot_page wp
                WHERE wp.id IN ({page_sql})
                ORDER BY wp.last_published DESC
                LIMIT ? OFFSET ?
            """
            count_params = list(page_params)
            data_params = page_params + [limit, skip]

        total = conn.execute(count_sql, count_params).fetchone()["total"]
        page_rows = conn.execute(data_sql, data_params).fetchall()

        # Attach tags to each page
        pages = []
        _dept_cache = {}
        for pr in page_rows:
            p = dict(pr)
            tag_rows = conn.execute("""
                SELECT t.title_en, t.title_fr, t.type, t.path
                FROM webbot_tag t
                INNER JOIN webbot_page_tags pt ON pt.tag_id = t.id
                WHERE pt.page_id = ?
                ORDER BY t.type, t.title_en
            """, (p["id"],)).fetchall()
            def _title_dict(t):
                d = {"en": t["title_en"]}
                if t["title_fr"]:
                    d["fr"] = t["title_fr"]
                return {"title": d}

            p["subjects"] = [_title_dict(t) for t in tag_rows if t["type"] == "subject"]
            p["audiences"] = [_title_dict(t) for t in tag_rows if t["type"] == "audience"]
            p["types"] = [_title_dict(t) for t in tag_rows if t["type"] == "type"]
            # department 级（语言下一级）页面信息：path + department/ministers/location 原文
            _parts = [pp for pp in p["path"].split("/") if pp]
            if len(_parts) >= 3:
                _dept_path = "/" + "/".join(_parts[:3])
                if _dept_path not in _dept_cache:
                    _drow = conn.execute(
                        "SELECT metadata FROM webbot_page WHERE path = ?", (_dept_path,)
                    ).fetchone()
                    try:
                        _dmeta = json.loads(_drow["metadata"]) if _drow and _drow["metadata"] else {}
                    except (ValueError, TypeError):
                        _dmeta = {}
                    _dept_cache[_dept_path] = _dmeta
                _dmeta = _dept_cache[_dept_path]
                p["department"] = {
                    "path": _dept_path,
                    "department": _dmeta.get("department", ""),
                    "ministers": _dmeta.get("ministers", ""),
                    "location": _dmeta.get("location", ""),
                }
            else:
                p["department"] = None
            pages.append(p)

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "pages": pages,
            "matched_tags": matched_tag_names,
            "not_found": not_found,
            "properties": fetch_page_tag_properties(conn, path) if path else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag search failed: {e}")
    finally:
        conn.close()


# ============================================================================
# OAG/BVG custom tags — aggregated properties for report metadata
# ============================================================================

OAG_BVG_CATEGORIES = [
    ("report_type", "Report type", "/canadasite/tags/custom/oag-bvg/report-type"),
    ("issue_year", "Issue year", "/canadasite/tags/custom/oag-bvg/issue-year"),
    ("issues", "Issues", "/canadasite/tags/custom/oag-bvg/issues"),
    ("location", "Location", "/canadasite/tags/custom/oag-bvg/location"),
    ("media_type", "Media type", "/canadasite/tags/custom/oag-bvg/media-type"),
    ("status", "Status", "/canadasite/tags/custom/oag-bvg/status"),
    ("topics", "Topics", "/canadasite/tags/custom/oag-bvg/topics"),
    ("department", "Department", "/canadasite/tags/custom/oag-bvg/department"),
    ("ministers", "Ministers", "/canadasite/tags/custom/oag-bvg/ministers"),
    ("audited_entities", "Audited entities", "/canadasite/tags/institutions"),
]


def fetch_oag_bvg_tags(executor):
    """共享查询：返回 OAG/BVG 报告 metadata 的全部 custom tag 分类及属性。

    executor 可为 sqlite3.Connection 或 Cursor（需 row_factory=sqlite3.Row）。
    供 /api/v1/tags/oag-bvg endpoint 与 mustache 本地数据源共用。
    """
    result = {"categories": {}}
    for key, label, cat_path in OAG_BVG_CATEGORIES:
        rows = executor.execute(
            """SELECT t.id, t.path, t.title_en, t.title_fr, t.type, t.parent_path,
                      (SELECT COUNT(*) FROM webbot_page_tags pt WHERE pt.tag_id = t.id) AS page_count
               FROM webbot_tag t
               WHERE t.path = ? OR t.path LIKE ?
               ORDER BY t.title_en COLLATE NOCASE, t.path""",
            (cat_path, cat_path + "/%")
        ).fetchall()
        tags = []
        for r in rows:
            if r["path"] == cat_path:
                continue  # 分类目录自身不是可选项
            tags.append({
                "id": r["id"],
                "path": r["path"],
                "slug": r["path"][len(cat_path) + 1:],
                "title_en": r["title_en"],
                "title_fr": r["title_fr"],
                "type": r["type"],
                "parent_path": r["parent_path"],
                "page_count": r["page_count"],
            })
        result["categories"][key] = {
            "label": label,
            "path": cat_path,
            "count": len(tags),
            "tags": tags,
        }
    return result


@router.get("/oag-bvg")
async def list_oag_bvg_tags():
    """返回 OAG/BVG 报告 metadata 的全部 custom tag 分类及属性（一次加载）。

    每个分类递归包含其下所有 tag（含子层级，如 location/alberta/...），
    每个 tag 带 id / path / slug / title_en / title_fr / type / page_count。
    """
    conn = get_db()
    try:
        return fetch_oag_bvg_tags(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAG/BVG tags failed: {e}")
    finally:
        conn.close()
