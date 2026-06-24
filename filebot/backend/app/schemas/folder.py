"""Folder schemas"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class FolderCreate(BaseModel):
    app_id: str
    name: str
    path: str
    parent_folder_path: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    is_system_folder: bool = False
    order_index: int = 0
    thumbnail_size: Optional[str] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    parent_folder_path: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    is_system_folder: Optional[bool] = None
    order_index: Optional[int] = None
    thumbnail_size: Optional[str] = None


class FolderResponse(BaseModel):
    app_id: str
    name: str
    title: Optional[str] = None
    path: str
    parent_folder_path: Optional[str] = None
    description: Optional[str] = None
    is_system_folder: Optional[bool] = False
    order_index: Optional[int] = None
    thumbnail_size: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    @field_validator('is_system_folder', mode='before')
    @classmethod
    def default_is_system_folder(cls, v):
        return v if v is not None else False

    @field_validator('order_index', mode='before')
    @classmethod
    def default_order_index(cls, v):
        return v if v is not None else 0

    class Config:
        from_attributes = True


class FolderTreeResponse(FolderResponse):
    subfolders: List["FolderTreeResponse"] = []
    document_count: int = 0
