from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional, Dict, Any
import traceback

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.app import App
from app.models.folder import Folder
from app.models.permission import Permission
from app.models.group import GroupMember
from app.models.document import Document, ConversionStatus, FileType, DocumentStatus, DocumentType
from app.models.page import Page
from app.schemas.document import DocumentResponse, PageResponse

router = APIRouter()


# ========== Permission Check Helpers ==========

def build_permission_query(current_user: User, db: Session):
    """Build permission-filtered base query: users can only access documents under their apps
    
    Returns:
        Query object with permission filter applied
    """
    from sqlalchemy.orm import aliased
    
    # Base query, join to folder and app (drawer layer removed)
    query = db.query(Document).options(
        joinedload(Document.folder).joinedload(Folder.app)
    )
    
    if current_user.is_superuser or current_user.username == "public":
        # Admin/public can access all documents
        return query
    
    # Regular users: their own apps + apps/folders they have permission on
    from app.models.permission import Permission
    from app.models.group import GroupMember
    
    # Owned apps
    owned_app_ids = [row[0] for row in db.query(App.id).filter(App.owner_id == current_user.id).all()]
    
    # Apps with direct user permission
    permitted_app_ids = [
        row[0] for row in db.query(Permission.resource_id)
        .filter(
            Permission.resource_type == "app",
            Permission.user_id == current_user.id,
        )
        .all()
    ]
    
    # Apps with group permission
    user_group_ids = [
        row[0] for row in db.query(GroupMember.group_id)
        .filter(GroupMember.user_id == current_user.id)
        .all()
    ]
    if user_group_ids:
        group_permitted_ids = [
            row[0] for row in db.query(Permission.resource_id)
            .filter(
                Permission.resource_type == "app",
                Permission.group_id.in_(user_group_ids),
            )
            .all()
        ]
        permitted_app_ids = list(set(permitted_app_ids + group_permitted_ids))
    
    # Also include folders user has permission on
    permitted_folder_paths = [
        row[0] for row in db.query(Permission.resource_id)
        .filter(
            Permission.resource_type == "folder",
            Permission.user_id == current_user.id,
        )
        .all()
    ]
    if user_group_ids:
        group_permitted_folder_paths = [
            row[0] for row in db.query(Permission.resource_id)
            .filter(
                Permission.resource_type == "folder",
                Permission.group_id.in_(user_group_ids),
            )
            .all()
        ]
        permitted_folder_paths = list(set(permitted_folder_paths + group_permitted_folder_paths))
    
    all_app_ids = list(set(owned_app_ids + permitted_app_ids))
    
    # Build query filter: docs in user's apps OR docs in permitted folders
    if all_app_ids or permitted_folder_paths:
        query = query.join(Folder).join(App)
        conditions = []
        if all_app_ids:
            conditions.append(App.id.in_(all_app_ids))
        if permitted_folder_paths:
            conditions.append(Folder.path.in_(permitted_folder_paths))
        query = query.filter(or_(*conditions))
    else:
        # No permissions at all, return empty set
        query = query.filter(False)
    
    return query


# ========== Search Routes ==========

@router.get("/documents", response_model=List[DocumentResponse])
def search_documents(
    # Document attribute search
    title: Optional[str] = Query(None, description="Document title (fuzzy match)"),
    description: Optional[str] = Query(None, description="Document description (fuzzy match)"),
    document_number: Optional[str] = Query(None, description="Document number (exact match)"),
    
    # Document status filters
    status: Optional[DocumentStatus] = Query(None, description="Document status"),
    document_type: Optional[DocumentType] = Query(None, description="Document type"),
    conversion_status: Optional[ConversionStatus] = Query(None, description="Conversion status"),
    
    # File attribute filters
    file_type: Optional[FileType] = Query(None, description="File type"),
    mime_type: Optional[str] = Query(None, description="MIME type"),
    
    # Folder-related filters
    folder_path: Optional[str] = Query(None, description="Filter by folder path"),
    app_id: Optional[str] = Query(None, description="Filter by app ID"),
    
    # Uploader filter
    uploaded_by: Optional[str] = Query(None, description="Uploader user ID"),
    
    # Time range filters
    created_after: Optional[str] = Query(None, description="Created after (format: YYYY-MM-DD)"),
    created_before: Optional[str] = Query(None, description="Created before (format: YYYY-MM-DD)"),
    updated_after: Optional[str] = Query(None, description="Updated after (format: YYYY-MM-DD)"),
    updated_before: Optional[str] = Query(None, description="Updated before (format: YYYY-MM-DD)"),
    
    # Archive status
    is_archived: Optional[bool] = Query(None, description="Is archived"),
    
    # Path filter
    path: Optional[str] = Query(None, description="Path prefix match (LIKE 'path%')"),
    
    # Pagination
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    
    # Sort parameters
    sort_by: Optional[str] = Query("created_at", description="Sort field: created_at, updated_at, title, file_size"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search documents
    
    Supports multi-condition combined search, including document attributes, status, folder hierarchy, time range, etc.
    """
    try:
        # Build base query (permission filter already applied)
        query = build_permission_query(current_user, db)
    
        # ===== Document attribute search =====
        if title:
            query = query.filter(Document.title.ilike(f"%{title}%"))
    
        if description:
            query = query.filter(Document.description.ilike(f"%{description}%"))
    
        if document_number:
            query = query.filter(Document.document_number == document_number)
    
        # ===== Document status filters =====
        if status:
            query = query.filter(Document.status == status)
    
        if document_type:
            query = query.filter(Document.type == document_type)
    
        if conversion_status:
            query = query.filter(Document.conversion_status == conversion_status)
    
        # ===== File attribute filters =====
        if file_type:
            query = query.filter(Document.file_type == file_type)
    
        if mime_type:
            query = query.filter(Document.mime_type.ilike(f"%{mime_type}%"))
    
        # ===== Folder hierarchy filters =====
        if folder_path:
            # Verify user has permission to access this folder
            try:
                from app.routers.documents import check_folder_access
                check_folder_access(folder_path, current_user, db)
                query = query.filter(Document.folder_path == folder_path)
            except HTTPException:
                # User has no permission, return empty
                return []
    
        if app_id:
            # Join directly through folder -> app (drawer layer removed)
            query = query.join(Folder).filter(Folder.app_id == app_id)
    
        # ===== Uploader filter =====
        if uploaded_by:
            query = query.filter(Document.uploaded_by == uploaded_by)
    
        # ===== Path filter =====
        if path:
            # Use LIKE for prefix matching
            query = query.filter(Document.path.like(f"{path}%"))
    
        # ===== Time range filters =====
        if created_after:
            query = query.filter(Document.created_at >= created_after)
    
        if created_before:
            query = query.filter(Document.created_at <= created_before)
    
        if updated_after:
            query = query.filter(Document.updated_at >= updated_after)
    
        if updated_before:
            query = query.filter(Document.updated_at <= updated_before)
    
        # ===== Archive status filter =====
        if is_archived is not None:
            query = query.filter(Document.is_archived == is_archived)
    
        # ===== Sorting =====
        sort_field_map = {
            "created_at": Document.created_at,
            "updated_at": Document.updated_at,
            "title": Document.title,
            "file_size": Document.file_size,
        }
    
        sort_field = sort_field_map.get(sort_by, Document.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())
    
        # ===== Pagination =====
        documents = query.offset(skip).limit(limit).all()
    
        return documents

    except Exception as e:
        print(f"[FileBot Search Error] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/pages", response_model=List[PageResponse])
def search_pages(
    # Index field search (9 index fields)
    index1: Optional[str] = Query(None, description="Index field 1 (fuzzy match)"),
    index2: Optional[str] = Query(None, description="Index field 2 (fuzzy match)"),
    index3: Optional[str] = Query(None, description="Index field 3 (fuzzy match)"),
    index4: Optional[str] = Query(None, description="Index field 4 (fuzzy match)"),
    index5: Optional[str] = Query(None, description="Index field 5 (fuzzy match)"),
    index6: Optional[str] = Query(None, description="Index field 6 (fuzzy match)"),
    index7: Optional[str] = Query(None, description="Index field 7 (fuzzy match)"),
    index8: Optional[str] = Query(None, description="Index field 8 (fuzzy match)"),
    index9: Optional[str] = Query(None, description="Index field 9 (fuzzy match)"),
    
    # Page range
    page_min: Optional[int] = Query(None, ge=1, description="Minimum page number"),
    page_max: Optional[int] = Query(None, ge=1, description="Maximum page number"),
    
    # OCR text search
    ocr_text: Optional[str] = Query(None, description="OCR text (fuzzy match)"),
    
    # Size filters
    width_min: Optional[int] = Query(None, ge=0, description="Minimum width"),
    width_max: Optional[int] = Query(None, ge=0, description="Maximum width"),
    height_min: Optional[int] = Query(None, ge=0, description="Minimum height"),
    height_max: Optional[int] = Query(None, ge=0, description="Maximum height"),
    
    # Pagination
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search pages (based on index fields)
    
    Core search functionality, searching based on 9 index fields.
    Results return full page information including associated documents.
    """
    # Build base query, join documents for permission check (drawer layer removed)
    query = db.query(Page).options(
        joinedload(Page.document).joinedload(Document.folder).joinedload(Folder.app)
    )
    
    # Apply permission filter: only pages under accessible documents
    if not current_user.is_superuser:
        # Regular users: permission filter through document -> folder -> app chain
        user_apps_subquery = db.query(App.id).filter(App.owner_id == current_user.id).subquery()
        
        query = query.join(Document).join(Folder).join(App)
        query = query.filter(App.id.in_(user_apps_subquery))
    
    # ===== Index field search =====
    # Support combined search with multiple index fields (AND relationship)
    index_filters = []
    
    if index1:
        index_filters.append(Page.index1.ilike(f"%{index1}%"))
    if index2:
        index_filters.append(Page.index2.ilike(f"%{index2}%"))
    if index3:
        index_filters.append(Page.index3.ilike(f"%{index3}%"))
    if index4:
        index_filters.append(Page.index4.ilike(f"%{index4}%"))
    if index5:
        index_filters.append(Page.index5.ilike(f"%{index5}%"))
    if index6:
        index_filters.append(Page.index6.ilike(f"%{index6}%"))
    if index7:
        index_filters.append(Page.index7.ilike(f"%{index7}%"))
    if index8:
        index_filters.append(Page.index8.ilike(f"%{index8}%"))
    if index9:
        index_filters.append(Page.index9.ilike(f"%{index9}%"))
    
    if index_filters:
        query = query.filter(and_(*index_filters))
    
    # ===== Page range filters =====
    if page_min:
        query = query.filter(Page.page_number >= page_min)
    
    if page_max:
        query = query.filter(Page.page_number <= page_max)
    
    # ===== OCR text search =====
    if ocr_text:
        query = query.filter(Page.ocr_text.ilike(f"%{ocr_text}%"))
    
    # ===== Size filters =====
    if width_min:
        query = query.filter(Page.width >= width_min)
    
    if width_max:
        query = query.filter(Page.width <= width_max)
    
    if height_min:
        query = query.filter(Page.height >= height_min)
    
    if height_max:
        query = query.filter(Page.height <= height_max)
    
    # ===== Sort and paginate =====
    query = query.order_by(Page.document_path, Page.page_number)
    pages = query.offset(skip).limit(limit).all()
    
    return pages


@router.get("/combined", response_model=List[DocumentResponse])
def combined_search(
    # Document search parameters (reusing document search params)
    title: Optional[str] = Query(None, description="Document title (fuzzy match)"),
    description: Optional[str] = Query(None, description="Document description (fuzzy match)"),
    document_number: Optional[str] = Query(None, description="Document number (exact match)"),
    
    # Page index search parameters
    index1: Optional[str] = Query(None, description="Index field 1 (fuzzy match)"),
    index2: Optional[str] = Query(None, description="Index field 2 (fuzzy match)"),
    index3: Optional[str] = Query(None, description="Index field 3 (fuzzy match)"),
    index4: Optional[str] = Query(None, description="Index field 4 (fuzzy match)"),
    index5: Optional[str] = Query(None, description="Index field 5 (fuzzy match)"),
    index6: Optional[str] = Query(None, description="Index field 6 (fuzzy match)"),
    index7: Optional[str] = Query(None, description="Index field 7 (fuzzy match)"),
    index8: Optional[str] = Query(None, description="Index field 8 (fuzzy match)"),
    index9: Optional[str] = Query(None, description="Index field 9 (fuzzy match)"),
    
    # OCR text search
    ocr_text: Optional[str] = Query(None, description="OCR text (fuzzy match)"),
    
    # Other filters
    status: Optional[DocumentStatus] = Query(None, description="Document status"),
    document_type: Optional[DocumentType] = Query(None, description="Document type"),
    folder_path: Optional[str] = Query(None, description="Filter by folder path"),
    
    # Pagination
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Combined search: search based on both document attributes and page index fields
    
    This is the most powerful search feature, enabling document-level search
    while filtering by page index fields. Returns documents matching all conditions.
    """
    # Build base document query (permission filter already applied)
    query = build_permission_query(current_user, db)
    
    # ===== Document attribute search =====
    if title:
        query = query.filter(Document.title.ilike(f"%{title}%"))
    
    if description:
        query = query.filter(Document.description.ilike(f"%{description}%"))
    
    if document_number:
        query = query.filter(Document.document_number == document_number)
    
    if status:
        query = query.filter(Document.status == status)
    
    if document_type:
        query = query.filter(Document.type == document_type)
    
    if folder_path:
        try:
            from app.routers.documents import check_folder_access
            check_folder_access(folder_path, current_user, db)
            query = query.filter(Document.folder_path == folder_path)
        except HTTPException:
            return []
    
    # ===== Page index field search =====
    # If any index field or OCR text condition is provided, join pages table
    has_page_conditions = any([
        index1, index2, index3, index4, index5, index6, index7, index8, index9, ocr_text
    ])
    
    if has_page_conditions:
        # Join pages table
        query = query.join(Page)
        
        # Build page conditions
        page_conditions = []
        
        if index1:
            page_conditions.append(Page.index1.ilike(f"%{index1}%"))
        if index2:
            page_conditions.append(Page.index2.ilike(f"%{index2}%"))
        if index3:
            page_conditions.append(Page.index3.ilike(f"%{index3}%"))
        if index4:
            page_conditions.append(Page.index4.ilike(f"%{index4}%"))
        if index5:
            page_conditions.append(Page.index5.ilike(f"%{index5}%"))
        if index6:
            page_conditions.append(Page.index6.ilike(f"%{index6}%"))
        if index7:
            page_conditions.append(Page.index7.ilike(f"%{index7}%"))
        if index8:
            page_conditions.append(Page.index8.ilike(f"%{index8}%"))
        if index9:
            page_conditions.append(Page.index9.ilike(f"%{index9}%"))
        
        if ocr_text:
            page_conditions.append(Page.ocr_text.ilike(f"%{ocr_text}%"))
        
        if page_conditions:
            query = query.filter(or_(*page_conditions))
        
        # Use distinct to avoid duplicate documents
        query = query.distinct()
    
    # ===== Sort and paginate =====
    query = query.order_by(Document.created_at.desc())
    documents = query.offset(skip).limit(limit).all()
    
    return documents


@router.get("/advanced", response_model=Dict[str, Any])
def advanced_search(
    # Search mode
    search_mode: str = Query("and", description="Search mode: and, or"),
    
    # Search keywords (comma-separated)
    keywords: Optional[str] = Query(None, description="Keywords, comma-separated, e.g.: invoice,2024,contract"),
    
    # Search field scope
    search_fields: Optional[str] = Query(
        "all",
        description="Search fields: all, title, description, indices, ocr, document_number"
    ),
    
    # Other parameters
    folder_path: Optional[str] = Query(None, description="Filter by folder path"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Advanced search: multi-keyword, multi-field, boolean search
    
    This interface is for advanced users, supporting more complex search requirements.
    """
    if not keywords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keywords are required"
        )
    
    # Parse keywords
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    
    # Build base query
    query = build_permission_query(current_user, db)
    
    # Apply folder filter
    if folder_path:
        try:
            from app.routers.documents import check_folder_access
            check_folder_access(folder_path, current_user, db)
            query = query.filter(Document.folder_path == folder_path)
        except HTTPException:
            return {"results": [], "total": 0, "keywords": keyword_list}
    
    # Build search conditions
    search_conditions = []
    
    # Determine search fields
    if search_fields == "all" or "title" in search_fields:
        for keyword in keyword_list:
            search_conditions.append(Document.title.ilike(f"%{keyword}%"))
    
    if search_fields == "all" or "description" in search_fields:
        for keyword in keyword_list:
            search_conditions.append(Document.description.ilike(f"%{keyword}%"))
    
    if search_fields == "all" or "document_number" in search_fields:
        for keyword in keyword_list:
            search_conditions.append(Document.document_number.ilike(f"%{keyword}%"))
    
    # If searching index fields or OCR text, join pages table
    if search_fields == "all" or "indices" in search_fields or "ocr" in search_fields:
        query = query.join(Page)
        
        if search_fields == "all" or "indices" in search_fields:
            for keyword in keyword_list:
                # Search all 9 index fields
                index_conditions = or_(
                    Page.index1.ilike(f"%{keyword}%"),
                    Page.index2.ilike(f"%{keyword}%"),
                    Page.index3.ilike(f"%{keyword}%"),
                    Page.index4.ilike(f"%{keyword}%"),
                    Page.index5.ilike(f"%{keyword}%"),
                    Page.index6.ilike(f"%{keyword}%"),
                    Page.index7.ilike(f"%{keyword}%"),
                    Page.index8.ilike(f"%{keyword}%"),
                    Page.index9.ilike(f"%{keyword}%"),
                )
                search_conditions.append(index_conditions)
        
        if search_fields == "all" or "ocr" in search_fields:
            for keyword in keyword_list:
                search_conditions.append(Page.ocr_text.ilike(f"%{keyword}%"))
        
        # Use distinct to avoid duplicate documents
        query = query.distinct()
    
    # Apply search conditions
    if search_conditions:
        if search_mode == "and":
            # AND mode: must match all keywords
            for condition in search_conditions:
                query = query.filter(condition)
        else:
            # OR mode: match any keyword
            query = query.filter(or_(*search_conditions))
    
    # Count total
    total = query.count()
    
    # Apply pagination
    query = query.order_by(Document.created_at.desc())
    documents = query.offset(skip).limit(limit).all()
    
    return {
        "results": documents,
        "total": total,
        "keywords": keyword_list,
        "search_mode": search_mode,
        "search_fields": search_fields,
        "pagination": {
            "skip": skip,
            "limit": limit,
            "has_more": (skip + limit) < total
        }
    }
