"""
Search proxy — queries FileBot's SQLite database directly for document/image search.
Available through webbot's port (8000) so frontend code never needs the FileBot port.

Usage in mustache-editor:
  GET /api/v1/search/documents?path=/boarding/canadasite/content/dam/canada%
"""

import os
import sqlite3
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

FILEBOT_DB_PATH = os.environ.get(
    "FILEBOT_DB_PATH",
    "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
)


def get_db() -> sqlite3.Connection:
    """Get read-only FileBot database connection"""
    try:
        conn = sqlite3.connect(FILEBOT_DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"FileBot DB connection failed: {e}")


router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("/documents")
def search_documents(
    path: Optional[str] = Query(None, description="Path prefix match (LIKE 'path%')"),
    title: Optional[str] = Query(None, description="Document title (fuzzy match)"),
    status: Optional[str] = Query(None, description="Document status"),
    document_type: Optional[str] = Query(None, description="Document type"),
    folder_path: Optional[str] = Query(None, description="Exact folder path"),
    app_id: Optional[str] = Query(None, description="Filter by app ID"),
    mime_type: Optional[str] = Query(None, description="MIME type (exact or LIKE)"),
    file_type: Optional[str] = Query(None, description="File type extension (e.g. JPEG, PNG)"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records to return"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
):
    """Search FileBot documents by various filters.

    Main use case — path prefix search for mustache-editor getimages:
      GET /api/v1/search/documents?path=/boarding/canadasite/content/dam/canada%
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        conditions: List[str] = []
        params: List[Any] = []

        if path:
            conditions.append("path LIKE ?")
            params.append(f"{path}%")

        if title:
            conditions.append("title LIKE ?")
            params.append(f"%{title}%")

        if status:
            conditions.append("status = ?")
            params.append(status)

        if document_type:
            conditions.append("type = ?")
            params.append(document_type)

        if folder_path:
            conditions.append("folder_path = ?")
            params.append(folder_path)

        if app_id:
            conditions.append("app_id = ?")
            params.append(app_id)

        if mime_type:
            if '%' in mime_type or '_' in mime_type:
                conditions.append("mime_type LIKE ?")
            else:
                conditions.append("mime_type = ?")
            params.append(mime_type)

        if file_type:
            conditions.append("file_type = ?")
            params.append(file_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Validate sort field to prevent SQL injection
        allowed_sorts = {"created_at", "updated_at", "title", "file_size", "path", "id"}
        if sort_by not in allowed_sorts:
            sort_by = "created_at"
        sort_order_sql = "ASC" if sort_order.lower() == "asc" else "DESC"

        # Count total
        cursor.execute(f"SELECT COUNT(*) as total FROM documents WHERE {where_clause}", params)
        total = cursor.fetchone()["total"]

        # Fetch results
        cursor.execute(
            f"SELECT * FROM documents WHERE {where_clause} ORDER BY {sort_by} {sort_order_sql} LIMIT ? OFFSET ?",
            params + [limit, skip]
        )
        rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        documents = [dict(zip(columns, row)) for row in rows]

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "documents": documents
        }

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
    finally:
        conn.close()
