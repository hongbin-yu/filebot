"""
WebBot Schedule API — 页面定时发布管理
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Optional
import sqlite3
from datetime import datetime

import os

router = APIRouter(prefix="/api/v1/pages", tags=["schedule"])

DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)


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

@router.api_route("/approve", methods=["GET", "POST"])
async def approve_page(
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact"),
    approved_by: str = Query("system", description="Who approved this page"),
    redirect: bool = Query(False, description="Redirect back to the public page after approval")
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
        if redirect:
            public_path = path.replace("/canadasite", "", 1)
            return RedirectResponse(url=public_path, status_code=302)
        return {"success": True, "path": path, "approved": True, "approved_at": now, "approved_by": approved_by}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/approve-batch")
async def approve_batch(
    lang: str = Query("both", description="Language filter: en, fr, or both"),
    prefix: str = Query("/canadasite", description="Approve all pages under this path prefix"),
    approved_by: str = Query("ai-approve", description="Who approved these pages"),
    dry_run: bool = Query(False, description="Only count pages without approving"),
):
    """Batch approve: mark all pages under a prefix as approved (enables publish).

    Mirrors publish-batch semantics: optional language filter, dry-run counting.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        base = prefix.rstrip("/")
        if lang in ("en", "fr"):
            base = base + "/" + lang
        cursor.execute(
            "SELECT path FROM webbot_page WHERE path = ? OR path LIKE ?",
            (base, base + "/%"),
        )
        paths = [r["path"] for r in cursor.fetchall()]
        total = len(paths)
        if dry_run:
            return {"dry_run": True, "total": total, "approved": 0, "failed": []}
        now = datetime.now().isoformat()
        failed = []
        for p in paths:
            try:
                cursor.execute(
                    "UPDATE webbot_page SET approved = 1, approved_at = ?, approved_by = ? WHERE path = ?",
                    (now, approved_by, p),
                )
            except Exception as e:  # noqa: BLE001 - collect failures per page
                failed.append({"path": p, "error": str(e)})
        conn.commit()
        return {
            "dry_run": False,
            "total": total,
            "approved": total - len(failed),
            "failed": failed,
            "approved_by": approved_by,
            "approved_at": now,
        }
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


# ==================== 🔒 锁管理 ====================

import json

@router.post("/lock")
async def lock_page(
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact"),
    locked_by: str = Query("system", description="Who locked this page")
):
    """Lock a page to prevent editing and publishing"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, metadata FROM webbot_page WHERE path = ?", (path,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        now = datetime.now().isoformat()
        meta["lock_status"] = "locked"
        meta["locked_at"] = now
        meta["locked_by"] = locked_by
        
        cursor.execute(
            "UPDATE webbot_page SET metadata = ? WHERE path = ?",
            (json.dumps(meta), path)
        )
        conn.commit()
        return {"success": True, "path": path, "locked": True, "locked_at": now, "locked_by": locked_by}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/unlock")
async def unlock_page(
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact")
):
    """Unlock a page to allow editing and publishing"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, metadata FROM webbot_page WHERE path = ?", (path,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        meta["lock_status"] = "unlocked"
        meta.pop("locked_at", None)
        meta.pop("locked_by", None)
        
        cursor.execute(
            "UPDATE webbot_page SET metadata = ? WHERE path = ?",
            (json.dumps(meta), path)
        )
        conn.commit()
        return {"success": True, "path": path, "locked": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/lock-status")
async def lock_status(
    path: str = Query(..., description="Full page path")
):
    """Get lock status for a page"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT metadata FROM webbot_page WHERE path = ?",
            (path,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        meta = json.loads(row["metadata"]) if row["metadata"] else {}
        return {
            "locked": meta.get("lock_status") == "locked",
            "lock_status": meta.get("lock_status", "unlocked"),
            "locked_at": meta.get("locked_at"),
            "locked_by": meta.get("locked_by")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
