"""
Search proxy — queries FileBot's PostgreSQL database directly for document/image search.
Available through webbot's port (8000) so frontend code never needs the FileBot port.

Usage in mustache-editor:
  GET /api/v1/search/documents?path=/boarding/canadasite/content/dam/canada%
"""

import os
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# ── Read Database URL from FileBot's .env ──────────────────────────────────

_filebot_env = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..",
    "filebot", "backend", ".env"
)

FILEBOT_DATABASE_URL = os.environ.get("FILEBOT_DATABASE_URL")
if not FILEBOT_DATABASE_URL and os.path.exists(_filebot_env):
    with open(_filebot_env) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                FILEBOT_DATABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

FILEBOT_DATABASE_URL = FILEBOT_DATABASE_URL or "postgresql://filebot:filebot@localhost:5432/filebot"


def get_db():
    """Get PostgreSQL connection to FileBot database."""
    try:
        conn = psycopg2.connect(FILEBOT_DATABASE_URL)
        conn.autocommit = True
        return conn
    except psycopg2.Error as e:
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
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            conditions: List[str] = []
            params: List[Any] = []

            if path:
                conditions.append("path LIKE %s")
                params.append(f"{path}%")

            if title:
                conditions.append("title ILIKE %s")
                params.append(f"%{title}%")

            if status:
                conditions.append("status = %s")
                params.append(status)

            if document_type:
                conditions.append("type = %s")
                params.append(document_type)

            if folder_path:
                conditions.append("folder_path = %s")
                params.append(folder_path)

            if app_id:
                conditions.append("app_id = %s")
                params.append(app_id)

            if mime_type:
                if '%' in mime_type or '_' in mime_type:
                    conditions.append("mime_type LIKE %s")
                else:
                    conditions.append("mime_type = %s")
                params.append(mime_type)

            if file_type:
                conditions.append("file_type = %s")
                params.append(file_type)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            # Validate sort field to prevent SQL injection
            allowed_sorts = {"created_at", "updated_at", "title", "file_size", "path", "id"}
            if sort_by not in allowed_sorts:
                sort_by = "created_at"
            sort_order_sql = "ASC" if sort_order.lower() == "asc" else "DESC"

            # Count total
            cur.execute(f"SELECT COUNT(*) as total FROM documents WHERE {where_clause}", params)
            total = cur.fetchone()["total"]

            # Fetch results
            cur.execute(
                f"SELECT * FROM documents WHERE {where_clause} ORDER BY {sort_by} {sort_order_sql} LIMIT %s OFFSET %s",
                params + [limit, skip]
            )
            rows = cur.fetchall()

            documents = [dict(row) for row in rows]

            return {
                "total": total,
                "skip": skip,
                "limit": limit,
                "documents": documents
            }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
    finally:
        conn.close()
