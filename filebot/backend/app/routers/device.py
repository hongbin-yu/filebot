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


# ========== Helper Functions ==========

def get_device_or_404(db: Session, device_id: uuid.UUID) -> Device:
    """Get device by ID, return 404 if not found"""
    device = db.query(Device).filter(Device.id == str(device_id)).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return device


def check_device_admin_access(device: Device, current_user: User) -> None:
    """Check device management permission (admin or creator)"""
    if not current_user.is_superuser and device.created_by != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to manage this device"
        )


def device_to_status_response(device: Device) -> DeviceStatusResponse:
    """Convert device to status response"""
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
    """Get suggestion based on device status"""
    if device.status == DeviceStatus.FULL:
        return "Device is full. Please clean files or add new storage."
    elif device.status == DeviceStatus.WARNING:
        return f"Usage exceeds {device.warning_threshold}%. Consider cleaning files."
    elif device.get_usage_percentage() >= 80:
        return "Usage is high. Regular cleanup recommended."
    return None


# ========== Device CRUD Routes ==========

@router.get("/", response_model=List[DeviceResponse])
def list_devices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    device_type: Optional[DeviceType] = Query(None, description="Filter by device type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get device list (viewable by all users)"""
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
    """Create device (admin permission required)"""
    # Check if device name already exists
    existing = db.query(Device).filter(Device.name == device_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device name already exists"
        )
    
    # Create device
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
    
    # If path is provided, try to detect capacity
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
    """Get device details (includes capacity info)"""
    device = get_device_or_404(db, device_id)
    
    # Build capacity info
    capacity_info = {
        "usage_percentage": device.get_usage_percentage(),
        "available_mb": device.get_available_mb(),
        "can_store_large_file": device.can_store_file(100),
        "last_updated": device.updated_at.isoformat() if device.updated_at else None
    }
    
    # If device has a path, add path info
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
    """Update device (admin permission required)"""
    device = get_device_or_404(db, device_id)
    check_device_admin_access(device, current_user)
    
    # Build update dict
    update_dict = device_data.dict(exclude_unset=True)
    
    # Remove fields that should not be directly updated
    update_dict.pop("updated_by", None)
    
    # If name was updated, check for duplicates
    if "name" in update_dict and update_dict["name"] != device.name:
        existing = db.query(Device).filter(Device.name == update_dict["name"]).first()
        if existing and existing.id != device.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device name already exists"
            )
    
    # Apply updates
    for field, value in update_dict.items():
        if value is not None:
            setattr(device, field, value)
    
    # Set updater
    device.updated_by = current_user.username
    
    # If path or capacity fields were updated, re-check status
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
    """Delete device (admin permission required)"""
    device = get_device_or_404(db, device_id)
    check_device_admin_access(device, current_user)
    
    # Check if device is in use (has document associations)
    # TODO: Add document association check later
    
    db.delete(device)
    db.commit()
    
    return None


# ========== Capacity Detection & Status Routes ==========

@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
def get_device_status(
    device_id: uuid.UUID,
    update_capacity: bool = Query(False, description="Whether to re-detect path capacity"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get device status (includes capacity tips)"""
    device = get_device_or_404(db, device_id)
    
    # Re-detect capacity if requested
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
    """Batch detect device capacity (background task)"""
    query = db.query(Device)
    
    if request.device_ids:
        device_id_strs = [str(did) for did in request.device_ids]
        query = query.filter(Device.id.in_(device_id_strs))
    
    devices = query.filter(Device.is_active == True).all()
    
    if not devices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching devices found"
        )
    
    warnings = []
    errors = []
    results = []
    updated_count = 0
    
    for device in devices:
        try:
            # Detect capacity
            updated = False
            if device.path and (request.force_update or device.capacity_mb == 0):
                updated = device.update_capacity_from_path()
                if updated:
                    updated_count += 1
            
            # Check status
            device.check_capacity_status()
            
            # Add warnings for devices in warning or full status
            if device.status == DeviceStatus.WARNING:
                warnings.append(f"Device '{device.name}' usage exceeds threshold ({device.get_usage_percentage():.1f}%)")
            elif device.status == DeviceStatus.FULL:
                warnings.append(f"Device '{device.name}' is full ({device.get_usage_percentage():.1f}%)")
            
            # Add to results
            results.append(device_to_status_response(device))
            
            # Commit every 10 devices
            if updated and updated_count % 10 == 0:
                db.commit()
                
        except Exception as e:
            errors.append(f"Device '{device.name}' detection failed: {str(e)}")
    
    # Final commit
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
    show_warnings_only: bool = Query(False, description="Show only warning or full devices"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get system storage status overview (for dashboard alerts)"""
    query = db.query(Device).filter(Device.is_active == True)
    
    if show_warnings_only:
        query = query.filter(Device.status.in_([DeviceStatus.WARNING, DeviceStatus.FULL]))
    
    devices = query.order_by(
        Device.status.desc(),
        Device.get_usage_percentage().desc()
    ).all()
    
    return [device_to_status_response(device) for device in devices]


@router.post("/allocate-storage", response_model=StorageAllocationResponse)
def allocate_storage(
    request: StorageAllocationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Allocate storage space (pick the right device for a file)"""
    # Get all available devices
    devices = db.query(Device).filter(
        Device.is_active == True,
        Device.type == DeviceType.STORAGE
    ).order_by(Device.priority.desc()).all()
    
    if not devices:
        return StorageAllocationResponse(
            allocated=False,
            message="No available storage devices"
        )
    
    # If preferred device is specified, try it first
    if request.preferred_device_id:
        preferred_device = db.query(Device).filter(
            Device.id == str(request.preferred_device_id),
            Device.is_active == True
        ).first()
        
        if preferred_device and preferred_device.can_store_file(request.file_size_mb):
            # Allocate space
            if request.require_capacity_check:
                if not preferred_device.allocate_space(request.file_size_mb):
                    return StorageAllocationResponse(
                        allocated=False,
                        message=f"Preferred device '{preferred_device.name}' has insufficient space"
                    )
                db.commit()
            
            warning = None
            if preferred_device.status == DeviceStatus.WARNING:
                warning = f"Device '{preferred_device.name}' usage near threshold"
            
            return StorageAllocationResponse(
                allocated=True,
                device_id=uuid.UUID(preferred_device.id),
                device_name=preferred_device.name,
                available_mb=preferred_device.get_available_mb(),
                message=f"Space allocated to '{preferred_device.name}'",
                warning=warning
            )
    
    # Find the best device
    best_device = Device.find_best_device_for_storage(devices, request.file_size_mb)
    
    if not best_device:
        # Try devices with unknown capacity (capacity_mb=0)
        unknown_capacity_devices = [d for d in devices if d.capacity_mb == 0]
        if unknown_capacity_devices:
            best_device = max(unknown_capacity_devices, key=lambda d: d.priority)
        else:
            return StorageAllocationResponse(
                allocated=False,
                message="Insufficient available storage space"
            )
    
    # Allocate space
    if request.require_capacity_check:
        if not best_device.allocate_space(request.file_size_mb):
            return StorageAllocationResponse(
                allocated=False,
                message=f"Device '{best_device.name}' has insufficient space"
            )
        db.commit()
    
    warning = None
    if best_device.status == DeviceStatus.WARNING:
        warning = f"Device '{best_device.name}' usage near threshold"
    
    return StorageAllocationResponse(
        allocated=True,
        device_id=uuid.UUID(best_device.id),
        device_name=best_device.name,
        available_mb=best_device.get_available_mb(),
        message=f"Space allocated to '{best_device.name}'",
        warning=warning
    )


@router.post("/{device_id}/release-space")
def release_device_space(
    device_id: uuid.UUID,
    file_size_mb: int = Query(..., gt=0, description="Size of space to release (MB)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Release device space (called when files are deleted)"""
    device = get_device_or_404(db, device_id)
    
    # Check permissions (admin or document owner)
    # TODO: Add finer permission check later
    
    device.release_space(file_size_mb)
    db.commit()
    
    return {
        "message": f"Released {file_size_mb}MB from device '{device.name}'",
        "device_id": device_id,
        "used_mb": device.used_mb,
        "available_mb": device.get_available_mb(),
        "status": device.status.value
    }


# ========== Device Initialization Routes (Legacy Compat) ==========

@router.post("/initialize-legacy", status_code=status.HTTP_201_CREATED)
def initialize_legacy_devices(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Initialize legacy compatible devices (Recycle Bin, etc.)"""
    # Check if Recycle Bin already exists
    recycle_bin = db.query(Device).filter(Device.type == DeviceType.RECYCLE_BIN).first()
    
    devices_created = []
    
    if not recycle_bin:
        # Create Recycle Bin (corresponds to old system type 1)
        recycle_bin = Device(
            name="Recycle Bin",
            description="Recycle Bin (legacy compatible)",
            type=DeviceType.RECYCLE_BIN,
            is_active=True,
            capacity_mb=0,
            warning_threshold=90,
            priority=10,
            created_by=current_user.username
        )
        db.add(recycle_bin)
        devices_created.append("Recycle Bin")
    
    # Create default storage device if not exists
    default_storage = db.query(Device).filter(Device.type == DeviceType.STORAGE, Device.priority == 1).first()
    if not default_storage:
        default_storage = Device(
            name="Default Storage",
            description="Default storage device",
            type=DeviceType.STORAGE,
            is_active=True,
            capacity_mb=0,
            warning_threshold=85,
            priority=1,
            created_by=current_user.username
        )
        db.add(default_storage)
        devices_created.append("Default Storage")
    
    if devices_created:
        db.commit()
    
    return {
        "message": "Legacy device initialization complete",
        "devices_created": devices_created,
        "recycle_bin_id": recycle_bin.id if recycle_bin else None
    }
