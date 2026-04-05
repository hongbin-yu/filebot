from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import enum


class DeviceType(str, enum.Enum):
    """设备类型枚举（兼容旧系统dev_type）"""
    STORAGE = "storage"          # 主存储设备
    RECYCLE_BIN = "recycle_bin"  # 回收站（对应旧系统类型1）
    ARCHIVE = "archive"          # 归档存储
    BACKUP = "backup"            # 备份存储
    TEMPORARY = "temporary"      # 临时存储


class DeviceStatus(str, enum.Enum):
    """设备状态枚举（基于容量使用情况）"""
    NORMAL = "normal"      # 正常 (< warning_threshold)
    WARNING = "warning"    # 警告 (>= warning_threshold)
    FULL = "full"          # 已满 (>= 100% 或手动标记)


# ========== 基础模型 ==========

class DeviceBase(BaseModel):
    """设备基础模型"""
    name: str = Field(..., max_length=255, description="设备名称")
    description: Optional[str] = Field(None, max_length=500, description="设备描述")
    path: Optional[str] = Field(None, max_length=500, description="存储路径（用于自动容量检测）")
    type: DeviceType = Field(default=DeviceType.STORAGE, description="设备类型")
    is_active: bool = Field(default=True, description="是否激活")
    
    # 容量配置
    capacity_mb: int = Field(default=0, ge=0, description="总容量（MB），0表示未知/自动检测")
    warning_threshold: int = Field(default=90, ge=0, le=100, description="警告阈值百分比（0-100）")
    
    # 优先级
    priority: int = Field(default=1, ge=1, le=10, description="优先级（1-10，空间分配时使用）")
    
    # 配置信息
    config: Optional[Dict[str, Any]] = Field(None, description="配置信息（JSON格式）")
    
    @validator('path')
    def validate_path(cls, v):
        """验证路径格式（如果提供）"""
        if v is not None and v.strip() == "":
            return None
        return v


# ========== 创建/更新模型 ==========

class DeviceCreate(DeviceBase):
    """设备创建模型"""
    created_by: Optional[str] = Field(None, description="创建者用户名")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "主存储设备",
                "description": "公司文件主存储",
                "path": "/data/storage",
                "type": DeviceType.STORAGE,
                "capacity_mb": 102400,  # 100GB
                "warning_threshold": 85,
                "priority": 1,
                "is_active": True
            }
        }


class DeviceUpdate(BaseModel):
    """设备更新模型"""
    name: Optional[str] = Field(None, max_length=255, description="设备名称")
    description: Optional[str] = Field(None, max_length=500, description="设备描述")
    path: Optional[str] = Field(None, max_length=500, description="存储路径")
    type: Optional[DeviceType] = Field(None, description="设备类型")
    is_active: Optional[bool] = Field(None, description="是否激活")
    
    # 容量配置
    capacity_mb: Optional[int] = Field(None, ge=0, description="总容量（MB）")
    used_mb: Optional[int] = Field(None, ge=0, description="已使用容量（MB）")
    warning_threshold: Optional[int] = Field(None, ge=0, le=100, description="警告阈值百分比")
    
    # 优先级
    priority: Optional[int] = Field(None, ge=1, le=10, description="优先级")
    
    # 配置信息
    config: Optional[Dict[str, Any]] = Field(None, description="配置信息")
    
    updated_by: Optional[str] = Field(None, description="更新者用户名")
    
    @validator('path')
    def validate_path(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v


# ========== 响应模型 ==========

class DeviceResponse(DeviceBase):
    """设备响应模型（包含ID和状态信息）"""
    id: uuid.UUID = Field(..., description="设备ID")
    status: DeviceStatus = Field(..., description="设备状态")
    used_mb: int = Field(..., ge=0, description="已使用容量（MB）")
    
    # 容量信息
    usage_percentage: float = Field(..., ge=0.0, le=100.0, description="使用百分比")
    available_mb: int = Field(..., ge=0, description="可用容量（MB）")
    
    # 审计字段
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    created_by: Optional[str] = Field(None, description="创建者")
    updated_by: Optional[str] = Field(None, description="更新者")
    
    class Config:
        orm_mode = True


class DeviceWithCapacityInfo(DeviceResponse):
    """包含详细容量信息的设备响应"""
    capacity_info: Dict[str, Any] = Field(..., description="容量详细信息")
    status_message: str = Field(..., description="状态提示消息")
    
    class Config:
        orm_mode = True


class DeviceStatusResponse(BaseModel):
    """设备状态响应（用于容量检测和提示）"""
    device_id: uuid.UUID = Field(..., description="设备ID")
    device_name: str = Field(..., description="设备名称")
    status: DeviceStatus = Field(..., description="设备状态")
    
    # 容量信息
    used_mb: int = Field(..., description="已使用容量（MB）")
    capacity_mb: int = Field(..., description="总容量（MB）")
    usage_percentage: float = Field(..., description="使用百分比")
    available_mb: int = Field(..., description="可用容量（MB）")
    
    # 阈值信息
    warning_threshold: int = Field(..., description="警告阈值")
    is_near_threshold: bool = Field(..., description="是否接近阈值")
    threshold_difference: float = Field(..., description="距离阈值的百分比差")
    
    # 提示信息
    status_message: str = Field(..., description="状态提示消息")
    suggestion: Optional[str] = Field(None, description="建议操作")
    
    class Config:
        orm_mode = True


# ========== 容量检测模型 ==========

class CapacityDetectionRequest(BaseModel):
    """容量检测请求模型"""
    device_ids: Optional[list[uuid.UUID]] = Field(None, description="设备ID列表，为空则检测所有设备")
    force_update: bool = Field(default=False, description="是否强制重新检测路径容量")


class CapacityDetectionResponse(BaseModel):
    """容量检测响应模型"""
    total_devices: int = Field(..., description="总设备数")
    devices_checked: int = Field(..., description="已检查设备数")
    devices_updated: int = Field(..., description="已更新设备数")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    results: list[DeviceStatusResponse] = Field(default_factory=list, description="检测结果")


class StorageAllocationRequest(BaseModel):
    """存储分配请求模型"""
    file_size_mb: int = Field(..., gt=0, description="文件大小（MB）")
    preferred_device_id: Optional[uuid.UUID] = Field(None, description="首选设备ID")
    require_capacity_check: bool = Field(default=True, description="是否要求容量检查")


class StorageAllocationResponse(BaseModel):
    """存储分配响应模型"""
    allocated: bool = Field(..., description="是否分配成功")
    device_id: Optional[uuid.UUID] = Field(None, description="分配的设备ID")
    device_name: Optional[str] = Field(None, description="设备名称")
    available_mb: Optional[int] = Field(None, description="分配后剩余容量（MB）")
    message: str = Field(..., description="分配结果消息")
    warning: Optional[str] = Field(None, description="警告信息（如果接近阈值）")