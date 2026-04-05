from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import uuid


# Token相关
class Token(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str
    user: Optional[dict] = None


class TokenData(BaseModel):
    """令牌数据"""
    username: Optional[str] = None


# 用户基础
class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")


class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("密码至少6个字符")
        # 可以添加更复杂的密码规则
        return v


class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """用户响应模型"""
    id: uuid.UUID
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """数据库中的用户模型"""
    password_hash: str


# 权限相关
class PermissionBase(BaseModel):
    """权限基础模型"""
    resource_type: str
    resource_id: uuid.UUID
    permission_level: str


class PermissionCreate(PermissionBase):
    """权限创建模型"""
    user_id: uuid.UUID


class PermissionResponse(PermissionBase):
    """权限响应模型"""
    id: uuid.UUID
    user_id: uuid.UUID
    expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True