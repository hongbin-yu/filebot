from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import uuid
import enum


# 枚举类
class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ConversionTask 基础模型
class ConversionTaskBase(BaseModel):
    """转换任务基础模型"""
    source_format: str = Field(..., max_length=20, description="源格式")
    target_format: str = Field(..., max_length=20, description="目标格式")
    status: Optional[TaskStatus] = Field(TaskStatus.QUEUED, description="任务状态")
    
    # 进度信息
    progress: Optional[int] = Field(0, ge=0, le=100, description="进度百分比")
    current_step: Optional[str] = Field(None, max_length=100, description="当前步骤描述")
    
    # 错误处理
    error_message: Optional[str] = Field(None, max_length=2000, description="错误信息")
    error_traceback: Optional[str] = Field(None, description="错误堆栈")
    
    # 系统信息
    worker_id: Optional[str] = Field(None, max_length=100, description="Worker ID")
    retry_count: Optional[int] = Field(0, ge=0, description="重试次数")


class ConversionTaskCreate(ConversionTaskBase):
    """转换任务创建模型"""
    document_id: uuid.UUID = Field(..., description="关联文档ID")


class ConversionTaskUpdate(BaseModel):
    """转换任务更新模型"""
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    progress: Optional[int] = Field(None, ge=0, le=100, description="进度百分比")
    current_step: Optional[str] = Field(None, max_length=100, description="当前步骤描述")
    
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    error_message: Optional[str] = Field(None, max_length=2000, description="错误信息")
    error_traceback: Optional[str] = Field(None, description="错误堆栈")
    
    worker_id: Optional[str] = Field(None, max_length=100, description="Worker ID")
    retry_count: Optional[int] = Field(None, ge=0, description="重试次数")


class ConversionTaskResponse(ConversionTaskBase):
    """转换任务响应模型"""
    id: uuid.UUID
    document_id: uuid.UUID
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# 文件上传相关
class FileUploadRequest(BaseModel):
    """文件上传请求模型"""
    folder_id: uuid.UUID = Field(..., description="目标文件夹ID")
    document_number: Optional[str] = Field(None, max_length=100, description="文档编号")
    title: Optional[str] = Field(None, max_length=255, description="文档标题")
    description: Optional[str] = Field(None, max_length=1000, description="文档描述")
    
    # 自动转换为PDF
    convert_to_pdf: Optional[bool] = Field(True, description="是否自动转换为PDF")


class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    document_id: uuid.UUID
    original_filename: str
    stored_filename: str
    file_size: int
    conversion_task_id: Optional[uuid.UUID] = None
    message: str


# 批量操作
class BatchConversionRequest(BaseModel):
    """批量转换请求模型"""
    document_ids: list[uuid.UUID] = Field(..., min_items=1, description="文档ID列表")
    target_format: str = Field("pdf", description="目标格式")


class BatchConversionResponse(BaseModel):
    """批量转换响应模型"""
    task_count: int
    queued_documents: list[uuid.UUID]
    failed_documents: list[uuid.UUID]