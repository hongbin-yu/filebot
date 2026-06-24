"""Institution schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class InstitutionBase(BaseModel):
    """部门基础模型"""
    name: str = Field(..., min_length=1, max_length=200, description="机构名称")
    slug: str = Field(..., min_length=1, max_length=100, description="机构缩写")
    description: Optional[str] = Field(None, description="描述")
    domain: Optional[str] = Field(None, max_length=200, description="域名")


class InstitutionCreate(InstitutionBase):
    """部门创建模型"""
    pass


class InstitutionUpdate(BaseModel):
    """部门更新模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    domain: Optional[str] = None
    is_active: Optional[bool] = None


class InstitutionResponse(InstitutionBase):
    """部门响应模型"""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
