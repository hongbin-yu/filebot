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
from app.models.institution import Institution
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== Schemas ==========

class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    institution_id: Optional[str] = None


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    institution_id: Optional[str] = None


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
    institution_name: Optional[str] = None

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

    # 确定 institution_id
    inst_id = group_data.institution_id
    if not current_user.is_superuser:
        # admin 只能在自己的机构下创建组
        inst_id = current_user.institution_id
    elif inst_id:
        # superuser 指定机构，验证其存在
        inst = db.query(Institution).filter(Institution.id == inst_id).first()
        if not inst:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    group = Group(
        name=group_data.name,
        description=group_data.description,
        owner_id=current_user.id,
        institution_id=inst_id
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
    return _to_response(group, member_count, db)


@router.get("/", response_model=List[GroupResponse])
def list_groups(
    institution_id: Optional[str] = Query(None, description="Filter by institution (superuser only)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """列出用户组 — superuser 看全部，admin 只看本机构

    可选参数:
      institution_id: superuser 可用此参数按机构过滤
    """
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superuser or admin can list groups"
        )

    query = db.query(Group)

    # superuser 可以指定 institution_id 过滤
    if current_user.is_superuser and institution_id:
        query = query.filter(Group.institution_id == institution_id)
    elif not current_user.is_superuser and current_user.institution_id:
        query = query.filter(Group.institution_id == current_user.institution_id)

    groups = query.order_by(Group.name).all()
    results = []
    for g in groups:
        count = db.query(GroupMember).filter(GroupMember.group_id == g.id).count()
        results.append(_to_response(g, count, db))
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
    if not _check_group_institution_access(group, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No permission to view this group")

    members = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
    member_infos = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u:
            member_infos.append(MemberInfo(
                user_id=u.id, username=u.username, email=u.email, role=m.role
            ))

    member_count = len(member_infos)
    resp = _to_response(group, member_count, db)
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
    if not _check_group_institution_access(group, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No permission to update this group")

    if group_data.name is not None:
        existing = db.query(Group).filter(Group.name == group_data.name, Group.id != group_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Group '{group_data.name}' already exists")
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description
    if group_data.institution_id is not None and current_user.is_superuser:
        inst = db.query(Institution).filter(Institution.id == group_data.institution_id).first()
        if not inst:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
        group.institution_id = group_data.institution_id

    db.commit()
    db.refresh(group)
    member_count = db.query(GroupMember).filter(GroupMember.group_id == group.id).count()
    return _to_response(group, member_count, db)


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
    if not _check_group_institution_access(group, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No permission to delete this group")
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
    if not _check_group_institution_access(group, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No permission to view this group's members")

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
    if not _check_group_institution_access(group, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No permission to manage members of this group")

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
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not _check_group_institution_access(group, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No permission to manage members of this group")
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in group")
    db.delete(member)
    db.commit()
    return {"message": "Member removed successfully"}


def _check_group_institution_access(group: Group, current_user: User) -> bool:
    """检查当前用户是否有权限访问该组"""
    if current_user.is_superuser:
        return True
    # admin 只能操作本机构组
    if current_user.institution_id and group.institution_id == current_user.institution_id:
        return True
    return False


def _to_response(group: Group, member_count: int, db: Session = None) -> GroupResponse:
    inst_name = None
    if group.institution_id and db:
        inst = db.query(Institution).filter(Institution.id == group.institution_id).first()
        if inst:
            inst_name = inst.name

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        owner_id=group.owner_id,
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=member_count,
        institution_id=group.institution_id,
        institution_name=inst_name
    )
