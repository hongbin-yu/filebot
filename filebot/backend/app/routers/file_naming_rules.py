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


# ========== Helper Functions ==========

def get_app_or_404(db: Session, app_id: uuid.UUID, current_user: User) -> App:
    """Get app, return 404 if not found or no permission"""
    app = db.query(App).filter(App.id == str(app_id)).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )
    
    # Check permission: admin or app owner
    if not current_user.is_superuser and str(app.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this app"
        )
    
    return app


def get_rule_or_404(db: Session, rule_id: uuid.UUID, app_id: uuid.UUID, current_user: User) -> FileNamingRule:
    """Get naming rule, return 404 if not found or no permission"""
    rule = db.query(FileNamingRule).filter(
        FileNamingRule.id == str(rule_id),
        FileNamingRule.app_id == str(app_id)
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Naming rule not found"
        )
    
    # Check app permission (via app)
    get_app_or_404(db, app_id, current_user)
    
    return rule


# ========== File Naming Rule Routes ==========

@router.get("/", response_model=List[FileNamingRuleResponse])
def get_file_naming_rules(
    app_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of file naming rules for an app"""
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
    """Create a new file naming rule"""
    app = get_app_or_404(db, app_id, current_user)
    
    # Check if rule with same basename already exists
    existing_rule = db.query(FileNamingRule).filter(
        FileNamingRule.app_id == str(app_id),
        FileNamingRule.basename == rule_data.basename
    ).first()
    
    if existing_rule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A naming rule with this prefix already exists for this app"
        )
    
    # Create new rule
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
    """Get a single file naming rule"""
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
    """Update a file naming rule"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    
    # Update fields
    update_data = rule_data.model_dump(exclude_unset=True)
    
    # Handle updater info
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
    """Delete a file naming rule"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    
    db.delete(rule)
    db.commit()
    
    return None


@router.get("/{rule_id}/next", response_model=FileNamingRuleWithNext)
def get_next_filename(
    app_id: uuid.UUID,
    rule_id: uuid.UUID,
    increment: bool = Query(False, description="Whether to increment sequence number (preview mode)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get next document number (optionally increment the sequence)"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    
    # Create response with next document number
    response = FileNamingRuleWithNext.from_orm_with_next(rule)
    
    # If increment is requested
    if increment:
        rule.max_number += rule.increment_by
        db.commit()
        db.refresh(rule)
        # Recreate response to reflect updated sequence
        response = FileNamingRuleWithNext.from_orm_with_next(rule)
    
    return response


@router.post("/{rule_id}/generate", response_model=FileNamingRuleWithNext)
def generate_filename(
    app_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate document number and increment sequence (for document upload)"""
    rule = get_rule_or_404(db, rule_id, app_id, current_user)
    
    # Generate current document number
    current_document_number = f"{rule.basename}{rule.max_number:04d}"
    
    # Increment sequence
    rule.max_number += rule.increment_by
    rule.updated_by = current_user.username
    
    db.commit()
    db.refresh(rule)
    
    # Create response
    response = FileNamingRuleWithNext.from_orm_with_next(rule)
    # Override to return the generated document number, not the next one
    response.next_document_number = current_document_number
    
    return response
