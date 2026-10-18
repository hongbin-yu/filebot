"""
WebBot Versions API — 页面发布版本管理
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sqlite3
import json
import re
import aiohttp
from datetime import datetime

from .. import versioning

router = APIRouter(prefix="/api/v1/versions", tags=["versions"])

import os

DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/page")
async def list_page_versions(
    path: str = Query(..., description="Page path, e.g. /canadasite/en/service"),
):
    """获取指定页面的所有发布版本及页面元数据"""
    versions = versioning.get_versions(path)

    # 获取页面元数据
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, title, navigation_title, language, status, parent_path, "
        "current_version, approved, approved_at, approved_by, scheduled_publish, last_published "
        "FROM webbot_page WHERE path = ?", (path,)
    )
    page = c.fetchone()
    conn.close()

    if not page:
        raise HTTPException(status_code=404, detail=f"Page not found: {path}")

    return {
        "page_path": path,
        "version_count": len(versions),
        "versions": versions,
        "metadata": dict(page),
    }


@router.get("/page/version")
async def get_specific_version(
    path: str = Query(..., description="Page path"),
    version: int = Query(..., description="Version number"),
):
    """获取指定版本的完整内容（content + metadata）"""
    snap = versioning.get_version(path, version)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Version v{version} not found for {path}")
    return snap


@router.get("/page/diff")
async def diff_versions(
    path: str = Query(..., description="Page path"),
    v1: int = Query(..., description="Older version to compare"),
    v2: int = Query(..., description="Newer version to compare"),
):
    """对比两个版本的页面内容"""
    snap1 = versioning.get_version(path, v1)
    snap2 = versioning.get_version(path, v2)
    if snap1 is None:
        raise HTTPException(status_code=404, detail=f"Version v{v1} not found")
    if snap2 is None:
        raise HTTPException(status_code=404, detail=f"Version v{v2} not found")
    return {
        "page_path": path,
        "v1": {
            "version": v1,
            "created_at": snap1["created_at"],
            "content": snap1.get("content", ""),
        },
        "v2": {
            "version": v2,
            "created_at": snap2["created_at"],
            "content": snap2.get("content", ""),
        },
    }


def _extract_footer(page_content: str) -> str:
    """从页面内容中提取 footer HTML"""
    footer_match = re.search(
        r'<footer[^>]*id=[\"\']wb-info[\"\'][^>]*>.*?</footer>',
        page_content or "", re.DOTALL | re.IGNORECASE
    )
    if footer_match:
        return footer_match.group(0)
    return ""


async def _load_template(path: str, page_path: str) -> str:
    """
    从 mustache template page 加载渲染后的模板片段。
    pages.py 中 render_mustache_template 的逻辑。
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (path,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return ""
    try:
        tmpl_config = json.loads(row[0])
        tmpl_content = tmpl_config.get("template", row[0])
    except json.JSONDecodeError:
        tmpl_content = row[0]
    try:
        import chevron
        return chevron.render(tmpl_content, {"path": page_path})
    except Exception:
        return tmpl_content


@router.post("/page/rollback")
async def rollback_page(
    path: str = Query(..., description="Page path"),
    version: int = Query(..., description="Version to rollback to"),
):
    """
    回滚到指定版本：把历史版本的 content（页面正文）写回 webbot_page.content。
    只回滚 content，不改 status（旧内容可能原本已 publish）。不自动 publish。
    """
    # 1. 获取历史 content（页面正文）
    content = versioning.rollback_to_version(path, version)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Version v{version} not found for {path}")

    # 2. 确认页面存在，并读取当前 status（保持不变）
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM webbot_page WHERE path = ?", (path,))
    page = cursor.fetchone()
    if not page:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Page not found: {path}")
    current_status = page[1]

    # 3. 只回滚 content，不改 status、不 publish
    now = datetime.utcnow()
    now_iso = now.isoformat()
    conn.execute(
        "UPDATE webbot_page SET content = ?, last_modified = ? WHERE path = ?",
        (content, now_iso, path)
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "path": path,
        "rolled_back_to": version,
        "status": current_status,
        "note": f"Rolled back to v{version}. Content restored; status unchanged ({current_status}).",
    }


@router.get("/summary")
async def versions_summary():
    """获取所有有版本的页面摘要"""
    return versioning.get_all_versions_summary()
