"""
WebBot Schedule API — 页面定时发布管理
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sqlite3
from datetime import datetime

router = APIRouter(prefix="/api/v1/pages", tags=["schedule"])

DB_PATH = "app/webbot.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.patch("/schedule")
async def set_schedule(
    path: str = Query(..., description="Page path"),
    scheduled_publish: str = Query(..., description="ISO datetime or empty string to cancel"),
):
    """设置或取消定时发布"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 验证页面存在
    cursor.execute("SELECT id FROM webbot_page WHERE path = ?", (path,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Page not found: {path}")
    
    value = scheduled_publish.strip() if scheduled_publish else None
    if value:
        # 验证时间格式
        try:
            datetime.fromisoformat(value)
        except ValueError:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Invalid datetime: {scheduled_publish}. Use ISO format e.g. 2026-06-30T09:00:00")
    
    cursor.execute(
        "UPDATE webbot_page SET scheduled_publish = ? WHERE path = ?",
        (value, path)
    )
    conn.commit()
    conn.close()
    
    if value:
        return {"success": True, "path": path, "scheduled_publish": value}
    else:
        return {"success": True, "path": path, "scheduled_publish": None, "note": "Schedule cancelled"}


@router.patch("/cancelschedule")
async def cancel_schedule(
    path: str = Query(..., description="Page path"),
):
    """取消页面的定时发布"""
    conn = get_db()
    conn.execute(
        "UPDATE webbot_page SET scheduled_publish = NULL WHERE path = ?", (path,)
    )
    conn.commit()
    conn.close()
    return {"success": True, "path": path, "note": "Schedule cancelled"}


@router.get("/scheduled")
async def list_scheduled():
    """获取所有已设定定时发布的页面"""
    conn = get_db()
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        "SELECT path, title, language, scheduled_publish, status, approved FROM webbot_page "
        "WHERE scheduled_publish IS NOT NULL AND scheduled_publish != '' "
        "ORDER BY scheduled_publish ASC"
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ==================== 审批管理 ====================

@router.post("/approve")
async def approve_page(
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact"),
    approved_by: str = Query("system", description="Who approved this page")
):
    """Approve a page, enabling it for publish"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM webbot_page WHERE path = ?", (path,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        now = datetime.now().isoformat()
        cursor.execute(
            "UPDATE webbot_page SET approved = 1, approved_at = ?, approved_by = ? WHERE path = ?",
            (now, approved_by, path)
        )
        conn.commit()
        return {"success": True, "path": path, "approved": True, "approved_at": now, "approved_by": approved_by}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/unapprove")
async def unapprove_page(
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact")
):
    """Revoke approval for a page"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM webbot_page WHERE path = ?", (path,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        cursor.execute(
            "UPDATE webbot_page SET approved = 0, approved_at = NULL, approved_by = NULL WHERE path = ?",
            (path,)
        )
        conn.commit()
        return {"success": True, "path": path, "approved": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/approval-status")
async def approval_status(
    path: str = Query(..., description="Full page path")
):
    """Get approval status for a page"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT approved, approved_at, approved_by FROM webbot_page WHERE path = ?",
            (path,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
