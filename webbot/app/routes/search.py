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
    ai_tag: Optional[str] = Query(None, description="Filter by AI tag (exact match on tag field within ai_tags JSON array)"),
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

            if ai_tag:
                # ai_tags column is JSON array like [{"tag": "contract", "score": 0.98}, ...]
                # Use json_array_elements to unnest and match on tag field
                conditions.append("path IN (SELECT path FROM documents d2, json_array_elements(d2.ai_tags) elem WHERE elem->>'tag' = %s AND json_typeof(d2.ai_tags) = 'array')")
                params.append(ai_tag)

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

            # Strip /boarding/canadasite prefix from path fields for frontend convenience
            # Frontend doesn't need to know about this FileBot internal path structure
            PREFIX = "/boarding/canadasite"
            for doc in documents:
                for field in ("path", "folder_path"):
                    val = doc.get(field)
                    if val and val.startswith(PREFIX):
                        doc[field] = val[len(PREFIX):] or "/"
                # Also handle storage_path if it starts with the prefix
                sp = doc.get("storage_path")
                if sp and sp.startswith(PREFIX):
                    doc["storage_path"] = sp[len(PREFIX):] or "/"

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


@router.get("/categories")
def get_ai_categories(
    path: Optional[str] = Query(None, description="Filter by folder path prefix (LIKE 'path%')"),
    from_: Optional[str] = Query(None, alias="from", description="Category source: clip (ai_category field) or ai (ai_tags field)"),
):
    """Get AI image categories/tags with document counts.
    
    Direct PostgreSQL query — no auth required.
    - from=clip (default): counts from ai_category column
    - from=ai: counts from ai_tags JSON array (each tag becomes a category)
    """
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            use_tags = from_ == "ai"

            # Build path conditions — support multiple source prefixes
            def build_path_condition(path_arg):
                """Build (clause, params) for a user-provided path.
                Documents can be stored under /boarding/canadasite/...,
                /publish/..., or /content/dam/... prefixes.
                Match all of them when a path filter is provided."""
                if not path_arg:
                    return "", []
                # Strip /canadasite prefix if present — frontend uses canonical paths
                stripped = path_arg
                if stripped.startswith("/canadasite/"):
                    stripped = stripped[len("/canadasite"):]
                # Also try with /boarding/canadasite and /publish/canadasite prefixes
                variants = [
                    f"/boarding/canadasite{stripped}%",
                    f"/publish/canadasite{stripped}%",
                    f"{stripped}%",
                ]
                clauses = "(" + " OR ".join(["path LIKE %s"] * len(variants)) + ")"
                return f" AND {clauses}", variants

            if use_tags:
                # from=ai: unnest ai_tags JSON array, count each tag value
                base_sql = """
                    SELECT item->>'tag' AS tag, COUNT(*) as cnt
                    FROM documents,
                         json_array_elements(
                             CASE WHEN ai_tags IS NULL THEN '[]'::json
                                  WHEN json_typeof(ai_tags) = 'array' THEN ai_tags
                                  ELSE '[]'::json
                             END
                         ) AS item
                    WHERE item->>'tag' IS NOT NULL AND item->>'tag' != ''
                """
                params = []
                path_clause, path_params = build_path_condition(path)
                if path_clause:
                    base_sql += path_clause
                    params.extend(path_params)
                base_sql += " GROUP BY tag ORDER BY cnt DESC"
                cur.execute(base_sql, params)
                rows = cur.fetchall()

                categories = [{"category": r["tag"], "count": r["cnt"]} for r in rows]

                # Count total tagged/untagged
                tagged_sql = "SELECT COUNT(*) as total FROM documents WHERE ai_tags IS NOT NULL AND json_typeof(ai_tags) = 'array'"
                untagged_sql = "SELECT COUNT(*) as total FROM documents WHERE ai_tags IS NULL OR json_typeof(ai_tags) != 'array'"
                tag_path_clause, tag_path_params = build_path_condition(path)
                if tag_path_clause:
                    tagged_sql += tag_path_clause
                    untagged_sql += tag_path_clause
                    cur.execute(tagged_sql, tag_path_params)
                    total_tagged = cur.fetchone()["total"]
                    cur.execute(untagged_sql, tag_path_params)
                    total_untagged = cur.fetchone()["total"]
                else:
                    cur.execute(tagged_sql)
                    total_tagged = cur.fetchone()["total"]
                    cur.execute(untagged_sql)
                    total_untagged = cur.fetchone()["total"]
            else:
                # from=clip (default): count from ai_category column
                base_sql = """
                    SELECT ai_category AS category, COUNT(*) as cnt
                    FROM documents
                    WHERE ai_category IS NOT NULL AND ai_category != ''
                """
                params = []
                path_clause, path_params = build_path_condition(path)
                if path_clause:
                    base_sql += path_clause
                    params.extend(path_params)
                base_sql += " GROUP BY ai_category ORDER BY cnt DESC"
                cur.execute(base_sql, params)
                rows = cur.fetchall()

                categories = [{"category": r["category"], "count": r["cnt"]} for r in rows]

                # Count total
                count_sql = "SELECT COUNT(*) as total FROM documents WHERE ai_category IS NOT NULL AND ai_category != ''"
                count_path_clause, count_path_params = build_path_condition(path)
                if count_path_clause:
                    count_sql += count_path_clause
                    cur.execute(count_sql, count_path_params)
                    total_tagged = cur.fetchone()["total"]
                else:
                    cur.execute(count_sql)
                    total_tagged = cur.fetchone()["total"]
                total_untagged = 0  # Not meaningful for clip mode in this proxy

            return {
                "categories": categories,
                "total_tagged": total_tagged,
                "total_untagged": total_untagged
            }

    except Exception as e:
        logger.error(f"Categories query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Categories query failed: {e}")
    finally:
        conn.close()
