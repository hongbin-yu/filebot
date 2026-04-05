from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import uuid

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.app import App
from app.models.file_naming_rule import FileNamingRule
from app.schemas.file_naming_rule import (
    FileNamingRuleCreate, FileNamingRuleResponse, FileNamingRuleUpdate,
    FileNamingRuleWithNext
)

router = APIRouter(prefix="/apps/{app_id}/file-naming-rules", tags=["file-naming-rules"])


# ========== 辅助函数 ==========

def get_app_or_404(db: Session, app_id: uuid.UUID, current_user: User) -> App:
    """获取应用，如果不存在或无权访问则返回404"""
    app = db.query(App).filter(App.id == str(app_id)).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="应用不存在"
        )
    
    # 检查权限：管理员或应用所有者
    if not current_user.is_superuser and str(app.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此应用"
        )
    
    return app


def get_rule_or_404(db: Session, rule_id: uuid.UUID, app_id: uuid.UUID, current_user: User) -> FileNamingRule:
    """获取命名规则，如果不存在或无权访问则返回404"""
    rule = db.query(FileNamingRule).filter(
        FileNamingRule.id == str(rule_id),
        FileNamingRule.app_id == str(app_id)
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="命名规则不存在"
        )
    
    # 检查应用权限（通过应用）
    get_app_or_404(db, app_id, current_user)
    
    return rule


# ========== 文件命名规则路由 ==========

@router.get("/", response_model=List[FileNamingRuleResponse])
def get_file_naming_rules(
    app_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取应用的文件命名规则列表"""
    app = get_app_or_404(db, app_id, current_user)
    
    rules = db.query(FileNamingRule).filter(
        FileNamingRule.app_id == str(app_id)
    ).offset(skip).limit(limit).all()
    
    return rules


@router.post("/", response_model=FileNamingRuleResponse, status_code=status.HTTP_201_CREATED)
def create_file_naming_rule(
    app_id: uuid.UUID,
    rule_data: FileNamingRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新的文件命名规则"""
    app = get_app_or_404(db, app_id, current_user)
    
    # 检查是否已存在相同basename的规则（可选，根据需求）
    existing_rule = db.query(FileNamingRule).filter(
        FileNamingRule.app_id == str(app_id),
        FileNamingRule.basename == rule_data.basename
    ).first()
    
    if existing_rule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此应用已存在相同前缀的命名规则"
        )
    
    # 创建新规则
    rule = FileNamingRule(
        **rule_data.model_dump(exclude={"app_id", "created_by"}),
        app_id=str(app_id),
        created_by=rule_data.created_by or current_user.username
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return rule


@router.get("/{rule_id}", response_model=FileNamingRuleResponse)
def get_file_naming_rule(
    app_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取单个文件命名规则"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    return rule


@router.put("/{rule_id}", response_model=FileNamingRuleResponse)
def update_file_naming_rule(
    app_id: uuid.UUID,
    rule_id: uuid.UUID,
    rule_data: FileNamingRuleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新文件命名规则"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    
    # 更新字段
    update_data = rule_data.model_dump(exclude_unset=True)
    
    # 处理更新者信息
    if update_data:
        update_data["updated_by"] = rule_data.updated_by or current_user.username
    
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    db.refresh(rule)
    
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_naming_rule(
    app_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除文件命名规则"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    
    db.delete(rule)
    db.commit()
    
    return None


@router.get("/{rule_id}/next", response_model=FileNamingRuleWithNext)
def get_next_filename(
    app_id: uuid.UUID,
    rule_id: uuid.UUID,
    increment: bool = Query(False, description="是否递增序列号（预览模式）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取下一个文档编号（可选择是否递增序列号）"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    
    # 创建响应（包含下一个文档编号）
    response = FileNamingRuleWithNext.from_orm_with_next(rule)
    
    # 如果请求递增序列号
    if increment:
        rule.max_number += rule.increment_by
        db.commit()
        db.refresh(rule)
        # 重新创建响应以反映更新后的序列号
        response = FileNamingRuleWithNext.from_orm_with_next(rule)
    
    return response


@router.post("/{rule_id}/generate", response_model=FileNamingRuleWithNext)
def generate_filename(
    app_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """生成文档编号并递增序列号（用于文档上传）"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    
    # 生成当前文档编号
    current_document_number = f"{rule.basename}{rule.max_number:04d}"
    
    # 递增序列号
    rule.max_number += rule.increment_by
    rule.updated_by = current_user.username
    
    db.commit()
    db.refresh(rule)
    
    # 创建响应
    response = FileNamingRuleWithNext.from_orm_with_next(rule)
    # 但这里需要返回生成的文档编号，不是下一个
    # 调整：手动设置next_document_number为生成的文档编号
    response.next_document_number = current_document_number
    
    return response