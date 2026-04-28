from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.folder import Folder
from app.models.document import Document
from app.models.page import Page
from app.schemas.document import PageResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/path", response_model=List[PageResponse])
def get_pages_by_path(
    path: str = Query(..., description="文件夹路径，格式: /app_slug/folder/subfolder"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    include_subfolders: bool = Query(False, description="是否包含子文件夹中的文档"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """根据文件夹路径获取页面列表
    
    通过文件夹路径获取该路径下的所有文档的所有页面。
    路径格式: /app_slug/folder/subfolder
    
    参数:
    - path: 文件夹路径
    - skip: 分页跳过数
    - limit: 每页数量
    - include_subfolders: 是否递归包含子文件夹中的文档
    """
    # 验证路径格式
    if not path or not path.startswith('/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径必须以斜杠开头，格式: /app_slug/folder/subfolder"
        )
    
    # 规范化路径：移除尾随斜杠（除非是根路径）
    normalized_path = path.rstrip('/') if path != '/' else path
    
    # 通过路径查找文件夹，支持带或不带尾随斜杠的路径
    folder = db.query(Folder).filter(
        (Folder.path == normalized_path) | 
        (Folder.path == normalized_path + '/')
    ).first()
    if not folder:
        # 如果文件夹不存在，尝试通过parent_folder_path查找
        # 但为了安全起见，先检查文件夹是否存在
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到路径对应的文件夹: {path}"
        )
    
    # 验证用户是否有权限访问该文件夹
    try:
        # check_folder_access期望UUID，但我们的folder.id是字符串
        # 转换为UUID进行验证
        folder_uuid = uuid.UUID(folder.id)
        
        # 导入check_folder_access函数
        from app.routers.documents import check_folder_access
        folder = check_folder_access(folder_uuid, current_user, db)
    except ValueError as e:
        logger.error(f"文件夹ID转换错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文件夹ID格式"
        )
    except Exception as e:
        logger.error(f"文件夹访问权限检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限访问此文件夹"
        )
    
    # 构建文档查询
    if include_subfolders:
        # 递归获取所有子文件夹的文档
        # 通过parent_folder_path查找所有以当前路径开头的文件夹
        folder_path_prefix = f"{path}/"
        subfolders = db.query(Folder).filter(
            Folder.parent_folder_path.like(f"{folder_path_prefix}%")
        ).all()
        
        # 收集所有相关文件夹的ID
        folder_ids = [folder.id] + [f.id for f in subfolders]
        
        # 查询这些文件夹下的所有文档
        documents_query = db.query(Document).filter(
            Document.folder_id.in_(folder_ids)
        )
    else:
        # 只查询当前文件夹下的文档
        documents_query = db.query(Document).filter(
            Document.folder_id == folder.id
        )
    
    # 获取文档ID列表
    documents = documents_query.all()
    if not documents:
        # 如果没有文档，返回空列表
        return []
    
    document_ids = [doc.id for doc in documents]
    
    # 查询这些文档的所有页面
    pages_query = db.query(Page).filter(
        Page.document_id.in_(document_ids)
    ).order_by(
        Page.document_id,
        Page.page_number
    )
    
    # 应用分页
    pages = pages_query.offset(skip).limit(limit).all()
    
    # 返回页面列表
    return pages