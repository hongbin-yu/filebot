from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import uuid
import os

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.device import Device, DeviceType, DeviceStatus
from app.schemas.device import (
    DeviceCreate, DeviceResponse, DeviceUpdate, DeviceWithCapacityInfo,
    DeviceStatusResponse, CapacityDetectionRequest, CapacityDetectionResponse,
    StorageAllocationRequest, StorageAllocationResponse
)

router = APIRouter(tags=["devices"])


# ========== 辅助函数 ==========

def get_device_or_404(db: Session, device_id: uuid.UUID) -> Device:
    """获取设备，如果不存在则返回404"""
    device = db.query(Device).filter(Device.id == str(device_id)).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设备不存在"
        )
    return device


def check_device_admin_access(device: Device, current_user: User) -> None:
    """检查设备管理权限（管理员或创建者）"""
    if not current_user.is_superuser and device.created_by != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权管理此设备"
        )


def device_to_status_response(device: Device) -> DeviceStatusResponse:
    """将设备转换为状态响应"""
    usage_percentage = device.get_usage_percentage()
    available_mb = device.get_available_mb()
    
    return DeviceStatusResponse(
        device_id=uuid.UUID(device.id),
        device_name=device.name,
        status=device.status,
        used_mb=device.used_mb,
        capacity_mb=device.capacity_mb,
        usage_percentage=usage_percentage,
        available_mb=available_mb,
        warning_threshold=device.warning_threshold,
        is_near_threshold=usage_percentage >= (device.warning_threshold - 10),
        threshold_difference=device.warning_threshold - usage_percentage,
        status_message=device.get_status_message(),
        suggestion=get_capacity_suggestion(device)
    )


def get_capacity_suggestion(device: Device) -> Optional[str]:
    """根据设备状态获取建议"""
    if device.status == DeviceStatus.FULL:
        return "设备已满，请清理文件或添加新存储设备"
    elif device.status == DeviceStatus.WARNING:
        return f"设备使用率超过{device.warning_threshold}%，建议清理文件"
    elif device.get_usage_percentage() >= 80:
        return "设备使用率较高，建议定期清理"
    return None


# ========== 设备CRUD路由 ==========

@router.get("/", response_model=List[DeviceResponse])
def list_devices(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    device_type: Optional[DeviceType] = Query(None, description="按设备类型过滤"),
    is_active: Optional[bool] = Query(None, description="按激活状态过滤"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取设备列表（所有用户可查看）"""
    query = db.query(Device)
    
    if device_type is not None:
        query = query.filter(Device.type == device_type)
    
    if is_active is not None:
        query = query.filter(Device.is_active == is_active)
    
    devices = query.order_by(Device.priority.desc(), Device.name).offset(skip).limit(limit).all()
    return devices


@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    device_data: DeviceCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建设备（需要管理员权限）"""
    # 检查设备名称是否已存在
    existing = db.query(Device).filter(Device.name == device_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="设备名称已存在"
        )
    
    # 创建设备
    device = Device(
        name=device_data.name,
        description=device_data.description,
        path=device_data.path,
        type=device_data.type.value,
        is_active=device_data.is_active,
        capacity_mb=device_data.capacity_mb,
        warning_threshold=device_data.warning_threshold,
        priority=device_data.priority,
        config=str(device_data.config) if device_data.config else None,
        created_by=current_user.username
    )
    
    # 如果提供了路径，尝试检测容量
    if device.path:
        device.update_capacity_from_path()
    
    db.add(device)
    db.commit()
    db.refresh(device)
    
    return device


@router.get("/{device_id}", response_model=DeviceWithCapacityInfo)
def get_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取设备详情（包含容量信息）"""
    device = get_device_or_404(db, device_id)
    
    # 构建容量信息
    capacity_info = {
        "usage_percentage": device.get_usage_percentage(),
        "available_mb": device.get_available_mb(),
        "can_store_large_file": device.can_store_file(100),  # 能否存储100MB文件
        "last_updated": device.updated_at.isoformat() if device.updated_at else None
    }
    
    # 如果设备有路径，添加路径信息
    if device.path and os.path.exists(device.path):
        capacity_info["path_exists"] = True
        capacity_info["path"] = device.path
    elif device.path:
        capacity_info["path_exists"] = False
        capacity_info["path"] = device.path
    
    response = DeviceWithCapacityInfo.from_orm(device)
    response.capacity_info = capacity_info
    response.status_message = device.get_status_message()
    
    return response


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: uuid.UUID,
    device_data: DeviceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新设备（需要管理员权限）"""
    device = get_device_or_404(db, device_id)
    check_device_admin_access(device, current_user)
    
    # 更新字段
    update_dict = device_data.dict(exclude_unset=True)
    
    # 移除不应直接更新的字段
    update_dict.pop("updated_by", None)
    
    # 如果更新了名称，检查是否重复
    if "name" in update_dict and update_dict["name"] != device.name:
        existing = db.query(Device).filter(Device.name == update_dict["name"]).first()
        if existing and existing.id != device.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="设备名称已存在"
            )
    
    # 更新字段
    for field, value in update_dict.items():
        if value is not None:
            setattr(device, field, value)
    
    # 设置更新者
    device.updated_by = current_user.username
    
    # 如果更新了路径或容量相关字段，重新检查状态
    if any(field in update_dict for field in ["path", "capacity_mb", "used_mb", "warning_threshold"]):
        device.check_capacity_status()
    
    db.commit()
    db.refresh(device)
    
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除设备（需要管理员权限）"""
    device = get_device_or_404(db, device_id)
    check_device_admin_access(device, current_user)
    
    # 检查设备是否在使用中（如果有文档关联）
    # TODO: 后续添加文档关联检查
    
    db.delete(device)
    db.commit()
    
    return None


# ========== 容量检测与提示路由 ==========

@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
def get_device_status(
    device_id: uuid.UUID,
    update_capacity: bool = Query(False, description="是否重新检测路径容量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取设备状态（包含容量提示）"""
    device = get_device_or_404(db, device_id)
    
    # 如果需要，重新检测容量
    if update_capacity and device.path:
        device.update_capacity_from_path()
        db.commit()
        db.refresh(device)
    
    return device_to_status_response(device)


@router.post("/capacity-detection", response_model=CapacityDetectionResponse)
def detect_capacity(
    request: CapacityDetectionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量检测设备容量（后台任务）"""
    query = db.query(Device)
    
    if request.device_ids:
        device_id_strs = [str(did) for did in request.device_ids]
        query = query.filter(Device.id.in_(device_id_strs))
    
    devices = query.filter(Device.is_active == True).all()
    
    if not devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到符合条件的设备"
        )
    
    warnings = []
    errors = []
    results = []
    updated_count = 0
    
    for device in devices:
        try:
            # 检测容量
            updated = False
            if device.path and (request.force_update or device.capacity_mb == 0):
                updated = device.update_capacity_from_path()
                if updated:
                    updated_count += 1
            
            # 检查状态
            device.check_capacity_status()
            
            # 如果设备状态为警告或已满，添加警告
            if device.status == DeviceStatus.WARNING:
                warnings.append(f"设备 '{device.name}' 使用率超过阈值 ({device.get_usage_percentage():.1f}%)")
            elif device.status == DeviceStatus.FULL:
                warnings.append(f"设备 '{device.name}' 已满 ({device.get_usage_percentage():.1f}%)")
            
            # 添加到结果
            results.append(device_to_status_response(device))
            
            # 提交更改（每10个设备提交一次）
            if updated and updated_count % 10 == 0:
                db.commit()
                
        except Exception as e:
            errors.append(f"设备 '{device.name}' 检测失败: {str(e)}")
    
    # 最终提交
    db.commit()
    
    return CapacityDetectionResponse(
        total_devices=len(devices),
        devices_checked=len(devices),
        devices_updated=updated_count,
        warnings=warnings,
        errors=errors,
        results=results
    )


@router.get("/system/status", response_model=List[DeviceStatusResponse])
def get_system_storage_status(
    show_warnings_only: bool = Query(False, description="只显示警告或已满的设备"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取系统存储状态概览（用于仪表板提示）"""
    query = db.query(Device).filter(Device.is_active == True)
    
    if show_warnings_only:
        query = query.filter(Device.status.in_([DeviceStatus.WARNING, DeviceStatus.FULL]))
    
    devices = query.order_by(
        Device.status.desc(),  # FULL, WARNING 在前
        Device.get_usage_percentage().desc()  # 使用率高的在前
    ).all()
    
    return [device_to_status_response(device) for device in devices]


@router.post("/allocate-storage", response_model=StorageAllocationResponse)
def allocate_storage(
    request: StorageAllocationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """分配存储空间（为文件选择合适的设备）"""
    # 获取所有可用的设备
    devices = db.query(Device).filter(
        Device.is_active == True,
        Device.type == DeviceType.STORAGE  # 只考虑存储类型设备
    ).order_by(Device.priority.desc()).all()
    
    if not devices:
        return StorageAllocationResponse(
            allocated=False,
            message="没有可用的存储设备"
        )
    
    # 如果有首选设备，优先考虑
    if request.preferred_device_id:
        preferred_device = db.query(Device).filter(
            Device.id == str(request.preferred_device_id),
            Device.is_active == True
        ).first()
        
        if preferred_device and preferred_device.can_store_file(request.file_size_mb):
            # 分配空间
            if request.require_capacity_check:
                if not preferred_device.allocate_space(request.file_size_mb):
                    return StorageAllocationResponse(
                        allocated=False,
                        message=f"首选设备 '{preferred_device.name}' 空间不足"
                    )
                db.commit()
            
            warning = None
            if preferred_device.status == DeviceStatus.WARNING:
                warning = f"设备 '{preferred_device.name}' 使用率接近阈值"
            
            return StorageAllocationResponse(
                allocated=True,
                device_id=uuid.UUID(preferred_device.id),
                device_name=preferred_device.name,
                available_mb=preferred_device.get_available_mb(),
                message=f"空间已分配至 '{preferred_device.name}'",
                warning=warning
            )
    
    # 寻找最佳设备
    best_device = Device.find_best_device_for_storage(devices, request.file_size_mb)
    
    if not best_device:
        # 尝试查找是否有容量未知的设备（capacity_mb=0）
        unknown_capacity_devices = [d for d in devices if d.capacity_mb == 0]
        if unknown_capacity_devices:
            # 使用优先级最高的未知容量设备
            best_device = max(unknown_capacity_devices, key=lambda d: d.priority)
        else:
            return StorageAllocationResponse(
                allocated=False,
                message="没有足够的可用存储空间"
            )
    
    # 分配空间
    if request.require_capacity_check:
        if not best_device.allocate_space(request.file_size_mb):
            return StorageAllocationResponse(
                allocated=False,
                message=f"设备 '{best_device.name}' 空间不足"
            )
        db.commit()
    
    warning = None
    if best_device.status == DeviceStatus.WARNING:
        warning = f"设备 '{best_device.name}' 使用率接近阈值"
    
    return StorageAllocationResponse(
        allocated=True,
        device_id=uuid.UUID(best_device.id),
        device_name=best_device.name,
        available_mb=best_device.get_available_mb(),
        message=f"空间已分配至 '{best_device.name}'",
        warning=warning
    )


@router.post("/{device_id}/release-space")
def release_device_space(
    device_id: uuid.UUID,
    file_size_mb: int = Query(..., gt=0, description="释放的空间大小（MB）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """释放设备空间（当文件被删除时调用）"""
    device = get_device_or_404(db, device_id)
    
    # 检查权限（管理员或文档所有者）
    # TODO: 后续添加更精细的权限检查
    
    device.release_space(file_size_mb)
    db.commit()
    
    return {
        "message": f"已从设备 '{device.name}' 释放 {file_size_mb}MB 空间",
        "device_id": device_id,
        "used_mb": device.used_mb,
        "available_mb": device.get_available_mb(),
        "status": device.status.value
    }


# ========== 设备初始化路由（兼容旧系统） ==========

@router.post("/initialize-legacy", status_code=status.HTTP_201_CREATED)
def initialize_legacy_devices(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """初始化旧系统兼容设备（Recycle Bin等）"""
    # 检查是否已存在回收站
    recycle_bin = db.query(Device).filter(Device.type == DeviceType.RECYCLE_BIN).first()
    
    devices_created = []
    
    if not recycle_bin:
        # 创建回收站（对应旧系统类型1）
        recycle_bin = Device(
            name="Recycle Bin",
            description="回收站（旧系统兼容）",
            type=DeviceType.RECYCLE_BIN,
            is_active=True,
            capacity_mb=0,  # 容量未知
            warning_threshold=90,
            priority=10,  # 最低优先级
            created_by=current_user.username
        )
        db.add(recycle_bin)
        devices_created.append("Recycle Bin")
    
    # 创建默认存储设备（如果不存在）
    default_storage = db.query(Device).filter(Device.type == DeviceType.STORAGE, Device.priority == 1).first()
    if not default_storage:
        default_storage = Device(
            name="Default Storage",
            description="默认存储设备",
            type=DeviceType.STORAGE,
            is_active=True,
            capacity_mb=0,  # 自动检测
            warning_threshold=85,
            priority=1,  # 最高优先级
            created_by=current_user.username
        )
        db.add(default_storage)
        devices_created.append("Default Storage")
    
    if devices_created:
        db.commit()
    
    return {
        "message": "旧系统设备初始化完成",
        "devices_created": devices_created,
        "recycle_bin_id": recycle_bin.id if recycle_bin else None
    }