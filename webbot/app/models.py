"""
WebBot数据模型
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# 枚举定义
class PageStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class LanguageCode(str, Enum):
    EN = "en"
    FR = "fr"

class TaskType(str, Enum):
    CREATE_PAGE = "create_page"
    OPTIMIZE_PAGE = "optimize_page"
    REVIEW_PAGE = "review_page"
    DELETE_PAGE = "delete_page"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# 页面相关模型
class PageBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="页面标题")
    description: Optional[str] = Field(None, max_length=1000, description="页面描述")
    keywords: Optional[str] = Field(None, max_length=500, description="SEO关键词，逗号分隔")
    content: Optional[str] = Field(None, description="页面内容(HTML)")
    language: str = Field(default="en", description="语言代码")
    path: Optional[str] = Field(None, description="页面路径，如/canadasite/en/about。如果提供，将用作页面ID并从路径中推断语言")
    parent_path: Optional[str] = Field(None, description="父页面ID")
    other_language_path: Optional[str] = Field(None, description="其他语言对应页面路径")
    status: PageStatus = Field(PageStatus.DRAFT, description="页面状态")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    hide_in_navigation: bool = Field(False, description="是否在页面导航中隐藏")
    tags: List[str] = Field(default_factory=list, description="页面标签列表")

class PageCreate(PageBase):
    """创建页面请求模型"""
    file_path: Optional[str] = Field(None, description="FileBot存储图像的路径。如果为空，将从父页面继承。")

class PageUpdate(BaseModel):
    """更新页面请求模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    keywords: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    language: Optional[str] = None
    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    status: Optional[PageStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = Field(None, description="FileBot image storage path. If empty, inherits from ancestor pages.")
    hide_in_navigation: Optional[bool] = None
    publish_template: Optional[str] = Field(None, description="Page-level Mustache template path. If set, publish uses this single template instead of the default hardcoded assembly.")
    tags: Optional[List[str]] = None

class PageResponse(BaseModel):
    """页面响应模型（含内容全文）"""
    id: str
    title: str
    description: Optional[str] = None
    keywords: Optional[str] = None
    content: Optional[str] = None
    language: str = "en"
    path: Optional[str] = None
    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    file_path: Optional[str] = Field(None, description="FileBot image storage path. If empty, inherits from ancestor pages.")
    status: str = "draft"
    metadata: Optional[Dict[str, Any]] = None
    hide_in_navigation: bool = False
    publish_template: Optional[str] = Field(None, description="Page-level Mustache template path for publish")
    tags: List[str] = []
    created_by: Optional[str] = None
    created_at: datetime
    last_modified: datetime
    last_published: Optional[datetime] = None
    class Config:
        from_attributes = True


class PreviewRequest(BaseModel):
    """Page preview request - sends editor content for rendering"""
    content: Optional[str] = Field(None, description="Page content override (unsaved editor content)")


class PageListItem(BaseModel):
    """页面列表响应模型（不含内容全文，用于列表展示）"""
    id: str
    title: str
    description: Optional[str] = None
    keywords: Optional[str] = None
    language: str = "en"
    path: Optional[str] = None
    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    status: str = "draft"
    metadata: Optional[Dict[str, Any]] = None
    hide_in_navigation: bool = False
    publish_template: Optional[str] = Field(None, description="Page-level Mustache template path for publish")
    tags: List[str] = []
    created_by: Optional[str] = None
    created_at: datetime
    last_modified: datetime
    last_published: Optional[datetime] = None
    class Config:
        from_attributes = True


# AI任务相关模型
class AITaskBase(BaseModel):
    task_type: TaskType = Field(..., description="任务类型")
    page_id: Optional[str] = Field(None, description="关联页面ID")
    description: str = Field(..., description="任务描述")
    ai_model: Optional[str] = Field(None, description="AI模型名称")
    prompt: str = Field(..., description="AI提示词")

class AITaskCreate(AITaskBase):
    """创建AI任务请求模型"""
    pass

class AITaskResponse(AITaskBase):
    """AI任务响应模型"""
    id: str
    status: TaskStatus
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# AI请求模型
class AIRequest(BaseModel):
    """AI处理请求模型"""
    action: TaskType = Field(..., description="AI动作类型")
    content: str = Field(..., description="输入内容")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")
    model: Optional[str] = Field(None, description="指定AI模型")

class AIResponse(BaseModel):
    """AI处理响应模型"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None
class PagePropertiesResponse(BaseModel):
    """页面属性响应"""
    id: str
    title: str = ""
    description: str = ""
    language: str = "en"
    status: str = "draft"
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    published_at: Optional[str] = None
    other_language_path: Optional[str] = None
    available_languages: List[str] = []
    has_children: bool = False
    metadata: Optional[Dict[str, Any]] = None


class PageMetadataResponse(BaseModel):
    """页面层级元数据响应
    包含当前页面、机构层级页面和语言层级页面的信息
    """
    page: Optional[PageListItem] = None
    institution_level: Optional[PageListItem] = None
    language_level: Optional[PageListItem] = None
    path: str
    path_depth: int