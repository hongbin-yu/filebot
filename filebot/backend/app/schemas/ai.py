"""
AI相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class AIClassifyRequest(BaseModel):
    """AI分类请求"""
    document_id: Optional[str] = Field(None, description="文档ID")
    text: Optional[str] = Field(None, description="直接提供的文本内容")
    model: Optional[str] = Field("llama3.1:latest", description="Ollama模型名称")
    extract_text: bool = Field(True, description="是否从文档文件提取文本")
    
    class Config:
        schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "model": "llama3.1:latest"
            }
        }

class AICategoryResult(BaseModel):
    """AI分类结果"""
    category: str = Field(..., description="分类类别")
    ai_category: str = Field(..., description="AI分类类别")
    document_type: str = Field(..., description="对应的文档类型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    tags: Optional[List[str]] = Field(None, description="提取的标签")

class AIClassifyResponse(BaseModel):
    """AI分类响应"""
    document_id: Optional[str] = Field(None, description="文档ID")
    success: bool = Field(..., description="是否成功")
    category: Optional[str] = Field(None, description="分类类别")
    ai_category: Optional[str] = Field(None, description="AI分类类别")
    document_type: Optional[str] = Field(None, description="对应的文档类型")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度")
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")
    model: Optional[str] = Field(None, description="使用的模型")
    raw_response: Optional[str] = Field(None, description="原始响应文本")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="处理时间戳")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "category": "INVOICE",
                "ai_category": "INVOICE",
                "document_type": "invoice",
                "confidence": 0.85,
                "processing_time": 2.34,
                "model": "llama3.1:latest",
                "timestamp": "2026-03-20T10:00:00Z"
            }
        }

class AIBatchRequest(BaseModel):
    """批量AI处理请求"""
    document_ids: List[str] = Field(..., description="文档ID列表")
    operation: str = Field("classify", description="操作类型: classify, summarize, extract")
    model: Optional[str] = Field("llama3.1:latest", description="模型名称")

class AIBatchResponse(BaseModel):
    """批量AI处理响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, processing, completed, failed")
    document_count: int = Field(..., description="文档数量")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

class AIServiceStatus(BaseModel):
    """AI服务状态"""
    service: str = Field(..., description="服务名称")
    status: str = Field(..., description="状态: connected, disconnected, error")
    url: str = Field(..., description="服务URL")
    available_models: List[str] = Field(..., description="可用模型列表")
    default_model: str = Field(..., description="默认模型")
    last_check: datetime = Field(default_factory=datetime.now, description="最后检查时间")

class AIDocumentUpdate(BaseModel):
    """AI文档更新请求"""
    ai_category: Optional[str] = Field(None, description="AI分类类别")
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI分类置信度")
    ai_tags: Optional[List[str]] = Field(None, description="AI提取的标签")
    ai_summary: Optional[str] = Field(None, description="AI生成的摘要")
    
    class Config:
        schema_extra = {
            "example": {
                "ai_category": "INVOICE",
                "ai_confidence": 0.92,
                "ai_tags": ["发票", "增值税", "付款"],
                "ai_summary": "这是一张某某科技有限公司的增值税专用发票，金额为50,000元。"
            }
        }

class WebsiteCrawlRequest(BaseModel):
    """网站爬取请求"""
    url: str = Field(..., description="要爬取的网站URL")
    depth: int = Field(1, ge=1, le=10, description="爬取深度（1-10）")
    folder_path: str = Field(..., description="目标文件夹路径（如 /boarding/canadasite）")
    include_images: bool = Field(True, description="是否包含图像")
    follow_external_links: bool = Field(False, description="是否跟踪外部链接")
    respect_robots_txt: bool = Field(True, description="是否遵守robots.txt")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com",
                "depth": 2,
                "folder_path": "/boarding/canadasite",
                "include_images": True,
                "follow_external_links": False,
                "respect_robots_txt": True
            }
        }

class WebsiteCrawlResponse(BaseModel):
    """网站爬取响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, crawling, processing, completed, failed")
    url: str = Field(..., description="爬取的URL")
    depth: int = Field(..., description="爬取深度")
    estimated_pages: Optional[int] = Field(None, description="预估页面数量")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    message: Optional[str] = Field(None, description="状态消息")
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "crawl_123e4567",
                "status": "pending",
                "url": "https://example.com",
                "depth": 2,
                "estimated_pages": 50,
                "started_at": "2026-03-29T14:30:00Z",
                "message": "网站爬取任务已开始"
            }
        }

class WebsiteCrawlStatus(BaseModel):
    """网站爬取状态"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    url: str = Field(..., description="爬取的URL")
    depth: int = Field(..., description="爬取深度")
    pages_crawled: int = Field(0, description="已爬取页面数")
    pages_processed: int = Field(0, description="已处理页面数")
    images_crawled: int = Field(0, description="已爬取图像数")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    started_at: datetime = Field(..., description="开始时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "crawl_123e4567",
                "status": "crawling",
                "url": "https://example.com",
                "depth": 2,
                "pages_crawled": 25,
                "pages_processed": 15,
                "images_crawled": 8,
                "errors": ["https://example.com/private-page: 403 Forbidden"],
                "started_at": "2026-03-29T14:30:00Z",
                "updated_at": "2026-03-29T14:32:00Z",
                "estimated_completion": "2026-03-29T14:45:00Z"
            }
        }


class WebsiteCrawlTaskList(BaseModel):
    """网站爬取任务列表响应"""
    tasks: List[WebsiteCrawlStatus] = Field(default_factory=list, description="任务列表")
    total: int = Field(0, description="总任务数")
    pending: int = Field(0, description="等待中的任务数")
    active: int = Field(0, description="活动中的任务数（crawling + processing）")
    completed: int = Field(0, description="已完成的任务数")
    failed: int = Field(0, description="失败的任务数")
    
    class Config:
        schema_extra = {
            "example": {
                "tasks": [
                    {
                        "task_id": "crawl_123e4567",
                        "status": "crawling",
                        "url": "https://example.com",
                        "depth": 2,
                        "pages_crawled": 25,
                        "pages_processed": 15,
                        "images_crawled": 8,
                        "errors": [],
                        "started_at": "2026-03-29T14:30:00Z",
                        "updated_at": "2026-03-29T14:32:00Z"
                    },
                    {
                        "task_id": "crawl_abcdef12",
                        "status": "completed",
                        "url": "https://example.org",
                        "depth": 1,
                        "pages_crawled": 10,
                        "pages_processed": 10,
                        "images_crawled": 5,
                        "errors": [],
                        "started_at": "2026-03-29T13:00:00Z",
                        "updated_at": "2026-03-29T13:10:00Z"
                    }
                ],
                "total": 2,
                "pending": 0,
                "active": 1,
                "completed": 1,
                "failed": 0
            }
        }


class SitemapImportRequest(BaseModel):
    """Sitemap 导入请求"""
    sitemap_url: str = Field(..., description="Sitemap.xml 的 URL")
    folder_path: str = Field(..., description="目标文件夹路径（如 /boarding/canadasite）")
    include_images: bool = Field(True, description="是否包含图像")
    depth: int = Field(0, ge=0, le=10, description="递归爬取深度（0=只抓sitemap页，1=抓子链接，2=再往下一层）")
    
    class Config:
        schema_extra = {
            "example": {
                "sitemap_url": "https://www.canada.ca/sitemap.xml",
                "folder_path": "/boarding/canadasite",
                "include_images": True,
                "depth": 1
            }
        }


class SitemapImportResponse(BaseModel):
    """Sitemap 导入响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    sitemap_url: str = Field(..., description="Sitemap URL")
    depth: int = Field(0, description="递归爬取深度")
    total_urls: Optional[int] = Field(None, description="Sitemap 中的 URL 总数")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    message: Optional[str] = Field(None, description="状态消息")
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "sitemap_123e4567",
                "status": "pending",
                "sitemap_url": "https://www.canada.ca/sitemap.xml",
                "total_urls": 4200,
                "started_at": "2026-04-27T17:00:00Z",
                "message": "Sitemap 导入任务已开始"
            }
        }