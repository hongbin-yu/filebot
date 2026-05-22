"""
WebBot Tags API — 通用树形标签系统 (path-based)
所有公共接口使用 path / parent_path，内部 join 表仍用 tag id
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import sqlite3
import json

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])

DB_PATH = "app/webbot.db"

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
