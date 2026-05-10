"""
导出相关Schema
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ExportOptions(BaseModel):
    """导出选项"""
    app_ids: Optional[List[str]] = Field(None, description="要导出的应用ID列表")
    folder_paths: Optional[List[str]] = Field(None, description="要导出的文件夹路径列表")
    include_documents: bool = Field(True, description="是否包含文档")
    include_metadata: bool = Field(True, description="是否包含元数据")
    recursive: bool = Field(True, description="是否递归包含子文件夹")
    format: str = Field("json", description="导出格式")
    compress: bool = Field(False, description="是否压缩")


class DocumentExport(BaseModel):
    """文档导出模型 — 用path替代UUID id"""
    path: Optional[str]
    title: Optional[str]
    description: Optional[str]
    document_number: Optional[str]
    status: Optional[str]
    type: Optional[str]
    comments: Optional[str]
    original_filename: Optional[str]
    stored_filename: Optional[str]
    file_size: Optional[int]
    file_type: Optional[str]
    mime_type: Optional[str]
    conversion_status: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[str]
    document_metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class FolderExport(BaseModel):
    """文件夹导出模型 — 用path替代UUID id"""
    name: str
    path: str
    title: Optional[str] = None
    description: Optional[str]
    app_id: str
    app_name: Optional[str]
    parent_folder_path: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[str]
    document_count: int
    documents: List[DocumentExport] = Field(default_factory=list)
    subfolders: List['FolderExport'] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class AppExport(BaseModel):
    """应用导出模型"""
    id: uuid.UUID
    name: str
    slug: Optional[str]
    description: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[str]
    settings: Optional[Dict[str, Any]]
    folders: List[FolderExport] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class FullExport(BaseModel):
    """完整导出模型"""
    export_time: datetime
    exported_by: Dict[str, Any]
    apps: List[AppExport]
    total_apps: int
    total_folders: int
    total_documents: int
    
    class Config:
        from_attributes = True


# 更新前向引用
FolderExport.update_forward_refs()