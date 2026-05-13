"""Pages routes — 基于文档路径而非 UUID"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging
import os
from pathlib import Path

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.folder import Folder
from app.models.document import Document
from app.models.page import Page
from app.schemas.document import PageResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class PublishRequest(BaseModel):
    html_content: str


PUBLISH_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "publish"


def _is_webbot_request(request: Request) -> bool:
    """检查是否为WebBot内部请求"""
    return request.headers.get("X-WebBot-Access") == "true"


@router.post("/publish")
def publish_page(
    path: str = Query(..., description="Page path, e.g. /canadasite/en/contact"),
    publish_req: PublishRequest = Body(..., description="Published HTML content"),
    output_dir: Optional[str] = Query(None, description="Override output directory"),
    request: Request = None,
):
    """
    保存发布的页面HTML到publish目录
    仅接受WebBot内部请求（X-WebBot-Access header），
    由WebBot负责外部身份认证和权限控制
    """
    # 安全检查：必须来自WebBot内部
    if not request or not _is_webbot_request(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only WebBot internal requests are allowed"
        )

    if not path or not path.startswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path must start with /")

    # Determine target directory
    site_root = Path(output_dir) if output_dir else PUBLISH_DIR

    # Normalize and ensure publish dir exists
    rel_path = path.lstrip("/")
    output_file = site_root / f"{rel_path}.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_file.write_text(publish_req.html_content, encoding="utf-8")
        logger.info(f"Published: {output_file} ({len(publish_req.html_content)} bytes)")
        return {
            "success": True,
            "path": path,
            "output_file": str(output_file),
            "html_length": len(publish_req.html_content)
        }
    except Exception as e:
        logger.error(f"Failed to write publish file {output_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write publish file: {str(e)}")


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
