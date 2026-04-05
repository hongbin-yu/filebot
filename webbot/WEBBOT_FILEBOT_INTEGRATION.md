# WebBot - FileBot 集成指南

## 版本信息
- **文档版本**: 1.0.0
- **创建日期**: 2026-03-22
- **最后更新**: 2026-03-22
- **集成方案**: 方案A - 紧密FileBot集成

## 集成概述

WebBot采用与FileBot紧密集成的架构（方案A），最大化利用FileBot现有的文件处理、存储和版本控制能力。本文档详细描述集成方案、API调用流程和技术实现细节。

## 集成架构

### 整体集成模式
```
┌─────────────────────────────────┐
│          WebBot系统             │
│                                 │
│  ┌─────────────┐  ┌──────────┐  │
│  │  页面管理   │  │  API网关 │  │
│  │  模块       │  │  模块    │◄─┼────┐
│  └──────┬──────┘  └────┬─────┘  │    │
│         │              │         │    │
│  ┌──────▼──────┐  ┌────▼─────┐  │    │
│  │  版本控制   │  │ 文件处理 │  │    │
│  │  模块       │  │  模块    │──┼────┤
│  └─────────────┘  └──────────┘  │    │
└───────────────────┬──────────────┘    │
                    │ WebBot内部调用    │
                    ▼                   │ FileBot API调用
┌─────────────────────────────────┐    │
│          FileBot系统            │    │
│                                 │    │
│  ┌─────────────┐  ┌──────────┐  │    │
│  │  文档存储   │  │ 文件处理 │  │    │
│  │  模块       │  │  引擎    │◄─┼────┘
│  └─────────────┘  └──────────┘  │
│                                 │
│  ┌─────────────┐  ┌──────────┐  │
│  │  版本管理   │  │ 转换服务 │  │
│  │  系统       │  │          │  │
│  └─────────────┘  └──────────┘  │
└─────────────────────────────────┘
```

### 数据流示意图
```
用户上传文件
    │
    ▼
WebBot接收文件 (multipart/form-data)
    │
    ▼
WebBot调用FileBot上传API
    │
    ▼
FileBot处理文件 (存储、转换、元数据提取)
    │
    ▼
FileBot返回: 文档ID + 处理结果
    │
    ▼
WebBot创建页面记录 (存储文本内容 + 文档引用)
    │
    ▼
WebBot创建版本记录 (关联FileBot文档)
    │
    ▼
返回页面预览给用户
```

## FileBot API 集成

### 基础信息
- **FileBot API地址**: `http://localhost:8001/api/v1`
- **认证方式**: JWT Token (共享FileBot认证系统)
- **API版本**: v1 (与FileBot保持一致)
- **超时设置**: 文件上传60秒，其他操作10秒

### 核心API端点

#### 1. 文件上传API
```http
POST /documents/upload
Content-Type: multipart/form-data
Authorization: Bearer {jwt_token}
```

**请求参数**:
- `file`: 文件二进制数据 (必需)
- `original_filename`: 原始文件名 (必需)
- `process_options`: 处理选项 (JSON字符串，可选)
- `metadata`: 自定义元数据 (JSON字符串，可选)

**WebBot调用示例**:
```python
async def upload_to_filebot(file_content, filename, process_options=None):
    """上传文件到FileBot并获取文档ID"""
    files = {
        'file': (filename, file_content, 'application/octet-stream')
    }
    
    data = {
        'original_filename': filename,
        'process_options': json.dumps(process_options or {
            'extract_text': True,
            'generate_html': True,
            'store_original': True
        })
    }
    
    response = await http_client.post(
        f"{FILEBOT_API}/documents/upload",
        files=files,
        data=data,
        headers={'Authorization': f'Bearer {jwt_token}'}
    )
    
    if response.status_code == 200:
        result = response.json()
        return {
            'document_id': result['id'],
            'text_content': result.get('extracted_text', ''),
            'html_content': result.get('html_content', ''),
            'metadata': result.get('metadata', {})
        }
    else:
        raise FileBotError(f"FileBot上传失败: {response.text}")
```

#### 2. 文档信息查询API
```http
GET /documents/{document_id}
Authorization: Bearer {jwt_token}
```

**响应示例**:
```json
{
  "id": "abc123-uuid",
  "original_filename": "report.pdf",
  "stored_filename": "abc123-uuid.pdf",
  "file_type": "pdf",
  "file_size": 102400,
  "storage_subfolder": "2024/03/22",
  "full_storage_path": "/filebot-storage/2024/03/22/abc123-uuid.pdf",
  "metadata": {
    "page_count": 5,
    "author": "John Doe",
    "created_date": "2024-03-22"
  },
  "converted_files": [
    {
      "format": "text",
      "path": "/filebot-storage/converted/abc123-uuid.txt",
      "size": 5120
    },
    {
      "format": "html", 
      "path": "/filebot-storage/converted/abc123-uuid.html",
      "size": 10240
    }
  ],
  "created_at": "2024-03-22T10:00:00Z",
  "updated_at": "2024-03-22T10:05:00Z"
}
```

#### 3. 文档处理状态API
```http
GET /tasks/{task_id}
Authorization: Bearer {jwt_token}
```

用于异步文件处理任务的状态查询。

#### 4. 文档版本API
```http
GET /documents/{document_id}/versions
Authorization: Bearer {jwt_token}
```

获取文档的所有版本信息。

### 处理选项配置

#### 基础处理选项
```json
{
  "extract_text": true,      // 提取文本内容
  "generate_html": true,     // 生成HTML版本
  "store_original": true,    // 存储原始文件
  "ocr_if_needed": false,    // 需要时进行OCR
  "extract_metadata": true   // 提取元数据
}
```

#### 文件类型特定选项
```json
{
  "pdf": {
    "extract_images": false,
    "preserve_layout": true
  },
  "word": {
    "preserve_formatting": true,
    "extract_comments": false
  },
  "image": {
    "generate_thumbnails": true,
    "thumbnail_sizes": ["300x300", "600x600"]
  },
  "video": {
    "extract_thumbnail": true,
    "thumbnail_time": "00:00:05"
  },
  "audio": {
    "extract_metadata": true,
    "generate_waveform": false
  }
}
```

## WebBot中的FileBot集成实现

### 1. 文件处理服务

```python
# webbot/services/filebot_service.py

import aiohttp
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class FileBotResult:
    """FileBot处理结果"""
    document_id: str
    text_content: str
    html_content: str
    metadata: Dict[str, Any]
    file_type: str
    file_size: int

class FileBotService:
    """FileBot集成服务"""
    
    def __init__(self, api_base_url: str, jwt_token: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.jwt_token = jwt_token
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def upload_and_process(
        self, 
        file_content: bytes, 
        filename: str,
        file_type: str,
        process_options: Optional[Dict] = None
    ) -> FileBotResult:
        """上传文件到FileBot并进行处理"""
        
        # 根据文件类型配置处理选项
        default_options = self._get_default_options(file_type)
        if process_options:
            default_options.update(process_options)
        
        # 准备上传数据
        files = {
            'file': (filename, file_content, self._get_mime_type(file_type))
        }
        
        data = {
            'original_filename': filename,
            'process_options': json.dumps(default_options)
        }
        
        # 调用FileBot API
        async with self.session.post(
            f"{self.api_base_url}/documents/upload",
            data=data,
            files=files,
            headers={'Authorization': f'Bearer {self.jwt_token}'}
        ) as response:
            
            if response.status != 200:
                error_text = await response.text()
                raise FileBotError(f"FileBot上传失败: {error_text}")
            
            result = await response.json()
            
            return FileBotResult(
                document_id=result['id'],
                text_content=result.get('extracted_text', ''),
                html_content=result.get('html_content', ''),
                metadata=result.get('metadata', {}),
                file_type=result.get('file_type', file_type),
                file_size=result.get('file_size', len(file_content))
            )
    
    async def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """获取文档信息"""
        async with self.session.get(
            f"{self.api_base_url}/documents/{document_id}",
            headers={'Authorization': f'Bearer {self.jwt_token}'}
        ) as response:
            if response.status != 200:
                raise FileBotError(f"获取文档信息失败: {await response.text()}")
            return await response.json()
    
    async def get_document_versions(self, document_id: str) -> List[Dict]:
        """获取文档版本列表"""
        async with self.session.get(
            f"{self.api_base_url}/documents/{document_id}/versions",
            headers={'Authorization': f'Bearer {self.jwt_token}'}
        ) as response:
            if response.status != 200:
                raise FileBotError(f"获取文档版本失败: {await response.text()}")
            return await response.json()
    
    def _get_default_options(self, file_type: str) -> Dict[str, Any]:
        """根据文件类型获取默认处理选项"""
        options = {
            'extract_text': True,
            'generate_html': True,
            'store_original': True,
            'extract_metadata': True
        }
        
        # 文件类型特定选项
        if file_type in ['pdf', 'doc', 'docx']:
            options.update({
                'preserve_layout': True,
                'extract_images': False
            })
        elif file_type in ['jpg', 'jpeg', 'png']:
            options.update({
                'generate_thumbnails': True,
                'ocr_if_needed': True,
                'thumbnail_sizes': ['300x300', '600x600', '1200x1200']
            })
        elif file_type in ['mp4', 'webm', 'avi']:
            options.update({
                'extract_thumbnail': True,
                'thumbnail_time': '00:00:05',
                'extract_metadata': True
            })
        elif file_type in ['mp3', 'wav', 'ogg']:
            options.update({
                'extract_metadata': True,
                'generate_waveform': False
            })
        
        return options
    
    def _get_mime_type(self, file_type: str) -> str:
        """根据文件类型获取MIME类型"""
        mime_map = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg'
        }
        return mime_map.get(file_type.lower(), 'application/octet-stream')


class FileBotError(Exception):
    """FileBot相关错误"""
    pass
```

### 2. 页面创建服务（集成FileBot）

```python
# webbot/services/page_service.py

from typing import Dict, Any, Optional
from models import Page, PageVersion, PageMetadata
from services.filebot_service import FileBotService, FileBotResult

class PageService:
    """页面服务（集成FileBot）"""
    
    def __init__(self, db_session, filebot_service: FileBotService):
        self.db = db_session
        self.filebot = filebot_service
    
    async def create_page_from_file(
        self,
        file_content: bytes,
        filename: str,
        title: str,
        user_id: int,
        language_code: str = 'en',
        parent_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Page:
        """从文件创建页面"""
        
        # 1. 上传文件到FileBot并处理
        file_type = self._detect_file_type(filename)
        filebot_result = await self.filebot.upload_and_process(
            file_content, filename, file_type
        )
        
        # 2. 生成页面ID（基于标题）
        page_id = self._generate_page_id(title)
        
        # 3. 创建页面记录
        page = Page(
            id=page_id,
            title=title,
            parent_id=parent_id,
            language_code=language_code,
            create_by=user_id,
            current_content_text=filebot_result.text_content,
            current_html_content=filebot_result.html_content,
            source_document_id=filebot_result.document_id,
            current_document_id=filebot_result.document_id,
            storage_subfolder=f"pages/{language_code}/{page_id}",
            html_file_path=f"/webbot-storage/pages/{language_code}/{filebot_result.document_id}/index.html",
            metadata_json=json.dumps(metadata or {}),
            has_media=file_type in ['image', 'video', 'audio'],
            media_type=file_type if file_type in ['image', 'video', 'audio'] else 'document'
        )
        
        self.db.add(page)
        await self.db.flush()
        
        # 4. 创建初始版本记录
        version = PageVersion(
            page_id=page_id,
            document_id=filebot_result.document_id,
            version_number=1,
            version_type='current',
            is_current=True,
            change_description='初始版本',
            created_by=user_id
        )
        
        self.db.add(version)
        
        # 5. 保存元数据
        if metadata:
            for key, value in metadata.items():
                meta = PageMetadata(
                    page_id=page_id,
                    meta_key=key,
                    meta_value=str(value),
                    meta_type=self._detect_meta_type(value)
                )
                self.db.add(meta)
        
        await self.db.commit()
        
        return page
    
    async def update_page_content(
        self,
        page_id: str,
        new_content: str,
        user_id: int,
        change_description: Optional[str] = None
    ) -> PageVersion:
        """更新页面内容，创建新版本"""
        
        # 1. 获取当前页面
        page = await self.db.get(Page, page_id)
        if not page:
            raise PageNotFoundError(f"页面不存在: {page_id}")
        
        # 2. 获取当前版本信息
        current_version = await self.db.execute(
            select(PageVersion)
            .where(PageVersion.page_id == page_id, PageVersion.is_current == True)
        ).scalar_one_or_none()
        
        # 3. 从当前FileBot文档创建新版本
        # （假设FileBot支持从现有文档创建新版本）
        new_document_id = await self._create_new_filebot_version(
            current_version.document_id,
            new_content,
            f"更新: {change_description or '内容更新'}"
        )
        
        # 4. 更新页面内容
        page.current_content_text = new_content
        page.current_document_id = new_document_id
        page.last_modify = datetime.utcnow()
        
        # 5. 标记旧版本为非当前
        if current_version:
            current_version.is_current = False
        
        # 6. 创建新版本记录
        new_version_number = current_version.version_number + 1 if current_version else 1
        
        new_version = PageVersion(
            page_id=page_id,
            document_id=new_document_id,
            version_number=new_version_number,
            version_type='current',
            is_current=True,
            change_description=change_description or '内容更新',
            created_by=user_id
        )
        
        self.db.add(new_version)
        await self.db.commit()
        
        return new_version
    
    def _generate_page_id(self, title: str) -> str:
        """根据标题生成页面ID"""
        # 实现id生成算法：空格→"-" + 小写 + 法语字符转换
        import re
        import unicodedata
        
        # 法语字符转换
        normalized = unicodedata.normalize('NFKD', title.strip())
        ascii_text = normalized.encode('ASCII', 'ignore').decode('ASCII')
        
        if not ascii_text:
            ascii_text = title.strip()
        
        # 生成基础id
        base_id = ascii_text.lower().replace(' ', '-')
        base_id = re.sub(r'[^a-z0-9-]', '', base_id)
        base_id = base_id.strip('-')
        
        # 检查重复并生成唯一id
        existing_ids = self._get_existing_page_ids()
        if base_id in existing_ids:
            suffix = 2
            while f"{base_id}-{suffix}" in existing_ids:
                suffix += 1
            base_id = f"{base_id}-{suffix}"
        
        return base_id
    
    def _detect_file_type(self, filename: str) -> str:
        """根据文件名检测文件类型"""
        ext = filename.split('.')[-1].lower()
        
        type_map = {
            'pdf': 'pdf',
            'doc': 'word',
            'docx': 'word',
            'jpg': 'image',
            'jpeg': 'image',
            'png': 'image',
            'mp4': 'video',
            'webm': 'video',
            'avi': 'video',
            'mp3': 'audio',
            'wav': 'audio',
            'ogg': 'audio'
        }
        
        return type_map.get(ext, 'document')
    
    def _detect_meta_type(self, value: Any) -> str:
        """检测元数据类型"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, (int, float)):
            return 'number'
        elif isinstance(value, dict) or isinstance(value, list):
            return 'json'
        elif value.startswith(('http://', 'https://')):
            return 'url'
        else:
            return 'text'
```

## 错误处理和恢复

### 1. FileBot服务不可用处理

```python
class FileBotFallbackService:
    """FileBot降级服务"""
    
    def __init__(self, primary_service: FileBotService, fallback_dir: str):
        self.primary = primary_service
        self.fallback_dir = fallback_dir
        self.is_filebot_available = True
    
    async def upload_and_process(self, file_content, filename, file_type, **kwargs):
        """尝试使用FileBot，失败时使用本地降级方案"""
        
        if self.is_filebot_available:
            try:
                return await self.primary.upload_and_process(
                    file_content, filename, file_type, **kwargs
                )
            except (aiohttp.ClientError, FileBotError) as e:
                # FileBot服务不可用，切换到降级模式
                self.is_filebot_available = False
                logger.warning(f"FileBot服务不可用，切换到降级模式: {e}")
        
        # 降级处理：本地文件存储和基础处理
        return await self._fallback_process(file_content, filename, file_type)
    
    async def _fallback_process(self, file_content, filename, file_type):
        """降级处理方案"""
        
        # 生成本地文档ID（模拟FileBot的UUID）
        import uuid
        document_id = str(uuid.uuid4())
        
        # 保存文件到本地目录
        file_path = os.path.join(self.fallback_dir, f"{document_id}_{filename}")
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # 基础文本提取（仅支持文本文件和简单PDF）
        text_content = ''
        if file_type in ['pdf', 'txt']:
            text_content = self._extract_text_fallback(file_content, file_type)
        
        return FileBotResult(
            document_id=document_id,
            text_content=text_content,
            html_content=f"<p>{text_content[:500]}...</p>" if text_content else "",
            metadata={'fallback_mode': True, 'local_path': file_path},
            file_type=file_type,
            file_size=len(file_content)
        )
```

### 2. 事务一致性保证

```python
async def create_page_with_transaction(
    db_session,
    filebot_service,
    file_content,
    filename,
    title,
    user_id,
    **kwargs
):
    """创建页面的事务性操作"""
    
    async with db_session.begin():
        try:
            # 1. 上传文件到FileBot
            filebot_result = await filebot_service.upload_and_process(
                file_content, filename, kwargs.get('file_type', 'document')
            )
            
            # 2. 创建页面记录
            page = Page(
                # ... 页面字段设置
            )
            db_session.add(page)
            
            # 3. 创建版本记录
            version = PageVersion(
                # ... 版本字段设置
            )
            db_session.add(version)
            
            # 4. 提交事务
            await db_session.commit()
            
            return page
            
        except Exception as e:
            # 事务回滚
            await db_session.rollback()
            
            # 尝试清理FileBot中的文件（如果已上传）
            if 'filebot_result' in locals():
                await cleanup_filebot_file(filebot_result.document_id)
            
            raise PageCreationError(f"创建页面失败: {e}")
```

## 性能优化

### 1. 批量处理支持
```python
async def batch_upload_files(self, files: List[Tuple[bytes, str, str]]):
    """批量上传文件到FileBot"""
    
    # 使用asyncio.gather并发处理
    tasks = [
        self.upload_and_process(file_content, filename, file_type)
        for file_content, filename, file_type in files
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理结果，区分成功和失败
    successful = []
    failed = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed.append((files[i][1], str(result)))
        else:
            successful.append(result)
    
    return successful, failed
```

### 2. 缓存策略
```python
class FileBotCache:
    """FileBot API结果缓存"""
    
    def __init__(self, redis_client=None, ttl_seconds=300):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self.local_cache = {}
    
    async def get_document_info(self, document_id: str):
        """获取文档信息（带缓存）"""
        
        cache_key = f"filebot:doc:{document_id}"
        
        # 尝试从缓存获取
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # 调用FileBot API
        result = await self.filebot_service.get_document_info(document_id)
        
        # 缓存结果
        await self._set_to_cache(cache_key, result)
        
        return result
```

## 监控和日志

### 1. 集成监控指标
```python
# 监控指标定义
filebot_metrics = {
    'filebot_api_calls_total': Counter('filebot_api_calls_total', 'FileBot API调用总数', ['endpoint', 'status']),
    'filebot_upload_duration_seconds': Histogram('filebot_upload_duration_seconds', 'FileBot文件上传耗时'),
    'filebot_processing_errors_total': Counter('filebot_processing_errors_total', 'FileBot处理错误总数'),
    'filebot_fallback_activations_total': Counter('filebot_fallback_activations_total', 'FileBot降级模式激活次数')
}
```

### 2. 详细日志记录
```python
# 结构化日志记录
logger = structlog.get_logger(__name__)

async def upload_to_filebot_with_logging(file_content, filename, user_id):
    """带详细日志的文件上传"""
    
    log = logger.bind(
        operation="filebot_upload",
        filename=filename,
        file_size=len(file_content),
        user_id=user_id
    )
    
    log.info("starting_filebot_upload")
    
    try:
        start_time = time.time()
        result = await filebot_service.upload_and_process(file_content, filename)
        duration = time.time() - start_time
        
        log.info(
            "filebot_upload_completed",
            document_id=result.document_id,
            duration_seconds=duration,
            success=True
        )
        
        return result
        
    except Exception as e:
        log.error(
            "filebot_upload_failed",
            error=str(e),
            error_type=type(e).__name__,
            success=False
        )
        raise
```

## 部署配置

### 1. 环境变量配置
```bash
# FileBot集成配置
FILEBOT_API_URL=http://localhost:8001/api/v1
FILEBOT_JWT_TOKEN=your_jwt_token_here
FILEBOT_TIMEOUT=60
FILEBOT_RETRY_ATTEMPTS=3
FILEBOT_FALLBACK_ENABLED=true
FILEBOT_FALLBACK_DIR=/tmp/webbot_fallback
```

### 2. 健康检查端点
```python
@app.get("/health/filebot")
async def filebot_health_check():
    """FileBot服务健康检查"""
    
    try:
        # 测试FileBot API连接
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{FILEBOT_API_URL}/health",
                timeout=5
            ) as response:
                if response.status == 200:
                    return {"filebot": "healthy", "status": "connected"}
                else:
                    return {"filebot": "unhealthy", "status": "api_error"}
                    
    except Exception as e:
        return {"filebot": "unhealthy", "status": "connection_failed", "error": str(e)}
```

## 测试策略

### 1. 单元测试
```python
@pytest.mark.asyncio
async def test_filebot_upload_success():
    """测试FileBot文件上传成功"""
    
    # Mock FileBot API响应
    mock_response = {
        'id': 'test-doc-id',
        'extracted_text': '测试文本内容',
        'html_content': '<p>测试HTML内容</p>',
        'metadata': {'page_count': 1}
    }
    
    # 测试上传逻辑
    result = await filebot_service.upload_and_process(
        b'test file content', 'test.pdf', 'pdf'
    )
    
    assert result.document_id == 'test-doc-id'
    assert '测试文本内容' in result.text_content
```

### 2. 集成测试
```python
@pytest.mark.integration
async def test_full_page_creation_flow():
    """测试完整页面创建流程（集成FileBot）"""
    
    # 1. 上传测试文件
    test_file = b'PDF test content...'
    
    # 2. 创建页面
    page = await page_service.create_page_from_file(
        file_content=test_file,
        filename='test.pdf',
        title='测试页面',
        user_id=1
    )
    
    # 3. 验证结果
    assert page.id == '测试页面'  # 转换后的ID
    assert page.source_document_id is not None
    assert page.current_document_id == page.source_document_id
    
    # 4. 验证版本记录
    versions = await db_session.execute(
        select(PageVersion).where(PageVersion.page_id == page.id)
    ).scalars().all()
    
    assert len(versions) == 1
    assert versions[0].version_number == 1
```

## 维护和故障排除

### 常见问题解决

#### 1. FileBot服务连接失败
- 检查FileBot服务是否运行 (`http://localhost:8001/health`)
- 验证JWT token是否有效
- 检查网络连接和防火墙设置

#### 2. 文件处理失败
- 检查文件格式是否支持
- 查看FileBot处理日志
- 验证文件大小限制

#### 3. 版本同步问题
- 检查WebBot和FileBot的版本关联
- 验证外键约束完整性
- 查看事务日志和错误信息

### 数据一致性检查脚本
```python
async def check_data_consistency(db_session):
    """检查WebBot和FileBot数据一致性"""
    
    # 检查页面引用无效的FileBot文档
    invalid_refs = await db_session.execute("""
        SELECT wp.id, wp.source_document_id 
        FROM webbot_page wp
        LEFT JOIN documents d ON wp.source_document_id = d.id
        WHERE d.id IS NULL AND wp.source_document_id IS NOT NULL
    """).fetchall()
    
    if invalid_refs:
        logger.warning(f"发现无效的FileBot文档引用: {len(invalid_refs)}个")
        
    # 检查版本记录的一致性
    inconsistent_versions = await db_session.execute("""
        SELECT wpv.page_id, wpv.document_id
        FROM webbot_page_versions wpv
        LEFT JOIN documents d ON wpv.document_id = d.id
        WHERE d.id IS NULL
    """).fetchall()
    
    return {
        'invalid_document_refs': len(invalid_refs),
        'inconsistent_versions': len(inconsistent_versions)
    }
```

---

**文档维护**
- 定期更新以反映FileBot API变更
- 记录集成问题和解决方案
- 更新性能优化和最佳实践