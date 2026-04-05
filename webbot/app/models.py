"""
WebBot数据模型
"""

from pydantic import BaseModel, Field
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
    language: LanguageCode = Field(LanguageCode.EN, description="语言代码")
    path: Optional[str] = Field(None, description="页面路径，如/canadasite/en/about。如果提供，将用作页面ID并从路径中推断语言")
    parent_id: Optional[str] = Field(None, description="父页面ID")
    other_lang_page_id: Optional[str] = Field(None, description="其他语言对应页面ID")
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
    language: Optional[LanguageCode] = None
    parent_id: Optional[str] = None
    other_lang_page_id: Optional[str] = None
    status: Optional[PageStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    hide_in_navigation: Optional[bool] = None
    tags: Optional[List[str]] = None

class PageResponse(PageBase):
    """页面响应模型"""
    id: str
    created_by: Optional[str]
    created_at: datetime
    last_modified: datetime
    last_published: Optional[datetime]
    
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