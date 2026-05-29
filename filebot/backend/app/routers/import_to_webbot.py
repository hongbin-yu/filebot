"""
Import folder documents from FileBot into WebBot's webbot_page table.
POST /api/v1/import-to-webbot
"""
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user_allow_query
from app.db.database import SessionLocal, get_db
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document, FileType
from app.schemas.document import DocumentCreate

logger = logging.getLogger(__name__)

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
    m = re.search(r'<meta\s+name=["\']description["\'][^>]*?\s+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        d = m.group(1).strip()
    m = re.search(r'<meta\s+name=["\']keywords["\'][^>]*?\s+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        k = m.group(1).strip()
    return d, k


def extract_dcterms_meta(html: str) -> dict:
    """Extract dcterms.subject, dcterms.audience, dcterms.type from HTML meta tags.
    
    Returns:
        dict with keys 'subjects', 'audience', 'type' (or empty if not found)
    """
    result = {}
    if not html:
        return result
    # dcterms.subject — multiple values, collect all (allow any attributes between name and content)
    subjects = []
    for m in re.finditer(
        r'<meta\s+name=["\']dcterms\.subject["\'][^>]*?\s+content=["\']([^"\']+)["\']',
        html, re.I
    ):
        val = m.group(1).strip()
        if val:
            subjects.append(val)
    if subjects:
        result['subjects'] = ';'.join(subjects)
    # dcterms.audience — multiple values
    audiences = []
    for m in re.finditer(
        r'<meta\s+name=["\']dcterms\.audience["\'][^>]*?\s+content=["\']([^"\']+)["\']',
        html, re.I
    ):
        val = m.group(1).strip()
        if val:
            audiences.append(val)
    if audiences:
        result['audience'] = ';'.join(audiences)
    # dcterms.type — single value
    m = re.search(
        r'<meta\s+name=["\']dcterms\.type["\'][^>]*?\s+content=["\']([^"\']+)["\']',
        html, re.I
    )
    if m:
        val = m.group(1).strip()
        if val:
            result['type'] = val
    return result


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

        # Compute webbot path: strip the app's data root (/boarding/{app_slug})
        # so the full relative path under the app is preserved in wb_path.
        # E.g. prefix=/boarding/canadasite/en/services
        #      → effective_prefix=/boarding/canadasite
        #      → rel_path=/en/services/xxx
        #      → wb_path=/canadasite/en/services/xxx
        effective_prefix = prefix
        prefix_parts = prefix.strip('/').split('/')
        if len(prefix_parts) >= 2 and prefix_parts[0] == 'boarding':
            effective_prefix = '/boarding/' + prefix_parts[1]

        if doc_path.startswith(effective_prefix):
            rel_path = doc_path[len(effective_prefix):]
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
        dcterms = extract_dcterms_meta(content)
        if dcterms:
            meta.update(dcterms)
        # Remove original_html from metadata — it's duplicated in the content column
        if isinstance(meta, dict):
            meta.pop('original_html', None)
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


class ImportSingleDocRequest(BaseModel):
    document_path: str
    path_prefix: str = '/canadasite'


@router.post("/import-to-webbot/single", response_model=ImportToWebBotResponse)
def import_single_to_webbot(
    req: ImportSingleDocRequest,
    current_user: User = Depends(get_current_active_user_allow_query),
):
    """
    Import a single FileBot document into WebBot's webbot_page table.
    POST /api/v1/import-to-webbot/single
    Body: {"document_path": "/boarding/canadasite/en/auditor-general"}
    """
    doc_path = req.document_path.rstrip('/')

    # Verify permission
    db: Session = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.path == doc_path).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_path}")

        app = db.query(App).join(Folder, Folder.app_id == App.id).filter(Folder.path == doc.folder_path).first()
        if app and current_user.role not in ["admin", "superuser"] and app.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="No permission")

        # Skip non-HTML documents
        is_html = (doc.file_type and hasattr(doc.file_type, 'value') and doc.file_type.value == 'HTML') \
                  or (doc.mime_type and 'html' in doc.mime_type.lower())
        if not is_html:
            raise HTTPException(status_code=400, detail=f"Document is not HTML (type={doc.file_type})")

        prefix = doc.folder_path.rstrip('/')
    finally:
        db.close()

    wb_conn = get_webbot_conn()
    cursor = wb_conn.cursor()

    cursor.execute('SELECT path FROM webbot_page')
    existing_paths = {r['path'] for r in cursor.fetchall()}

    # --- Per-document import logic (same as bulk import) ---
    doc_title = doc.title or ''
    storage_path = doc.stored_filename or ''
    doc_meta_raw = doc.document_metadata

    # Compute webbot path: strip the app's data root (/boarding/{app_slug})
    # so the full relative path under the app is preserved in wb_path
    effective_prefix = prefix
    prefix_parts = prefix.strip('/').split('/')
    if len(prefix_parts) >= 2 and prefix_parts[0] == 'boarding':
        effective_prefix = '/boarding/' + prefix_parts[1]

    if not doc.path.startswith(effective_prefix):
        wb_conn.close()
        return ImportToWebBotResponse(path=doc_path, total=1, inserted=0, updated=0, skipped=1,
                                      detail="Document path does not match prefix")

    rel_path = doc.path[len(effective_prefix):]
    if not rel_path.startswith('/'):
        rel_path = '/' + rel_path
    wb_path = req.path_prefix.rstrip('/') + rel_path

    # Parse metadata
    meta = {}
    if doc_meta_raw:
        try:
            meta = json.loads(doc_meta_raw) if isinstance(doc_meta_raw, str) else dict(doc_meta_raw)
        except (json.JSONDecodeError, TypeError):
            meta = {}

    # Read file content
    rel_dir = os.path.dirname(doc.path.lstrip('/'))
    full_file_path = os.path.join(FILEBOT_DATA_DIR, rel_dir, storage_path) if storage_path else ''
    if full_file_path and os.path.exists(full_file_path):
        with open(full_file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    else:
        content = read_file(storage_path)
    if content is None:
        wb_conn.close()
        return ImportToWebBotResponse(path=doc_path, total=1, inserted=0, updated=0, skipped=0, errors=1,
                                      detail="Could not read file content")

    meta_desc, meta_keywords = extract_meta_tags(content)
    dcterms = extract_dcterms_meta(content)
    if dcterms:
        meta.update(dcterms)
    # Remove original_html from metadata — it's duplicated in the content column
    if isinstance(meta, dict):
        meta.pop('original_html', None)
    page_desc = meta_desc or doc.description or ''

    path_parts = [p for p in wb_path.strip('/').split('/') if p]
    if not path_parts:
        wb_conn.close()
        return ImportToWebBotResponse(path=doc_path, total=1, inserted=0, updated=0, skipped=1,
                                      detail="Empty WebBot path")

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
                parent_path = cum
            continue
        cum += '/' + seg
        if i == len(path_parts) - 1:
            break  # leaf node
        if cum not in existing_paths:
            ok = ensure_page_exists(cursor, cum, parent_path, seg, "",
                                    "dir", status="draft",
                                    metadata={"is_folder": True},
                                    hide_in_nav=True)
            if ok != 'failed':
                existing_paths.add(cum)
        parent_path = cum

    # Create/update leaf page
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

    inserted = 0
    updated_count = 0
    if ok == 'inserted':
        inserted = 1
    elif ok == 'updated':
        updated_count = 1

    wb_conn.commit()
    wb_conn.close()

    return ImportToWebBotResponse(
        path=doc_path,
        total=1,
        inserted=inserted,
        updated=updated_count,
        skipped=0 if (inserted or updated_count) else 1,
        detail=f"Imported {inserted} new pages, updated {updated_count} existing pages in WebBot"
    )


def _resolve_en_doc_path_prefix(en_url: str) -> str:
    """Extract clean URL path from en_alternate_url"""
    parsed = urlparse(en_url)
    p = parsed.path.rstrip('/')
    if p.endswith('.html'):
        p = p[:-5]
    return p


def _background_crawl_alternates(
    db: Session,
    items: list,
    root_path: str,
    username: str
):
    """Background task: crawl missing EN alternate URLs and save as documents."""
    from pathlib import Path as PLPath
    import sys

    backend_dir = str(PLPath(__file__).resolve().parents[2])
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)

    from ..ai.website_crawler import get_folder_for_url
    from ..core.path_utils import generate_storage_paths, make_filename_safe
    from ..models.folder import Folder as FolderModel
    from ..models.app import App as AppModel
    from ..models.document import Document as DocumentModel
    from ..core.config import settings as cfg
    from sqlalchemy import func

    # Resolve absolute data root once
    data_root = PLPath(backend_dir) / cfg.DATA_ROOT
    data_root = data_root.resolve()
    logger.info(f"  Absolute data_root: {data_root}")

    def _create_doc_simple(dbs, document_data, folder_path, html_content):
        folder_obj = dbs.query(FolderModel).filter(FolderModel.path == folder_path).first()
        if not folder_obj:
            raise ValueError(f"Folder {folder_path} does not exist")

        app_obj = dbs.query(AppModel).filter(AppModel.id == folder_obj.app_id).first()
        if not app_obj:
            raise ValueError(f"App {folder_obj.app_id} does not exist")

        app_slug = app_obj.slug
        final_filename = make_filename_safe(document_data.original_filename or 'untitled.html')
        filename_stem = PLPath(final_filename).stem

        # Detect: if the filename stem matches the folder's last segment, the
        # document IS the page at the folder path level, NOT a sub-page inside it.
        # This happens because get_folder_for_url() creates folders for ALL path
        # segments, including the page's own segment.
        folder_last_seg = folder_path.rstrip('/').split('/')[-1] if folder_path.strip('/') else ''
        
        if folder_last_seg and folder_last_seg == filename_stem:
            # Page-level doc: stored at the folder path itself
            clean_folder = '/' + '/'.join(folder_path.strip('/').split('/')[1:])  # all segments
            url_path = f"/{app_slug}{clean_folder}"  # e.g. /boarding/canadasite/en/xxx
            storage_path = data_root / f"{app_slug}{clean_folder}" / final_filename
        else:
            # Sub-page: stored inside the folder
            if app_slug and folder_path.startswith('/' + app_slug):
                clean_folder = folder_path[len(app_slug) + 1:]
            else:
                clean_folder = folder_path
            clean_folder = '/' + clean_folder.strip('/')
            url_path = f"/{app_slug}{clean_folder}/{filename_stem}"
            storage_path = data_root / f"{app_slug}{clean_folder}" / final_filename

        logger.info(f"  storage_path={storage_path}, url_path={url_path}, filename_matches_folder={folder_last_seg == filename_stem}")

        # Check if doc already exists by path
        existing_doc = dbs.query(DocumentModel).filter(DocumentModel.path == url_path).first()
        if existing_doc:
            logger.info(f"  Doc already exists at {url_path}, updating")
            existing_doc.title = document_data.title or existing_doc.title
            existing_doc.description = document_data.description or existing_doc.description
            existing_doc.original_filename = document_data.original_filename or existing_doc.original_filename
            existing_doc.document_metadata = document_data.document_metadata or existing_doc.document_metadata
            existing_doc.updated_at = func.now()
            existing_doc.uploaded_by = str(document_data.uploaded_by)
            
            storage_path.write_text(html_content, encoding='utf-8')
            dbs.commit()
            dbs.refresh(existing_doc)
            logger.info(f"  Updated existing doc at {url_path}")
            return existing_doc

        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_text(html_content, encoding='utf-8')

        from ..models.document import DocumentStatus, ConversionStatus

        doc = DocumentModel(
            path=url_path,
            folder_path=folder_path,
            title=document_data.title or '',
            description=document_data.description or '',
            original_filename=document_data.original_filename,
            stored_filename=final_filename,
            storage_path=str(storage_path.relative_to(data_root)),
            file_size=document_data.file_size or len(html_content.encode('utf-8')),
            mime_type=document_data.mime_type or 'text/html',
            file_type=FileType.HTML,
            document_metadata=document_data.document_metadata or {},
            status=DocumentStatus.ACTIVE,
            uploaded_by=str(document_data.uploaded_by),
            conversion_status=ConversionStatus.PENDING,
        )
        dbs.add(doc)
        dbs.commit()
        dbs.refresh(doc)
        return doc

    results = {'crawled': 0, 'failed': 0, 'errors': []}
    for fr_doc, en_url in items:
        try:
            logger.info(f"Crawling EN alternate: {en_url}")
            resp = requests.get(en_url, timeout=20, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; FileBotCrawler/1.0)'
            })
            resp.raise_for_status()

            soup = BeautifulSoup(resp.content, 'html.parser')
            title = soup.title.string.strip()[:200] if soup.title and soup.title.string else en_url
            title = re.sub(r'\s+', ' ', title)

            doc_folder_path = get_folder_for_url(db, root_path, en_url, username=username)

            en_path = _resolve_en_doc_path_prefix(en_url)
            safe_name = en_path.split('/')[-1] if en_path.split('/')[-1] else 'index'

            doc_meta_raw = fr_doc.document_metadata
            fr_url = None
            try:
                meta = json.loads(doc_meta_raw) if isinstance(doc_meta_raw, str) else (dict(doc_meta_raw) if doc_meta_raw else {})
                fr_url = meta.get('url', '')
            except (json.JSONDecodeError, TypeError):
                pass

            doc_data = DocumentCreate(
                original_filename=f"{safe_name}.html",
                file_type=FileType.HTML,
                title=title,
                description="Auto-crawled from alternate language URL",
                file_size=len(resp.content),
                mime_type='text/html',
                folder_path=doc_folder_path,
                uploaded_by=username,
                document_metadata={
                    'url': en_url,
                    'original_url': en_url,
                    'crawled_at': time.time(),
                    'depth': 1,
                    'original_html': resp.text[:10000],
                    'fr_alternate_url': fr_url,
                }
            )

            _create_doc_simple(db, doc_data, doc_folder_path, resp.text)
            results['crawled'] += 1
            logger.info(f"  ✅ Saved: {en_url} -> {doc_folder_path}/{safe_name}.html")

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            results['failed'] += 1
            results['errors'].append({'url': en_url, 'error': str(e)[:200]})
            logger.error(f"  ❌ Failed: {en_url}: {e}")
            for line in tb.split('\n')[-8:]:
                logger.error(f"     {line}")

    logger.info(f"Crawl alternates done: {results['crawled']} crawled, {results['failed']} failed")


@router.post("/crawl-missing-alternates")
async def crawl_missing_alternates(
    req: ImportToWebBotRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_allow_query),
):
    """
    Find French HTML pages whose English alternate URL hasn't been crawled
    into FileBot, then crawl those English URLs and save them as documents.
    After this, re-run import-to-webbot to pick up the new English pages.
    """
    folder_path = req.folder_path.rstrip('/')
    if not folder_path.startswith('/'):
        folder_path = '/' + folder_path

    # Verify folder and app
    folder = db.query(Folder).filter(Folder.path == folder_path).first()
    if not folder:
        raise HTTPException(404, detail=f"Folder not found: {folder_path}")

    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        raise HTTPException(404, detail="App not found for folder")

    if current_user.role not in ["admin", "superuser"] and app.created_by != current_user.id:
        raise HTTPException(403, detail="No permission")

    # Compute root path for EN pages: strip to app data root (/boarding/{app_slug})
    root_path = folder_path
    path_parts = folder_path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == 'boarding':
        root_path = '/boarding/' + path_parts[1]

    # Query FR HTML docs
    if req.recursive:
        docs = db.query(Document).filter(
            Document.path.like(folder_path + '/%'),
        ).all()
    else:
        docs = db.query(Document).filter(
            Document.path.like(folder_path + '/%'),
            ~Document.path.like(folder_path + '/%/%')
        ).all()

    html_docs = [
        d for d in docs
        if (hasattr(d.file_type, 'value') and d.file_type.value == 'HTML')
        or (d.mime_type and 'html' in d.mime_type.lower())
    ]

    # For each FR doc, check en_alternate_url
    with_alternate = 0
    already_exists = 0
    to_crawl = []

    for doc in html_docs:
        if not doc.path or '/fr/' not in doc.path:
            continue  # skip non-French pages

        meta_raw = doc.document_metadata
        if not meta_raw:
            continue
        try:
            meta = json.loads(meta_raw) if isinstance(meta_raw, str) else dict(meta_raw)
        except (json.JSONDecodeError, TypeError):
            continue

        # Look for English alternate URL
        alt_fields = ['alternate_en_url', 'en_alternate_url']
        alt_url = None
        for f in alt_fields:
            val = meta.get(f)
            if val and isinstance(val, str) and val.startswith('http'):
                alt_url = val
                break

        if not alt_url:
            continue

        with_alternate += 1
        en_path = _resolve_en_doc_path_prefix(alt_url)

        # Check if a doc with this path already exists in FileBot
        like_pattern = f'%{en_path}'
        exists = db.query(Document).filter(Document.path.like(like_pattern)).count() > 0

        if exists:
            already_exists += 1
        else:
            to_crawl.append((doc, alt_url))

    if not to_crawl:
        return {
            "folder_path": folder_path,
            "effective_root": root_path,
            "total_french_pages": len([d for d in html_docs if '/fr/' in (d.path or '')]),
            "with_alternate_url": with_alternate,
            "already_exists": already_exists,
            "crawled": 0,
            "detail": "No missing English pages found — all alternates are already crawled"
        }

    # Start background crawl
    background_tasks.add_task(
        _background_crawl_alternates,
        db=db,
        items=to_crawl,
        root_path=root_path,
        username=str(current_user.id)
    )

    return {
        "folder_path": folder_path,
        "effective_root": root_path,
        "total_french_pages": len([d for d in html_docs if '/fr/' in (d.path or '')]),
        "with_alternate_url": with_alternate,
        "already_exists": already_exists,
        "crawled": 0,
        "detail": f"Found {len(to_crawl)} missing English pages, crawl started in background. Re-run import-to-webbot after it finishes."
    }

