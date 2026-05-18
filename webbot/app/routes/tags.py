"""
WebBot Tags API — 通用树形标签系统
支持无限层级嵌套（根标签 = 顶层分类，子标签 = 细分）
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import sqlite3
import json

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])

DB_PATH = "app/webbot.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ============================================================================
# Tag CRUD
# ============================================================================

@router.get("")
async def list_tags(
    type: Optional[str] = Query(None, description="Filter by type (free-form, e.g. subject, audience)"),
    parent_id: Optional[str] = Query(None, description="Filter by parent"),
    flat: bool = Query(False, description="Return flat list (no tree)")
):
    """列出所有标签，可选按 type / parent 过滤"""
    conn = get_db()
    try:
        sql = "SELECT t.*, (SELECT COUNT(*) FROM webbot_page_tags WHERE tag_id = t.id) AS page_count FROM webbot_tag t"
        params = []
        conditions = []
        if type:
            conditions.append("t.type = ?")
            params.append(type)
        if parent_id is not None:
            conditions.append("t.parent_id IS ?")
            params.append(parent_id)
        else:
            conditions.append("t.parent_id IS NULL")
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY t.type, t.id"
        rows = conn.execute(sql, params).fetchall()
        tags = [dict(r) for r in rows]
        for t in tags:
            t["children_count"] = 0
        # If not flat, count children
        if not flat:
            # Get all tags to count children
            all_rows = conn.execute("SELECT id, parent_id FROM webbot_tag").fetchall()
            children_count = {}
            for r in all_rows:
                p = r["parent_id"]
                if p:
                    children_count[p] = children_count.get(p, 0) + 1
            for t in tags:
                t["children_count"] = children_count.get(t["id"], 0)
        return tags
    finally:
        conn.close()


@router.get("/{tag_id}")
async def get_tag(tag_id: str):
    """获取单个标签详情"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT t.*, "
            "(SELECT COUNT(*) FROM webbot_page_tags WHERE tag_id = t.id) AS page_count "
            "FROM webbot_tag t WHERE t.id = ?",
            (tag_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Tag '{tag_id}' not found")
        tag = dict(row)
        tag["children_count"] = conn.execute(
            "SELECT COUNT(*) FROM webbot_tag WHERE parent_id = ?", (tag_id,)
        ).fetchone()[0]
        return tag
    finally:
        conn.close()


@router.post("", status_code=201)
async def create_tag(data: dict):
    """创建标签"""
    tag_id = data.get("id", "").strip()
    if not tag_id:
        raise HTTPException(400, "id is required")
    # type is free-form: any string or None (defaults to "general")

    conn = get_db()
    try:
        # Check duplicate
        existing = conn.execute("SELECT id FROM webbot_tag WHERE id = ?", (tag_id,)).fetchone()
        if existing:
            raise HTTPException(409, f"Tag '{tag_id}' already exists")

        # Validate parent if given
        parent_id = data.get("parent_id")
        if parent_id:
            parent = conn.execute("SELECT id FROM webbot_tag WHERE id = ?", (parent_id,)).fetchone()
            if not parent:
                raise HTTPException(400, f"Parent tag '{parent_id}' not found")

        conn.execute(
            "INSERT INTO webbot_tag (id, label_fr, type, parent_id, description, description_fr) VALUES (?, ?, ?, ?, ?, ?)",
            (
                tag_id,
                data.get("label_fr", ""),
                data.get("type", "subject"),
                parent_id,
                data.get("description", ""),
                data.get("description_fr", ""),
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


@router.put("/{tag_id}")
async def update_tag(tag_id: str, data: dict):
    """更新标签"""
    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM webbot_tag WHERE id = ?", (tag_id,)).fetchone()
        if not existing:
            raise HTTPException(404, f"Tag '{tag_id}' not found")

        # Build dynamic update
        fields = []
        params = []
        for key in ("label_fr", "type", "parent_id", "description", "description_fr"):
            if key in data:
                val = data[key]
                # type is free-form: any string or None
                # Allow setting parent_id to None (null)
                if key == "parent_id":
                    fields.append(f"{key} = ?")
                    params.append(val)
                else:
                    fields.append(f"{key} = ?")
                    params.append(val)

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
            "SELECT COUNT(*) FROM webbot_tag WHERE parent_id = ?", (tag_id,)
        ).fetchone()[0]
        return tag
    finally:
        conn.close()


@router.delete("/{tag_id}")
async def delete_tag(tag_id: str):
    """删除标签（同时删除关联）"""
    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM webbot_tag WHERE id = ?", (tag_id,)).fetchone()
        if not existing:
            raise HTTPException(404, f"Tag '{tag_id}' not found")

        # Remove child references
        conn.execute("UPDATE webbot_tag SET parent_id = NULL WHERE parent_id = ?", (tag_id,))
        # Remove page associations
        conn.execute("DELETE FROM webbot_page_tags WHERE tag_id = ?", (tag_id,))
        # Remove tag
        conn.execute("DELETE FROM webbot_tag WHERE id = ?", (tag_id,))
        conn.commit()
        return {"deleted": tag_id}
    finally:
        conn.close()


# ============================================================================
# Page-Tag assignment
# ============================================================================

@router.get("/page/{page_path:path}")
async def get_page_tags(page_path: str):
    """获取页面的标签"""
    conn = get_db()
    try:
        # Normalize path
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
    """设置页面的标签（覆盖式）"""
    tag_ids = data.get("tag_ids", data.get("tags", []))
    if not isinstance(tag_ids, list):
        raise HTTPException(400, "tag_ids must be a list of tag IDs")

    conn = get_db()
    try:
        if not page_path.startswith("/"):
            page_path = "/" + page_path

        page = conn.execute("SELECT id FROM webbot_page WHERE path = ?", (page_path,)).fetchone()
        if not page:
            raise HTTPException(404, f"Page not found: {page_path}")

        page_id = page["id"]

        # Validate all tag IDs exist
        valid_ids = set()
        if tag_ids:
            placeholders = ",".join("?" for _ in tag_ids)
            existing = conn.execute(
                f"SELECT id FROM webbot_tag WHERE id IN ({placeholders})", tag_ids
            ).fetchall()
            valid_ids = {r["id"] for r in existing}
            invalid = set(tag_ids) - valid_ids
            if invalid:
                raise HTTPException(400, f"Tags not found: {', '.join(sorted(invalid))}")

        # Replace all tags for this page
        conn.execute("DELETE FROM webbot_page_tags WHERE page_id = ?", (page_id,))
        for tid in valid_ids:
            conn.execute(
                "INSERT OR IGNORE INTO webbot_page_tags (page_id, tag_id) VALUES (?, ?)",
                (page_id, tid)
            )
        conn.commit()

        # Return updated tags
        rows = conn.execute("""
            SELECT t.* FROM webbot_tag t
            INNER JOIN webbot_page_tags pt ON pt.tag_id = t.id
            WHERE pt.page_id = ?
            ORDER BY t.type, t.id
        """, (page_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.delete("/page/{page_path:path}/{tag_id}")
async def remove_page_tag(page_path: str, tag_id: str):
    """从页面移除一个标签"""
    conn = get_db()
    try:
        if not page_path.startswith("/"):
            page_path = "/" + page_path
        page = conn.execute("SELECT id FROM webbot_page WHERE path = ?", (page_path,)).fetchone()
        if not page:
            raise HTTPException(404, f"Page not found: {page_path}")
        conn.execute(
            "DELETE FROM webbot_page_tags WHERE page_id = ? AND tag_id = ?",
            (page["id"], tag_id)
        )
        conn.commit()
        return {"removed": tag_id}
    finally:
        conn.close()
