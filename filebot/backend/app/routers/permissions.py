"""
Permissions management routes — 权限管理
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.permission import Permission, ResourceType, PermissionLevel
from app.schemas.permission import (
    PermissionCreate, PermissionResponse, PermissionCheckRequest,
    PermissionCheckResponse, BatchPermissionCreate
)
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(
    data: PermissionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建权限（支持 user_id 或 group_id）"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can manage permissions")

    if not data.user_id and not data.group_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Either user_id or group_id must be provided")

    if data.user_id:
        user = db.query(User).filter(User.id == data.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.group_id:
        group = db.query(Group).filter(Group.id == data.group_id).first()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    permission = Permission(
        user_id=data.user_id,
        group_id=data.group_id,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        permission_level=data.permission_level,
        expires_at=data.expires_at
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return _to_response(permission)


@router.delete("/{permission_id}")
def delete_permission(
    permission_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除权限"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can delete permissions")
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    db.delete(permission)
    db.commit()
    return {"message": "Permission deleted successfully"}


@router.get("/", response_model=List[PermissionResponse])
def list_permissions(
    resource_type: Optional[str] = Query(None, description="Filter by resource type (app/folder)"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    group_id: Optional[str] = Query(None, description="Filter by group ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """查询权限列表（可过滤）"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can view permissions")

    query = db.query(Permission)
    if resource_type:
        query = query.filter(Permission.resource_type == resource_type)
    if resource_id:
        query = query.filter(Permission.resource_id == resource_id)
    if user_id:
        query = query.filter(Permission.user_id == user_id)
    if group_id:
        query = query.filter(Permission.group_id == group_id)

    permissions = query.order_by(Permission.created_at.desc()).all()
    return [_to_response(p) for p in permissions]


@router.get("/users/{user_id}", response_model=List[PermissionResponse])
def get_user_permissions(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """查询用户所有权限（含通过组的）"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can view user permissions")

    # 1. 用户直接权限
    direct_perms = db.query(Permission).filter(Permission.user_id == user_id).all()

    # 2. 通过组的权限
    group_ids = [
        m.group_id for m in db.query(GroupMember).filter(GroupMember.user_id == user_id).all()
    ]
    group_perms = []
    if group_ids:
        group_perms = db.query(Permission).filter(
            Permission.group_id.in_(group_ids)
        ).all()

    # 合并去重（按 resource_type + resource_id + level 取最高级别）
    all_perms = direct_perms + group_perms
    seen = {}
    for p in all_perms:
        key = (p.resource_type.value, p.resource_id)
        if key not in seen or _level_weight(p.permission_level) > _level_weight(seen[key].permission_level):
            # 检查是否过期
            if p.expires_at and p.expires_at < datetime.now(p.expires_at.tzinfo):
                continue
            seen[key] = p

    return [_to_response(p) for p in seen.values()]


@router.post("/check", response_model=PermissionCheckResponse)
def check_permission(
    req: PermissionCheckRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """检查当前用户对某资源的权限"""
    has_perm, actual_level = _check_user_permission(db, current_user, req.resource_type.value, req.resource_id, req.required_level.value)
    return PermissionCheckResponse(
        has_permission=has_perm,
        actual_level=actual_level,
        message="Permission granted" if has_perm else "Insufficient permissions"
    )


def _level_weight(level: PermissionLevel) -> int:
    """权限级别权重"""
    weights = {
        PermissionLevel.READ: 1,
        PermissionLevel.WRITE: 2,
        PermissionLevel.ADMIN: 3,
        PermissionLevel.OWNER: 4,
    }
    return weights.get(level, 0)


def _check_user_permission(
    db: Session,
    user: User,
    resource_type: str,
    resource_id: str,
    required_level: str
) -> tuple[bool, Optional[str]]:
    """核心权限检查逻辑"""
    # 超级用户通通放行
    if user.is_superuser:
        return True, "owner"

    # 查找该资源的所有权限记录（含通配符 *）
    perms = db.query(Permission).filter(
        Permission.resource_type == resource_type,
        Permission.resource_id.in_([resource_id, "*"])
    ).all()

    # 当前用户所属的组ID
    user_group_ids = [
        m.group_id for m in db.query(GroupMember).filter(GroupMember.user_id == user.id).all()
    ]

    best_level = None
    for p in perms:
        # 检查过期
        if p.expires_at and p.expires_at < datetime.now(p.expires_at.tzinfo):
            continue

        # 检查是否匹配：直接用户权限 或 组权限
        if p.user_id == user.id:
            pass  # 直接用户匹配
        elif p.group_id and p.group_id in user_group_ids:
            pass  # 组权限匹配
        else:
            continue

        weight = _level_weight(p.permission_level)
        if best_level is None or weight > _level_weight(best_level):
            best_level = p.permission_level

    if best_level is not None:
        has = _level_weight(best_level) >= _level_weight(PermissionLevel(required_level))
        return has, best_level.value

    # 检查层级继承：如果是 folder，看是否有 app 级别的父级权限
    if resource_type == "folder":
        # resource_id 是 folder path，反查 app
        from app.models.folder import Folder
        folder = db.query(Folder).filter(Folder.path == resource_id).first()
        if folder and folder.app_id:
            return _check_user_permission(db, user, "app", folder.app_id, required_level)

    return False, None


def _to_response(p: Permission) -> PermissionResponse:
    return PermissionResponse(
        id=p.id,
        user_id=p.user_id,
        group_id=p.group_id,
        resource_type=p.resource_type,
        resource_id=p.resource_id,
        permission_level=p.permission_level,
        expires_at=p.expires_at,
        created_at=p.created_at,
        updated_at=p.updated_at
    )
