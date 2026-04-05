from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ImportSourceType(str, Enum):
    URL = "url"
    RSS = "rss"
    SITEMAP = "sitemap"
    BATCH = "batch"

class ImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PageStatus(str, Enum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    CONVERTED = "converted"
    SENT_TO_WEBBOT = "sent_to_webbot"
    SENT_TO_FILEBOT = "sent_to_filebot"
    FAILED = "failed"

# Request schemas
class ImportRequest(BaseModel):
    urls: List[HttpUrl] = Field(..., description="List of URLs to import")
    name: Optional[str] = Field(None, description="Optional name for this import job")
    source_type: ImportSourceType = ImportSourceType.URL
    target_system: str = Field("webbot", description="Target system: 'webbot' or 'filebot'")
    convert_to_markdown: bool = Field(True, description="Convert HTML to Markdown")
    preserve_images: bool = Field(True, description="Download and preserve images")
    
class SingleUrlImportRequest(BaseModel):
    url: HttpUrl
    name: Optional[str] = None
    target_system: str = "webbot"
    convert_to_markdown: bool = True
    preserve_images: bool = True

# Response schemas
class ImportedPageResponse(BaseModel):
    id: str
    source_url: str
    title: Optional[str]
    status: PageStatus
    extraction_error: Optional[str]
    webbot_page_id: Optional[str]
    webbot_page_url: Optional[str]
    filebot_file_id: Optional[str]
    filebot_file_path: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ImportJobResponse(BaseModel):
    id: str
    name: Optional[str]
    source_type: ImportSourceType
    status: ImportStatus
    total_urls: int
    successful_imports: int
    failed_imports: int
    errors: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    imported_pages: List[ImportedPageResponse] = []
    
    class Config:
        from_attributes = True

class ImportStatusResponse(BaseModel):
    job_id: str
    status: ImportStatus
    progress: float = Field(..., ge=0, le=100)
    message: Optional[str]
    details: Optional[Dict[str, Any]]

class WebBotPageCreate(BaseModel):
    """Schema for creating a page in WebBot"""
    title: str
    content: str
    language: str = "en"
    status: str = "draft"
    metadata: Optional[Dict[str, Any]] = None