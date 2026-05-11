"""
Import folder documents from FileBot into WebBot's webbot_page table.
POST /api/v1/import-to-webbot
"""
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user_allow_query
from app.db.database import SessionLocal
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document

router = APIRouter(tags=["webbot"])

WEBBOT_DB_PATH = str(Path(__file__).resolve().parents[4] / "webbot" / "app" / "webbot.db")
FILEBOT_DATA_DIR = str(Path(__file__).resolve().parents[2] / "data")

LANG_CODES = frozenset({'en', 'cn', 'fr', 'zh'})


def get_webbot_conn():
    if not os.path.exists(WEBBOT_DB_PATH):
        raise HTTPException(status_code=500, detail=f"WebBot DB not found at {WEBBOT_DB_PATH}")
    conn = sqlite3.connect(WEBBOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def read_file(storage_path: str) -> Optional[str]:
    full_path = os.path.join(FILEBOT_DATA_DIR, storage_path)
    if not os.path.isfile(full_path):
        return None
    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"read_file failed for {storage_path}: {e}")
        return None


def extract_lang(path: str) -> str:
    for p in path.strip('/').split('/'):
        if p in LANG_CODES:
            return p
    return 'en'


def extract_meta_tags(html: str):
    d = k = ''
    if not html:
        return d, k
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        d = m.group(1).strip()
    m = re.search(r'<meta\s+name=["\']keywords["\']\s+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        k = m.group(1).strip()
    return d, k


def ensure_page_exists(cursor, path, parent_path, title, content, language,
                       description="", keywords="", status="published",
                       metadata=None, hide_in_nav=False, other_language_path=None):
    """Upsert a page into webbot_page. Returns 'inserted', 'updated', or 'failed'."""
    now = datetime.now().isoformat()
    meta = json.dumps(metadata or {})

    cursor.execute('SELECT id FROM webbot_page WHERE path = ?', (path,))
    existing = cursor.fetchone()
    if existing:
        # Update existing page — only update other_language_path if provided
        try:
            if other_language_path is not None:
                cursor.execute("""
                    UPDATE webbot_page SET
                        title = ?, description = ?, keywords = ?, content = ?,
                        language = ?, parent_path = ?, other_language_path = ?,
                        status = ?, metadata = ?, hide_in_navigation = ?,
                        last_modified = ?
                    WHERE path = ?
                """, (title, description, keywords, content, language, parent_path,
                      other_language_path, status, meta, 1 if hide_in_nav else 0,
                      now, path))
            else:
                # Don't overwrite other_language_path
                cursor.execute("""
                    UPDATE webbot_page SET
                        title = ?, description = ?, keywords = ?, content = ?,
                        language = ?, parent_path = ?,
                        status = ?, metadata = ?, hide_in_navigation = ?,
                        last_modified = ?
                    WHERE path = ?
                """, (title, description, keywords, content, language, parent_path,
                      status, meta, 1 if hide_in_nav else 0,
                      now, path))
            return 'updated'
        except Exception as e:
            logger.error(f"UPDATE failed for path={path}: {e}")
            return 'failed'

    # Insert new page
    page_id = str(uuid.uuid4())[:24]
    try:
        cursor.execute("""
            INSERT INTO webbot_page 
                (id, title, description, keywords, content, language, parent_path, 
                 other_language_path, status, metadata, hide_in_navigation,
                 created_by, created_at, last_modified, path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (page_id, title, description, keywords, content, language, parent_path,
              other_language_path, status, meta, 1 if hide_in_nav else 0,
              "system", now, now, path))
        return 'inserted'
    except sqlite3.IntegrityError as e:
        logger.warning(f"INSERT integrity error for path={path}: {e}")
        return 'failed'
    except Exception as e:
        logger.error(f"INSERT failed for path={path}: {e}")
        return 'failed'


class ImportToWebBotRequest(BaseModel):
    folder_path: str
    recursive: bool = True
    path_prefix: str = '/canadasite'


class ImportToWebBotResponse(BaseModel):
    path: str
    total: int
    inserted: int
    updated: int = 0
    skipped: int
    detail: str


@router.post("/import-to-webbot", response_model=ImportToWebBotResponse)
def import_to_webbot(
    req: ImportToWebBotRequest,
    current_user: User = Depends(get_current_active_user_allow_query),
):
    folder_path = req.folder_path.rstrip('/')
    if not folder_path.startswith('/'):
        folder_path = '/' + folder_path

    # Verify permission
    db: Session = SessionLocal()
    try:
        folder = db.query(Folder).filter(Folder.path == folder_path).first()
        if not folder:
            raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")

        app = db.query(App).filter(App.id == folder.app_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="App not found for folder")

        if current_user.role not in ["admin", "superuser"] and app.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="No permission")

        # Query all documents under this folder
        prefix = folder_path
        if req.recursive:
            docs = db.query(Document).filter(Document.path.like(prefix + '/%')).order_by(Document.path).all()
        else:
            docs = db.query(Document).filter(
                Document.path.like(prefix + '/%'),
                ~Document.path.like(prefix + '/%/%')
            ).order_by(Document.path).all()
    finally:
        db.close()

    # Filter to HTML documents only (in Python, since file_type is SQLAlchemy Enum)
    html_docs = [d for d in docs if (d.file_type and hasattr(d.file_type, 'value') and d.file_type.value == 'HTML') 
                 or (d.mime_type and 'html' in d.mime_type.lower())]

    # Connect to WebBot DB
    wb_conn = get_webbot_conn()
    cursor = wb_conn.cursor()

    cursor.execute('SELECT path FROM webbot_page')
    existing_paths = {r['path'] for r in cursor.fetchall()}

    inserted = 0
    updated_count = 0
    skipped = 0
    errors = 0

    for doc in html_docs:
        doc_path = doc.path or ''
        doc_title = doc.title or ''
        storage_path = doc.stored_filename or ''
        doc_meta_raw = doc.document_metadata

        # Compute webbot path: strip FileBot prefix, prepend WebBot path prefix
        if doc_path.startswith(prefix):
            rel_path = doc_path[len(prefix):]
            if not rel_path.startswith('/'):
                rel_path = '/' + rel_path
            wb_path = req.path_prefix.rstrip('/') + rel_path
        else:
            skipped += 1
            continue

        # Parse metadata
        meta = {}
        if doc_meta_raw:
            try:
                meta = json.loads(doc_meta_raw) if isinstance(doc_meta_raw, str) else dict(doc_meta_raw)
            except (json.JSONDecodeError, TypeError):
                meta = {}

        # Read file content — use doc path to find the file (stored_filename is just the base name)
        rel_dir = os.path.dirname(doc_path.lstrip('/'))
        full_file_path = os.path.join(FILEBOT_DATA_DIR, rel_dir, storage_path) if storage_path else ''
        if full_file_path and os.path.exists(full_file_path):
            with open(full_file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            # Fallback to old method
            content = read_file(storage_path)
        if content is None:
            errors += 1
            continue

        meta_desc, meta_keywords = extract_meta_tags(content)
        page_desc = meta_desc or doc.description or ''

        path_parts = [p for p in wb_path.strip('/').split('/') if p]
        if not path_parts:
            skipped += 1
            continue

        lang = extract_lang(wb_path)

        # Build directory hierarchy
        parent_path = ''
        cum = ''
        for i, seg in enumerate(path_parts):
            if seg in LANG_CODES:
                cum += '/' + seg
                if cum not in existing_paths:
                    ok = ensure_page_exists(cursor, cum, parent_path, seg, "",
                                            lang, status="draft",
                                            metadata={"is_folder": True, "is_language_root": True},
                                            hide_in_nav=True)
                    if ok != 'failed':
                        existing_paths.add(cum)
                if i < len(path_parts) - 1:
                    parent_path = cum  # only for intermediate lang roots, not leaf
                continue

            cum += '/' + seg
            if i == len(path_parts) - 1:
                break  # leaf node, handled below

            if cum not in existing_paths:
                ok = ensure_page_exists(cursor, cum, parent_path, seg, "",
                                        "dir", status="draft",
                                        metadata={"is_folder": True},
                                        hide_in_nav=True)
                if ok != 'failed':
                    existing_paths.add(cum)
            parent_path = cum

        # Insert leaf page
        if wb_path not in existing_paths:
            other_lang_path = None
            if isinstance(meta, dict):
                alt_fields = ['alternate_fr_url', 'fr_alternate_url'] if lang == 'en' else ['alternate_en_url', 'en_alternate_url']
                alt_url = None
                for f in alt_fields:
                    alt_url = meta.get(f)
                    if alt_url and isinstance(alt_url, str):
                        break
                if alt_url and isinstance(alt_url, str) and alt_url.startswith('http'):
                    parsed = urlparse(alt_url)
                    alt_p = parsed.path.rstrip('/')
                    if alt_p.endswith('.html'):
                        alt_p = alt_p[:-5]
                    other_lang_path = req.path_prefix.rstrip('/') + alt_p if alt_p else None

            ok = ensure_page_exists(cursor, wb_path, parent_path, doc_title, content, lang,
                                    description=page_desc, keywords=meta_keywords,
                                    status="published", metadata=meta,
                                    hide_in_nav=len(path_parts) <= 2,
                                    other_language_path=other_lang_path)
            if ok == 'inserted':
                inserted += 1
                existing_paths.add(wb_path)
            elif ok == 'updated':
                updated_count += 1
            else:
                skipped += 1
        else:
            # Path already known to exist — still update content
            other_lang_path = None
            if isinstance(meta, dict):
                alt_fields = ['alternate_fr_url', 'fr_alternate_url'] if lang == 'en' else ['alternate_en_url', 'en_alternate_url']
                alt_url = None
                for f in alt_fields:
                    alt_url = meta.get(f)
                    if alt_url and isinstance(alt_url, str):
                        break
                if alt_url and isinstance(alt_url, str) and alt_url.startswith('http'):
                    parsed = urlparse(alt_url)
                    alt_p = parsed.path.rstrip('/')
                    if alt_p.endswith('.html'):
                        alt_p = alt_p[:-5]
                    other_lang_path = req.path_prefix.rstrip('/') + alt_p if alt_p else None
            ok = ensure_page_exists(cursor, wb_path, parent_path, doc_title, content, lang,
                                    description=page_desc, keywords=meta_keywords,
                                    status="published", metadata=meta,
                                    hide_in_nav=len(path_parts) <= 2,
                                    other_language_path=other_lang_path)
            if ok == 'updated':
                updated_count += 1
            elif ok == 'inserted':
                inserted += 1
                existing_paths.add(wb_path)
            else:
                skipped += 1

    wb_conn.commit()
    wb_conn.close()

    return ImportToWebBotResponse(
        path=prefix,
        total=len(html_docs),
        inserted=inserted,
        updated=updated_count,
        skipped=skipped + errors,
        detail=f"Imported {inserted} new pages, updated {updated_count} existing pages in WebBot"
    )
