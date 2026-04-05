from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Path as FastaPath, Request
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
import uuid
import os
import logging
import shutil
import tempfile
from pathlib import Path
import PyPDF2
from PIL import Image
from urllib.parse import urlparse

from app.db.database import get_db
from app.core.security import get_current_active_user, get_current_user, oauth2_scheme
from app.core.config import settings
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.document import Document, ConversionStatus, FileType, DocumentStatus, DocumentType, PublishStatus
from app.models.page import Page
from app.models.file_naming_rule import FileNamingRule
from app.models.device import Device, DeviceType, DeviceStatus
from app.schemas.document import (
    DocumentCreate, DocumentResponse, DocumentUpdate,
    PageCreate, PageResponse, PageUpdate
)
from app.services.conversion_worker import create_conversion_task_for_document

router = APIRouter()


# ========== 权限检查辅助函数 ==========

def check_folder_access(
    folder_id: uuid.UUID,
    current_user: User,
    db: Session,
    require_owner: bool = False
) -> Folder:
    """检查用户是否有权限访问文件夹
    
    Args:
        folder_id: 文件夹ID
        current_user: 当前用户
        db: 数据库会话
        require_owner: 是否要求用户必须是文件夹的所有者（应用所有者）
    
    Returns:
        Folder对象（如果权限检查通过）
    
    Raises:
        HTTPException: 如果文件夹不存在或用户没有权限
    """
    # 将UUID转换为字符串进行查询
    folder_id_str = str(folder_id)
    
    # 超级用户可以访问所有资源
    if current_user.is_superuser or current_user.username == "public":
        folder = db.query(Folder).options(
            joinedload(Folder.app)
        ).filter(Folder.id == folder_id_str).first()
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
        return folder
    
    # 获取文件夹及其关联的应用
    folder = db.query(Folder).options(
        joinedload(Folder.app)
    ).filter(Folder.id == folder_id_str).first()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    # 检查应用权限
    app = folder.app
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此文件夹"
        )
    
    # 如果要求所有者，确保用户是应用所有者
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者才能执行此操作"
        )
    
    return folder


def check_document_access(
    document_id: uuid.UUID,
    current_user: User,
    db: Session,
    require_owner: bool = False
) -> Document:
    """检查用户是否有权限访问文档
    
    Args:
        document_id: 文档ID
        current_user: 当前用户
        db: 数据库会话
        require_owner: 是否要求用户必须是文档的所有者（应用所有者）
    
    Returns:
        Document对象（如果权限检查通过）
    """
    # 将UUID转换为字符串进行查询
    document_id_str = str(document_id)
    
    # 超级用户可以访问所有资源
    if current_user.is_superuser or current_user.username == "public":
        document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.id == document_id_str).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        return document
    
    # 获取文档及其关联的文件夹和应用
    document = db.query(Document).options(
            joinedload(Document.folder).joinedload(Folder.app)
        ).filter(Document.id == document_id_str).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 检查应用权限
    app = document.folder.app
    if app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此文档"
        )
    
    # 如果要求所有者，确保用户是应用所有者
    if require_owner and app.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有所有者才能执行此操作"
        )
    
    return document


def get_document_file_path(document: Document, settings) -> Path:
    """
    获取文档的实际存储文件路径
    
    根据文档的存储信息构建路径：
    1. 如果文档有 full_storage_path，使用设备存储路径
    2. 否则，使用默认存储路径
    3. 兼容旧版本爬虫存储路径 (data/documents/)
    """
    if document.full_storage_path and document.stored_filename:
        # 使用设备存储路径
        return Path(document.full_storage_path) / document.stored_filename
    
    # 尝试多个可能的存储位置
    possible_paths = []
    
    # 1. 默认存储路径
    default_path = Path(settings.FILE_STORAGE_PATH) / "original" / document.stored_filename
    possible_paths.append(default_path)
    
    # 2. 旧版本爬虫存储路径 (data/documents/)
    old_crawler_path = Path("data/documents") / document.stored_filename
    possible_paths.append(old_crawler_path)
    
    # 3. 直接使用 stored_filename（如果它是绝对路径）
    if document.stored_filename and os.path.isabs(document.stored_filename):
        possible_paths.append(Path(document.stored_filename))
    
    # 检查哪个路径存在
    for path in possible_paths:
        if path.exists():
            return path
    
    # 如果没有路径存在，返回默认路径（将导致404错误，但至少会抛出明确的异常）
    return default_path


def get_document_pdf_path(document: Document, settings) -> Optional[Path]:
    """
    获取文档的PDF文件路径（如果已转换）
    """
    if document.converted_pdf_path:
        return Path(document.converted_pdf_path)
    return None


# ========== Document (文档) 路由 ==========

@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    folder_id: Optional[uuid.UUID] = Query(None, description="按文件夹ID筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    status_filter: Optional[DocumentStatus] = Query(None, description="按文档状态筛选"),
    type_filter: Optional[DocumentType] = Query(None, description="按文档类型筛选"),
    conversion_status_filter: Optional[ConversionStatus] = Query(None, description="按转换状态筛选"),
    search_term: Optional[str] = Query(None, description="搜索文档标题或描述"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文档列表
    
    支持多种筛选条件：
    - 按文件夹筛选
    - 按文档状态筛选
    - 按文档类型筛选
    - 按转换状态筛选
    - 按标题/描述搜索
    """
    # 构建基础查询
    query = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    )
    
    # 添加权限筛选：只能查看自己有权限的应用下的文档
    if not current_user.is_superuser:
        # 子查询：获取当前用户拥有的所有应用ID
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        # 通过文件夹→应用链进行筛选（移除抽屉层）
        query = query.join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # 应用筛选条件
    if folder_id:
        # 验证用户是否有权限访问该文件夹
        folder = check_folder_access(folder_id, current_user, db)
        # 将UUID转换为字符串进行查询，因为数据库中的folder_id是字符串类型
        query = query.filter(Document.folder_id == str(folder_id))
    
    if status_filter:
        query = query.filter(Document.status == status_filter)
    
    if type_filter:
        query = query.filter(Document.type == type_filter)
    
    if conversion_status_filter:
        query = query.filter(Document.conversion_status == conversion_status_filter)
    
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            (Document.title.ilike(search_pattern)) |
            (Document.description.ilike(search_pattern)) |
            (Document.document_number.ilike(search_pattern))
        )
    
    # 排序和分页
    query = query.order_by(Document.created_at.desc())
    documents = query.offset(skip).limit(limit).all()
    
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文档详情"""
    document = check_document_access(document_id, current_user, db)
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: uuid.UUID,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新文档信息"""
    document = check_document_access(document_id, current_user, db)
    
    # 如果修改了文档编号，检查是否与现有文档冲突
    if document_update.document_number and document_update.document_number != document.document_number:
        existing_doc = db.query(Document).filter(
            Document.document_number == document_update.document_number,
            Document.id != document_id
        ).first()
        
        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文档编号已存在"
            )
    
    # 更新字段
    update_data = document_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    # 更新审计字段
    document.updated_by = document_update.updated_by or current_user.username
    
    db.commit()
    db.refresh(document)
    
    return document


@router.delete("/{document_id}")
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除文档
    
    注意：会同时删除关联的页面和转换任务
    """
    document = check_document_access(document_id, current_user, db)
    
    # 删除物理文件（TODO: 需要配置存储路径）
    # 这里暂时只删除数据库记录
    
    db.delete(document)
    db.commit()
    
    return {"message": "文档删除成功"}


# ========== Page (页面) 路由 ==========

@router.get("/{document_id}/pages", response_model=List[PageResponse])
def get_document_pages(
    document_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文档的所有页面"""
    # 先验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 获取页面列表
    pages = db.query(Page).filter(
        Page.document_id == document_id
    ).order_by(Page.page_number).offset(skip).limit(limit).all()
    
    return pages


@router.get("/{document_id}/pages/{page_id}", response_model=PageResponse)
def get_document_page(
    document_id: uuid.UUID,
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取文档的特定页面"""
    # 先验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 获取页面
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document_id
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在或不属于此文档"
        )
    
    return page


@router.put("/{document_id}/pages/{page_id}", response_model=PageResponse)
def update_document_page(
    document_id: uuid.UUID,
    page_id: uuid.UUID,
    page_update: PageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新页面信息（主要用于更新索引字段）"""
    # 先验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 获取页面
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document_id
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在或不属于此文档"
        )
    
    # 如果修改了页码，检查是否与其他页面冲突
    if page_update.page_number and page_update.page_number != page.page_number:
        existing_page = db.query(Page).filter(
            Page.document_id == document_id,
            Page.page_number == page_update.page_number,
            Page.id != page_id
        ).first()
        
        if existing_page:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此文档中已存在该页码的页面"
            )
    
    # 更新字段
    update_data = page_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(page, field, value)
    
    # 更新审计字段
    page.updated_by = page_update.updated_by or current_user.username
    
    db.commit()
    db.refresh(page)
    
    return page


@router.delete("/{document_id}/pages/{page_id}")
def delete_document_page(
    document_id: uuid.UUID,
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除页面"""
    # 先验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 获取页面
    page = db.query(Page).filter(
        Page.id == page_id,
        Page.document_id == document_id
    ).first()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在或不属于此文档"
        )
    
    db.delete(page)
    db.commit()
    
    return {"message": "页面删除成功"}


# ========== 文件操作路由 ==========

@router.post("/upload/")
async def upload_document(
    file: UploadFile = File(...),
    folder_id: uuid.UUID = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_type: DocumentType = Form(DocumentType.GENERAL),
    naming_rule_id: Optional[uuid.UUID] = Form(None),
    device_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """上传文档文件
    
    注意：这里只保存文件基本信息，实际的文件处理和转换通过异步任务完成
    
    如果提供了 naming_rule_id，将使用文件命名规则生成文档编号（document_number）
    文档编号格式：{basename}{序列号}，如"PO-1001"
    系统存储的文件名使用UUID确保唯一性，用户不关心系统文件名
    
    如果命名规则包含 subfolder_name 或提供了 device_id，文件将存储到设备的子文件夹中
    实现文件按类型分目录存储，避免所有文件堆在同一个目录
    """
    # 验证文件夹权限
    folder = check_folder_access(folder_id, current_user, db)
    
    # 如果提供了命名规则ID，验证规则并获取下一个文档编号
    generated_document_number = None
    naming_rule = None
    
    if naming_rule_id:
        # 获取命名规则
        naming_rule = db.query(FileNamingRule).filter(
            FileNamingRule.id == str(naming_rule_id)
        ).first()
        
        if not naming_rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="命名规则不存在"
            )
        
        # 验证命名规则属于同一个应用
        # 通过文件夹→抽屉→应用链找到应用ID
        app_from_folder = folder.drawer.app
        if str(naming_rule.app_id) != str(app_from_folder.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="命名规则不属于当前应用"
            )
        
        # 生成文档编号（如"PO-1001"）
        generated_document_number = f"{naming_rule.basename}{naming_rule.max_number:04d}"
        
        # 递增序列号
        naming_rule.max_number += naming_rule.increment_by
        naming_rule.updated_by = current_user.username
    
    # 检查文件大小（限制为100MB）
    file_size = 0
    temp_file_path = None
    try:
        # 保存到临时文件
        temp_dir = Path("/tmp/filebot/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"
        
        with open(temp_file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                file_size += len(chunk)
                if file_size > 100 * 1024 * 1024:  # 100MB限制
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="文件大小不能超过100MB"
                    )
                buffer.write(chunk)
        
        # 确定文件类型和扩展名
        original_uploaded_filename = file.filename
        file_extension = Path(original_uploaded_filename).suffix.lower()
        
        # 映射扩展名到FileType枚举
        extension_to_type = {
            'tiff': FileType.TIFF, 'tif': FileType.TIFF,
            'pdf': FileType.PDF,
            'doc': FileType.DOC, 'docx': FileType.DOCX,
            'jpeg': FileType.JPEG, 'jpg': FileType.JPG,
            'png': FileType.PNG,
            'pcl': FileType.PCL,
            'ps': FileType.PS,
            'txt': FileType.TXT
        }
        
        # 去掉扩展名前的点
        ext_without_dot = file_extension.lstrip('.')
        file_type = extension_to_type.get(ext_without_dot, FileType.OTHER)
        
        # 确定MIME类型
        mime_type = file.content_type or "application/octet-stream"
        
        # 生成存储文件名（UUID）
        stored_filename = str(uuid.uuid4())
        
        # 确定最终显示的文件名
        # original_filename 保持用户上传的原始文件名
        original_filename = original_uploaded_filename
        
        # 如果使用命名规则，生成文档编号（document_number）
        document_number = None
        if generated_document_number:
            # 使用命名规则生成文档编号（如"PO-1001"）
            document_number = generated_document_number
        
        # ========== 设备选择和存储路径确定 ==========
        selected_device = None
        storage_subfolder = None
        full_storage_path = None
        
        # 计算文件大小（MB）
        file_size_mb = file_size // (1024 * 1024) + 1  # 向上取整
        
        # 情况1：指定了device_id
        if device_id:
            selected_device = db.query(Device).filter(
                Device.id == str(device_id),
                Device.is_active == True
            ).first()
            
            if not selected_device:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="指定的设备不存在或未激活"
                )
            
            if not selected_device.can_store_file(file_size_mb):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"设备 '{selected_device.name}' 空间不足，无法存储文件"
                )
        
        # 情况2：使用命名规则，且规则指定了subfolder_name，自动选择设备
        elif naming_rule and naming_rule.subfolder_name:
            # 获取所有活跃的存储设备
            storage_devices = db.query(Device).filter(
                Device.is_active == True,
                Device.type == DeviceType.STORAGE  # 只使用主存储设备
            ).all()
            
            if not storage_devices:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="没有可用的存储设备，请先创建设备"
                )
            
            # 选择最佳设备
            selected_device = Device.find_best_device_for_storage(storage_devices, file_size_mb)
            
            if not selected_device:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="所有存储设备空间不足，无法存储文件"
                )
            
            # 使用命名规则的子文件夹名称
            storage_subfolder = naming_rule.subfolder_name
        
        # 情况3：使用默认存储（不指定设备）
        
        # 如果选择了设备，确定存储路径
        if selected_device:
            # 确保设备路径存在
            if not selected_device.path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"设备 '{selected_device.name}' 没有配置存储路径"
                )
            
            # 确定子文件夹路径
            if not storage_subfolder:
                storage_subfolder = "default"  # 默认子文件夹
            
            # 构建完整存储路径
            full_storage_path = str(Path(selected_device.path) / storage_subfolder)
            
            # 创建子文件夹（如果不存在）
            Path(full_storage_path).mkdir(parents=True, exist_ok=True)
        
        # ========== 设备选择和存储路径确定结束 ==========
        
        # 创建文档记录 - 确保所有UUID都转换为字符串
        import uuid as uuid_module
        document = Document(
            id=str(uuid_module.uuid4()),  # 显式设置ID为字符串
            folder_id=str(folder_id),
            uploaded_by=str(current_user.id),
            
            # 文档信息
            title=title or Path(original_filename).stem,
            description=description,
            document_number=document_number,  # 如果使用命名规则，设置文档编号
            status=DocumentStatus.ACTIVE,
            type=document_type,
            comments=f"上传文件: {original_uploaded_filename}" + 
                     (f" (使用命名规则: {naming_rule.basename})" if naming_rule else ""),
            
            # 文件信息
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            
            # 存储设备信息
            device_id=str(selected_device.id) if selected_device else None,
            storage_subfolder=storage_subfolder,
            full_storage_path=full_storage_path,
            
            # 转换状态
            conversion_status=ConversionStatus.PENDING,
            
            # 审计字段
            created_by=current_user.username
        )
        
        db.add(document)
        
        # 如果使用了命名规则，保存规则更新
        if naming_rule:
            db.add(naming_rule)
        
        db.commit()
        db.refresh(document)
        
        # 确定最终存储路径
        if selected_device and full_storage_path:
            # 使用设备存储路径
            target_path = Path(full_storage_path) / stored_filename
            
            # 分配设备存储空间
            if not selected_device.allocate_space(file_size_mb):
                # 回滚事务（删除文档记录）
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"设备 '{selected_device.name}' 空间分配失败"
                )
            
            # 保存设备容量更新
            db.add(selected_device)
            db.commit()
        else:
            # 使用默认存储路径
            original_dir = Path(settings.FILE_STORAGE_PATH) / "original"
            original_dir.mkdir(parents=True, exist_ok=True)
            target_path = original_dir / stored_filename
        
        # 移动文件
        shutil.move(str(temp_file_path), str(target_path))
        
        # 创建转换任务
        conversion_task = create_conversion_task_for_document(
            db, document.id, target_format="pdf"
        )
        
        # 准备响应数据
        response_data = {
            "message": "文件上传成功，转换任务已创建",
            "document_id": str(document.id),
            "conversion_task_id": str(conversion_task.id) if conversion_task else None,
            "original_filename": original_filename,
            "document_number": document_number,  # 如果使用命名规则生成的文档编号
            "naming_rule_used": naming_rule.basename if naming_rule else None,
            "next_sequence_number": naming_rule.max_number if naming_rule else None
        }
        
        return response_data
        
    except Exception as e:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.get("/{document_id}/download")
def download_document(
    request: Request,
    document_id: uuid.UUID,
    download_type: str = Query("original", description="下载类型: original 或 pdf"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """下载文档文件
    
    支持下载原始文件或转换后的PDF
    """
    document = check_document_access(document_id, current_user, db)
    
    # 检查发布状态：只有PUBLISHED状态的文档可以通过URL访问
    # 如果publish_status为None（旧文档），允许访问以保持向后兼容
    
    # 检查是否为WebBot请求（特殊权限允许访问未发布文档）
    import logging
    logger = logging.getLogger(__name__)
    is_webbot_request = request.headers.get("X-WebBot-Access") == "true"
    if is_webbot_request:
        logger.info(f"WebBot请求访问未发布文档 {document.id}，跳过发布状态检查")
    elif document.publish_status is not None and document.publish_status != PublishStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="文档未发布，无法通过URL访问"
        )
    
    # TODO: 根据配置的存储路径构建实际文件路径
    # 这里只是一个示例实现
    
    file_path = None
    filename = document.original_filename
    
    if download_type == "pdf" and document.converted_pdf_path:
        # 下载PDF版本
        file_path = document.converted_pdf_path
        filename = f"{Path(document.original_filename).stem}.pdf"
    else:
        # 下载原始文件
        file_path = get_document_file_path(document, settings)
        filename = document.original_filename
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 确定media_type：使用文档的mime_type，如果不存在则根据文件扩展名判断
    media_type = document.mime_type if document.mime_type else "application/octet-stream"
    
    # 如果mime_type为空或未知，根据文件扩展名设置
    if not media_type or media_type == "application/octet-stream":
        if filename.lower().endswith(('.html', '.htm')):
            media_type = "text/html"
        elif filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif filename.lower().endswith('.png'):
            media_type = "image/png"
        elif filename.lower().endswith('.tiff') or filename.lower().endswith('.tif'):
            media_type = "image/tiff"
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@router.post("/{document_id}/extract-pages")
async def extract_pages_from_pdf(
    document_id: uuid.UUID,
    page_numbers: List[int] = Query(..., description="要提取的页码列表（从1开始）"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """从PDF文档中提取指定页面，生成新的临时PDF文件
    
    注意：生成的PDF是临时文件，不会保存到系统中
    """
    # 验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 检查文档是否为PDF
    if document.file_type != FileType.PDF:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能从PDF文件中提取页面"
        )
    
    # 获取PDF文件路径
    pdf_path = None
    if document.converted_pdf_path and os.path.exists(document.converted_pdf_path):
        # 使用已转换的PDF版本
        pdf_path = document.converted_pdf_path
    else:
        # 使用原始文件（假设已经是PDF）
        pdf_path = get_document_file_path(document, settings)
    
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF文件不存在"
        )
    
    # 验证页码有效性
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            
            # 检查页码范围
            for page_num in page_numbers:
                if page_num < 1 or page_num > total_pages:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"页码 {page_num} 超出范围（文档共有 {total_pages} 页）"
                    )
            
            # 创建PDF写入器
            pdf_writer = PyPDF2.PdfWriter()
            
            # 提取指定页面
            for page_num in page_numbers:
                page = pdf_reader.pages[page_num - 1]  # 转换为0-based索引
                pdf_writer.add_page(page)
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_path = temp_file.name
                # 写入提取的页面
                with open(temp_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            # 生成下载文件名
            original_stem = Path(document.original_filename).stem
            if len(page_numbers) == 1:
                download_filename = f"{original_stem}_page{page_numbers[0]}.pdf"
            else:
                page_range = f"pages_{'-'.join(map(str, page_numbers))}"
                download_filename = f"{original_stem}_{page_range}.pdf"
            
            # 返回文件响应（临时文件会在发送后自动清理）
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="application/pdf",
                background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
            )
    
    except PyPDF2.errors.PdfReadError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法读取PDF文件，文件可能已损坏或不是有效的PDF"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提取页面时发生错误: {str(e)}"
        )


@router.post("/{document_id}/extract-tiff-pages")
async def extract_pages_from_tiff(
    document_id: uuid.UUID,
    page_numbers: List[int] = Query(..., description="要提取的页码列表（从1开始）"),
    output_format: str = Query("pdf", description="输出格式: 'pdf' 或 'tiff'"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """从TIFF文档中提取指定页面，生成新的临时文件
    
    注意：生成的文件是临时文件，不会保存到系统中
    """
    # 验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 检查文档是否为TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能从图像文件（TIFF/JPEG/PNG）中提取页面"
        )
    
    # 验证输出格式
    if output_format.lower() not in ["pdf", "tiff"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="输出格式必须是 'pdf' 或 'tiff'"
        )
    
    # 获取文件路径
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        # 打开TIFF文件
        with Image.open(file_path) as img:
            # 获取TIFF页数（如果是多页TIFF）
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                # 到达文件结尾，page_count现在包含总页数
                pass
            
            # 单页图像的情况
            if page_count == 0:
                page_count = 1
            
            # 检查页码范围
            for page_num in page_numbers:
                if page_num < 1 or page_num > page_count:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"页码 {page_num} 超出范围（文档共有 {page_count} 页）"
                    )
            
            # 根据输出格式处理
            if output_format.lower() == "pdf":
                return _extract_tiff_pages_to_pdf(
                    file_path, page_numbers, document.original_filename
                )
            else:  # tiff
                return _extract_tiff_pages_to_tiff(
                    file_path, page_numbers, document.original_filename
                )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提取页面时发生错误: {str(e)}"
        )


def _extract_tiff_pages_to_pdf(
    tiff_path: str,
    page_numbers: List[int],
    original_filename: str
) -> FileResponse:
    """从TIFF提取页面并生成PDF"""
    try:
        images = []
        
        # 提取指定页面
        for page_num in page_numbers:
            with Image.open(tiff_path) as img:
                # 跳转到指定页面（0-based索引）
                img.seek(page_num - 1)
                
                # 转换为RGB模式（如果需要）
                if img.mode not in ["RGB", "L"]:
                    img = img.convert("RGB")
                
                images.append(img.copy())
        
        # 创建临时PDF文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # 保存第一页
            images[0].save(temp_path, "PDF", save_all=True, 
                          append_images=images[1:] if len(images) > 1 else [])
        
        # 生成下载文件名
        original_stem = Path(original_filename).stem
        if len(page_numbers) == 1:
            download_filename = f"{original_stem}_page{page_numbers[0]}.pdf"
        else:
            page_range = f"pages_{'-'.join(map(str, page_numbers))}"
            download_filename = f"{original_stem}_{page_range}.pdf"
        
        # 返回文件响应
        return FileResponse(
            path=temp_path,
            filename=download_filename,
            media_type="application/pdf",
            background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
        )
    
    except Exception as e:
        # 清理临时文件（如果存在）
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


def _extract_tiff_pages_to_tiff(
    tiff_path: str,
    page_numbers: List[int],
    original_filename: str
) -> FileResponse:
    """从TIFF提取页面并生成新的TIFF"""
    try:
        images = []
        
        # 提取指定页面
        for page_num in page_numbers:
            with Image.open(tiff_path) as img:
                # 跳转到指定页面（0-based索引）
                img.seek(page_num - 1)
                images.append(img.copy())
        
        # 创建临时TIFF文件
        with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # 保存第一页
            images[0].save(temp_path, "TIFF", save_all=True, 
                          append_images=images[1:] if len(images) > 1 else [],
                          compression="tiff_deflate")
        
        # 生成下载文件名
        original_stem = Path(original_filename).stem
        if len(page_numbers) == 1:
            download_filename = f"{original_stem}_page{page_numbers[0]}.tiff"
        else:
            page_range = f"pages_{'-'.join(map(str, page_numbers))}"
            download_filename = f"{original_stem}_{page_range}.tiff"
        
        # 返回文件响应
        return FileResponse(
            path=temp_path,
            filename=download_filename,
            media_type="image/tiff",
            background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
        )
    
    except Exception as e:
        # 清理临时文件（如果存在）
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


@router.post("/{document_id}/retry-conversion")
def retry_document_conversion(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """重新尝试文档转换（针对转换失败的文档）"""
    document = check_document_access(document_id, current_user, db)
    
    if document.conversion_status not in [ConversionStatus.FAILED, ConversionStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文档当前状态为 {document.conversion_status.value}，无法重新转换"
        )
    
    # 重置转换状态
    document.conversion_status = ConversionStatus.PENDING
    document.conversion_error = None
    document.updated_by = current_user.username
    
    db.commit()
    db.refresh(document)
    
    # TODO: 触发异步转换任务
    
    return {
        "message": "转换任务已重新启动",
        "document_id": str(document.id),
        "conversion_status": document.conversion_status.value
    }

# ========== TIFF预览相关路由 ==========

@router.get("/{document_id}/tiff-info")
def get_tiff_info(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取TIFF文件的详细信息（页数、每页尺寸等）"""
    # 验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 检查文档是否为TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能获取图像文件（TIFF/JPEG/PNG）的信息"
        )
    
    # 获取文件路径
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        with Image.open(file_path) as img:
            # 获取图像信息
            width, height = img.size
            mode = img.mode
            format = img.format
            
            # 获取页数（对于多页TIFF）
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                # 到达文件结尾，page_count现在包含总页数
                pass
            
            # 单页图像的情况
            if page_count == 0:
                page_count = 1
            
            # 获取每页尺寸（假设所有页面尺寸相同）
            page_dimensions = []
            for i in range(page_count):
                try:
                    img.seek(i)
                    page_width, page_height = img.size
                    page_dimensions.append({
                        "page_number": i + 1,
                        "width": page_width,
                        "height": page_height,
                        "mode": img.mode
                    })
                except Exception as e:
                    # 如果无法读取某页，跳过
                    continue
            
            return {
                "document_id": str(document_id),
                "original_filename": document.original_filename,
                "file_type": document.file_type,
                "mime_type": document.mime_type,
                "total_pages": page_count,
                "format": format,
                "page_dimensions": page_dimensions,
                "file_size_bytes": document.file_size
            }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取TIFF文件时发生错误: {str(e)}"
        )


@router.get("/{document_id}/tiff-thumbnail/{page_number}")
def get_tiff_thumbnail(
    document_id: uuid.UUID,
    page_number: int = FastaPath(..., ge=1, description="页码（从1开始）"),
    width: int = Query(200, ge=50, le=800, description="缩略图宽度"),
    height: int = Query(200, ge=50, le=800, description="缩略图高度"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取TIFF文件指定页面的缩略图"""
    # 验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 检查文档是否为TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能获取图像文件（TIFF/JPEG/PNG）的缩略图"
        )
    
    # 获取文件路径
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        with Image.open(file_path) as img:
            # 获取页数
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                pass
            
            if page_count == 0:
                page_count = 1
            
            # 检查页码范围
            if page_number < 1 or page_number > page_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"页码 {page_number} 超出范围（文档共有 {page_count} 页）"
                )
            
            # 跳转到指定页面
            img.seek(page_number - 1)
            
            # 转换为RGB模式（如果需要）
            if img.mode not in ["RGB", "RGBA", "L"]:
                img = img.convert("RGB")
            
            # 生成缩略图
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # 保存为JPEG格式（压缩率较高）
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # 如果是RGBA模式，需要添加白色背景
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])  # 使用alpha通道作为遮罩
                    img = background
                
                img.save(temp_path, "JPEG", quality=85, optimize=True)
            
            # 生成文件名
            original_stem = Path(document.original_filename).stem
            download_filename = f"{original_stem}_page{page_number}_thumbnail.jpg"
            
            # 返回文件响应
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="image/jpeg",
                background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
            )
    
    except Exception as e:
        # 清理临时文件（如果存在）
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成缩略图时发生错误: {str(e)}"
        )


@router.get("/{document_id}/tiff-preview/{page_number}")
def get_tiff_preview(
    document_id: uuid.UUID,
    page_number: int = FastaPath(..., ge=1, description="页码（从1开始）"),
    max_width: int = Query(1200, ge=100, le=2500, description="预览图最大宽度"),
    max_height: int = Query(1600, ge=100, le=2500, description="预览图最大高度"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取TIFF文件指定页面的预览图像（质量较高，适合查看）"""
    # 验证文档访问权限
    document = check_document_access(document_id, current_user, db)
    
    # 检查文档是否为TIFF
    if document.file_type not in [FileType.TIFF, FileType.JPEG, FileType.JPG, FileType.PNG]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能获取图像文件（TIFF/JPEG/PNG）的预览图"
        )
    
    # 获取文件路径
    file_path = get_document_file_path(document, settings)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    try:
        with Image.open(file_path) as img:
            # 获取页数
            page_count = 0
            try:
                while True:
                    img.seek(page_count)
                    page_count += 1
            except EOFError:
                pass
            
            if page_count == 0:
                page_count = 1
            
            # 检查页码范围
            if page_number < 1 or page_number > page_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"页码 {page_number} 超出范围（文档共有 {page_count} 页）"
                )
            
            # 跳转到指定页面
            img.seek(page_number - 1)
            
            # 转换为RGB模式（如果需要）
            if img.mode not in ["RGB", "RGBA", "L"]:
                img = img.convert("RGB")
            
            # 调整大小（保持宽高比）
            original_width, original_height = img.size
            ratio = min(max_width / original_width, max_height / original_height)
            
            if ratio < 1:  # 只有在需要缩小的情况下才调整大小
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存为JPEG格式（较高质量）
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # 如果是RGBA模式，需要添加白色背景
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                
                img.save(temp_path, "JPEG", quality=90, optimize=True)
            
            # 生成文件名
            original_stem = Path(document.original_filename).stem
            download_filename = f"{original_stem}_page{page_number}_preview.jpg"
            
            # 返回文件响应
            return FileResponse(
                path=temp_path,
                filename=download_filename,
                media_type="image/jpeg",
                background=lambda: os.unlink(temp_path)  # 发送后删除临时文件
            )
    
    except Exception as e:
        # 清理临时文件（如果存在）
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成预览图时发生错误: {str(e)}"
        )


# ========== 批量操作路由 ==========

@router.post("/batch/archive")
def batch_archive_documents(
    document_ids: List[uuid.UUID],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量归档文档"""
    updated_count = 0
    
    for doc_id in document_ids:
        try:
            document = check_document_access(doc_id, current_user, db)
            document.is_archived = True
            document.updated_by = current_user.username
            updated_count += 1
        except HTTPException:
            # 跳过没有权限或找不到的文档
            continue
    
    if updated_count > 0:
        db.commit()
    
    return {
        "message": f"成功归档 {updated_count}/{len(document_ids)} 个文档",
        "updated_count": updated_count
    }


@router.post("/batch/delete")
def batch_delete_documents(
    document_ids: List[uuid.UUID],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量删除文档"""
    deleted_count = 0
    
    for doc_id in document_ids:
        try:
            document = check_document_access(doc_id, current_user, db)
            db.delete(document)
            deleted_count += 1
        except HTTPException:
            # 跳过没有权限或找不到的文档
            continue
    
    if deleted_count > 0:
        db.commit()
    
    return {
        "message": f"成功删除 {deleted_count}/{len(document_ids)} 个文档",
        "deleted_count": deleted_count
    }


@router.get("/by-path/{path:path}")
def download_document_by_path(
    request: Request,
    path: str,
    download_type: str = Query("original", description="下载类型: original 或 pdf"),
    db: Session = Depends(get_db)
):
    """
    根据原始URL路径下载文档
    
    路径格式: /content/dam/cra-arc/camp-promo/features/cvtp_bnnr_360x203.jpg
    会匹配 document_metadata.url 中包含该路径的文档
    """
    import json
    
    # 清理路径，确保以斜杠开头
    if not path.startswith('/'):
        path = '/' + path
    
    logger = logging.getLogger(__name__)
    logger.info(f"尝试通过路径查找文档: {path}")
    
    # 存储最终匹配的路径
    final_path = path
    
    # 如果路径以/content开头，也尝试不带/content的版本（为了前端预览）
    # 例如：/content/dam/... 也尝试 /dam/...
    alternative_paths = []
    if path.startswith('/content/'):
        alternative_paths.append(path[len('/content'):])  # 移除开头的/content
    elif not path.startswith('/content/') and path != '/content':
        # 如果路径不以/content开头，尝试添加/content前缀
        alternative_paths.append('/content' + path)
    
    # 手动处理用户认证（支持匿名访问图片文件）
    current_user = None
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # 移除"Bearer "前缀
            from app.core.security import get_current_user
            user = get_current_user(db, token)
            if user and user.is_active:
                current_user = user
                logger.info(f"通过token认证用户: {current_user.username}")
    
    # 如果没有认证用户，创建public用户
    if not current_user:
        from app.models.user import User
        current_user = User(
            id=str(uuid.uuid4()),
            username="public",
            email="public@example.com",
            full_name="Public User",
            is_superuser=False,
            is_active=True,
            role="public"
        )
        logger.info("使用public用户（匿名访问）")
    
    # 查询所有文档，查找匹配的URL
    all_documents = db.query(Document).all()
    matched_documents = []
    
    # 尝试的路径列表：原始路径 + 替代路径
    paths_to_try = [path] + alternative_paths
    logger.info(f"尝试匹配的路径列表: {paths_to_try}")
    
    for doc in all_documents:
        if not doc.document_metadata:
            continue
        
        try:
            metadata = json.loads(doc.document_metadata) if isinstance(doc.document_metadata, str) else doc.document_metadata
            url = metadata.get('url') or metadata.get('original_url')
            if url:
                parsed = urlparse(url)
                url_path = parsed.path
                
                # 检查是否匹配任何一个路径
                for try_path in paths_to_try:
                    # 如果路径完全匹配或以路径开头
                    if url_path == try_path or url_path.endswith(try_path):
                        matched_documents.append((doc, url, try_path))
                        logger.info(f"文档 {doc.id} 匹配路径 {try_path} (原始URL: {url})")
                        break  # 找到一个匹配就停止检查其他路径
        except (json.JSONDecodeError, TypeError):
            continue
    
    if not matched_documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到路径匹配的文档。尝试的路径: {paths_to_try}"
        )
    
    # 如果有多个匹配，选择第一个（TODO: 可能需要更精确的匹配）
    if len(matched_documents) > 1:
        logger.warning(f"找到 {len(matched_documents)} 个匹配文档，使用第一个")
    
    document, matched_url, matched_path = matched_documents[0]
    logger.info(f"使用匹配的文档: {document.id}, 路径: {matched_path}")
    
    # 检查是否是图片文件类型（允许公开访问）
    is_image_file = document.file_type in [
        FileType.JPG, FileType.JPEG, FileType.PNG, FileType.TIFF
    ]
    
    # 对于所有通过URL路径访问的文档，都必须已发布
    # 首先获取完整的文档信息
    document_id_str = str(document.id)
    document = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    ).filter(Document.id == document_id_str).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 检查发布状态：只有PUBLISHED状态的文档可以通过URL访问
    # 如果publish_status为None（旧文档），允许访问以保持向后兼容
    
    # 检查是否为WebBot请求（特殊权限允许访问未发布文档）
    is_webbot_request = request.headers.get("X-WebBot-Access") == "true"
    if is_webbot_request:
        logger.info(f"WebBot请求访问未发布文档 {document.id}，跳过发布状态检查")
    elif document.publish_status is not None and document.publish_status != PublishStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="文档未发布，无法通过URL访问"
        )
    
    if is_image_file:
        # 对于图片文件，跳过进一步的权限检查
        logger.info(f"图片文件 {document.original_filename} 跳过权限检查，允许公开访问")
    else:
        # 对于非图片文件，进行完整的权限检查
        document = check_document_access(document.id, current_user, db)
    
    # 直接提供文件下载，复用 download_document 的逻辑
    # 确定文件路径和文件名
    file_path = None
    filename = document.original_filename
    
    if download_type == "pdf" and document.converted_pdf_path:
        # 下载PDF版本
        file_path = document.converted_pdf_path
        filename = f"{Path(document.original_filename).stem}.pdf"
    else:
        # 下载原始文件
        file_path = get_document_file_path(document, settings)
        filename = document.original_filename
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 确定media_type：使用文档的mime_type，如果不存在则根据文件扩展名判断
    media_type = document.mime_type if document.mime_type else "application/octet-stream"
    
    # 如果mime_type为空或未知，根据文件扩展名设置
    if not media_type or media_type == "application/octet-stream":
        if filename.lower().endswith(('.html', '.htm')):
            media_type = "text/html"
        elif filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif filename.lower().endswith('.png'):
            media_type = "image/png"
        elif filename.lower().endswith('.tiff') or filename.lower().endswith('.tif'):
            media_type = "image/tiff"
    
    logger.info(f"通过路径找到文档: {document.id}, 文件: {filename}, 类型: {media_type}")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )