"""
Page management routes
"""

from fastapi import APIRouter, HTTPException, Depends, Query
import sqlite3
import json
import uuid
import os
import requests
import re
import traceback
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.models import PageCreate, PageUpdate, PageResponse, PageListItem, PagePropertiesResponse, PageMetadataResponse, PageStatus

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])

WEBBOT_DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)

def get_db_connection():
    """Get WebBot database connection"""
    try:
        conn = sqlite3.connect(WEBBOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")

def generate_page_id(title: str) -> str:
    """Generate page ID from title"""
    # 简单实现:将标题Transform为小写,Replace空格为连字符
    import re
    # 移除特殊字符,只保留字母数字和空格
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    # Replace空格为连字符,Transform为小写
    page_id = re.sub(r'\s+', '-', cleaned.strip()).lower()
    # If为空,Generate随机ID
    if not page_id:
        page_id = f"page-{uuid.uuid4().hex[:8]}"
    return page_id

def extract_language_from_path(path: str) -> str:
    """
    Extract language code from path
    Supports multiple path formats:
    - /en/contact → "en" (simple format, first node is language)
    - /canadasite/en/contact → "en" (full format, second node is language)
    - /fr/about → "fr"
    - /zh/contact → "zh" (Chinese support, BC key requirement)
    """
    if not path:
        return "en"

    # 清理路径:移除首尾斜杠,分割节点
    clean_path = path.strip('/')
    parts = clean_path.split('/')

    if len(parts) == 0:
        return "en"

    # 检查常见站点前缀
    # If第一个部分已知站点前缀(如canadasite),则第二个部分语言
    known_site_prefixes = ['canadasite', 'site', 'www']
    if len(parts) >= 2 and parts[0] in known_site_prefixes:
        # 完整格式:/canadasite/en/contact
        lang = parts[1].lower()
    else:
        # 简单格式:/en/contact
        lang = parts[0].lower()

    # 验证为支持的语言(扩展支持中文)
    if lang in ['en', 'fr', 'zh']:
        return lang

    # 默认返回英语
    return "en"

def get_ancestor_file_path(page_path: Optional[str], conn) -> Optional[str]:
    """
    Get file_path from ancestor pages.
    Walk up from the current page to parent pages until file_path is found or root is reached.
    """
    if not page_path:
        return None

    current_path = page_path
    visited = set()  # 防止循环

    while current_path and current_path not in visited:
        visited.add(current_path)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM webbot_page WHERE path = ?", (current_path,))
        row = cursor.fetchone()

        if not row:
            break

        metadata_str = row["metadata"]
        if metadata_str:
            try:
                metadata = json.loads(metadata_str)
                if metadata and "file_path" in metadata:
                    file_path = metadata.get("file_path")
                    if file_path:
                        return file_path
            except json.JSONDecodeError:
                pass

        # 继续向上查询父page(Infer parent path from path)
        current_path = extract_parent_path_from_path(current_path)

    return None

def normalize_path(path: str) -> str:
    """Normalize path: ensure it starts with / and does not end with /"""
    if not path:
        return ""
    # 确保以斜杠开头
    if not path.startswith('/'):
        path = '/' + path
    # 移除末尾斜杠(除非Root path)
    if path.endswith('/') and path != '/':
        path = path.rstrip('/')
    return path

def extract_parent_path_from_path(path: str) -> Optional[str]:
    """
    Infer parent path from page path
    Examples:
    - /canadasite/en/about → /canadasite/en
    - /canadasite/en → None (root page)
    - /canadasite/en/about/contact → /canadasite/en/about
    """
    if not path or path == '/':
        return None

    normalized = normalize_path(path)
    # 移除末尾的路径部分
    parent_path = '/'.join(normalized.rstrip('/').split('/')[:-1])

    # If父path is空,返回None
    if not parent_path:
        return None

    return parent_path if parent_path.startswith('/') else '/' + parent_path

def calculate_page_path(page_id: str, parent_path: Optional[str], language: str, conn) -> str:
    """
    Calculate full page path
    Rules:
    1. If parent_path is empty: root page, path is /{language}/{page_id}
       Special case: if page_id is language code (en/fr), path is /{page_id}
    2. If parent_path is not empty: path is {parent_path}/{page_id}
    """
    if not parent_path:
        # 根page
        if page_id in ['en', 'fr']:
            return f"/{page_id}"
        return f"/{language}/{page_id}"

    # Parent path已经由调用方提供了Full path
    return f"{parent_path.rstrip('/')}/{page_id}"

# get_parent_parent_path 已移除 - is now id = path,层级关系通过路径前缀查询

def update_page_path(old_path: str, new_path: str, conn):
    """Update page ID (path) and recursively update child page paths"""
    cursor = conn.cursor()

    # 更New当前page
    cursor.execute("""
        UPDATE webbot_page
        SET id = ?, path = ?, last_modified = CURRENT_TIMESTAMP
        WHERE path = ?
    """, (new_path, new_path, old_path))

    # 递归更New子page
    rebuild_subtree_paths(old_path, new_path, conn)

def rebuild_subtree_paths(old_root: str, new_root: str, conn):
    """Recursively rebuild all child page IDs and paths under the specified root path"""
    cursor = conn.cursor()

    # 获取直接子page:path以 old_root/ 开头,且只有一个额外层级
    cursor.execute("""
        SELECT path FROM webbot_page
        WHERE path LIKE ? || '/%'
          AND instr(substr(path, length(?) + 2), '/') = 0
    """, (old_root, old_root))
    children = cursor.fetchall()

    for child in children:
        child_path = child['path']
        suffix = child_path[len(old_root):]
        new_child_path = new_root + suffix

        # 更New子page
        cursor.execute("""
            UPDATE webbot_page
            SET id = ?, path = ?, last_modified = CURRENT_TIMESTAMP
            WHERE path = ?
        """, (new_child_path, new_child_path, child_path))

        # 递归更New子page
        rebuild_subtree_paths(child_path, new_child_path, conn)



# 路径Name翻译映射表(常见词汇)
PATH_TRANSLATION_MAP = {
    # 英文 -> 法文
    "models": "modeles",
    "about": "a-propos",
    "services": "services",
    "contact": "contact",
    "home": "accueil",
    "products": "produits",
    "news": "actualites",
    "blog": "blog",
    "careers": "carrieres",
    "support": "assistance",
    "faq": "faq",
    "pricing": "tarifs",
    "team": "equipe",
    "portfolio": "portfolio",
    "testimonials": "temoignages",
    "events": "evenements",
    "resources": "ressources",
    "downloads": "telechargements",
    "login": "connexion",
    "register": "inscription",
    "privacy": "confidentialite",
    "terms": "conditions",
    "sitemap": "plan-du-site",
    # 组件相关词汇 - 根据用户需求Add
    "components": "composants",
    "header": "header",  # 用户Example中保持相同
    "footer": "footer",  # 用户Example中保持相同
}

def translate_path_component(component: str, source_lang: str = "en", target_lang: str = "fr") -> str:
    """
    Translate a path component
    Example: "models" -> "modeles"
    """
    if source_lang == "en" and target_lang == "fr":
        # 首先检查映射表
        if component.lower() in PATH_TRANSLATION_MAP:
            return PATH_TRANSLATION_MAP[component.lower()]

        # TODO: 后续可以IntegrationOllama API进行动态翻译
        # 暂时返回原始组件(保持一致性)
        return component

    # 其他语言方向暂时返回原始组件
    return component

def generate_french_path(english_path: str) -> str:
    """
    Generate French path from English path (translation scheme)
    Example: /canadasite/en/models → /canadasite/fr/modeles

    Rules:
    1. Keep site prefix unchanged
    2. Replace language code: en → fr
    3. Translate path name components
    """
    if not english_path:
        return ""

    # Normalize path
    normalized_path = normalize_path(english_path)

    # 分割路径组件
    components = normalized_path.strip('/').split('/')

    if len(components) < 3:
        # 路径太短,不符合 /canadasite/en/xxx 格式
        return normalized_path

    # 确保 /canadasite/en/xxx 格式
    if components[0] != "canadasite" or components[1] != "en":
        # 不Standard格式,返回原始路径
        return normalized_path

    # 构建法文路径
    french_components = []
    french_components.append(components[0])  # canadasite
    french_components.append("fr")  # Replace en → fr

    # 翻译剩余的路径组件
    for i in range(2, len(components)):
        component = components[i]
        translated = translate_path_component(component, "en", "fr")
        french_components.append(translated)

    # 重New组装路径
    french_path = '/' + '/'.join(french_components)
    return normalize_path(french_path)


@router.get("/translate")
async def translate_text(text: str = Query(..., description="English text to translate to French")):
    """Translate English text to French using Google Translate"""
    from deep_translator import GoogleTranslator
    try:
        translated = GoogleTranslator(source='en', target='fr').translate(text)
        return {"original": text, "translated": translated}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation failed: {str(e)}")


@router.post("/", response_model=PageResponse)
async def create_page(page: PageCreate):
    """Create new page"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 确定Page ID、父ID和语言
        if page.path:
            # 从路径提取Information
            normalized_path = normalize_path(page.path)
            clean_path = normalized_path.lstrip('/')
            path_parts = clean_path.split('/') if clean_path else []

            if len(path_parts) == 0:
                raise HTTPException(status_code=400, detail="Path cannot be empty")

            # Page IDis nowFull path
            page_id = normalized_path

            # Infer parent path from path
            parent_path = '/'.join(normalized_path.rstrip('/').split('/')[:-1])
            if not parent_path:
                parent_path = None

            # Extract language code from path(覆盖提供的语言)
            language_from_path = extract_language_from_path(page.path)
        else:
            # Generate基于标题的Page ID
            page_id = generate_page_id(page.title)
            parent_path = page.parent_path
            language_from_path = page.language if page.language else 'en'

        # Check if page path already exists
        cursor.execute("SELECT id FROM webbot_page WHERE path = ?", (page_id,))

        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Page path '{page_id}' already exists."
            )

        # 确定file_path:If提供则使用,则从祖先获取
        file_path = None
        if page.file_path:
            file_path = page.file_path
        elif parent_path:
            # 从祖先page获取file_path
            file_path = get_ancestor_file_path(parent_path, conn)

        # Build metadata: merge existing metadata和file_path
        metadata_dict = {}
        if page.metadata:
            if isinstance(page.metadata, dict):
                metadata_dict = page.metadata.copy()
            elif isinstance(page.metadata, str):
                try:
                    metadata_dict = json.loads(page.metadata)
                except json.JSONDecodeError:
                    metadata_dict = {}

        # Remove unnecessary fields to reduce storage
        metadata_dict.pop('original_html', None)

        # If找到file_path,Add到metadata中
        if file_path:
            metadata_dict["file_path"] = file_path

        # Page path = Page ID(is nowID就Full path)
        page_path = page_id

        other_language_path = page.other_language_path if page.other_language_path else None

        # Insert into database
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO webbot_page
            (id, title, description, keywords, content, language, parent_path, path, other_language_path, status, metadata, hide_in_navigation, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page_id,
            page.title,
            page.description or "",
            page.keywords or "",
            page.content or "",
            language_from_path,  # 使用从路径提取的语言或原始语言
            parent_path,
            page_path,
            page.other_language_path if page.other_language_path else other_language_path,
            page.status.value if isinstance(page.status, PageStatus) else (page.status or PageStatus.DRAFT.value),
            json.dumps(metadata_dict) if metadata_dict else "{}",
            1 if page.hide_in_navigation else 0,
            now,
            now
        ))

        conn.commit()

        # Handle tags(If提供)
        if hasattr(page, 'tags') and page.tags:
            for tag_name in page.tags:
                if tag_name and tag_name.strip():
                    tag_name = tag_name.strip()
                    # Generateslug
                    slug = re.sub(r'[^\w\s-]', '', tag_name.lower())
                    slug = re.sub(r'[-\s]+', '-', slug).strip('-')

                    # Check if tag already exists
                    cursor.execute("SELECT id FROM webbot_tag WHERE name = ? OR slug = ?",
                                 (tag_name, slug))
                    existing_tag = cursor.fetchone()

                    if existing_tag:
                        tag_id = existing_tag[0]
                    else:
                        # Create new tag
                        created_at = datetime.now().isoformat()
                        cursor.execute(
                            "INSERT INTO webbot_tag (name, slug, created_at) VALUES (?, ?, ?)",
                            (tag_name, slug, created_at)
                        )
                        tag_id = cursor.lastrowid

                    # 创建page-Tags关联
                    try:
                        cursor.execute(
                            "INSERT INTO webbot_page_tag (page_id, tag_id) VALUES (?, ?)",
                            (page_id, tag_id)
                        )
                    except sqlite3.IntegrityError:
                        # Association already exists, skipping
                        pass

            conn.commit()

        # 获取创建的page
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (page_id,))
        created_page = cursor.fetchone()

        if not created_page:
            raise HTTPException(status_code=500, detail="pageCreate failed")

        # TransformFor response model
        result = dict(created_page)
        # 解析metadata field(数据库存储为JSON字符串)
        if result.get("metadata") and isinstance(result["metadata"], str):
            try:
                result["metadata"] = json.loads(result["metadata"])
            except json.JSONDecodeError:
                result["metadata"] = {}
        elif result.get("metadata") is None:
            result["metadata"] = {}
        # language和status字段已经字符串,Pydantic会自动Transform为枚举
        result["language"] = result["language"]
        result["status"] = result["status"]

        # 获取pageTags
        cursor.execute("""
            SELECT t.name
            FROM webbot_tag t
            JOIN webbot_page_tag pt ON t.id = pt.tag_id
            WHERE pt.page_id = ?
            ORDER BY t.name
        """, (page_id,))
        tag_rows = cursor.fetchall()
        result["tags"] = [row[0] for row in tag_rows] if tag_rows else []

        return PageResponse(**result)

    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@router.get("/path", response_model=List[PageListItem])
async def get_pages_by_path(path: str = Query(..., description="Parent page path, returns all direct children. e.g. path=/en returns pages with parent_path=/en. path=/ returns root pagese(parent_path IS NULL)。")):
    """Get pages by parent path

    Get all pages under a specific path (direct children).
    Simplified version of /api/v1/pages?path=..., designed for path filtering.

    Example:
    - GET /api/v1/pages/path?path=/en → returns all pages with parent_path=/en
    - GET /api/v1/pages/path?path=/ → returns root pages
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        normalized_path = path.rstrip('/')
        if normalized_path == '':
            # Root path:查找所有parent_path为NULL的page
            cursor.execute("SELECT * FROM webbot_page WHERE parent_path IS NULL ORDER BY title ASC")
        else:
            # 查找parent_path等于指定路径的page
            cursor.execute("SELECT * FROM webbot_page WHERE parent_path = ? ORDER BY title ASC", (normalized_path,))

        pages = cursor.fetchall()
        result = []

        for page in pages:
            page_dict = dict(page)
            # 解析metadata field(数据库存储为JSON字符串)
            if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
                try:
                    page_dict["metadata"] = json.loads(page_dict["metadata"])
                except json.JSONDecodeError:
                    page_dict["metadata"] = {}
            elif page_dict.get("metadata") is None:
                page_dict["metadata"] = {}
            result.append(PageListItem(**page_dict))

        return result

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()

@router.get("/", response_model=List[PageListItem])
async def list_pages(skip: int = 0, limit: int = 100, path: Optional[str] = Query(None, description="Parent page path, returns all direct children under this path. e.g. path=/en returns pages with parent_path=/en. If omitted, returns all pagese。")):
    """Get page list

    Supports filtering by parent path, returns all pages under a specific path (direct children).
    Example:
    - GET /api/v1/pages?path=/en → returns pages with parent_path=/en
    - GET /api/v1/pages?path=/ → returns root pages (parent_path IS NULL)
    - GET /api/v1/pages?path= → returns all pages

    Parameters:
    - skip: Records to skip (pagination)
    - limit: Records to return (pagination)
    - path: Parent page path, e.g. /en or /en/contact. If provided, filters by parent_path field.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT * FROM webbot_page"
        params = []

        # If提供了pathParameter,Add过滤条件
        if path is not None:
            normalized_path = path.rstrip('/')
            if normalized_path == '':
                # Root path:查找所有parent_path为NULL的page
                query += " WHERE parent_path IS NULL"
            else:
                # 查找parent_path等于指定路径的page
                query += " WHERE parent_path = ?"
                params.append(normalized_path)

        # AddSort和Pagination
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        cursor.execute(query, tuple(params))

        pages = cursor.fetchall()
        result = []

        for page in pages:
            page_dict = dict(page)
            # 解析metadata field(数据库存储为JSON字符串)
            if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
                try:
                    page_dict["metadata"] = json.loads(page_dict["metadata"])
                except json.JSONDecodeError:
                    page_dict["metadata"] = {}
            elif page_dict.get("metadata") is None:
                page_dict["metadata"] = {}
            result.append(PageListItem(**page_dict))

        return result

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()

@router.get("/getheader")
async def get_header(path: str = ""):
    """
    Get header component content
    Fallback: try level 3 (language-specific) first, then level 2 (generic)

    Example: for path /canadasite/en/about
    1. First try /canadasite/en/header
    2. If not found, try /canadasite/header
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalize path
        normalized_path = normalize_path(path) if path else ""

        # Extract language
        language = extract_language_from_path(normalized_path)

        # 第一步:尝试第三级(语言特定)
        third_level_path = ""
        if language and normalized_path:
            # Build level 3 path:/canadasite/{language}/header
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 2:
                # 保持站点Name
                site_name = parts[0]
                third_level_path = f"/{site_name}/{language}/header"

        # 第二步:尝试第二级(通用)
        second_level_path = ""
        if normalized_path:
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 1 and parts[0]:  # 确保站点Name不为空
                site_name = parts[0]
                second_level_path = f"/{site_name}/header"

        # 查询优先级:第三级 -> 第二级
        header_path = None
        header_content = None

        # 先查第三级
        if third_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (third_level_path,))
            result = cursor.fetchone()
            if result:
                header_path = third_level_path
                header_content = result["content"]

        # If第三级没找到,查第二级
        if not header_content and second_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (second_level_path,))
            result = cursor.fetchone()
            if result:
                header_path = second_level_path
                header_content = result["content"]

        if not header_content:
            # 都没有找到,返回空内容
            return {
                "success": False,
                "message": "Header not found",
                "content": "",
                "path_used": None,
                "fallback_level": None
            }

        return {
            "success": True,
            "content": header_content,
            "path_used": header_path,
            "fallback_level": "third" if header_path == third_level_path else "second",
            "language": language
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    finally:
        conn.close()

@router.get("/getfooter")
async def get_footer(path: str = ""):
    """
    Get footer component content
    Fallback: try level 3 (language-specific) first, then level 2 (generic)

    Example: for path /canadasite/en/about
    1. First try /canadasite/en/footer
    2. If not found, try /canadasite/footer
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalize path
        normalized_path = normalize_path(path) if path else ""

        # Extract language
        language = extract_language_from_path(normalized_path)

        # 第一步:尝试第三级(语言特定)
        third_level_path = ""
        if language and normalized_path:
            # Build level 3 path:/canadasite/{language}/footer
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 2:
                # 保持站点Name
                site_name = parts[0]
                third_level_path = f"/{site_name}/{language}/footer"

        # 第二步:尝试第二级(通用)
        second_level_path = ""
        if normalized_path:
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 1 and parts[0]:  # 确保站点Name不为空
                site_name = parts[0]
                second_level_path = f"/{site_name}/footer"

        # 查询优先级:第三级 -> 第二级
        footer_path = None
        footer_content = None

        # 先查第三级
        if third_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (third_level_path,))
            result = cursor.fetchone()
            if result:
                footer_path = third_level_path
                footer_content = result["content"]

        # If第三级没找到,查第二级
        if not footer_content and second_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (second_level_path,))
            result = cursor.fetchone()
            if result:
                footer_path = second_level_path
                footer_content = result["content"]

        if not footer_content:
            # 都没有找到,返回空内容
            return {
                "success": False,
                "message": "Footer not found",
                "content": "",
                "path_used": None,
                "fallback_level": None
            }

        return {
            "success": True,
            "content": footer_content,
            "path_used": footer_path,
            "fallback_level": "third" if footer_path == third_level_path else "second",
            "language": language
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    finally:
        conn.close()


@router.get("/getmegamenu")
async def get_megamenu(path: str = ""):
    """
    Get megamenu component content
    Fallback: try level 3 (language-specific) first, then level 2 (generic)

    Example: for path /canadasite/en/about
    1. First try /canadasite/en/megamenu
    2. If not found, try /canadasite/megamenu

    Same rules as header and footer
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalize path
        normalized_path = normalize_path(path) if path else ""

        # Extract language
        language = extract_language_from_path(normalized_path)

        # 第一步:尝试第三级(语言特定)
        third_level_path = ""
        if language and normalized_path:
            # Build level 3 path:/canadasite/{language}/megamenu
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 2:
                # 保持站点Name
                site_name = parts[0]
                third_level_path = f"/{site_name}/{language}/megamenu"

        # 第二步:尝试第二级(通用)
        second_level_path = ""
        if normalized_path:
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 1 and parts[0]:  # 确保站点Name不为空
                site_name = parts[0]
                second_level_path = f"/{site_name}/megamenu"

        # 查询优先级:第三级 -> 第二级
        megamenu_path = None
        megamenu_content = None

        # 先查第三级
        if third_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (third_level_path,))
            result = cursor.fetchone()
            if result:
                megamenu_path = third_level_path
                megamenu_content = result["content"]

        # If第三级没找到,查第二级
        if not megamenu_content and second_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (second_level_path,))
            result = cursor.fetchone()
            if result:
                megamenu_path = second_level_path
                megamenu_content = result["content"]

        if not megamenu_content:
            # 都没有找到,返回空内容
            return {
                "success": False,
                "message": "Megamenu not found",
                "content": "",
                "path_used": None,
                "fallback_level": None
            }

        return {
            "success": True,
            "content": megamenu_content,
            "path_used": megamenu_path,
            "fallback_level": "third" if megamenu_path == third_level_path else "second",
            "language": language
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    finally:
        conn.close()

@router.get("/by-path", response_model=PageResponse)
async def get_page_by_path(path: str = Query(..., description="Full page path, e.g. /en/contact", alias="path")):
    """Get page by full path (e.g. /en/contact)

    Queries directly by path field without parsing id or parent_path.
    Supports same page name across multiple languages, e.g.:
    - /en/contact → English contact page
    - /fr/contact → French contact page

    Path format: /{language}/{page} or /{site}/{language}/{page} or any depth
    """
    import sys, json
    from fastapi import Query
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalize path
        normalized_path = normalize_path(path)
        print(f"DEBUG get_page_by_path: input='{path}', normalized='{normalized_path}'", file=sys.stderr)
        sys.stderr.flush()

        # 硬编码特定路径: /boarding/content/dam
        if normalized_path == '/boarding/content/dam':
            print(f"DEBUG: Returning hardcoded page for /boarding/content/dam", file=sys.stderr)
            sys.stderr.flush()
            # 创建硬编码的page响应
            from datetime import datetime
            now = datetime.now().isoformat()
            return PageResponse(
                id="dam",
                title="Boarding Content DAM Page",
                description="Hardcoded Digital Asset Management page for boarding content",
                keywords="boarding,content,dam,assets,digital",
                content="<h1>Boarding Content DAM</h1><p>This is a hardcoded Digital Asset Management page for boarding content.</p><p>Path: /boarding/content/dam</p>",
                language="en",
                parent_path="content",
                other_language_path=None,
                status="published",
                metadata={"hardcoded": True, "path": "/boarding/content/dam", "source": "hardcoded-special-route"},
                hide_in_navigation=False,
                tags=["boarding", "content", "dam"],
                created_by="system",
                created_at=now,
                last_modified=now,
                last_published=now
            )

        # If路径Root path,返回合成page
        if normalized_path == '/':
            from datetime import datetime
            now = datetime.now().isoformat()
            return PageResponse(
                id='root',
                title='Root',
                description='Root page',
                keywords='',
                content='',
                language='en',
                parent_path=None,
                other_language_path=None,
                status='published',
                metadata={},
                hide_in_navigation=False,
                tags=[],
                created_by='system',
                created_at=now,
                last_modified=now,
                last_published=now
            )

        # Query directly using path field (simplified refactoring)
        sql = "SELECT * FROM webbot_page WHERE path = ?"
        params = (normalized_path,)
        print(f"DEBUG: SQL='{sql}', params={params}", file=sys.stderr)
        sys.stderr.flush()

        cursor.execute(sql, params)
        page = cursor.fetchone()
        print(f"DEBUG: found page={page}", file=sys.stderr)
        sys.stderr.flush()

        if not page:
            # 未找到page
            print(f"DEBUG: Page not found, raising 404", file=sys.stderr)
            sys.stderr.flush()
            raise HTTPException(status_code=404, detail=f"Page path not found: {path}")

        # Transform为字典并返回
        page_dict = dict(page)
        # 解析metadata field
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}

        # Populate file_path from ancestor inheritance if not directly set
        if not page_dict.get('file_path'):
            inherited_fp = get_ancestor_file_path(normalized_path, conn)
            if inherited_fp:
                page_dict['file_path'] = inherited_fp

        print(f"DEBUG: Returning page with id={page_dict.get('id')}, path={page_dict.get('path')}", file=sys.stderr)
        sys.stderr.flush()
        return PageResponse(**page_dict)

    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()

@router.get("/by-path/{path:path}/children", response_model=List[PageListItem])
async def get_page_children_by_path(path: str = ""):
    """Get direct children of a page by path

    Example: /api/v1/pages/by-path/canadasite/en/children
             /api/v1/pages/by-path/canadasite/en/mustache-templates/children
    """
    import sys
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalize path
        normalized_path = normalize_path(path)
        print(f"DEBUG get_page_children_by_path: path='{path}', normalized='{normalized_path}'", file=sys.stderr)

        # If路径Root path(空或单个斜杠),特殊处理
        if normalized_path == '/' or normalized_path == '':
            print("DEBUG: Root path requested, returning pages with parent_path IS NULL", file=sys.stderr)
            cursor.execute("""
                SELECT * FROM webbot_page
                WHERE parent_path IS NULL
                ORDER BY title ASC
            """)
        else:
            # 直接通过 path 列查找page(支持任意层级的路径)
            cursor.execute("SELECT id FROM webbot_page WHERE path = ?", (normalized_path,))
            parent_page = cursor.fetchone()
            if not parent_page:
                raise HTTPException(status_code=404, detail=f"Parent page path not found: {normalized_path}")

            parent_id = parent_page[0]
            # 查询所有parent_path等于该Page ID的子page
            cursor.execute("""
                SELECT * FROM webbot_page
                WHERE parent_path = ?
                ORDER BY title ASC
            """, (parent_id,))

        children = cursor.fetchall()
        result = []

        for child in children:
            child_dict = dict(child)
            # 解析metadata field
            if child_dict.get("metadata") and isinstance(child_dict["metadata"], str):
                try:
                    child_dict["metadata"] = json.loads(child_dict["metadata"])
                except json.JSONDecodeError:
                    child_dict["metadata"] = {}
            elif child_dict.get("metadata") is None:
                child_dict["metadata"] = {}
            result.append(PageListItem(**child_dict))

        print(f"DEBUG: Returning {len(result)} child pages", file=sys.stderr)
        return result

    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()

@router.get("/by-path/{full_path:path}", response_model=PageResponse)
async def get_page_by_path_param(full_path: str):
    """Get page by full path (path parameter version)

    Supports path parameter format: /api/v1/pages/by-path/boarding/content/dam
    Queries directly by path field without parsing id or parent_path.
    """
    import sys, json
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalize path
        normalized_path = normalize_path(full_path)
        print(f"DEBUG get_page_by_path_param: input='{full_path}', normalized='{normalized_path}'", file=sys.stderr)
        sys.stderr.flush()

        # 硬编码特定路径: /boarding/content/dam
        if normalized_path == '/boarding/content/dam':
            print(f"DEBUG: Returning hardcoded page for /boarding/content/dam", file=sys.stderr)
            sys.stderr.flush()
            # 创建硬编码的page响应
            from datetime import datetime
            now = datetime.now().isoformat()
            return PageResponse(
                id="dam",
                title="Boarding Content DAM Page",
                description="Hardcoded Digital Asset Management page for boarding content",
                keywords="boarding,content,dam,assets,digital",
                content="<h1>Boarding Content DAM</h1><p>This is a hardcoded Digital Asset Management page for boarding content.</p><p>Path: /boarding/content/dam</p>",
                language="en",
                parent_path="content",
                other_language_path=None,
                status="published",
                metadata={"hardcoded": True, "path": "/boarding/content/dam", "source": "hardcoded-special-route"},
                hide_in_navigation=False,
                tags=["boarding", "content", "dam"],
                created_by="system",
                created_at=now,
                last_modified=now,
                last_published=now
            )

        # If路径Root path,返回合成page
        if normalized_path == '/':
            from datetime import datetime
            now = datetime.now().isoformat()
            return PageResponse(
                id='root',
                title='Root',
                description='Root page',
                keywords='',
                content='',
                language='en',
                parent_path=None,
                other_language_path=None,
                status='published',
                metadata={},
                hide_in_navigation=False,
                tags=[],
                created_by='system',
                created_at=now,
                last_modified=now,
                last_published=now
            )

        # Query directly using path field (simplified refactoring)
        sql = "SELECT * FROM webbot_page WHERE path = ?"
        params = (normalized_path,)
        print(f"DEBUG: SQL='{sql}', params={params}", file=sys.stderr)
        sys.stderr.flush()

        cursor.execute(sql, params)
        page = cursor.fetchone()
        print(f"DEBUG: found page={page}", file=sys.stderr)
        sys.stderr.flush()

        if not page:
            # 未找到page
            print(f"DEBUG: Page not found, raising 404", file=sys.stderr)
            sys.stderr.flush()
            raise HTTPException(status_code=404, detail=f"Page path not found: {full_path}")

        # Transform为字典并返回
        page_dict = dict(page)
        # 解析metadata field
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}

        # Populate file_path from ancestor inheritance if not directly set
        if not page_dict.get('file_path'):
            inherited_fp = get_ancestor_file_path(normalized_path, conn)
            if inherited_fp:
                page_dict['file_path'] = inherited_fp

        print(f"DEBUG: Returning page with id={page_dict.get('id')}, path={page_dict.get('path')}", file=sys.stderr)
        sys.stderr.flush()
        return PageResponse(**page_dict)

    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()


@router.get("/metadata", response_model=PageMetadataResponse)
async def get_page_metadata(path: str = Query(..., description="Full page path, e.g. /canadasite/en/government")):
    """Get page hierarchy metadata

    Given a page path, returns:
    - page: current page
    - institution_level: third-level page (e.g. /canadasite/en/government)
    - language_level: second-level page (e.g. /canadasite/en)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        normalized = normalize_path(path)

        # 1. 获取当前page
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (normalized,))
        page_row = cursor.fetchone()
        page_data = dict(page_row) if page_row else None
        if page_data:
            _parse_page_dict(page_data)

        # 2. 获取语言级page (第2层 - /canadasite/en)
        path_parts = normalized.strip('/').split('/')
        lang_level_path = None
        if len(path_parts) >= 2:
            lang_level_path = '/' + '/'.join(path_parts[:2])

        lang_level_data = None
        if lang_level_path:
            cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (lang_level_path,))
            lang_row = cursor.fetchone()
            if lang_row:
                lang_level_data = dict(lang_row)
                _parse_page_dict(lang_level_data)

        # 3. 获取机构级page (第3层 - /canadasite/en/government)
        inst_level_path = None
        if len(path_parts) >= 3:
            inst_level_path = '/' + '/'.join(path_parts[:3])

        inst_level_data = None
        if inst_level_path and inst_level_path != normalized:
            cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (inst_level_path,))
            inst_row = cursor.fetchone()
            if inst_row:
                inst_level_data = dict(inst_row)
                _parse_page_dict(inst_level_data)

        return PageMetadataResponse(
            page=PageListItem(**page_data) if page_data else None,
            institution_level=PageListItem(**inst_level_data) if inst_level_data else None,
            language_level=PageListItem(**lang_level_data) if lang_level_data else None,
            path=normalized,
            path_depth=len(path_parts)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata query failed: {e}")
    finally:
        conn.close()


def _parse_page_dict(page_dict: dict):
    """Parse metadata field from page dictionary"""
    if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
        try:
            page_dict["metadata"] = json.loads(page_dict["metadata"])
        except json.JSONDecodeError:
            page_dict["metadata"] = {}
    elif page_dict.get("metadata") is None:
        page_dict["metadata"] = {}
    

@router.get("/parents")
async def get_parent_pages(path: str = Query(..., description="Full page path. Returns ancestor list (excluding self) and current page, e.g. path=/canadasite/en/government/system/laws")):
    """Get all ancestor pages and current page
    
    Given a page path, returns list of ancestor pages (from root to direct parent) and current page.
    Used for breadcrumb navigation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        normalized = normalize_path(path)
        path_parts = normalized.strip("/").split("/")
        
        parents = []
        page = None
        
        for depth in range(2, len(path_parts) + 1):
            ancestor_path = "/" + "/".join(path_parts[:depth])
            cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (ancestor_path,))
            row = cursor.fetchone()
            if row:
                page_dict = dict(row)
                _parse_page_dict(page_dict)
                item = PageListItem(**page_dict)
                if depth == len(path_parts):
                    page = item
                else:
                    parents.append(item)
        
        return {"parents": parents, "page": page}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ancestor query failed: {e}")
    finally:
        conn.close()

    
    
@router.get("/{page_id:path}/children", response_model=List[PageListItem])
async def get_page_children(page_id: str,
                            parent_path: Optional[str] = Query(None, description="Parent page path or ID, e.g. /en.")):
    """Get direct children of a page

    In the navigation tree, children need to be loaded on demand without loading all pages at once.
    This endpoint returns direct children of a page for lazy loading the navigation tree.

    Parameters:
    - page_id: parent page ID or path
    - parent_path: parent page path or ID, e.g. /en or page ID

    Returns:
    - all pages with parent_path matching the specified page_id
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        target_parent_path = None

        # 优先使用parent_pathParameter
        if parent_path is not None:
            # 使用parent_path查找父page
            # 首先尝试将parent_path作为路径查找父page
            cursor.execute("SELECT id, path FROM webbot_page WHERE path = ?", (parent_path.rstrip('/'),))
            parent_page = cursor.fetchone()

            if parent_page:
                # 找到了父page,使用其ID作为target_parent_path
                target_parent_path = parent_page['id']
            else:
                # Ifparent_path不Full path,可能父Page ID
                cursor.execute("SELECT id, path FROM webbot_page WHERE id = ?", (parent_path,))
                parent_page = cursor.fetchone()
                if parent_page:
                    target_parent_path = parent_page['id']
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Parent page not found: parent_path='{parent_path}'"
                    )

            # is now根据page_id和target_parent_path查找具体的父page
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path = ?", (page_id, target_parent_path))
            actual_parent = cursor.fetchone()
            if not actual_parent:
                # If找不到,尝试将page_id作为路径查找
                path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
                cursor.execute("SELECT id, parent_path FROM webbot_page WHERE path = ?", (path_to_try.rstrip('/'),))
                actual_parent = cursor.fetchone()
                if actual_parent:
                    target_parent_path = actual_parent['id']
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Parent page not found: id='{page_id}', parent_path='{parent_path}'"
                    )

        else:
            # 未指定父标识符,需要找到具体的父page
            # 首先尝试将page_id作为路径查找父page
            path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
            cursor.execute("SELECT id, parent_path FROM webbot_page WHERE path = ?", (path_to_try.rstrip('/'),))
            parent_page = cursor.fetchone()

            if parent_page:
                # 找到了page,使用其ID作为target_parent_path
                target_parent_path = parent_page['id']
            else:
                # 查找parent_path为NULL的page(根page)
                cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
                parent_page = cursor.fetchone()
                if parent_page:
                    target_parent_path = page_id
                else:
                    # 查找第一个匹配的page
                    cursor.execute("SELECT id FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                    parent_page = cursor.fetchone()
                    if not parent_page:
                        raise HTTPException(status_code=404, detail=f"Page not found: id='{page_id}'")
                    target_parent_path = page_id

        # Query all child pages whose parent_path equals target ID
        cursor.execute("""
            SELECT * FROM webbot_page
            WHERE parent_path = ?
            ORDER BY title ASC
        """, (target_parent_path,))

        children = cursor.fetchall()
        result = []

        for child in children:
            child_dict = dict(child)
            # 解析metadata field
            if child_dict.get("metadata") and isinstance(child_dict["metadata"], str):
                try:
                    child_dict["metadata"] = json.loads(child_dict["metadata"])
                except json.JSONDecodeError:
                    child_dict["metadata"] = {}
            elif child_dict.get("metadata") is None:
                child_dict["metadata"] = {}
            result.append(PageListItem(**child_dict))

        return result

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()


@router.get("/{page_id:path}/properties", response_model=PagePropertiesResponse)
async def get_page_properties(page_id: str,
                   parent_path: Optional[str] = Query(None, description="Parent page path or ID, e.g. /en or page ID.")):
    """Get page properties (without content field)

    Enhanced smart page lookup logic:
    1. First try page_id as path (path field)
    2. If not found, try using parent_path parameter (if provided)

    Supported formats:
    - Path format: GET /api/v1/pages/en/contact/properties → query path="/en/contact"
    - GET /api/v1/pages/contact/properties?parent_path=/en → query id="contact" AND parent_path="/en"
    - Full path: GET /api/v1/pages/canadasite/en/contact-us-page/properties → path="/canadasite/en/contact-us-page"
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        page = None

        # 步骤1: 尝试将page_id作为路径查询(最常见情况)
        # 确保路径以/开头(Ifpage_id不以/开头,Add/)
        path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
        normalized_path = path_to_try.rstrip('/')

        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (normalized_path,))
        page = cursor.fetchone()

        # 步骤2: If没找到,且page_id不以/开头,尝试使用parent_pathParameter
        if not page and not page_id.startswith('/'):
            if parent_path is not None:
                # 使用parent_pathParameter查找
                # parent_path可能Full path如"/en",也可能父Page ID
                # 首先尝试直接查询:id = ? AND parent_path = ?
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?",
                             (page_id, parent_path))
                page = cursor.fetchone()

                if not page:
                    # Ifparent_path父Page ID(如"en"),而不Full path,尝试Transform
                    # 查询父page的路径
                    cursor.execute("SELECT path FROM webbot_page WHERE id = ? LIMIT 1", (parent_path,))
                    parent_row = cursor.fetchone()
                    if parent_row:
                        actual_parent_path = parent_row['path']
                        cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?",
                                     (page_id, actual_parent_path))
                        page = cursor.fetchone()

            # 步骤3: If还没有找到,尝试查找parent_path为NULL的page(根page)
            if not page and parent_path is None:
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
                page = cursor.fetchone()

                # 步骤5: 作为最后手段,查找第一个匹配的page
                if not page:
                    cursor.execute("SELECT * FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                    page = cursor.fetchone()

        if not page:
            # Provide useful error message
            error_details = []
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")

            error_msg = f"Page not found: id='{page_id}'"
            if error_details:
                error_msg += f", {', '.join(error_details)}"
            error_msg += f". Tried path: '{normalized_path}'"

            raise HTTPException(status_code=404, detail=error_msg)

        page_dict = dict(page)
        # 解析metadata field(数据库存储为JSON字符串)
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}
        # 移除content字段,因为它可能很大
        page_dict.pop("content", None)
        return PagePropertiesResponse(**page_dict)

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()


@router.get("/{page_id:path}", response_model=PageResponse)
async def get_page(page_id: str,
                   parent_path: Optional[str] = Query(None, description="Parent page path or ID, e.g. /en or page ID.")):
    """Get a single page

    Enhanced smart page lookup logic:
    1. First try page_id as path (path field)
    2. If not found, try using parent_path parameter (if provided)

    Supported formats:
    - Path format: GET /api/v1/pages/en/contact → query path="/en/contact"
    - GET /api/v1/pages/contact?parent_path=/en → query id="contact" AND parent_path="/en"
    - Full path: GET /api/v1/pages/canadasite/en/contact-us-page → path="/canadasite/en/contact-us-page"
    """
    # Root path / 特殊处理:返回合成根page
    if page_id == '/' or page_id == '':
        now = datetime.utcnow()
        return PageResponse(
            id='root',
            title='Home',
            path='/',
            language='en',
            status='published',
            created_by='system',
            created_at=now,
            last_modified=now,
            last_published=None,
            metadata={}
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        page = None

        # 步骤1: 尝试将page_id作为路径查询(最常见情况)
        # 确保路径以/开头(Ifpage_id不以/开头,Add/)
        path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
        normalized_path = path_to_try.rstrip('/')

        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (normalized_path,))
        page = cursor.fetchone()

        # 步骤2: If没找到,且page_id不以/开头,尝试使用parent_pathParameter
        if not page and not page_id.startswith('/'):
            if parent_path is not None:
                # 使用parent_pathParameter查找
                # parent_path可能Full path如"/en",也可能父Page ID
                # 首先尝试直接查询:id = ? AND parent_path = ?
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?",
                             (page_id, parent_path))
                page = cursor.fetchone()

                if not page:
                    # Ifparent_path父Page ID(如"en"),而不Full path,尝试Transform
                    # 查询父page的路径
                    cursor.execute("SELECT path FROM webbot_page WHERE id = ? LIMIT 1", (parent_path,))
                    parent_row = cursor.fetchone()
                    if parent_row:
                        actual_parent_path = parent_row['path']
                        cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?",
                                     (page_id, actual_parent_path))
                        page = cursor.fetchone()

            # 步骤3: If还没有找到,尝试查找parent_path为NULL的page(根page)
            if not page and parent_path is None:
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
                page = cursor.fetchone()

                # 步骤5: 作为最后手段,查找第一个匹配的page
                if not page:
                    cursor.execute("SELECT * FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                    page = cursor.fetchone()

        if not page:
            # Provide useful error message
            error_details = []
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")

            error_msg = f"Page not found: id='{page_id}'"
            if error_details:
                error_msg += f", {', '.join(error_details)}"
            error_msg += f". Tried path: '{normalized_path}'"

            raise HTTPException(status_code=404, detail=error_msg)

        page_dict = dict(page)
        # 解析metadata field(数据库存储为JSON字符串)
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}
        return PageResponse(**page_dict)

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()



@router.put("/{page_id:path}", response_model=PageResponse)
async def update_page(page_id: str, page_update: PageUpdate,
                     parent_path: Optional[str] = Query(None, description="Parent page path or ID, e.g. /en or page ID.")):
    """Update page

    Enhanced smart page lookup logic (consistent with GET endpoint):
    1. First try page_id as path (path field)
    2. If not found, try using parent_path parameter (if provided)

    Supported formats:
    - Path format: PUT /api/v1/pages/en/contact → update page with path="/en/contact"
    - PUT /api/v1/pages/contact?parent_path=/en → update with id="contact" AND parent_path="/en"

    When updating parent_path field, the page path is automatically recalculated.
    """
    import sys
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 智能page查找逻辑(与GET和DELETE端点保持一致)
        existing_page = None
        target_parent_path = None
        target_parent_path = None
        actual_page_id = page_id  # 实际用于WHERE条件的Page ID

        # 步骤1: 尝试将page_id作为路径查询(最常见情况)
        # 确保路径以/开头(Ifpage_id不以/开头,Add/)
        path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
        normalized_path = path_to_try.rstrip('/')

        print(f"DEBUG update_page: page_id='{page_id}', path_to_try='{path_to_try}', normalized_path='{normalized_path}'", file=sys.stderr)
        sys.stderr.flush()

        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (normalized_path,))
        existing_page = cursor.fetchone()
        print(f"DEBUG update_page: existing_page found via path={existing_page is not None}", file=sys.stderr)
        sys.stderr.flush()

        # 步骤2: If没找到,且page_id不以/开头,尝试使用parent_pathParameter
        if not existing_page and not page_id.startswith('/'):
            if parent_path is not None:
                # 使用parent_pathParameter查找
                target_parent_path = parent_path
                # parent_path可能Full path如"/en",也可能父Page ID
                # 首先尝试直接查询:id = ? AND parent_path = ?
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?",
                             (page_id, parent_path))
                existing_page = cursor.fetchone()

                if not existing_page:
                    # Ifparent_path父Page ID(如"en"),而不Full path,尝试Transform
                    # 查询父page的路径
                    cursor.execute("SELECT path FROM webbot_page WHERE id = ? LIMIT 1", (parent_path,))
                    parent_row = cursor.fetchone()
                    if parent_row:
                        actual_parent_path = parent_row['path']
                        target_parent_path = actual_parent_path
                        cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?",
                                     (page_id, actual_parent_path))
                        existing_page = cursor.fetchone()

            # 步骤3: If还没有找到,尝试查找parent_path为NULL的page(根page)
            if not existing_page and parent_path is None:
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
                existing_page = cursor.fetchone()

                # 步骤5: 作为最后手段,查找第一个匹配的page
                if not existing_page:
                    cursor.execute("SELECT * FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                    existing_page = cursor.fetchone()

        if not existing_page:
            # Provide useful error message
            error_details = []
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")

            error_msg = f"Page not found: id='{page_id}'"
            if error_details:
                error_msg += f", {', '.join(error_details)}"
            error_msg += f". Tried path: '{normalized_path}'"

            raise HTTPException(status_code=404, detail=error_msg)

        # Determine target parent identifier for subsequent update
        # If通过Parameter找到了page,使用相应的标识符
        # 则使用page本身的parent_path或parent_path
        if not target_parent_path and not target_parent_path:
            # 从现有page获取实际ID和父标识符
            actual_page_id = existing_page['id']
            if existing_page['parent_path']:
                target_parent_path = existing_page['parent_path']
                print(f"DEBUG update_page: setting target_parent_path from existing_page: '{target_parent_path}'", file=sys.stderr)
                sys.stderr.flush()
            elif existing_page['parent_path']:
                target_parent_path = existing_page['parent_path']
                print(f"DEBUG update_page: setting target_parent_path from existing_page: '{target_parent_path}'", file=sys.stderr)
                sys.stderr.flush()
        else:
            # 通过Parameter找到page,使用传入的page_id
            actual_page_id = page_id

        print(f"DEBUG update_page: actual_page_id='{actual_page_id}', target_parent_path='{target_parent_path}', target_parent_path='{target_parent_path}'", file=sys.stderr)
        sys.stderr.flush()

        # Build update fields
        update_fields = []
        update_values = []

        if page_update.title is not None:
            update_fields.append("title = ?")
            update_values.append(page_update.title)

        if page_update.description is not None:
            update_fields.append("description = ?")
            update_values.append(page_update.description)

        if page_update.keywords is not None:
            update_fields.append("keywords = ?")
            update_values.append(page_update.keywords)

        if page_update.content is not None:
            update_fields.append("content = ?")
            update_values.append(page_update.content)

        if page_update.language is not None:
            update_fields.append("language = ?")
            update_values.append(page_update.language)

        if page_update.parent_path is not None:
            update_fields.append("parent_path = ?")
            update_values.append(page_update.parent_path)

        if page_update.other_language_path is not None:
            update_fields.append("other_language_path = ?")
            update_values.append(page_update.other_language_path)

        if page_update.other_language_path is not None:
            update_fields.append("other_language_path = ?")
            update_values.append(page_update.other_language_path)

        if page_update.status is not None:
            update_fields.append("status = ?")
            update_values.append(page_update.status.value)

        if page_update.metadata is not None or page_update.file_path is not None:
            # Get existing metadata from DB (may include file_path etc.)
            cursor.execute("SELECT metadata FROM webbot_page WHERE id = ?", (actual_page_id,))
            existing_row = cursor.fetchone()
            merged_metadata = json.loads(existing_row['metadata']) if existing_row and existing_row['metadata'] else {}

            if page_update.metadata is not None:
                merged_metadata.update(page_update.metadata)
                merged_metadata.pop('original_html', None)

            if page_update.file_path is not None:
                if page_update.file_path == '':
                    merged_metadata.pop('file_path', None)
                else:
                    merged_metadata['file_path'] = page_update.file_path

            update_fields.append("metadata = ?")
            update_values.append(json.dumps(merged_metadata))

        if page_update.hide_in_navigation is not None:
            update_fields.append("hide_in_navigation = ?")
            update_values.append(1 if page_update.hide_in_navigation else 0)

        # IfNo update fields,直接返回原page
        if not update_fields:
            return PageResponse(**dict(existing_page))

        # Add最后修改时间
        update_fields.append("last_modified = ?")
        update_values.append(datetime.now().isoformat())

        print(f"DEBUG update_page: update_fields={update_fields}", file=sys.stderr)
        sys.stderr.flush()
        print(f"DEBUG update_page: update_values={update_values}", file=sys.stderr)
        sys.stderr.flush()

        # Execute update - using smart identifier
        # Build WHERE clause:优先使用parent_path,其次parent_path

        if target_parent_path is not None:
            # 使用parent_path作为标识符
            update_values.append(actual_page_id)  # WHERE条件: id = ?
            update_values.append(target_parent_path)  # AND parent_path = ?
            update_query = f"UPDATE webbot_page SET {', '.join(update_fields)} WHERE id = ? AND parent_path = ?"
            print(f"DEBUG update_page: Executing query: {update_query}", file=sys.stderr)
            print(f"DEBUG update_page: With values: {update_values}", file=sys.stderr)
            sys.stderr.flush()
            cursor.execute(update_query, update_values)
            print(f"UPDATE: Using parent_path={target_parent_path} for page {actual_page_id}", file=sys.stderr)
            sys.stderr.flush()
        elif target_parent_path is not None:
            # 使用parent_path作为标识符(向后兼容)
            update_values.append(actual_page_id)  # WHERE条件: id = ?
            update_values.append(target_parent_path)  # AND parent_path = ?
            update_query = f"UPDATE webbot_page SET {', '.join(update_fields)} WHERE id = ? AND parent_path = ?"
            print(f"DEBUG update_page: Executing query: {update_query}", file=sys.stderr)
            print(f"DEBUG update_page: With values: {update_values}", file=sys.stderr)
            sys.stderr.flush()
            cursor.execute(update_query, update_values)
            print(f"DEPRECATED UPDATE: Using parent_path={target_parent_path} for page {actual_page_id}. Please update to use parent_path.", file=sys.stderr)
            sys.stderr.flush()
        else:
            # 没有父标识符,查找parent_path为NULL的page(根page)
            update_values.append(actual_page_id)  # WHERE条件: id = ?
            update_query = f"UPDATE webbot_page SET {', '.join(update_fields)} WHERE id = ? AND parent_path IS NULL"
            print(f"DEBUG update_page: Executing query: {update_query}", file=sys.stderr)
            print(f"DEBUG update_page: With values: {update_values}", file=sys.stderr)
            sys.stderr.flush()
            cursor.execute(update_query, update_values)

        # Check if path needs updating
        need_path_update = False
        if page_update.parent_path is not None or page_update.parent_path is not None or page_update.language is not None:
            need_path_update = True

        # If需要更New路径,重New计算path和other_language_path
        # TODO: 实现完整的路径重New计算逻辑,支持parent_path
        # 当前Version简化处理,仅记录日志
        if need_path_update:
            print(f"PATH UPDATE NEEDED for page {page_id}: parent_path={page_update.parent_path}, parent_path={page_update.parent_path}, language={page_update.language}")
            # 简化处理:暂时不重New计算路径,避免复杂逻辑错误
            # 完整实现将在后续Version中Add
            pass

        conn.commit()

        # Cascade other_language_path to parent if parent's is empty
        if page_update.other_language_path is not None and existing_page is not None:
            try:
                # Convert Row to dict for .get() method
                existing_dict = dict(existing_page)
                parent_path_col = existing_dict.get('parent_path')
                if parent_path_col:
                    child_other = page_update.other_language_path.rstrip('/')
                    # Derive parent other_language_path: remove last segment from child's
                    parent_other = '/'.join(child_other.split('/')[:-1]) or '/'
                    if parent_other:
                        cursor.execute("SELECT id, other_language_path FROM webbot_page WHERE path = ? LIMIT 1", (parent_path_col,))
                        parent_row = cursor.fetchone()
                        if parent_row and not parent_row['other_language_path']:
                            cursor.execute(
                                "UPDATE webbot_page SET other_language_path = ?, last_modified = ? WHERE path = ?",
                                (parent_other, datetime.now().isoformat(), parent_path_col)
                            )
                            conn.commit()
                            print(f"CASCADED other_language_path to parent {parent_path_col}: {parent_other}", file=sys.stderr)
            except Exception as e:
                print(f"ERROR cascading other_language_path: {e}", file=sys.stderr)
                traceback.print_exc()

        print(f"DEBUG update_page: Fetching updated page with actual_page_id='{actual_page_id}',", file=sys.stderr)
        sys.stderr.flush()

        # 获取更New后的page - 使用智能标识符
        if target_parent_path is not None:
            cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?",
                         (actual_page_id, target_parent_path))
            print(f"DEBUG update_page: Querying updated page: id={actual_page_id}, parent_path={target_parent_path}", file=sys.stderr)
            sys.stderr.flush()
        elif target_parent_path is not None:
            cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?",
                         (actual_page_id, target_parent_path))
            print(f"DEBUG update_page: Querying updated page: id={actual_page_id}, parent_path={target_parent_path}", file=sys.stderr)
            sys.stderr.flush()
        else:
            cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path IS NULL",
                         (actual_page_id,))
            print(f"DEBUG update_page: Querying updated page: id={actual_page_id}, parent_path IS NULL", file=sys.stderr)
            sys.stderr.flush()
        updated_page = cursor.fetchone()
        print(f"DEBUG update_page: updated_page found={updated_page is not None}", file=sys.stderr)
        sys.stderr.flush()

        if not updated_page:
            # If找不到更New后的page,返回原始page(至少更New应该成功了)
            print(f"WARNING: Could not fetch updated page after update. Returning original page.", file=sys.stderr)
            sys.stderr.flush()
            updated_page = existing_page

        # 解析metadata field(数据库存储为JSON字符串)
        page_dict = dict(updated_page)
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}

        print(f"DEBUG update_page: Successfully updated page {actual_page_id}", file=sys.stderr)
        sys.stderr.flush()
        return PageResponse(**page_dict)

    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {e}")
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    finally:
        conn.close()

@router.delete("/{page_id:path}")
async def delete_page(
    page_id: str,
    delete_other_language: bool = Query(False, description="Also delete the other language page"),
    other_language_path: Optional[str] = Query(None, description="Explicit other language path to delete")
):
    """Delete page

    page_id is now the full path (e.g. /canadasite/en/contact), queried directly by path.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Look up page directly by path
        cursor.execute("SELECT id, other_language_path FROM webbot_page WHERE path = ?", (page_id,))
        page_row = cursor.fetchone()
        if not page_row:
            raise HTTPException(status_code=404, detail="Page not found")

        # Determine the other language path to also delete
        target_other_path = other_language_path or page_row['other_language_path']

        # Delete main page
        cursor.execute("DELETE FROM webbot_page WHERE path = ?", (page_id,))

        # Delete other language page if requested
        deleted_other = None
        if delete_other_language and target_other_path:
            cursor.execute("SELECT id FROM webbot_page WHERE path = ?", (target_other_path,))
            if cursor.fetchone():
                cursor.execute("DELETE FROM webbot_page WHERE path = ?", (target_other_path,))
                deleted_other = target_other_path

        conn.commit()

        result = {"message": "Page deleted successfully", "page_id": page_id}
        if deleted_other:
            result["other_deleted"] = deleted_other
        return result

    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
    finally:
        conn.close()


# ==================== Template-related API ====================

@router.get("/templates", response_model=List[PageListItem])
async def list_templates():
    """Get all template pages"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 查询所有以 /templates/ 开头的page
        cursor.execute("""
            SELECT * FROM webbot_page
            WHERE id LIKE '/templates/%'
            ORDER BY created_at DESC
        """)

        templates = cursor.fetchall()
        result = []

        for template in templates:
            template_dict = dict(template)
            # 解析metadata field
            if template_dict.get("metadata") and isinstance(template_dict["metadata"], str):
                try:
                    template_dict["metadata"] = json.loads(template_dict["metadata"])
                except json.JSONDecodeError:
                    template_dict["metadata"] = {}
            elif template_dict.get("metadata") is None:
                template_dict["metadata"] = {}
            result.append(PageListItem(**template_dict))

        return result

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()


# ==================== Bilingual page creation API ====================

# 双语创建请求模型(临时定义,后续可移到models.py)
from pydantic import BaseModel, Field

class BilingualTemplateCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=100, description="Filename (without path)")
    description: str = Field(..., min_length=1, max_length=1000, description="pageDescription")
    template_id: str = Field(..., description="Template page ID, e.g. /templates/standard-page")
    input_language: str = Field("en", description="Enter language code (en, fr, zh)")
    auto_translate: bool = Field(True, description="Auto-translate?")


def _preserve_case(original: str, translated: str) -> str:
    """Preserve original text casing"""
    if not original or not translated:
        return translated

    # If原始文本全部大写
    if original.isupper():
        return translated.upper()
    # If原始文本标题格式(每个单词首字母大写)
    elif original.istitle():
        return translated.title()
    # If原始文本首字母大写
    elif original[0].isupper() and not original[1:].isupper():
        return translated[0].upper() + translated[1:] if translated else translated
    # 其他情况保持小写
    else:
        return translated.lower()


def translate_with_ollama(text: str, source_lang: str = "en", target_lang: str = "fr") -> str:
    """Translate text using Ollama (supports en↔fr, en↔zh, fr↔zh)"""
    try:
        if not text or text.strip() == "":
            return text

        # 根据语言对选择提示词
        prompt_templates = {
            ("en", "fr"): "Translate the following English text to French. Only return the translation, no explanation:\n\n{text}",
            ("en", "zh"): "Translate the following English text to Chinese. Only return the translation, no explanation:\n\n{text}",
            ("fr", "en"): "Translate the following French text to English. Only return the translation, no explanation:\n\n{text}",
            ("fr", "zh"): "Translate the following French text to Chinese. Only return the translation, no explanation:\n\n{text}",
            ("zh", "en"): "Translate the following Chinese text to English. Only return the translation, no explanation:\n\n{text}",
            ("zh", "fr"): "Translate the following Chinese text to French. Only return the translation, no explanation:\n\n{text}",
        }

        # 获取对应的提示词模板
        prompt_template = prompt_templates.get((source_lang, target_lang))
        if not prompt_template:
            print(f"不支持的翻译方向: {source_lang} → {target_lang}")
            return text

        prompt = prompt_template.format(text=text)

        # 尝试多个模型,从最小的开始(is now有了tinyllama)
        models_to_try = ["tinyllama:latest", "deepseek-r1:8b", "llama3.1:latest"]

        for model in models_to_try:
            try:
                print(f"尝试使用模型 {model} 翻译 {source_lang}→{target_lang}: '{text[:50]}...'")
                response = requests.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3}
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    result = response.json()
                    translation = result.get("response", "").strip()
                    # 清理可能的额外文本
                    translation = translation.split('\n')[0].strip()
                    if translation and translation != text:
                        print(f"翻译成功: '{text}' -> '{translation}' (模型: {model})")
                        return translation
                    else:
                        print(f"翻译返回空或相同文本,尝试下一个模型")
                else:
                    error_msg = response.json().get("error", "Unknown error") if response.text else "No error message"
                    print(f"模型 {model} 失败: {response.status_code} - {error_msg}")

            except Exception as model_error:
                print(f"模型 {model} 异常: {model_error}")
                continue

        # 所有模型都失败,尝试简单回退翻译
        print(f"所有Ollama模型失败,使用简单回退翻译")

        # 多语言回退词典(简化版)
        fallback_translations = {
            # 英法词典
            ("en", "fr"): {
                "welcome": "bienvenue",
                "summerland": "Summerland",
                "contact": "contact",
                "services": "services",
                "government": "gouvernement",
                "municipal": "municipal",
                "public": "public",
                "information": "information",
                "home": "accueil",
                "about": "à propos",
                "contact us": "contactez-nous",
                "services portal": "portail de services",
            },

            # 英中词典 (BC省市政服务重点词汇)
            ("en", "zh"): {
                "welcome": "欢迎",
                "summerland": "夏乡",
                "contact": "联系我们",
                "services": "服务项目",
                "government": "政府",
                "municipal": "市政府",
                "public": "公共",
                "information": "Information",
                "home": "首页",
                "about": "关于我们",
                "contact us": "联系我们",
                "services portal": "服务门户",
                "government services": "政府服务",
                "public services": "公共服务",
                "community services": "社区服务",
                "online services": "在线服务",
            },

            # 法中词典
            ("fr", "zh"): {
                "bienvenue": "欢迎",
                "contactez-nous": "联系我们",
                "services": "服务",
                "gouvernement": "政府",
                "municipal": "市政",
                "public": "公共",
                "information": "Information",
                "accueil": "首页",
                "à propos": "关于",
                "portail de services": "服务门户",
                "services gouvernementaux": "政府服务",
            },

            # 中英词典
            ("zh", "en"): {
                "欢迎": "welcome",
                "联系我们": "contact us",
                "服务": "services",
                "政府": "government",
                "市政": "municipal",
                "公共": "public",
                "Information": "information",
                "首页": "home",
                "关于": "about",
            }
        }

        # 获取对应语言对的词典
        lang_dict = fallback_translations.get((source_lang, target_lang), {})
        text_lower = text.lower()

        # 首先尝试完全匹配
        if text_lower in lang_dict:
            translated = lang_dict[text_lower]
            return _preserve_case(text, translated)

        # 然后尝试部分匹配(包含关系)
        for source_word, target_word in lang_dict.items():
            if source_word in text_lower:
                # If匹配的整个单词(有空格边界或字符串边界)
                import re
                pattern = r'(^|\s)' + re.escape(source_word) + r'(\s|$)'
                if re.search(pattern, text_lower):
                    # Replace匹配的部分
                    result = re.sub(r'(^|\s)' + re.escape(source_word) + r'(\s|$)',
                                   r'\1' + target_word + r'\2',
                                   text_lower,
                                   flags=re.IGNORECASE)
                    # 恢复原始大小写格式
                    return _preserve_case(text, result)

        # 没有匹配的简单翻译,返回原文本
        return text

    except Exception as e:
        print(f"翻译异常: {e}")
        return text

@router.post("/bilingual-template", response_model=Dict[str, Any])
async def create_bilingual_template(page_data: BilingualTemplateCreate):
    """
    Create bilingual page from template

    Workflow:
    1. Get template page content
    2. Translate filename and description
    3. Generate bilingual paths
    4. Create English page
    5. Create French page
    6. Set page association as bilingual path
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # ========== 步骤1: Get template ==========
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (page_data.template_id,))
        template = cursor.fetchone()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {page_data.template_id}")

        template_dict = dict(template)

        # ========== 步骤2: 翻译处理 ==========
        # Prepare English data
        english_title = page_data.filename.replace('-', ' ').title()
        english_description = page_data.description

        # Translate to French
        french_title = english_title
        french_description = english_description

        if page_data.auto_translate:
            # 翻译标题
            french_title = translate_with_ollama(english_title, "en", "fr")
            # 翻译Description
            french_description = translate_with_ollama(english_description, "en", "fr")

        # ========== 步骤3: Generate paths ==========
        # Generate base filename(URL友好格式)
        import re
        english_filename = re.sub(r'[^a-zA-Z0-9]', '-', page_data.filename.lower()).strip('-')
        french_filename = re.sub(r'[^a-zA-Z0-9]', '-', french_title.lower()).strip('-')

        # Generate paths
        english_path = f"/canadasite/en/{english_filename}"
        french_path = generate_french_path(english_path)

        # If翻译后的路径与英文路径相同,使用备用方案
        if french_path == english_path:
            french_path = f"/canadasite/fr/{french_filename}"

        # ========== 步骤4: 创建英文page ==========
        now = datetime.now().isoformat()

        # 准备Page data
        english_page_data = {
            "id": english_path,
            "title": english_title,
            "content": template_dict.get("content", ""),
            "language": "en",
            "parent_path": extract_parent_path_from_path(english_path),
            "other_language_path": french_path,  # 关联法文page
            "status": "draft",
            "metadata": json.dumps({"template_source": page_data.template_id}),
            "created_at": now,
            "last_modified": now
        }

        cursor.execute("""
            INSERT INTO webbot_page
            (id, title, content, language, parent_path, other_language_path, status, metadata, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            english_page_data["id"],
            english_page_data["title"],
            english_page_data["content"],
            english_page_data["language"],
            english_page_data["parent_path"],
            english_page_data["other_language_path"],
            english_page_data["status"],
            english_page_data["metadata"],
            english_page_data["created_at"],
            english_page_data["last_modified"]
        ))

        # ========== 步骤5: 创建法文page ==========
        french_page_data = {
            "id": french_path,
            "title": french_title,
            "content": template_dict.get("content", ""),
            "language": "fr",
            "parent_path": extract_parent_path_from_path(french_path),
            "other_language_path": english_path,  # 关联英文page
            "status": "draft",
            "metadata": json.dumps({"template_source": page_data.template_id}),
            "created_at": now,
            "last_modified": now
        }

        cursor.execute("""
            INSERT INTO webbot_page
            (id, title, content, language, parent_path, other_language_path, status, metadata, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            french_page_data["id"],
            french_page_data["title"],
            french_page_data["content"],
            french_page_data["language"],
            french_page_data["parent_path"],
            french_page_data["other_language_path"],
            french_page_data["status"],
            french_page_data["metadata"],
            french_page_data["created_at"],
            french_page_data["last_modified"]
        ))

        conn.commit()

        # ========== 步骤6: 获取创建的page ==========
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (english_path,))
        english_page = dict(cursor.fetchone())

        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (french_path,))
        french_page = dict(cursor.fetchone())

        # 解析metadata field
        for page in [english_page, french_page]:
            if page.get("metadata") and isinstance(page["metadata"], str):
                try:
                    page["metadata"] = json.loads(page["metadata"])
                except json.JSONDecodeError:
                    page["metadata"] = {}
            elif page.get("metadata") is None:
                page["metadata"] = {}

        return {
            "english_page": PageResponse(**english_page),
            "french_page": PageResponse(**french_page),
            "translation_stats": {
                "english_title": english_title,
                "french_title": french_title,
                "english_path": english_path,
                "french_path": french_path,
                "auto_translate": page_data.auto_translate,
                "template_used": page_data.template_id
            }
        }

    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="Page path already exists, please use a different filename")
        raise HTTPException(status_code=500, detail=f"Database constraint error: {e}")
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Create failed: {e}")
    finally:
        conn.close()

@router.get("/test-debug")
async def test_debug():
    """Test endpoint to verify routing works"""
    import sys
    print("DEBUG: test_debug endpoint called", file=sys.stderr)
    sys.stderr.flush()
    return {"message": "Test endpoint working", "status": "ok"}

@router.get("/test-path-param")
async def test_path_param(path: str = Query(..., description="Test path parameter")):
    """Test Query parameter reception"""
    import sys
    print(f"DEBUG: test_path_param called with path={path}", file=sys.stderr)
    sys.stderr.flush()
    return {"received_path": path, "status": "success"}


