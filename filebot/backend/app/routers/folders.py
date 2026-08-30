"""
Folder management routes — 基于路径主键，彻底移除UUID
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import logging

from app.db.database import get_db
from app.core.config import settings
from app.core.security import get_current_active_user, has_app_access, has_folder_access
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate, FolderTreeResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== Helper Functions ==========

def get_app_or_check_permission(app_id: str, current_user: User, db: Session, required_level: str = "read") -> App:
    """获取应用并检查权限"""
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        # 兼容客户端传 slug 作为 app_id（GET /folders/ 已支持 app_slug，这里保持一致）
        app = db.query(App).filter(App.slug == app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    if not current_user.is_superuser and app.owner_id != current_user.id:
        if not has_app_access(current_user, app_id, required_level, db):
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


def check_folder_permission(folder: Folder, current_user: User, db: Session, required_level: str = "read"):
    """检查用户是否有权限操作该文件夹（含 app 层级继承）"""
    if current_user.is_superuser:
        return
    if not has_folder_access(current_user, folder.path, required_level, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to access this folder")


# ========== 路由 ==========

@router.get("/", response_model=List[FolderResponse])
def get_folders(
    app_id: Optional[str] = Query(None, description="Filter by app ID"),
    app_slug: Optional[str] = Query(None, description="Filter by app slug (path prefix)"),
    parent_folder_path: Optional[str] = Query(None, description="Filter by parent folder path"),
    path_starts_with: Optional[str] = Query(None, description="Filter by path prefix (e.g. '/boarding' for all app folders)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
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
        # 使用 get_app_or_check_permission 做权限检查（含 has_app_access）
        get_app_or_check_permission(app.id, current_user, db)
        query = query.filter(Folder.app_id == app.id)
    else:
        if not current_user.is_superuser:
            # Owned apps
            owned_app_ids = [row[0] for row in db.query(App.id).filter(App.owner_id == current_user.id).all()]
            # Apps with direct user permission
            from app.models.permission import Permission
            from app.models.group import GroupMember
            perm_app_ids = [
                row[0] for row in db.query(Permission.resource_id)
                .filter(
                    Permission.resource_type == "app",
                    Permission.user_id == current_user.id,
                )
                .all()
            ]
            # Apps with group permission
            user_group_ids = [
                row[0] for row in db.query(GroupMember.group_id)
                .filter(GroupMember.user_id == current_user.id)
                .all()
            ]
            if user_group_ids:
                group_perm_ids = [
                    row[0] for row in db.query(Permission.resource_id)
                    .filter(
                        Permission.resource_type == "app",
                        Permission.group_id.in_(user_group_ids),
                    )
                    .all()
                ]
                perm_app_ids = list(set(perm_app_ids + group_perm_ids))

            all_app_ids = list(set(owned_app_ids + perm_app_ids))
            if all_app_ids:
                query = query.filter(Folder.app_id.in_(all_app_ids))
            else:
                query = query.filter(Folder.app_id == "")  # Return nothing

    # 非超级用户的文件夹权限过滤：按用户拥有的 folder 级别权限缩小可见范围
    if not current_user.is_superuser:
        from app.models.permission import Permission
        from app.models.group import GroupMember
        from sqlalchemy import or_

        # 收集用户所有 folder 级别权限的 path
        folder_paths = set()

        # 直接权限
        direct = db.query(Permission.resource_id).filter(
            Permission.user_id == current_user.id,
            Permission.resource_type == "folder",
        ).all()
        folder_paths.update(p[0] for p in direct)

        # 组权限
        user_group_ids_2 = [
            row[0] for row in db.query(GroupMember.group_id)
            .filter(GroupMember.user_id == current_user.id)
            .all()
        ]
        if user_group_ids_2:
            group_perms_2 = db.query(Permission.resource_id).filter(
                Permission.group_id.in_(user_group_ids_2),
                Permission.resource_type == "folder",
            ).all()
            folder_paths.update(p[0] for p in group_perms_2)

        if folder_paths:
            # 构建可导航树：授权文件夹 + 它们的祖先（供导航用）+ 它们的子孙（供查看用）
            # 例如：授权 path=/boarding/canadasite/en/employment-social-development
            # → 可导航的祖先：/boarding, /boarding/canadasite, /boarding/canadasite/en
            # → 直接可查看：该 path 及其子孙
            # 不可见：/boarding 下 OTHER 子文件夹（如 /boarding/other-app）
            ancestor_paths = set()
            for p in folder_paths:
                parts = p.strip("/").split("/")
                for i in range(1, len(parts)):
                    ancestor_paths.add("/" + "/".join(parts[:i]))

            # (A) 精确匹配祖先（导航用）
            # (B) 精确匹配授权路径 or 以授权路径 + "/" 开头（内容可见）
            # (A) AND (B) 都只匹配自己；防止 (A) 中的祖先把不相关子文件夹也带进来
            path_conditions = [Folder.path == ap for ap in ancestor_paths]
            path_conditions += [Folder.path == p for p in folder_paths]
            path_conditions += [Folder.path.startswith(p + "/") for p in folder_paths]
            query = query.filter(or_(*path_conditions))

    if path_starts_with:
        query = query.filter(Folder.path.startswith(path_starts_with))
    elif parent_folder_path is not None:
        query = query.filter(Folder.parent_folder_path == parent_folder_path)
    else:
        # Default: root folders for the specified app, or NULL parent (backward compat)
        if app_slug:
            query = query.filter(Folder.parent_folder_path == '/' + app_slug)
        else:
            # No app specified — only superusers can see all root folders
            query = query.filter(Folder.parent_folder_path == None)

    folders = query.order_by(Folder.order_index, Folder.name).offset(skip).limit(limit).all()
    return folders


def _ensure_folder_chain(db: Session, app, folder_path: str, current_user: User) -> Folder:
    """确保文件夹路径及其所有祖先都存在（自愈缺失的根/中间文件夹，修复 FK 违例）"""
    path = (folder_path or "").strip().rstrip('/')
    if not path or path == '/':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid folder path: {folder_path}")
    existing = db.query(Folder).filter(Folder.path == path).first()
    if existing:
        return existing
    if '/' not in path[1:]:
        # 应用根目录（如 /78431）：挂在全局根 / 下（若存在），否则 parent=NULL
        # 规则：parent_folder_path = path 去掉最后一个 /segment（2026-08-30 统一）
        root = db.query(Folder).filter(Folder.path == '/').first()
        parent = root if root else None
    else:
        parent = _ensure_folder_chain(db, app, path.rsplit('/', 1)[0], current_user)
    folder = Folder(
        name=path.rsplit('/', 1)[-1],
        title=path.rsplit('/', 1)[-1],
        path=path,
        app_id=app.id,
        parent_folder_path=parent.path if parent else None,
        created_by=current_user.username if current_user else "system",
    )
    db.add(folder)
    db.flush()
    return folder


@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建文件夹（基于路径层级）"""
    app = get_app_or_check_permission(str(folder_data.app_id), current_user, db, "write")

    # 解析父路径（缺失时自动补建祖先链，自愈 FK 违例）
    parent_path = folder_data.parent_folder_path or ('/' + app.slug)
    parent = _ensure_folder_chain(db, app, parent_path, current_user)

    # 检查同级同名冲突（基于归一化后的父路径）
    existing = db.query(Folder).filter(
        Folder.app_id == app.id,
        Folder.parent_folder_path == parent.path,
        Folder.name == folder_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder '{folder_data.name}' already exists at same level"
        )

    # 自动生成路径（客户端显式传 path 时保留，并确保其祖先链存在）
    if folder_data.path:
        path = folder_data.path
        anc = path.rstrip('/').rsplit('/', 1)[0]
        if anc and anc != parent.path:
            parent = _ensure_folder_chain(db, app, anc, current_user)
    else:
        path = f"{parent.path.rstrip('/')}/{folder_data.name}"

    folder = Folder(
        name=folder_data.name,
        title=folder_data.title or folder_data.name,
        path=path,
        description=folder_data.description,
        app_id=app.id,  # 存 UUID（客户端可能传 slug）
        parent_folder_path=parent.path,
        is_system_folder=folder_data.is_system_folder,
        order_index=folder_data.order_index,
        thumbnail_size=folder_data.thumbnail_size,
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
    """获取应用的文件夹树（支持 UUID 或 slug）"""
    # 先按 UUID 查，再按 slug 查
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        app = db.query(App).filter(App.slug == app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    # 权限检查
    if not current_user.is_superuser and app.owner_id != current_user.id:
        from app.models.permission import Permission
        has_perm = db.query(Permission).filter(
            Permission.resource_type == "app",
            Permission.resource_id == app.id,
            Permission.user_id == current_user.id,
        ).first()
        if not has_perm:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to access this app")

    all_folders = db.query(Folder).filter(Folder.app_id == app.id).all()

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
                is_system_folder=folder.is_system_folder if folder.is_system_folder is not None else False,
                order_index=folder.order_index if folder.order_index is not None else 0,
                created_by=folder.created_by,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
                updated_by=folder.updated_by,
                subfolders=subfolders,
                document_count=doc_count
            ))
        return result

    # Start from root folders (parent_folder_path = /{app.slug})
    return build_tree('/' + app.slug)


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
    if 'thumbnail_size' in update_data:
        folder.thumbnail_size = update_data['thumbnail_size']

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


@router.get("/effective-thumbnail-size")
def get_effective_thumbnail_size(
    path: str = Query(..., description="Folder path, e.g. /boarding/canadasite/fr/some-folder"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取文件夹的生效缩略图尺寸。
    如果文件夹自身设置了 thumbnail_size 则使用自身值，
    否则沿父链向上查找，直到找到非空值或到达根节点。
    默认值: "128x128"
    """
    folder = get_folder_or_404(path, db)
    check_folder_permission(folder, current_user, db)

    current_path = folder.path
    while current_path:
        f = db.query(Folder).filter(Folder.path == current_path).first()
        if f and f.thumbnail_size:
            return {"path": path, "thumbnail_size": f.thumbnail_size}
        # 向上走父路径
        if current_path == '/':
            break
        parent = current_path.rstrip('/').rsplit('/', 1)
        current_path = parent[0] if len(parent) > 1 and parent[0] else '/'

    return {"path": path, "thumbnail_size": "128x128"}


def _delete_storage_file(path: str):
    """Delete a single storage file by its relative path, silently skip missing."""
    if not path:
        return
    try:
        fp = Path(settings.DATA_ROOT) / path
        if fp.exists():
            fp.unlink()
            logging.info(f"Deleted storage file: {fp}")
    except Exception as e:
        logging.warning(f"Failed to delete storage file {path}: {e}")


def _recursive_delete(folder_path: str, db: Session):
    """递归删除文件夹及其下所有内容（DB + 存储文件）"""
    subfolders = db.query(Folder).filter(Folder.parent_folder_path == folder_path).all()
    for sf in subfolders:
        _recursive_delete(sf.path, db)

    # 删除该文件夹下所有文档（先删物理文件，再删DB记录）
    docs = db.query(Document).filter(Document.folder_path == folder_path).all()
    for doc in docs:
        _delete_storage_file(doc.storage_path)
        _delete_storage_file(doc.full_storage_path)
        _delete_storage_file(doc.converted_pdf_path)
        _delete_storage_file(doc.thumbnail_path)
        db.delete(doc)

    # 删除当前文件夹
    folder = db.query(Folder).filter(Folder.path == folder_path).first()
    if folder:
        db.delete(folder)


@router.get("/{folder_path:path}/children", response_model=List[FolderResponse])
def get_folder_children(
    folder_path: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
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
    """移动文件夹到另一父目录（递归更新所有子文件夹和文档路径）"""
    full_path = "/" + folder_path.lstrip("/")
    folder = get_folder_or_404(full_path, db)
    check_folder_permission(folder, current_user, db)

    target = get_folder_or_404(target_parent_path, db)
    check_folder_permission(target, current_user, db)

    if full_path == target_parent_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot move folder to itself")

    # 防止移动到自身子目录
    current = target
    while current and current.path != current.parent_folder_path:
        if current.path == full_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot move to own subfolder")
        if current.parent_folder_path:
            current = db.query(Folder).filter(Folder.path == current.parent_folder_path).first()
        else:
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

    old_path = folder.path
    new_path = f"{target_parent_path.rstrip('/')}/{folder.name}"

    # ── 用原始 SQL 批量更新 ─────────────────────────────────
    # 临时禁用 FK 触发器（PostgreSQL 语句级检查，跨表更新需关闭）
    db.execute(text("ALTER TABLE documents DISABLE TRIGGER ALL"))
    db.execute(text("ALTER TABLE folders DISABLE TRIGGER ALL"))
    try:
        # 更新文件夹（含自身 + 子文件夹的 path 和 parent_folder_path）
        db.execute(
            text("""
                UPDATE folders
                SET path = REPLACE(path, :old_path, :new_path),
                    parent_folder_path = CASE
                        WHEN path = :old_path_exact THEN :target_parent_path
                        ELSE REPLACE(parent_folder_path, :old_path, :new_path)
                    END,
                    updated_by = :updated_by
                WHERE path = :old_path_exact OR path LIKE :old_path_pattern
            """),
            {
                "old_path": old_path,
                "new_path": new_path,
                "target_parent_path": target_parent_path.rstrip('/'),
                "updated_by": current_user.username,
                "old_path_exact": old_path,
                "old_path_pattern": old_path + "/%",
            }
        )

        # 更新文档路径
        db.execute(
            text("""
                UPDATE documents
                SET path = REPLACE(path, :old_path, :new_path),
                    folder_path = REPLACE(folder_path, :old_path, :new_path)
                WHERE path = :old_path_exact OR path LIKE :old_path_pattern
                   OR folder_path = :old_path_exact OR folder_path LIKE :old_path_pattern
            """),
            {
                "old_path": old_path,
                "new_path": new_path,
                "old_path_exact": old_path,
                "old_path_pattern": old_path + "/%",
            }
        )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.execute(text("ALTER TABLE documents ENABLE TRIGGER ALL"))
        db.execute(text("ALTER TABLE folders ENABLE TRIGGER ALL"))

    # 重新查询返回更新后的文件夹
    moved = get_folder_or_404(new_path, db)
    return {"message": "Folder moved successfully", "folder": moved}


@router.post("/repair/parent-folder-paths")
def repair_parent_folder_paths(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """修复所有文件夹的 parent_folder_path（根据 path 重新计算）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin only")

    db.execute(text("ALTER TABLE folders DISABLE TRIGGER ALL"))
    try:
        result = db.execute(
            text("""
                UPDATE folders
                SET parent_folder_path = 
                    CASE
                        WHEN path = '/' THEN NULL
                        WHEN path ~ '^/[^/]+$' THEN '/'
                        ELSE regexp_replace(path, '/[^/]+$', '')
                    END,
                    updated_by = :updated_by
                WHERE parent_folder_path IS DISTINCT FROM
                    CASE
                        WHEN path = '/' THEN NULL
                        WHEN path ~ '^/[^/]+$' THEN '/'
                        ELSE regexp_replace(path, '/[^/]+$', '')
                    END
            """),
            {"updated_by": current_user.username}
        )
        db.commit()
        return {"message": "Repair completed", "fixed_count": result.rowcount}
    except Exception:
        db.rollback()
        raise
    finally:
        db.execute(text("ALTER TABLE folders ENABLE TRIGGER ALL"))
