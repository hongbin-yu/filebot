"""
Groups management routes — 用户组管理
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.group import Group, GroupMember
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== Schemas ==========

class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class MemberInfo(BaseModel):
    user_id: str
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True


class GroupResponse(GroupBase):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    member_count: int = 0

    class Config:
        from_attributes = True


class GroupDetailResponse(GroupResponse):
    members: List[MemberInfo] = []


class AddMemberRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: str = Field("member", pattern="^(admin|member)$")


# ========== Routes ==========

@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建用户组（仅 superuser 或 admin）"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superuser or admin can create groups"
        )

    # 检查重名
    existing = db.query(Group).filter(Group.name == group_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group '{group_data.name}' already exists"
        )

    group = Group(
        name=group_data.name,
        description=group_data.description,
        owner_id=current_user.id
    )
    db.add(group)
    db.flush()

    # 创建者自动成为组管理员
    member = GroupMember(
        group_id=group.id,
        user_id=current_user.id,
        role="admin"
    )
    db.add(member)
    db.commit()
    db.refresh(group)

    member_count = db.query(GroupMember).filter(GroupMember.group_id == group.id).count()
    return _to_response(group, member_count)


@router.get("/", response_model=List[GroupResponse])
def list_groups(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """列出所有用户组"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superuser or admin can list groups"
        )
    groups = db.query(Group).order_by(Group.name).all()
    results = []
    for g in groups:
        count = db.query(GroupMember).filter(GroupMember.group_id == g.id).count()
        results.append(_to_response(g, count))
    return results


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(
    group_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取组详情（含成员列表）"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can view groups")
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    members = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
    member_infos = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u:
            member_infos.append(MemberInfo(
                user_id=u.id, username=u.username, email=u.email, role=m.role
            ))

    member_count = len(member_infos)
    resp = _to_response(group, member_count)
    return GroupDetailResponse(**resp.model_dump(), members=member_infos)


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: str,
    group_data: GroupUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新组信息"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can update groups")
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if group_data.name is not None:
        # 检查重名
        existing = db.query(Group).filter(Group.name == group_data.name, Group.id != group_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Group '{group_data.name}' already exists")
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description

    db.commit()
    db.refresh(group)
    member_count = db.query(GroupMember).filter(GroupMember.group_id == group.id).count()
    return _to_response(group, member_count)


@router.delete("/{group_id}")
def delete_group(
    group_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除用户组"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can delete groups")
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    db.delete(group)
    db.commit()
    return {"message": "Group deleted successfully"}


@router.get("/{group_id}/members", response_model=List[MemberInfo])
def list_group_members(
    group_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """列出组成员"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can view group members")
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    members = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
    result = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u:
            result.append(MemberInfo(user_id=u.id, username=u.username, email=u.email, role=m.role))
    return result


@router.post("/{group_id}/members", response_model=MemberInfo, status_code=status.HTTP_201_CREATED)
def add_group_member(
    group_id: str,
    req: AddMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """添加组成员"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can manage group members")
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 检查是否已存在
    existing = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == req.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User is already a member of this group")

    member = GroupMember(
        group_id=group_id,
        user_id=req.user_id,
        role=req.role
    )
    db.add(member)
    db.commit()
    return MemberInfo(user_id=user.id, username=user.username, email=user.email, role=req.role)


@router.delete("/{group_id}/members/{user_id}")
def remove_group_member(
    group_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """移除组成员"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only superuser or admin can manage group members")
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in group")
    db.delete(member)
    db.commit()
    return {"message": "Member removed successfully"}


def _to_response(group: Group, member_count: int) -> GroupResponse:
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        owner_id=group.owner_id,
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=member_count
    )
