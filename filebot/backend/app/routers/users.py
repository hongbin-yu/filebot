from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.core.security import get_current_active_user, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.models.institution import Institution
from app.models.group import Group, GroupMember
from pydantic import BaseModel

router = APIRouter()


def _get_visible_user_query(current_user: User, db: Session):
    """返回当前用户可见的用户查询范围"""
    if current_user.is_superuser:
        return db.query(User)
    if current_user.institution_id:
        return db.query(User).filter(User.institution_id == current_user.institution_id)
    # 管理员但没有机构？只能看到自己
    return db.query(User).filter(User.id == current_user.id)


def _check_user_institution_access(target_user: User, current_user: User):
    """检查当前用户是否有权限操作目标用户"""
    if current_user.is_superuser:
        return True
    # admin 只能操作同机构用户
    if current_user.institution_id and target_user.institution_id == current_user.institution_id:
        return True
    # 操作自己（非管理员也可以）
    if str(current_user.id) == str(target_user.id):
        return True
    return False


@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user list - superuser sees all, admin sees own institution only"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission"
        )

    query = _get_visible_user_query(current_user, db)
    users = query.offset(skip).limit(limit).all()
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new user - superuser or admin only"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission"
        )

    # Check if username or email already exists
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    # Only superuser can create superusers; non-superuser admin gets institution auto-assigned
    if user_data.is_superuser and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create superuser accounts"
        )

    # Non-superuser admin: force their own institution
    institution_id = user_data.institution_id
    if not current_user.is_superuser:
        institution_id = current_user.institution_id

    # Non-superuser admin: cannot set role to admin or superuser
    role = user_data.role or "user"
    if not current_user.is_superuser and role in ("admin", "superuser"):
        role = "user"

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=user_data.is_superuser if current_user.is_superuser else False,
        role=role,
        institution_id=institution_id
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user info"""
    if str(current_user.id) != user_id and not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to view other user's info"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # admin 只能看同机构用户
    if not _check_user_institution_access(user, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission: user belongs to a different institution"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user info - superuser can edit any user, admin can edit own institution"""
    if str(current_user.id) != user_id and not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to update other user's info"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 非 superuser 的管理员只能编辑同机构用户
    if not current_user.is_superuser and str(current_user.id) != user_id:
        if not _check_user_institution_access(user, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission: user belongs to a different institution"
            )

    # 非 superuser 不允许修改 institution_id
    update_data = user_update.dict(exclude_unset=True)
    if not current_user.is_superuser:
        update_data.pop("institution_id", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete user (admin only, institution-scoped)"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission"
        )

    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not _check_user_institution_access(user, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission: user belongs to a different institution"
        )

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.put("/{user_id}/toggle-active", response_model=UserResponse)
def toggle_user_active(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Toggle user active/deactivated status (institution-scoped)"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not _check_user_institution_access(user, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission: user belongs to a different institution"
        )

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


# ========== User-to-Group endpoints ==========

class UserGroupInfo(BaseModel):
    """简化的组信息，用于返回用户所属的组"""
    id: str
    name: str

    class Config:
        from_attributes = True


@router.get("/{user_id}/groups", response_model=List[UserGroupInfo])
def get_user_groups(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取用户所属的所有组"""
    # 先查目标用户
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if not _check_user_institution_access(target_user, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission: user belongs to a different institution"
        )

    # 通过 group_members 关联查询用户所属的组
    groups = (
        db.query(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .filter(GroupMember.user_id == user_id)
        .all()
    )
    return groups
