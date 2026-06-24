"""
Content API routes — 内容浏览与导航
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db.database import get_db
from app.core.security import get_current_active_user, has_folder_access
from app.models.user import User
from app.models.folder import Folder
from app.schemas.folder import FolderResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def get_ancestors(folder_path: str, db: Session) -> List[Folder]:
    """获取文件夹的所有祖先（从根到直系父文件夹）"""
    ancestors: List[Folder] = []
    current = db.query(Folder).filter(Folder.path == folder_path).first()
    if not current or not current.parent_folder_path:
        return ancestors
    
    # walk up the parent chain
    parent_path = current.parent_folder_path
    while parent_path:
        parent = db.query(Folder).filter(Folder.path == parent_path).first()
        if not parent:
            break
        ancestors.append(parent)
        parent_path = parent.parent_folder_path
    
    # reverse so root is first
    ancestors.reverse()
    return ancestors


def get_direct_children(folder_path: str, db: Session) -> List[Folder]:
    """获取直接子文件夹"""
    return db.query(Folder).filter(
        Folder.parent_folder_path == folder_path
    ).order_by(Folder.order_index, Folder.name).all()


def _folder_to_dict(folder: Folder) -> dict:
    """Convert Folder model to dict for response"""
    return {
        "app_id": folder.app_id,
        "name": folder.name,
        "title": folder.title,
        "path": folder.path,
        "parent_folder_path": folder.parent_folder_path,
        "description": folder.description,
        "is_system_folder": folder.is_system_folder,
        "order_index": folder.order_index,
        "thumbnail_size": folder.thumbnail_size,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
        "created_by": folder.created_by,
        "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
        "updated_by": folder.updated_by,
    }


@router.get("/content/folders")
def get_content_folder(
    path: str = Query(..., description="Folder path, e.g. /canadasite/content/dam/en"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取文件夹信息及其层级上下文
    
    Returns:
    - parent: 祖先文件夹列表（从根到直系父文件夹）
    - folder: 当前文件夹对象
    - subfolder: 直接子文件夹列表
    """
    # Normalize path
    if not path.startswith('/'):
        path = '/' + path
    
    # Check permission
    if not current_user.is_superuser:
        # extract app slug (first segment after /)
        root_path = '/' + path.strip('/').split('/')[0]
        if not has_folder_access(current_user, root_path, "read", db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access this folder"
            )
    
    # Query folder
    folder = db.query(Folder).filter(Folder.path == path).first()
    if not folder:
        # Try to find closest parent that exists and return partial info
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder not found: {path}"
        )
    
    # Get ancestors
    ancestors = get_ancestors(path, db)
    
    # Get direct children
    children = get_direct_children(path, db)
    
    return {
        "parent": [_folder_to_dict(a) for a in ancestors],
        "folder": _folder_to_dict(folder),
        "subfolder": [_folder_to_dict(c) for c in children],
    }
