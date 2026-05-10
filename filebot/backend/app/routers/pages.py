"""Pages routes — 基于文档路径而非 UUID"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.folder import Folder
from app.models.document import Document
from app.models.page import Page
from app.schemas.document import PageResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/path", response_model=List[PageResponse])
def get_pages_by_path(
    path: str = Query(..., description="Folder path, e.g. /boarding/canadasite/fr"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_subfolders: bool = Query(False, description="是否递归包含子文件夹中的文档"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """按文件夹路径获取所有文档的页面"""
    if not path or not path.startswith('/'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path must start with /")

    normalized = path.rstrip('/')
    folder = db.query(Folder).filter(Folder.path == normalized).first()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Folder not found: {path}")

    # 构建文档查询
    if include_subfolders:
        folder_path_prefix = f"{normalized}/"
        subfolders = db.query(Folder).filter(
            Folder.parent_folder_path.like(f"{folder_path_prefix}%")
        ).all()
        folder_paths = [folder.path] + [f.path for f in subfolders]
        docs = db.query(Document).filter(Document.folder_path.in_(folder_paths)).all()
    else:
        docs = db.query(Document).filter(Document.folder_path == folder.path).all()

    if not docs:
        return []

    doc_paths = [d.path for d in docs]
    pages = db.query(Page).filter(
        Page.document_path.in_(doc_paths)
    ).order_by(Page.document_path, Page.page_number).offset(skip).limit(limit).all()

    return pages
