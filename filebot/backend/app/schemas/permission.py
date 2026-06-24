from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime
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


# Enum coercion helper — Pydantic v2 validates `str,Enum` by name by default,
# but the frontend sends the value (lowercase). This makes both work.
def _coerce_enum(v: Any, enum_cls: type) -> Any:
    """Try to coerce a string to an enum member by value, then by name."""
    if isinstance(v, enum_cls):
        return v
    if isinstance(v, str):
        # Try value first (e.g. "app" -> ResourceType.APP)
        for member in enum_cls:
            if member.value == v:
                return member
        # Try name (e.g. "APP" -> ResourceType.APP)
        try:
            return enum_cls[v.upper()]
        except (LookupError, KeyError):
            pass
    return v


# Permission 基础模型
class PermissionBase(BaseModel):
    """权限基础模型"""
    resource_type: ResourceType = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    permission_level: PermissionLevel = Field(..., description="权限级别")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @field_validator("resource_type", mode="before")
    @classmethod
    def coerce_resource_type(cls, v):
        return _coerce_enum(v, ResourceType)

    @field_validator("permission_level", mode="before")
    @classmethod
    def coerce_permission_level(cls, v):
        return _coerce_enum(v, PermissionLevel)


class PermissionCreate(PermissionBase):
    """权限创建模型 - 支持 user_id 或 group_id"""
    user_id: Optional[str] = Field(None, description="用户ID")
    group_id: Optional[str] = Field(None, description="组ID")


class PermissionUpdate(BaseModel):
    """权限更新模型"""
    permission_level: Optional[PermissionLevel] = Field(None, description="权限级别")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class PermissionResponse(PermissionBase):
    """权限响应模型"""
    id: str
    user_id: Optional[str] = None
    group_id: Optional[str] = None
    institution_id: Optional[str] = Field(None, description="所属机构ID（直接从 user/group 继承）")
    institution_name: Optional[str] = Field(None, description="所属机构名称")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 权限检查
class PermissionCheckRequest(BaseModel):
    """权限检查请求模型"""
    resource_type: ResourceType = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    required_level: PermissionLevel = Field(..., description="所需权限级别")

    @field_validator("resource_type", mode="before")
    @classmethod
    def coerce_resource_type(cls, v):
        return _coerce_enum(v, ResourceType)

    @field_validator("required_level", mode="before")
    @classmethod
    def coerce_required_level(cls, v):
        return _coerce_enum(v, PermissionLevel)


class PermissionCheckResponse(BaseModel):
    """权限检查响应模型"""
    has_permission: bool
    actual_level: Optional[PermissionLevel] = None
    message: Optional[str] = None


# 批量权限操作
class BatchPermissionCreate(BaseModel):
    """批量权限创建模型"""
    user_ids: list[str] = Field(..., min_items=1, description="用户ID列表")
    resource_type: ResourceType = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    permission_level: PermissionLevel = Field(..., description="权限级别")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @field_validator("resource_type", mode="before")
    @classmethod
    def coerce_resource_type(cls, v):
        return _coerce_enum(v, ResourceType)

    @field_validator("permission_level", mode="before")
    @classmethod
    def coerce_permission_level(cls, v):
        return _coerce_enum(v, PermissionLevel)


class BatchPermissionResponse(BaseModel):
    """批量权限响应模型"""
    created_count: int
    failed_users: list[str]
    errors: list[str]
