"""
Page Reference API Routes
"""

import sqlite3
import os
from fastapi import APIRouter, Query, HTTPException
from app.services.references import (
    get_page_references,
    full_scan_all_pages,
    scan_page_references,
    search_references,
)

router = APIRouter(prefix="/api/v1/pages", tags=["references"])


@router.get("/{path:path}/references")
async def api_get_references(path: str):
    """Get internal page references for a given page path."""
    normalized = path if path.startswith("/") else f"/{path}"
    normalized = normalized.rstrip("/")
    try:
        refs = get_page_references(normalized)
        return refs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get references: {e}")


@router.get("/_search-references")
async def api_search_references(
    q: str = Query(..., description="Path prefix to search"),
    status: str = Query(None, description="Filter by status: published, draft, file, broken"),
    target_prefix: str = Query(None, description="Filter by target path prefix (e.g., /content/dam)"),
):
    """Search references by path prefix and optional filters."""
    try:
        return search_references(q, status, target_prefix)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.post("/_scan-references")
async def api_scan_references(
    path: str = Query(..., description="Page path to scan"),
    content: str = Query("", description="Page content to scan (optional, will use saved content if empty)"),
):
    """Manually trigger reference scan for a page."""
    normalized = path if path.startswith("/") else f"/{path}"
    normalized = normalized.rstrip("/")

    if not content:
        _db_path = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)
        conn = sqlite3.connect(_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT content FROM webbot_page WHERE path = ?", (normalized,))
        row = cur.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Page not found")
        content = row["content"] or ""

    scan_page_references(normalized, content)
    refs = get_page_references(normalized)

    return {
        "path": normalized,
        "outgoing_count": refs["outgoing_count"],
        "incoming_count": refs["incoming_count"],
    }


@router.post("/_full-scan-references")
async def api_full_scan(
    limit: int = Query(0, description="Max pages to scan (0 = all)"),
    offset: int = Query(0, description="Skip N pages"),
):
    """Full reference scan of all pages."""
    result = full_scan_all_pages(limit=limit, offset=offset)
    return result
