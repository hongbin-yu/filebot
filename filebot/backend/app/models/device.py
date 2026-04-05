from sqlalchemy import Column, DateTime, String, Integer, BigInteger, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import uuid
import enum
import os
import shutil

from ..db.database import Base


class DeviceType(enum.Enum):
    """设备类型枚举（兼容旧系统dev_type）"""
    STORAGE = "storage"          # 主存储设备
    RECYCLE_BIN = "recycle_bin"  # 回收站（对应旧系统类型1）
    ARCHIVE = "archive"          # 归档存储
    BACKUP = "backup"            # 备份存储
    TEMPORARY = "temporary"      # 临时存储


class DeviceStatus(enum.Enum):
    """设备状态枚举（基于容量使用情况）"""
    NORMAL = "normal"      # 正常 (< warning_threshold)
    WARNING = "warning"    # 警告 (>= warning_threshold)
    FULL = "full"          # 已满 (>= 100% 或手动标记)


class Device(Base):
    """设备表 (Device) - 存储空间管理，对应旧系统device表"""
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 设备基本信息
    name = Column(String(255), nullable=False, index=True)  # 设备名称
    description = Column(String(500), nullable=True)         # 设备描述
    path = Column(String(500), nullable=True)                # 存储路径（可选，用于自动容量检测）
    
    # 设备类型和状态
    type = Column(String(50), nullable=False, default="storage")
    status = Column(String(50), nullable=False, default="normal")
    is_active = Column(Boolean, nullable=False, default=True)  # 是否激活
    
    # 容量信息（单位：MB）
    capacity_mb = Column(Integer, nullable=False, default=0)    # 总容量，0表示未知/自动检测
    used_mb = Column(Integer, nullable=False, default=0)        # 已使用容量
    warning_threshold = Column(Integer, nullable=False, default=90)  # 警告阈值百分比（0-100）
    
    # 优先级和配置
    priority = Column(Integer, nullable=False, default=1)       # 优先级（空间分配时使用）
    config = Column(String(1000), nullable=True)                # 配置信息（JSON格式）
    
    # 审计字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    
    # 关系
    documents = relationship("Document", back_populates="device")  # 后续添加
    
    def __repr__(self):
        return f"<Device(id={self.id}, name={self.name}, type={self.type}, used={self.used_mb}/{self.capacity_mb}MB)>"
    
    # ========== 字段验证器 ==========
    
    @validates('type')
    def validate_type(self, key, value):
        """验证设备类型值"""
        valid_types = {e.value for e in DeviceType}
        if value not in valid_types:
            raise ValueError(f"无效的设备类型: {value}，有效值: {valid_types}")
        return value
    
    @validates('status')
    def validate_status(self, key, value):
        """验证设备状态值"""
        valid_statuses = {e.value for e in DeviceStatus}
        if value not in valid_statuses:
            raise ValueError(f"无效的设备状态: {value}，有效值: {valid_statuses}")
        return value
    
    # ========== 容量检测方法 ==========
    
    def get_usage_percentage(self) -> float:
        """
        获取使用百分比
        """
        if self.capacity_mb <= 0:
            return 0.0
        return (self.used_mb / self.capacity_mb) * 100.0
    
    def get_available_mb(self) -> int:
        """
        获取可用容量（MB）
        """
        if self.capacity_mb <= 0:
            return 0
        return max(0, self.capacity_mb - self.used_mb)
    
    def check_capacity_status(self) -> str:
        """
        检查容量状态并更新设备状态
        返回当前状态（字符串）
        """
        if self.capacity_mb <= 0:
            self.status = DeviceStatus.NORMAL.value
            return self.status
        
        usage_percentage = self.get_usage_percentage()
        
        if usage_percentage >= 100:
            self.status = DeviceStatus.FULL.value
        elif usage_percentage >= self.warning_threshold:
            self.status = DeviceStatus.WARNING.value
        else:
            self.status = DeviceStatus.NORMAL.value
        
        return self.status
    
    def update_capacity_from_path(self) -> bool:
        """
        根据存储路径自动检测容量和使用情况
        返回是否成功更新
        """
        if not self.path or not os.path.exists(self.path):
            return False
        
        try:
            # 获取磁盘使用统计
            total, used, free = shutil.disk_usage(self.path)
            
            # 转换为MB（1MB = 1024*1024 bytes）
            self.capacity_mb = total // (1024 * 1024)
            self.used_mb = used // (1024 * 1024)
            
            # 更新状态
            self.check_capacity_status()
            return True
            
        except Exception as e:
            # 记录错误，但不抛出异常
            print(f"设备容量检测失败: {e}")
            return False
    
    def can_store_file(self, file_size_mb: int) -> bool:
        """
        检查设备是否可以存储指定大小的文件
        """
        if not self.is_active or self.status == DeviceStatus.FULL.value:
            return False
        
        if self.capacity_mb <= 0:
            # 容量未知，假设可以存储（依赖外部检测）
            return True
        
        return (self.used_mb + file_size_mb) <= self.capacity_mb
    
    def allocate_space(self, file_size_mb: int) -> bool:
        """
        分配存储空间（增加已使用容量）
        返回是否成功
        """
        if not self.can_store_file(file_size_mb):
            return False
        
        self.used_mb += file_size_mb
        self.check_capacity_status()
        return True
    
    def release_space(self, file_size_mb: int) -> None:
        """
        释放存储空间（减少已使用容量）
        """
        self.used_mb = max(0, self.used_mb - file_size_mb)
        self.check_capacity_status()
    
    def get_status_message(self) -> str:
        """
        获取状态描述消息（用于提示）
        """
        usage_percentage = self.get_usage_percentage()
        
        if self.status == DeviceStatus.FULL.value:
            return f"设备 '{self.name}' 已满 ({usage_percentage:.1f}% 使用)"
        elif self.status == DeviceStatus.WARNING.value:
            return f"设备 '{self.name}' 空间不足 ({usage_percentage:.1f}% 使用，阈值 {self.warning_threshold}%)"
        else:
            return f"设备 '{self.name}' 空间正常 ({usage_percentage:.1f}% 使用)"
    
    # ========== 静态方法 ==========
    
    @staticmethod
    def detect_path_capacity(path: str) -> dict:
        """
        检测指定路径的磁盘容量
        返回字典：total_mb, used_mb, free_mb, usage_percentage
        """
        if not os.path.exists(path):
            return {"error": "路径不存在"}
        
        try:
            total, used, free = shutil.disk_usage(path)
            
            total_mb = total // (1024 * 1024)
            used_mb = used // (1024 * 1024)
            free_mb = free // (1024 * 1024)
            usage_percentage = (used / total * 100) if total > 0 else 0
            
            return {
                "total_mb": total_mb,
                "used_mb": used_mb,
                "free_mb": free_mb,
                "usage_percentage": round(usage_percentage, 2),
                "path": path
            }
        except Exception as e:
            return {"error": str(e)}
    
    @classmethod
    def find_best_device_for_storage(cls, devices, file_size_mb: int):
        """
        从设备列表中找到最适合存储文件的设备
        基于优先级、可用空间和状态
        """
        suitable_devices = []
        
        for device in devices:
            if not device.is_active:
                continue
            
            if device.can_store_file(file_size_mb):
                # 计算得分：优先级高 + 可用空间百分比高
                available_mb = device.get_available_mb()
                if device.capacity_mb > 0:
                    available_percentage = available_mb / device.capacity_mb
                else:
                    available_percentage = 1.0  # 容量未知，假设有空间
                
                score = device.priority * 100 + available_percentage * 10
                suitable_devices.append((score, device))
        
        if not suitable_devices:
            return None
        
        # 按得分降序排序
        suitable_devices.sort(key=lambda x: x[0], reverse=True)
        return suitable_devices[0][1]


# 添加检查约束
Device.__table__.append_constraint(
    CheckConstraint('capacity_mb >= 0', name='check_capacity_positive')
)
Device.__table__.append_constraint(
    CheckConstraint('used_mb >= 0', name='check_used_positive')
)
Device.__table__.append_constraint(
    CheckConstraint('warning_threshold >= 0 AND warning_threshold <= 100', name='check_warning_threshold_range')
)
Device.__table__.append_constraint(
    CheckConstraint('priority >= 1 AND priority <= 10', name='check_priority_range')
)