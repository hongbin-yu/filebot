from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
import enum


# 枚举类
class ResourceType(str, enum.Enum):
    APP = "app"
    DRAWER = "drawer"
    FOLDER = "folder"
    DOCUMENT = "document"


class PermissionLevel(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


# Permission 基础模型
class PermissionBase(BaseModel):
    """权限基础模型"""
    resource_type: ResourceType = Field(..., description="资源类型")
    resource_id: uuid.UUID = Field(..., description="资源ID")
    permission_level: PermissionLevel = Field(..., description="权限级别")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class PermissionCreate(PermissionBase):
    """权限创建模型"""
    user_id: uuid.UUID = Field(..., description="用户ID")


class PermissionUpdate(BaseModel):
    """权限更新模型"""
    permission_level: Optional[PermissionLevel] = Field(None, description="权限级别")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class PermissionResponse(PermissionBase):
    """权限响应模型"""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# 权限检查
class PermissionCheckRequest(BaseModel):
    """权限检查请求模型"""
    resource_type: ResourceType = Field(..., description="资源类型")
    resource_id: uuid.UUID = Field(..., description="资源ID")
    required_level: PermissionLevel = Field(..., description="所需权限级别")


class PermissionCheckResponse(BaseModel):
    """权限检查响应模型"""
    has_permission: bool
    actual_level: Optional[PermissionLevel] = None
    message: Optional[str] = None


# 批量权限操作
class BatchPermissionCreate(BaseModel):
    """批量权限创建模型"""
    user_ids: list[uuid.UUID] = Field(..., min_items=1, description="用户ID列表")
    resource_type: ResourceType = Field(..., description="资源类型")
    resource_id: uuid.UUID = Field(..., description="资源ID")
    permission_level: PermissionLevel = Field(..., description="权限级别")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class BatchPermissionResponse(BaseModel):
    """批量权限响应模型"""
    created_count: int
    failed_users: list[uuid.UUID]
    errors: list[str]