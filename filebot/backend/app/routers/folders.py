"""
Folder management routes — 基于路径主键，彻底移除UUID
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate, FolderTreeResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== Helper Functions ==========

def get_app_or_check_permission(app_id: str, current_user: User, db: Session) -> App:
    """获取应用并检查权限"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    if not current_user.is_superuser and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this app"
        )
    return app


def get_folder_or_404(folder_path: str, db: Session) -> Folder:
    """按路径查找文件夹，找不到返回404"""
    folder = db.query(Folder).filter(Folder.path == folder_path).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder not found: {folder_path}"
        )
    return folder


def check_folder_permission(folder: Folder, current_user: User, db: Session):
    """检查用户是否有权限操作该文件夹"""
    if current_user.is_superuser:
        return
    app = db.query(App).filter(App.id == folder.app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated app not found")
    if app.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to access this folder")


# ========== 路由 ==========

@router.get("/", response_model=List[FolderResponse])
def get_folders(
    app_id: Optional[str] = Query(None, description="Filter by app ID"),
    app_slug: Optional[str] = Query(None, description="Filter by app slug (path prefix)"),
    parent_folder_path: Optional[str] = Query(None, description="Filter by parent folder path"),
    path_starts_with: Optional[str] = Query(None, description="Filter by path prefix (e.g. '/boarding' for all app folders)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文件夹列表，支持按 app_id / app_slug / parent_folder_path / path_starts_with 过滤"""
    query = db.query(Folder)

    if app_id:
        get_app_or_check_permission(app_id, current_user, db)
        query = query.filter(Folder.app_id == app_id)
    elif app_slug:
        app = db.query(App).filter(App.slug == app_slug).first()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"App not found: {app_slug}")
        if not current_user.is_superuser and app.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to access this app")
        query = query.filter(Folder.app_id == app.id)
    else:
        if not current_user.is_superuser:
            user_app_ids = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
            query = query.filter(Folder.app_id.in_(user_app_ids))

    if path_starts_with:
        query = query.filter(Folder.path.startswith(path_starts_with))
    elif parent_folder_path is not None:
        query = query.filter(Folder.parent_folder_path == parent_folder_path)
    else:
        # 默认只返回顶层文件夹
        query = query.filter(Folder.parent_folder_path == None)

    folders = query.order_by(Folder.order_index, Folder.name).offset(skip).limit(limit).all()
    return folders


@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建文件夹（基于路径层级）"""
    app = get_app_or_check_permission(str(folder_data.app_id), current_user, db)

    # 检查同级同名冲突
    existing = db.query(Folder).filter(
        Folder.app_id == str(folder_data.app_id),
        Folder.parent_folder_path == folder_data.parent_folder_path,
        Folder.name == folder_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder '{folder_data.name}' already exists at same level"
        )

    # 自动生成路径
    if folder_data.parent_folder_path:
        parent = get_folder_or_404(folder_data.parent_folder_path, db)
        path = f"{parent.path.rstrip('/')}/{folder_data.name}"
    else:
        path = f"/{app.slug}/{folder_data.name}"

    folder = Folder(
        name=folder_data.name,
        title=folder_data.title or folder_data.name,
        path=folder_data.path or path,
        description=folder_data.description,
        app_id=str(folder_data.app_id),
        parent_folder_path=folder_data.parent_folder_path or None,
        is_system_folder=folder_data.is_system_folder,
        order_index=folder_data.order_index,
        created_by=current_user.username
    )

    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.get("/by-path", response_model=FolderResponse)
def get_folder_by_path(
    path: str = Query(..., description="Folder path, e.g. /boarding/canadasite/fr"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """按路径获取文件夹"""
    folder = get_folder_or_404(path, db)
    check_folder_permission(folder, current_user, db)
    return folder


@router.get("/tree/{app_id}", response_model=List[FolderTreeResponse])
def get_folder_tree(
    app_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取应用的文件夹树"""
    get_app_or_check_permission(app_id, current_user, db)

    all_folders = db.query(Folder).filter(Folder.app_id == app_id).all()

    def build_tree(parent_path: Optional[str] = None) -> List[FolderTreeResponse]:
        children = [f for f in all_folders if f.parent_folder_path == parent_path]
        result = []
        for folder in children:
            subfolders = build_tree(folder.path)
            # 递归计算文档数
            doc_count = db.query(Document).filter(Document.folder_path == folder.path).count()
            for sf in subfolders:
                doc_count += sf.document_count
            result.append(FolderTreeResponse(
                name=folder.name,
                title=folder.title,
                path=folder.path,
                parent_folder_path=folder.parent_folder_path,
                description=folder.description,
                app_id=folder.app_id,
                is_system_folder=folder.is_system_folder,
                order_index=folder.order_index,
                created_by=folder.created_by,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
                updated_by=folder.updated_by,
                subfolders=subfolders,
                document_count=doc_count
            ))
        return result

    return build_tree(None)


@router.get("/{folder_path:path}", response_model=FolderResponse)
def get_folder(
    folder_path: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """按路径获取单个文件夹"""
    folder = get_folder_or_404("/" + folder_path.lstrip("/"), db)
    check_folder_permission(folder, current_user, db)
    return folder


@router.put("/{folder_path:path}", response_model=FolderResponse)
def update_folder(
    folder_path: str,
    folder_data: FolderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新文件夹"""
    full_path = "/" + folder_path.lstrip("/")
    folder = get_folder_or_404(full_path, db)
    check_folder_permission(folder, current_user, db)

    update_data = folder_data.model_dump(exclude_unset=True)

    if 'name' in update_data:
        folder.name = update_data['name']
        # 更新路径
        old_name = folder.path.rstrip('/').split('/')[-1]
        folder.path = folder.path.replace(f"/{old_name}", f"/{update_data['name']}", 1)

    if 'title' in update_data:
        folder.title = update_data['title']
    if 'description' in update_data:
        folder.description = update_data['description']
    if 'parent_folder_path' in update_data:
        folder.parent_folder_path = update_data['parent_folder_path']

    folder.updated_by = current_user.username
    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/{folder_path:path}")
def delete_folder(
    folder_path: str,
    recursive: bool = Query(False, description="递归删除子文件夹和文档"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除文件夹，支持递归删除"""
    full_path = "/" + folder_path.lstrip("/")
    folder = get_folder_or_404(full_path, db)
    check_folder_permission(folder, current_user, db)

    subfolder_count = db.query(Folder).filter(Folder.parent_folder_path == full_path).count()
    doc_count = db.query(Document).filter(Document.folder_path == full_path).count()

    if (subfolder_count > 0 or doc_count > 0) and not recursive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder not empty. Use recursive=true to delete."
        )

    if recursive:
        _recursive_delete(full_path, db)
    else:
        db.delete(folder)

    db.commit()
    return {"message": "Folder deleted successfully"}


def _recursive_delete(folder_path: str, db: Session):
    """递归删除文件夹及其下所有内容"""
    subfolders = db.query(Folder).filter(Folder.parent_folder_path == folder_path).all()
    for sf in subfolders:
        _recursive_delete(sf.path, db)

    # 删除该文件夹下所有文档
    db.query(Document).filter(Document.folder_path == folder_path).delete()

    # 删除当前文件夹
    folder = db.query(Folder).filter(Folder.path == folder_path).first()
    if folder:
        db.delete(folder)


@router.get("/{folder_path:path}/children", response_model=List[FolderResponse])
def get_folder_children(
    folder_path: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取子文件夹列表"""
    full_path = "/" + folder_path.lstrip("/")
    folder = get_folder_or_404(full_path, db)
    check_folder_permission(folder, current_user, db)

    children = db.query(Folder).filter(
        Folder.parent_folder_path == full_path
    ).order_by(Folder.order_index, Folder.name).offset(skip).limit(limit).all()
    return children


@router.get("/{folder_path:path}/path-to-root", response_model=List[FolderResponse])
def get_path_to_root(
    folder_path: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取从根到当前文件夹的面包屑路径"""
    full_path = "/" + folder_path.lstrip("/")
    folder = get_folder_or_404(full_path, db)
    check_folder_permission(folder, current_user, db)

    path_items = []
    current = folder
    while current:
        path_items.append(current)
        if current.parent_folder_path:
            current = db.query(Folder).filter(Folder.path == current.parent_folder_path).first()
        else:
            current = None

    path_items.reverse()
    return path_items


@router.post("/{folder_path:path}/move")
def move_folder(
    folder_path: str,
    target_parent_path: str = Query(..., description="目标父文件夹路径"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """移动文件夹到另一父目录"""
    full_path = "/" + folder_path.lstrip("/")
    folder = get_folder_or_404(full_path, db)
    check_folder_permission(folder, current_user, db)

    target = get_folder_or_404(target_parent_path, db)
    check_folder_permission(target, current_user, db)

    if full_path == target_parent_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot move folder to itself")

    # 防止移动到自身子目录
    current = target
    while current.parent_folder_path:
        if current.parent_folder_path == full_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot move to own subfolder")
        current = db.query(Folder).filter(Folder.path == current.parent_folder_path).first()
        if not current:
            break

    # 检查目标目录下同名冲突
    existing = db.query(Folder).filter(
        Folder.parent_folder_path == target_parent_path,
        Folder.name == folder.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder '{folder.name}' already exists under target parent"
        )

    folder.parent_folder_path = target_parent_path
    # 重建路径
    folder.path = f"{target_parent_path.rstrip('/')}/{folder.name}"
    folder.updated_by = current_user.username

    db.commit()
    db.refresh(folder)
    return {"message": "Folder moved successfully", "folder": folder}
