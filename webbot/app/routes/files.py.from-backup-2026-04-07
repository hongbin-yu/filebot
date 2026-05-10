"""
文件管理路由 - 集成FileBot文件功能
提供文件上传、列表、预览功能，界面与WebBot一体

第一阶段：模拟实现，返回示例数据
第二阶段：集成FileBot API调用

现在实现第二阶段：集成真实的FileBot文档访问
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import RedirectResponse, Response
import uuid
import os
from datetime import datetime
from typing import Optional, List
import json
import sqlite3
import requests

# aiohttp是可选的，用于转发上传到FileBot
try:
    import aiohttp
    import asyncio
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("⚠️  aiohttp模块未安装，文件上传转发到FileBot将不可用")

# FileBot数据库路径（与WebBot共享）
FILEBOT_DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = sqlite3.connect(FILEBOT_DB_PATH)
        conn.row_factory = sqlite3.Row  # 返回字典格式的结果
        return conn
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        raise

router = APIRouter(prefix="/api/v1/files", tags=["files"])

# 模拟文件数据存储（内存中）
mock_files_db = [
    {
        "id": "doc-001",
        "name": "example-document.pdf",
        "type": "application/pdf",
        "size": 1024576,
        "uploaded_at": "2026-04-02T10:30:00Z",
        "description": "示例PDF文档",
        "url": "/api/v1/files/doc-001/download",
        "thumbnail_url": "/api/v1/files/doc-001/thumbnail"
    },
    {
        "id": "img-001",
        "name": "logo.png",
        "type": "image/png",
        "size": 245760,
        "uploaded_at": "2026-04-02T11:15:00Z",
        "description": "网站Logo图片",
        "url": "/api/v1/files/img-001/download",
        "thumbnail_url": "/api/v1/files/img-001/thumbnail"
    },
    {
        "id": "img-002",
        "name": "banner.jpg",
        "type": "image/jpeg",
        "size": 512000,
        "uploaded_at": "2026-04-02T12:45:00Z",
        "description": "首页横幅图片",
        "url": "/api/v1/files/img-002/download",
        "thumbnail_url": "/api/v1/files/img-002/thumbnail"
    },
    {
        "id": "doc-002",
        "name": "user-manual.docx",
        "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size": 2048000,
        "uploaded_at": "2026-04-02T14:20:00Z",
        "description": "用户手册文档",
        "url": "/api/v1/files/doc-002/download",
        "thumbnail_url": "/api/v1/files/doc-002/thumbnail"
    }
]

# 存储上传的文件元数据（内存中，重启会丢失）
uploaded_files = mock_files_db.copy()

@router.get("/")
async def list_files(
    folder_id: Optional[str] = Query(None, description="文件夹ID"),
    limit: int = Query(50, ge=1, le=100, description="返回文件数量"),
    offset: int = Query(0, ge=0, description="分页偏移量")
):
    """
    获取文件列表 - 集成FileBot真实数据
    """
    try:
        # 首先尝试从FileBot数据库获取真实数据
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 构建查询
            query = """
                SELECT id, original_filename, stored_filename, file_size, 
                       file_type, mime_type, title, description, created_at,
                       converted_pdf_path
                FROM documents
                WHERE status = 'active' AND is_archived = 0
            """
            
            params = []
            if folder_id and folder_id != "default-folder":
                # 如果需要文件夹筛选，但FileBot有folder_id字段
                # 先简单实现，不筛选文件夹
                pass
                
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # 获取总数
            count_query = "SELECT COUNT(*) as total FROM documents WHERE status = 'active' AND is_archived = 0"
            cursor.execute(count_query)
            total = cursor.fetchone()["total"]
            
            # 转换为API响应格式
            files = []
            for row in rows:
                # 构建下载URL - 指向FileBot的API
                # FileBot运行在端口8001
                download_url = f"http://localhost:8001/api/v1/documents/{row['id']}/download"
                
                # 如果是PDF且有转换后路径，优先使用转换后的PDF
                if row['converted_pdf_path'] and os.path.exists(row['converted_pdf_path']):
                    # 对于转换后的PDF，可能需要不同的URL
                    download_url = f"http://localhost:8001/api/v1/documents/{row['id']}/download?converted=true"
                
                file_record = {
                    "id": row["id"],
                    "name": row["original_filename"],
                    "type": row["mime_type"],
                    "size": row["file_size"],
                    "uploaded_at": row["created_at"] if row["created_at"] else datetime.utcnow().isoformat() + "Z",
                    "description": row["description"] or row["title"] or f"FileBot document: {row['original_filename']}",
                    "url": download_url,
                    "thumbnail_url": f"/api/v1/files/{row['id']}/thumbnail",
                    "source": "filebot",  # 标记来源为FileBot
                    "file_type": row["file_type"]  # 原始文件类型
                }
                files.append(file_record)
            
            conn.close()
            
            # 总是包含模拟上传的文件（用于测试）
            # 合并数据库文件和模拟文件，去重
            all_files = files.copy()
            for mock_file in uploaded_files:
                # 检查是否已存在（基于ID）
                if not any(f['id'] == mock_file['id'] for f in all_files):
                    all_files.append(mock_file)
            
            files = all_files
            total = len(files)
            
            return {
                "files": files,
                "total": total,
                "limit": limit,
                "offset": offset,
                "folder_id": folder_id or "default-folder",
                "source": "filebot-database" if total > 0 else "mock-data-fallback"
            }
            
        except Exception as db_error:
            # 如果数据库查询失败，回退到模拟数据
            print(f"数据库查询失败，回退到模拟数据: {db_error}")
            if conn:
                conn.close()
            
            # 应用分页到模拟数据
            start = offset
            end = offset + limit
            paginated_files = uploaded_files[start:end]
            
            return {
                "files": paginated_files,
                "total": len(uploaded_files),
                "limit": limit,
                "offset": offset,
                "folder_id": folder_id or "default-folder",
                "source": "mock-data-fallback"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """
    上传文件 - 尝试转发到FileBot，失败则使用模拟存储
    """
    try:
        # 读取文件内容
        contents = await file.read()
        file_size = len(contents)
        
        # 首先尝试转发到FileBot API（如果aiohttp可用）
        if AIOHTTP_AVAILABLE:
            try:
                # 创建FormData
                form_data = aiohttp.FormData()
                form_data.add_field('file', contents, filename=file.filename, content_type=file.content_type)
                if folder_id:
                    form_data.add_field('folder_id', folder_id)
                if title:
                    form_data.add_field('title', title)
                if description:
                    form_data.add_field('description', description)
                
                # 发送到FileBot，添加X-WebBot-Access头
                filebot_url = "http://localhost:8001/api/v1/documents/upload/"
                
                # 设置较短的超时时间
                timeout = aiohttp.ClientTimeout(total=30)
                
                # 添加X-WebBot-Access头，允许WebBot访问
                headers = {"X-WebBot-Access": "true"}
                
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.post(filebot_url, data=form_data) as response:
                        if response.status == 200:
                            filebot_result = await response.json()
                            
                            # 从FileBot响应中提取文件信息
                            file_record = {
                                "id": filebot_result.get("id", f"filebot-{uuid.uuid4().hex[:8]}"),
                                "name": file.filename,
                                "type": file.content_type or "application/octet-stream",
                                "size": file_size,
                                "uploaded_at": datetime.utcnow().isoformat() + "Z",
                                "description": description or f"Uploaded to FileBot: {file.filename}",
                                "url": f"/api/v1/files/{filebot_result.get('id')}/download",
                                "thumbnail_url": f"/api/v1/files/{filebot_result.get('id')}/thumbnail",
                                "source": "filebot-api",
                                "filebot_response": filebot_result
                            }
                            
                            return {
                                "success": True,
                                "file": file_record,
                                "message": "文件已成功上传到FileBot系统",
                                "forwarded_to_filebot": True
                            }
                        else:
                            # FileBot API失败，继续到模拟存储
                            error_text = await response.text()
                            print(f"FileBot上传失败 ({response.status}): {error_text}")
                            raise Exception(f"FileBot API返回 {response.status}")
                            
            except Exception as filebot_error:
                print(f"转发到FileBot失败，使用模拟存储: {filebot_error}")
                # 继续到模拟存储
        
        # 如果aiohttp不可用，或者转发失败，使用模拟存储
        file_id = f"file-{uuid.uuid4().hex[:8]}"
        
        # 创建文件记录
        file_record = {
            "id": file_id,
            "name": file.filename,
            "type": file.content_type or "application/octet-stream",
            "size": file_size,
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "description": description or f"Uploaded file: {file.filename}",
            "url": f"/api/v1/files/{file_id}/download",
            "thumbnail_url": f"/api/v1/files/{file_id}/thumbnail",
            "source": "mock-storage"
        }
        
        # 添加到内存数据库
        uploaded_files.insert(0, file_record)  # 添加到开头
        
        forwarded = AIOHTTP_AVAILABLE  # 如果aiohttp可用，我们至少尝试过转发
        return {
            "success": True,
            "file": file_record,
            "message": "文件上传成功" + ("（使用模拟存储）" if not AIOHTTP_AVAILABLE else "（使用模拟存储，FileBot不可用）"),
            "forwarded_to_filebot": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    finally:
        await file.close()

@router.get("/{file_id}")
async def get_file_info(file_id: str):
    """
    获取文件详细信息 - 集成FileBot真实数据
    """
    try:
        # 首先尝试从FileBot数据库获取真实数据
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, original_filename, stored_filename, file_size, 
                   file_type, mime_type, title, description, created_at,
                   converted_pdf_path, page_count, resolution, document_metadata
            FROM documents
            WHERE id = ? AND status = 'active' AND is_archived = 0
        """
        
        cursor.execute(query, (file_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # 构建下载URL
            download_url = f"http://localhost:8001/api/v1/documents/{row['id']}/download"
            
            # 如果是PDF且有转换后路径
            if row['converted_pdf_path'] and os.path.exists(row['converted_pdf_path']):
                download_url = f"http://localhost:8001/api/v1/documents/{row['id']}/download?converted=true"
            
            # 解析文档元数据
            metadata = {}
            if row['document_metadata']:
                try:
                    metadata = json.loads(row['document_metadata']) if isinstance(row['document_metadata'], str) else row['document_metadata']
                except:
                    metadata = {}
            
            file_info = {
                "id": row["id"],
                "name": row["original_filename"],
                "type": row["mime_type"],
                "size": row["file_size"],
                "uploaded_at": row["created_at"] if row["created_at"] else datetime.utcnow().isoformat() + "Z",
                "description": row["description"] or row["title"] or f"FileBot document: {row['original_filename']}",
                "url": download_url,
                "thumbnail_url": f"/api/v1/files/{row['id']}/thumbnail",
                "source": "filebot",
                "file_type": row["file_type"],
                "page_count": row["page_count"],
                "resolution": row["resolution"],
                "metadata": metadata,
                "converted_pdf_available": bool(row['converted_pdf_path'] and os.path.exists(row['converted_pdf_path']))
            }
            return file_info
        
        # 如果数据库中找不到，回退到模拟数据
        for file in uploaded_files:
            if file["id"] == file_id:
                return file
        
        # 如果模拟数据中也找不到，返回示例数据
        return {
            "id": file_id,
            "name": f"example-file-{file_id}.pdf",
            "type": "application/pdf",
            "size": 1048576,
            "uploaded_at": "2026-04-02T10:30:00Z",
            "description": "示例文件（未在FileBot中找到）",
            "url": f"/api/v1/files/{file_id}/download",
            "thumbnail_url": f"/api/v1/files/{file_id}/thumbnail",
            "source": "mock-data"
        }
        
    except Exception as e:
        # 出错时回退到模拟数据
        for file in uploaded_files:
            if file["id"] == file_id:
                return file
        
        # 如果模拟数据中也找不到，返回示例数据
        return {
            "id": file_id,
            "name": f"example-file-{file_id}.pdf",
            "type": "application/pdf",
            "size": 1048576,
            "uploaded_at": "2026-04-02T10:30:00Z",
            "description": f"示例文件（查询错误: {str(e)}）",
            "url": f"/api/v1/files/{file_id}/download",
            "thumbnail_url": f"/api/v1/files/{file_id}/thumbnail",
            "source": "error-fallback"
        }

@router.get("/{file_id}/download")
async def download_file(file_id: str, converted: bool = Query(False, description="是否下载转换后的PDF版本")):
    """
    下载文件 - 重定向到FileBot的下载端点
    """
    try:
        # 首先检查文件是否存在于FileBot数据库中
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT id FROM documents WHERE id = ? AND status = 'active' AND is_archived = 0"
        cursor.execute(query, (file_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # 文件存在，重定向到FileBot的下载端点
            # FileBot运行在端口8001
            filebot_url = f"http://localhost:8001/api/v1/documents/{file_id}/download"
            if converted:
                filebot_url += "?converted=true"
            
            # 返回重定向响应
            return RedirectResponse(url=filebot_url, status_code=307)  # 307保持请求方法
        
        # 如果数据库中不存在，检查模拟数据
        for file in uploaded_files:
            if file["id"] == file_id:
                # 对于模拟文件，返回信息
                return {
                    "id": file_id,
                    "name": file["name"],
                    "message": "文件下载功能处于模拟模式。第二阶段将实现实际文件下载。",
                    "simulated_url": f"filebot://files/{file_id}/{file['name']}",
                    "redirect_url": f"http://localhost:8001/api/v1/documents/{file_id}/download"
                }
        
        raise HTTPException(status_code=404, detail="文件未找到")
        
    except Exception as e:
        # 出错时返回错误信息
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@router.get("/{file_id}/thumbnail")
async def get_file_thumbnail(file_id: str):
    """
    获取文件缩略图 - 尝试从FileBot获取，失败则回退到模拟
    """
    try:
        # 首先检查文件是否存在于FileBot数据库中
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, mime_type, file_type FROM documents WHERE id = ? AND status = 'active' AND is_archived = 0"
        cursor.execute(query, (file_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            mime_type = row["mime_type"]
            file_type = row["file_type"]
            
            # 根据文件类型返回不同的缩略图
            if mime_type and mime_type.startswith("image/"):
                # 图片文件：重定向到FileBot的预览或直接下载
                filebot_url = f"http://localhost:8001/api/v1/documents/{file_id}/download"
                return {"thumbnail_url": filebot_url}
            elif file_type in ["pdf", "tiff"]:
                # PDF或TIFF文件：如果有第一页预览，重定向到预览
                # FileBot可能有预览端点
                preview_url = f"http://localhost:8001/api/v1/documents/{file_id}/tiff-preview/1"
                return {"thumbnail_url": preview_url}
            else:
                # 其他文件类型：返回通用图标
                return {"thumbnail_url": "/static/icons/file-icon.png"}
        
        # 如果数据库中不存在，检查模拟数据
        for file in uploaded_files:
            if file["id"] == file_id:
                if file["type"].startswith("image/"):
                    return {"thumbnail_url": file["url"]}
                else:
                    return {"thumbnail_url": "/static/icons/file-icon.png"}
        
        return {"thumbnail_url": "/static/icons/file-icon.png"}
        
    except Exception as e:
        # 出错时返回通用图标
        return {"thumbnail_url": "/static/icons/file-icon.png"}

@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """
    删除文件 - 对于FileBot文档返回提示信息
    """
    try:
        # 首先检查文件是否存在于FileBot数据库中
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, original_filename FROM documents WHERE id = ?"
        cursor.execute(query, (file_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # 文件存在于FileBot中，返回提示信息
            return {
                "success": False,
                "message": f"文件 '{row['original_filename']}' 由FileBot管理。请在FileBot界面中删除。",
                "filebot_management_url": f"http://localhost:8001/documents/{file_id}",
                "can_delete": False
            }
        
        # 如果数据库中不存在，检查模拟数据
        global uploaded_files
        for i, file in enumerate(uploaded_files):
            if file["id"] == file_id:
                uploaded_files.pop(i)
                return {
                    "success": True,
                    "message": f"文件 {file_id} 已删除（模拟）",
                    "can_delete": True
                }
        
        return {
            "success": False,
            "message": f"文件 {file_id} 未找到"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")

@router.get("/folders/")
async def list_folders():
    """
    获取可用的文件夹列表 - 尝试从FileBot获取真实文件夹
    """
    try:
        # 首先尝试从FileBot数据库获取真实文件夹
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询FileBot的folders表
        query = """
            SELECT id, name, description, created_at
            FROM folders
            ORDER BY name
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            folders = []
            for row in rows:
                # 获取每个文件夹中的文件数量
                conn = get_db_connection()
                cursor = conn.cursor()
                count_query = "SELECT COUNT(*) as file_count FROM documents WHERE folder_id = ? AND status = 'active' AND is_archived = 0"
                cursor.execute(count_query, (row["id"],))
                count_result = cursor.fetchone()
                file_count = count_result["file_count"] if count_result else 0
                conn.close()
                
                folder_info = {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"] or f"FileBot folder: {row['name']}",
                    "file_count": file_count,
                    "source": "filebot"
                }
                folders.append(folder_info)
            
            # 添加默认文件夹选项
            folders.insert(0, {
                "id": "default-folder",
                "name": "All Files",
                "description": "所有文件（不按文件夹筛选）",
                "file_count": sum(f["file_count"] for f in folders),
                "source": "virtual"
            })
            
            return {"folders": folders, "source": "filebot-database"}
        
        # 如果没有找到文件夹，回退到模拟数据
        return {
            "folders": [
                {
                    "id": "default-folder",
                    "name": "WebBot Files",
                    "description": "WebBot上传的文件存储位置",
                    "file_count": len(uploaded_files)
                },
                {
                    "id": "images-folder",
                    "name": "Images",
                    "description": "图片文件",
                    "file_count": len([f for f in uploaded_files if f["type"].startswith("image/")])
                },
                {
                    "id": "documents-folder",
                    "name": "Documents",
                    "description": "文档文件",
                    "file_count": len([f for f in uploaded_files if f["type"] in ["application/pdf", 
                                                                                  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                                                                  "application/msword"]])
                }
            ],
            "source": "mock-data-fallback"
        }
        
    except Exception as e:
        # 出错时回退到模拟数据
        print(f"获取文件夹列表失败: {e}")
        return {
            "folders": [
                {
                    "id": "default-folder",
                    "name": "WebBot Files",
                    "description": "WebBot上传的文件存储位置",
                    "file_count": len(uploaded_files)
                }
            ],
            "source": "error-fallback"
        }

@router.post("/folders/")
async def create_folder(name: str, description: Optional[str] = None):
    """
    创建新文件夹（模拟）
    """
    folder_id = str(uuid.uuid4())
    return {
        "success": True,
        "folder": {
            "id": folder_id,
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    }


@router.get("/content/{document_id}")
async def get_document_content(document_id: str, download_type: str = Query("original", description="下载类型: original 或 pdf")):
    """
    通过FileBot API获取文档内容（使用X-WebBot-Access头）
    支持访问未发布文档
    """
    try:
        # 构建FileBot API URL
        filebot_url = f"http://localhost:8001/api/v1/documents/{document_id}"
        
        # 如果是PDF请求，添加参数
        if download_type == "pdf":
            filebot_url += f"?download_type=pdf"
        
        # 发送请求到FileBot，添加X-WebBot-Access头
        headers = {"X-WebBot-Access": "true"}
        
        response = requests.get(filebot_url, headers=headers)
        
        if response.status_code == 200:
            # 成功获取文档，返回FileBot的响应
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            
            # 检查是否为文件下载
            content_disposition = response.headers.get("Content-Disposition", "")
            if "attachment" in content_disposition or "filename=" in content_disposition:
                # 文件下载，直接返回二进制数据
                return Response(
                    content=response.content,
                    media_type=content_type,
                    headers=dict(response.headers)
                )
            else:
                # 可能是JSON响应（文档信息）
                try:
                    return response.json()
                except:
                    # 如果不是JSON，返回原始内容
                    return Response(
                        content=response.content,
                        media_type=content_type,
                        headers=dict(response.headers)
                    )
        else:
            # FileBot API错误
            error_detail = f"FileBot API错误: {response.status_code}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_detail = f"FileBot API错误: {error_data['detail']}"
            except:
                pass
            
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="无法连接到FileBot服务")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档内容失败: {str(e)}")


@router.get("/by-path/{path:path}")
async def get_document_by_path(path: str, download_type: str = Query("original", description="下载类型: original 或 pdf")):
    """
    通过原始URL路径获取文档内容（使用X-WebBot-Access头）
    支持访问未发布文档
    
    路径格式: /en/services/indigenous-peoples.html
    匹配FileBot的document_metadata.url字段
    """
    try:
        # 清理路径，确保格式正确
        if not path.startswith('/'):
            path = '/' + path
        
        # 构建FileBot API URL
        filebot_url = f"http://localhost:8001/api/v1/documents/by-path/{path}"
        
        # 添加查询参数
        params = {}
        if download_type == "pdf":
            params["download_type"] = "pdf"
        
        # 发送请求到FileBot，添加X-WebBot-Access头
        headers = {"X-WebBot-Access": "true"}
        
        response = requests.get(filebot_url, headers=headers, params=params)
        
        if response.status_code == 200:
            # 成功获取文档，返回FileBot的响应
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            
            # 检查是否为文件下载
            content_disposition = response.headers.get("Content-Disposition", "")
            if "attachment" in content_disposition or "filename=" in content_disposition:
                # 文件下载，直接返回二进制数据
                return Response(
                    content=response.content,
                    media_type=content_type,
                    headers=dict(response.headers)
                )
            else:
                # 可能是JSON响应（文档信息）
                try:
                    return response.json()
                except:
                    # 如果不是JSON，返回原始内容
                    return Response(
                        content=response.content,
                        media_type=content_type,
                        headers=dict(response.headers)
                    )
        else:
            # FileBot API错误
            error_detail = f"FileBot API错误: {response.status_code}"
            try:
                error_data = response.json()
                if "detail" in error_data:
                    error_detail = f"FileBot API错误: {error_data['detail']}"
            except:
                pass
            
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="无法连接到FileBot服务")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"通过路径获取文档失败: {str(e)}")