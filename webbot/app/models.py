"""WebBot Pydantic models"""
from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# AI models
# ============================================================================

class TaskType(str, Enum):
    create = "create"
    optimize = "optimize"
    review = "review"
    delete = "delete"

class TaskStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class AIRequest(BaseModel):
    prompt: str
    page_id: Optional[str] = None

class AIResponse(BaseModel):
    result: str
    page_id: Optional[str] = None
    task_id: Optional[str] = None

class AITaskCreate(BaseModel):
    task_type: TaskType
    page_id: str
    description: str = ""
    prompt: Optional[str] = None

class AITaskResponse(BaseModel):
    id: str
    task_type: str
    page_id: str
    description: str = ""
    status: str = "pending"
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


# ============================================================================
# Tag models
# ============================================================================

class TagCreate(BaseModel):
    """创建标签"""
    id: str
    title_en: str = ""
    title_fr: str = ""
    type: str = "subject"  # subject | audience
    parent_id: Optional[str] = None
    path: str = ""
    parent_path: Optional[str] = None
    description: str = ""
    description_fr: str = ""


class TagUpdate(BaseModel):
    """更新标签"""
    title_en: Optional[str] = None
    title_fr: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[str] = None
    path: Optional[str] = None
    parent_path: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    label_fr: Optional[str] = None  # legacy compat


class TagResponse(BaseModel):
    """标签响应"""
    id: str
    title_en: str = ""
    title_fr: str = ""
    type: str = "subject"
    parent_id: Optional[str] = None
    path: str = ""
    parent_path: Optional[str] = None
    description: str = ""
    description_fr: str = ""
    created_at: Optional[str] = None
    children_count: int = 0  # 子标签数量
    page_count: int = 0       # 关联页面数量
    label_fr: str = ""  # legacy compat


# ============================================================================
# Page models
# ============================================================================

class PageCreate(BaseModel):
    """Page creation request"""
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    keywords: Optional[str] = None
    content: Optional[str] = None
    language: str = "en"
    path: Optional[str] = None
    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    status: str = "draft"
    metadata: Optional[Dict[str, Any]] = None
    hide_in_navigation: bool = False
    navigation_title: Optional[str] = None
    file_path: Optional[str] = None
    publish_template: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="页面标签列表")
    skip_if_exists: bool = False


class PageUpdate(BaseModel):
    """Page update request"""
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    path: Optional[str] = None
    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    file_path: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    hide_in_navigation: Optional[bool] = None
    navigation_title: Optional[str] = None
    publish_template: Optional[str] = None
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

    @computed_field
    @property
    def canada_ca_url(self) -> Optional[str]:
        """Relative Canada.ca path by stripping /canadasite prefix"""
        if self.path and self.path.startswith('/canadasite'):
            return self.path[len('/canadasite'):]
        return None

    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    file_path: Optional[str] = Field(None, description="FileBot image storage path. If empty, inherits from ancestor pages.")
    status: str = "draft"
    metadata: Optional[Dict[str, Any]] = None
    hide_in_navigation: bool = False
    navigation_title: Optional[str] = None
    publish_template: Optional[str] = Field(None, description="Page-level Mustache template path for publish")
    tags: List[str] = []
    created_by: Optional[str] = None
    created_at: datetime
    last_modified: datetime
    last_published: Optional[datetime] = None
    out_of_sync: bool = Field(False, description="True if this page was modified after its linked other-language page")
    is_republish: Optional[bool] = Field(None, description="True if last_modified > last_published (page edited after last publish, needs republish)")
    class Config:
        from_attributes = True


class PreviewRequest(BaseModel):
    """Page preview request - sends editor content for rendering"""
    content: Optional[str] = Field(None, description="Page content override (unsaved editor content)")


class PagePropertiesResponse(BaseModel):
    """页面属性响应"""
    id: str
    title: str = ""
    description: Optional[str] = ""
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
    publish_template: Optional[str] = None
    tags: List[str] = []
    redirect_to: Optional[str] = Field(None, description="Redirect target URL from metadata")
    out_of_sync: bool = Field(False, description="True if this page was modified after its linked other-language page")


class PageListItem(BaseModel):
    """Page list item model"""
    id: str
    title: str = ""
    description: Optional[str] = ""
    language: str = "en"
    status: str = "draft"
    path: Optional[str] = None

    @computed_field
    @property
    def canada_ca_url(self) -> Optional[str]:
        """Relative Canada.ca path by stripping /canadasite prefix"""
        if self.path and self.path.startswith('/canadasite'):
            return self.path[len('/canadasite'):]
        return None

    @computed_field
    @property
    def other_language_url(self) -> Optional[str]:
        """Public URL of the linked other-language page (Canada.ca relative path)."""
        if not self.other_language_path:
            return None
        if self.other_language_path.startswith('/canadasite'):
            return self.other_language_path[len('/canadasite'):]
        return self.other_language_path

    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    has_children: bool = False
    hide_in_navigation: bool = False
    navigation_title: Optional[str] = None
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    last_published: Optional[str] = None
    tags: List[str] = []
    lock_status: Optional[str] = None
    redirectTo: Optional[str] = Field(None, description="Redirect target URL if page has redirect_to in metadata")
    out_of_sync: bool = Field(False, description="True if this page was modified after its linked other-language page")
    is_republish: Optional[bool] = Field(None, description="True if last_modified > last_published (page edited after last publish, needs republish)")

    @computed_field
    @property
    def isPublished(self) -> bool:
        return self.status == 'published'


class PageMetadataItem(BaseModel):
    """Page metadata item - all page fields except content"""
    id: str
    title: str = ""
    description: Optional[str] = None
    keywords: Optional[str] = None
    language: str = "en"
    path: Optional[str] = None
    parent_path: Optional[str] = None
    other_language_path: Optional[str] = None
    file_path: Optional[str] = None
    status: str = "draft"
    metadata: Optional[Dict[str, Any]] = None
    hide_in_navigation: bool = False
    navigation_title: Optional[str] = None
    publish_template: Optional[str] = None
    tags: List[str] = []
    subjects: Optional[str] = None  # ;-separated dcterms.subject values
    audience: Optional[str] = None  # ;-separated dcterms.audience values
    type: Optional[str] = None      # single dcterms.type value
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    last_modified: Optional[str] = None
    last_published: Optional[str] = None


class PageMetadataResponse(BaseModel):
    """页面层级元数据响应
    包含当前页面、机构层级页面和语言层级页面的信息
    """
    page: Optional[PageMetadataItem] = None
    institution_level: Optional[PageMetadataItem] = None
    language_level: Optional[PageMetadataItem] = None
    path: str = ""
    path_depth: int = 0


class PageStatus(BaseModel):
    id: str
    status: str = "draft"
    path: Optional[str] = None
    parent_path: Optional[str] = None
    title: Optional[str] = None
