"""Institution router - 部门/机构管理"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.institution import Institution
from app.schemas.institution import InstitutionCreate, InstitutionUpdate, InstitutionResponse

router = APIRouter()


@router.get("/", response_model=List[InstitutionResponse])
def get_institutions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取所有机构（需要登录）"""
    query = db.query(Institution).filter(Institution.is_active == True)
    # admin/superuser 看到所有，普通用户只看自己所在机构
    if not current_user.is_superuser and current_user.role != "admin":
        if current_user.institution_id:
            query = query.filter(Institution.id == current_user.institution_id)
        else:
            return []
    return query.offset(skip).limit(limit).all()


@router.get("/all", response_model=List[InstitutionResponse])
def get_all_institutions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取全部机构（含 inactive）- 仅 admin/superuser"""
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission")
    return db.query(Institution).all()


@router.get("/{institution_id}", response_model=InstitutionResponse)
def get_institution(
    institution_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取机构详情"""
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    # 非 admin 只能看自己的机构
    if not current_user.is_superuser and current_user.role != "admin":
        if current_user.institution_id != institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission")

    return inst


@router.post("/", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
def create_institution(
    data: InstitutionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建机构（仅 superuser）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superuser can create institutions")

    # 检查重复
    if db.query(Institution).filter(Institution.slug == data.slug).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Institution slug '{data.slug}' already exists")

    inst = Institution(**data.dict())
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@router.put("/{institution_id}", response_model=InstitutionResponse)
def update_institution(
    institution_id: str,
    data: InstitutionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新机构（仅 superuser）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superuser can update institutions")

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(inst, field, value)

    db.commit()
    db.refresh(inst)
    return inst


@router.delete("/{institution_id}")
def delete_institution(
    institution_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除机构（仅 superuser）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superuser can delete institutions")

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    # 检查是否有用户关联
    users_count = db.query(User).filter(User.institution_id == institution_id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {users_count} user(s) still belong to this institution. Reassign them first."
        )

    db.delete(inst)
    db.commit()
    return {"message": "Institution deleted successfully"}
