from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


# App 基础模型
class AppBase(BaseModel):
    """应用基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="应用名称")
    slug: Optional[str] = Field(None, max_length=120, description="URL友好标识符")
    description: Optional[str] = Field(None, max_length=500, description="应用描述")
    settings: Optional[dict] = Field(default_factory=dict, description="应用设置")
    redirect_url: Optional[str] = Field(None, max_length=500, description="重定向URL，用于集成外部应用")
    icon: Optional[str] = Field(None, max_length=200, description="图标URL或图标名称")


class AppCreate(AppBase):
    """应用创建模型"""
    owner_id: uuid.UUID = Field(..., description="所有者用户ID")
    created_by: Optional[str] = Field(None, description="创建者用户名")


class AppUpdate(BaseModel):
    """应用更新模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="应用名称")
    slug: Optional[str] = Field(None, max_length=120, description="URL友好标识符")
    description: Optional[str] = Field(None, max_length=500, description="应用描述")
    settings: Optional[dict] = Field(None, description="应用设置")
    redirect_url: Optional[str] = Field(None, max_length=500, description="重定向URL，用于集成外部应用")
    icon: Optional[str] = Field(None, max_length=200, description="图标URL或图标名称")
    updated_by: Optional[str] = Field(None, description="更新者用户名")


class AppResponse(AppBase):
    """应用响应模型"""
    id: uuid.UUID
    owner_id: uuid.UUID
    created_by: Optional[str]
    updated_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Folder 基础模型 (无抽屉层，直接关联应用)
class FolderResponse(BaseModel):
    """文件夹响应模型（纯path架构）"""
    app_id: str = Field(..., description="所属应用ID")
    name: str = Field(..., description="文件夹名称")
    title: Optional[str] = Field(None, description="文件夹标题")
    path: str = Field(..., max_length=500, description="文件夹路径（PK）")
    parent_folder_path: Optional[str] = Field(None, max_length=500, description="父文件夹路径")
    description: Optional[str] = Field(None, max_length=500, description="文件夹描述")
    app_slug: Optional[str] = Field(None, max_length=120, description="应用slug标识符")
    app_path: Optional[str] = Field(None, max_length=500, description="应用根路径，如'/test-admin'")
    created_by: Optional[str]
    updated_by: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    document_count: Optional[int] = Field(0, description="文件夹中的文档数量")
    
    class Config:
        from_attributes = True