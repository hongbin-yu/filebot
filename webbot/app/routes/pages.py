"""
页面管理路由
"""

from fastapi import APIRouter, HTTPException, Depends, Query
import sqlite3
import json
import uuid
import requests
import re
import traceback
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.models import PageCreate, PageUpdate, PageResponse, PagePropertiesResponse, PageStatus

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = sqlite3.connect("/home/hongb/.openclaw/workspace/filebot/backend/filebot.db")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {e}")

def generate_page_id(title: str) -> str:
    """根据标题生成页面ID"""
    # 简单实现：将标题转换为小写，替换空格为连字符
    import re
    # 移除特殊字符，只保留字母数字和空格
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    # 替换空格为连字符，转换为小写
    page_id = re.sub(r'\s+', '-', cleaned.strip()).lower()
    # 如果为空，生成随机ID
    if not page_id:
        page_id = f"page-{uuid.uuid4().hex[:8]}"
    return page_id

def extract_language_from_path(path: str) -> str:
    """
    从路径中提取语言代码
    支持多种路径格式：
    - /en/contact → "en" (简单格式，第一个节点是语言)
    - /canadasite/en/contact → "en" (完整格式，第二个节点是语言)
    - /fr/about → "fr"
    - /zh/contact → "zh" (中文支持，BC省重点需求)
    """
    if not path:
        return "en"
    
    # 清理路径：移除首尾斜杠，分割节点
    clean_path = path.strip('/')
    parts = clean_path.split('/')
    
    if len(parts) == 0:
        return "en"
    
    # 检查常见站点前缀
    # 如果第一个部分是已知站点前缀（如canadasite），则第二个部分是语言
    known_site_prefixes = ['canadasite', 'site', 'www']
    if len(parts) >= 2 and parts[0] in known_site_prefixes:
        # 完整格式：/canadasite/en/contact
        lang = parts[1].lower()
    else:
        # 简单格式：/en/contact
        lang = parts[0].lower()
    
    # 验证是否为支持的语言（扩展支持中文）
    if lang in ['en', 'fr', 'zh']:
        return lang
    
    # 默认返回英语
    return "en"

def get_ancestor_file_path(parent_path: Optional[str], conn) -> Optional[str]:
    """
    递归获取祖先页面的file_path。
    从父页面开始，向上查询直到找到file_path或到达根页面。
    """
    if not parent_path:
        return None
    
    current_id = parent_path
    visited = set()  # 防止循环
    
    while current_id and current_id not in visited:
        visited.add(current_id)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata, parent_path FROM webbot_page WHERE id = ?", (current_id,))
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
        
        # 继续向上查询父页面
        current_id = row["parent_path"]
    
    return None

def normalize_path(path: str) -> str:
    """规范化路径：确保以斜杠开头，不以斜杠结尾"""
    if not path:
        return ""
    # 确保以斜杠开头
    if not path.startswith('/'):
        path = '/' + path
    # 移除末尾斜杠（除非是根路径）
    if path.endswith('/') and path != '/':
        path = path.rstrip('/')
    return path

def extract_parent_path_from_path(path: str) -> Optional[str]:
    """
    从路径推断父页面路径
    例如：
    - /canadasite/en/about → /canadasite/en
    - /canadasite/en → None (根页面)
    - /canadasite/en/about/contact → /canadasite/en/about
    """
    if not path or path == '/':
        return None
    
    normalized = normalize_path(path)
    # 移除末尾的路径部分
    parent_path = '/'.join(normalized.rstrip('/').split('/')[:-1])
    
    # 如果父路径为空，返回None
    if not parent_path:
        return None
    
    return parent_path if parent_path.startswith('/') else '/' + parent_path

def calculate_page_path(page_id: str, parent_path: Optional[str], language: str, conn) -> str:
    """
    计算页面的完整路径
    规则：
    1. 如果parent_path为空：根页面，路径为 /{language}/{page_id} 
       特殊情况：如果page_id是语言代码（en/fr），路径为 /{page_id}
    2. 如果parent_path不为空：路径为 {父页面路径}/{page_id}
    """
    if not parent_path:
        # 根页面
        if page_id in ['en', 'fr']:
            return f"/{page_id}"
        return f"/{language}/{page_id}"
    
    # 获取父页面路径
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM webbot_page WHERE id = ? AND parent_path IS ?", 
                  (parent_path, get_parent_parent_path(parent_path, conn)))
    parent_row = cursor.fetchone()
    
    if not parent_row or not parent_row['path']:
        # 父页面没有路径，递归计算
        # 先获取父页面的信息
        cursor.execute("SELECT language, parent_path FROM webbot_page WHERE id = ? AND parent_path IS ?", 
                      (parent_path, get_parent_parent_path(parent_path, conn)))
        parent_info = cursor.fetchone()
        if not parent_info:
            # 父页面不存在，按根页面处理
            return f"/{language}/{page_id}"
        
        parent_language = parent_info['language']
        parent_parent_path = parent_info['parent_path']
        parent_path = calculate_page_path(parent_path, parent_parent_path, parent_language, conn)
    else:
        parent_path = parent_row['path']
    
    # 构建完整路径
    return f"{parent_path.rstrip('/')}/{page_id}"

def get_parent_parent_path(parent_path: str, conn) -> Optional[str]:
    """获取父页面的parent_path（用于复合主键查询）"""
    cursor = conn.cursor()
    cursor.execute("SELECT parent_path FROM webbot_page WHERE id = ? LIMIT 1", (parent_path,))
    row = cursor.fetchone()
    return row['parent_path'] if row else None

def update_page_path(page_id: str, parent_path: Optional[str], new_path: str, conn):
    """更新页面路径，并递归更新子页面路径"""
    cursor = conn.cursor()
    
    # 更新当前页面路径
    cursor.execute("""
        UPDATE webbot_page 
        SET path = ?, last_modified = CURRENT_TIMESTAMP
        WHERE id = ? AND parent_path IS ?
    """, (new_path, page_id, parent_path))
    
    # 递归更新所有子页面
    rebuild_subtree_paths(page_id, new_path, conn)

def rebuild_subtree_paths(root_id: str, parent_path: str, conn):
    """递归重建子树中所有页面的路径"""
    cursor = conn.cursor()
    
    # 获取所有直接子页面
    cursor.execute("SELECT id, language, parent_path FROM webbot_page WHERE parent_path = ?", (parent_path,))
    children = cursor.fetchall()
    
    for child in children:
        child_id = child['id']
        child_language = child['language']
        
        # 计算子页面新路径
        child_path = f"{parent_path.rstrip('/')}/{child_id}"
        
        # 更新子页面
        cursor.execute("""
            UPDATE webbot_page 
            SET path = ?, last_modified = CURRENT_TIMESTAMP
            WHERE id = ? AND parent_path = ?
        """, (child_path, child_id, parent_path))
        
        # 递归处理子页面的子页面
        rebuild_subtree_paths(child_id, child_path, conn)



# 路径名称翻译映射表（常见词汇）
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
    # 组件相关词汇 - 根据用户需求添加
    "components": "composants",
    "header": "header",  # 用户示例中保持相同
    "footer": "footer",  # 用户示例中保持相同
}

def translate_path_component(component: str, source_lang: str = "en", target_lang: str = "fr") -> str:
    """
    翻译路径组件
    例如: "models" -> "modeles"
    """
    if source_lang == "en" and target_lang == "fr":
        # 首先检查映射表
        if component.lower() in PATH_TRANSLATION_MAP:
            return PATH_TRANSLATION_MAP[component.lower()]
        
        # TODO: 后续可以集成Ollama API进行动态翻译
        # 暂时返回原始组件（保持一致性）
        return component
    
    # 其他语言方向暂时返回原始组件
    return component

def generate_french_path(english_path: str) -> str:
    """
    根据英文路径生成法文路径（翻译转换方案）
    例如: /canadasite/en/models → /canadasite/fr/modeles
    
    规则:
    1. 保持站点前缀不变
    2. 替换语言代码: en → fr
    3. 翻译路径名称组件
    """
    if not english_path:
        return ""
    
    # 规范化路径
    normalized_path = normalize_path(english_path)
    
    # 分割路径组件
    components = normalized_path.strip('/').split('/')
    
    if len(components) < 3:
        # 路径太短，不符合 /canadasite/en/xxx 格式
        return normalized_path
    
    # 确保是 /canadasite/en/xxx 格式
    if components[0] != "canadasite" or components[1] != "en":
        # 不是标准格式，返回原始路径
        return normalized_path
    
    # 构建法文路径
    french_components = []
    french_components.append(components[0])  # canadasite
    french_components.append("fr")  # 替换 en → fr
    
    # 翻译剩余的路径组件
    for i in range(2, len(components)):
        component = components[i]
        translated = translate_path_component(component, "en", "fr")
        french_components.append(translated)
    
    # 重新组装路径
    french_path = '/' + '/'.join(french_components)
    return normalize_path(french_path)

@router.post("/", response_model=PageResponse)
async def create_page(page: PageCreate):
    """创建新页面"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 确定页面ID、父ID和语言
        if page.path:
            # 从路径提取信息
            normalized_path = normalize_path(page.path)
            clean_path = normalized_path.lstrip('/')
            path_parts = clean_path.split('/') if clean_path else []
            
            if len(path_parts) == 0:
                raise HTTPException(status_code=400, detail="路径不能为空")
            
            # 页面ID是路径的最后一部分
            page_id = path_parts[-1]
            
            # 父页面ID是倒数第二部分（如果有的话）
            if len(path_parts) > 1:
                parent_path = path_parts[-2]
            else:
                parent_path = None
            
            # 从路径中提取语言代码（覆盖提供的语言）
            language_from_path = extract_language_from_path(page.path)
        else:
            # 生成基于标题的页面ID
            page_id = generate_page_id(page.title)
            parent_path = page.parent_path
            language_from_path = page.language if page.language else 'en'
        
        # 检查 (id, parent_path) 组合是否已存在（唯一性约束）
        # 注意：parent_path 可能为 None（根页面）
        if parent_path is None:
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
        else:
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path = ?", (page_id, parent_path))
        
        if cursor.fetchone():
            # 组合已存在，报错
            if page.path:
                raise HTTPException(
                    status_code=400, 
                    detail=f"页面路径 '{page.path}' 已存在。在同一个父页面下不能有相同ID的页面。"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"页面ID '{page_id}' 在父页面 '{parent_path}' 下已存在。请使用不同的ID或父页面。"
                )
        
        # 确定file_path：如果提供则使用，否则从祖先获取
        file_path = None
        if page.file_path:
            file_path = page.file_path
        elif parent_path:
            # 从祖先页面获取file_path
            file_path = get_ancestor_file_path(parent_path, conn)
        
        # 构建metadata：合并现有metadata和file_path
        metadata_dict = {}
        if page.metadata:
            if isinstance(page.metadata, dict):
                metadata_dict = page.metadata.copy()
            elif isinstance(page.metadata, str):
                try:
                    metadata_dict = json.loads(page.metadata)
                except json.JSONDecodeError:
                    metadata_dict = {}
        
        # 如果找到file_path，添加到metadata中
        if file_path:
            metadata_dict["file_path"] = file_path
        
        # 计算页面路径
        page_path = ""
        if parent_path:
            # 获取父页面路径
            cursor.execute("SELECT path FROM webbot_page WHERE id = ?", (parent_path,))
            parent_row = cursor.fetchone()
            if parent_row and parent_row['path']:
                page_path = f"{parent_row['path'].rstrip('/')}/{page_id}"
            else:
                # 父页面没有路径，按根页面处理
                page_path = f"/{language_from_path}/{page_id}"
        else:
            # 根页面
            if page_id in ['en', 'fr']:
                page_path = f"/{page_id}"
            else:
                page_path = f"/{language_from_path}/{page_id}"
        
        other_language_path = page.other_language_path if page.other_language_path else None
        
        # 插入数据库
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
        
        # 处理标签（如果提供）
        if hasattr(page, 'tags') and page.tags:
            for tag_name in page.tags:
                if tag_name and tag_name.strip():
                    tag_name = tag_name.strip()
                    # 生成slug
                    slug = re.sub(r'[^\w\s-]', '', tag_name.lower())
                    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
                    
                    # 检查标签是否已存在
                    cursor.execute("SELECT id FROM webbot_tag WHERE name = ? OR slug = ?", 
                                 (tag_name, slug))
                    existing_tag = cursor.fetchone()
                    
                    if existing_tag:
                        tag_id = existing_tag[0]
                    else:
                        # 创建新标签
                        created_at = datetime.now().isoformat()
                        cursor.execute(
                            "INSERT INTO webbot_tag (name, slug, created_at) VALUES (?, ?, ?)",
                            (tag_name, slug, created_at)
                        )
                        tag_id = cursor.lastrowid
                    
                    # 创建页面-标签关联
                    try:
                        cursor.execute(
                            "INSERT INTO webbot_page_tag (page_id, tag_id) VALUES (?, ?)",
                            (page_id, tag_id)
                        )
                    except sqlite3.IntegrityError:
                        # 关联已存在，忽略
                        pass
            
            conn.commit()
        
        # 获取创建的页面
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (page_id,))
        created_page = cursor.fetchone()
        
        if not created_page:
            raise HTTPException(status_code=500, detail="页面创建失败")
        
        # 转换为响应模型
        result = dict(created_page)
        # 解析metadata字段（数据库存储为JSON字符串）
        if result.get("metadata") and isinstance(result["metadata"], str):
            try:
                result["metadata"] = json.loads(result["metadata"])
            except json.JSONDecodeError:
                result["metadata"] = {}
        elif result.get("metadata") is None:
            result["metadata"] = {}
        # language和status字段已经是字符串，Pydantic会自动转换为枚举
        result["language"] = result["language"]
        result["status"] = result["status"]
        
        # 获取页面标签
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
        raise HTTPException(status_code=500, detail=f"数据库错误: {e}")
    finally:
        conn.close()

@router.get("/path", response_model=List[PageResponse])
async def get_pages_by_path(path: str = Query(..., description="父页面路径，返回该路径下的所有页面（直接子页面）。例如：path=/en 返回所有父路径为/en的页面。path=/ 返回根页面（parent_path IS NULL）。")):
    """通过父路径获取页面列表
    
    专门用于获取指定路径下的所有页面（直接子页面）。
    这是 /api/v1/pages?path=... 的简化版本，专为路径过滤设计。
    
    示例:
    - GET /api/v1/pages/path?path=/en → 返回所有父路径为/en的页面
    - GET /api/v1/pages/path?path=/ → 返回根页面
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        normalized_path = path.rstrip('/')
        if normalized_path == '':
            # 根路径：查找所有parent_path为NULL的页面
            cursor.execute("SELECT * FROM webbot_page WHERE parent_path IS NULL ORDER BY title ASC")
        else:
            # 查找parent_path等于指定路径的页面
            cursor.execute("SELECT * FROM webbot_page WHERE parent_path = ? ORDER BY title ASC", (normalized_path,))
        
        pages = cursor.fetchall()
        result = []
        
        for page in pages:
            page_dict = dict(page)
            # 解析metadata字段（数据库存储为JSON字符串）
            if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
                try:
                    page_dict["metadata"] = json.loads(page_dict["metadata"])
                except json.JSONDecodeError:
                    page_dict["metadata"] = {}
            elif page_dict.get("metadata") is None:
                page_dict["metadata"] = {}
            result.append(PageResponse(**page_dict))
        
        return result
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()

@router.get("/", response_model=List[PageResponse])
async def list_pages(skip: int = 0, limit: int = 100, path: Optional[str] = Query(None, description="父页面路径，返回该路径下的所有页面（直接子页面）。例如：path=/en 返回所有父路径为/en的页面。如果未提供，返回所有页面。")):
    """获取页面列表
    
    支持按父路径过滤，返回指定路径下的所有页面（直接子页面）。
    例如：
    - GET /api/v1/pages?path=/en → 返回所有父路径为/en的页面
    - GET /api/v1/pages?path=/ → 返回根页面（parent_path IS NULL）
    - GET /api/v1/pages → 返回所有页面
    
    参数:
    - skip: 跳过记录数（分页）
    - limit: 返回记录数（分页）
    - path: 父页面路径，如 /en 或 /en/contact。如果提供，将过滤parent_path字段。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM webbot_page"
        params = []
        
        # 如果提供了path参数，添加过滤条件
        if path is not None:
            normalized_path = path.rstrip('/')
            if normalized_path == '':
                # 根路径：查找所有parent_path为NULL的页面
                query += " WHERE parent_path IS NULL"
            else:
                # 查找parent_path等于指定路径的页面
                query += " WHERE parent_path = ?"
                params.append(normalized_path)
        
        # 添加排序和分页
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        
        cursor.execute(query, tuple(params))
        
        pages = cursor.fetchall()
        result = []
        
        for page in pages:
            page_dict = dict(page)
            # 解析metadata字段（数据库存储为JSON字符串）
            if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
                try:
                    page_dict["metadata"] = json.loads(page_dict["metadata"])
                except json.JSONDecodeError:
                    page_dict["metadata"] = {}
            elif page_dict.get("metadata") is None:
                page_dict["metadata"] = {}
            result.append(PageResponse(**page_dict))
        
        return result
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()

@router.get("/getheader")
async def get_header(path: str = ""):
    """
    获取header组件内容
    回退逻辑：先在第三级找（语言特定），如果没有找到再到第二级找（通用）
    
    例如：对于路径 /canadasite/en/about
    1. 先尝试 /canadasite/en/header
    2. 如果没找到，尝试 /canadasite/header
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 规范化路径
        normalized_path = normalize_path(path) if path else ""
        
        # 提取语言
        language = extract_language_from_path(normalized_path)
        
        # 第一步：尝试第三级（语言特定）
        third_level_path = ""
        if language and normalized_path:
            # 构建第三级路径：/canadasite/{language}/header
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 2:
                # 保持站点名称
                site_name = parts[0]
                third_level_path = f"/{site_name}/{language}/header"
        
        # 第二步：尝试第二级（通用）
        second_level_path = ""
        if normalized_path:
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 1 and parts[0]:  # 确保站点名称不为空
                site_name = parts[0]
                second_level_path = f"/{site_name}/header"
        
        # 查询优先级：第三级 -> 第二级
        header_path = None
        header_content = None
        
        # 先查第三级
        if third_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (third_level_path,))
            result = cursor.fetchone()
            if result:
                header_path = third_level_path
                header_content = result["content"]
        
        # 如果第三级没找到，查第二级
        if not header_content and second_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (second_level_path,))
            result = cursor.fetchone()
            if result:
                header_path = second_level_path
                header_content = result["content"]
        
        if not header_content:
            # 都没有找到，返回空内容
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
        raise HTTPException(status_code=500, detail=f"内部错误: {e}")
    finally:
        conn.close()

@router.get("/getfooter")
async def get_footer(path: str = ""):
    """
    获取footer组件内容
    回退逻辑：先在第三级找（语言特定），如果没有找到再到第二级找（通用）
    
    例如：对于路径 /canadasite/en/about
    1. 先尝试 /canadasite/en/footer
    2. 如果没找到，尝试 /canadasite/footer
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 规范化路径
        normalized_path = normalize_path(path) if path else ""
        
        # 提取语言
        language = extract_language_from_path(normalized_path)
        
        # 第一步：尝试第三级（语言特定）
        third_level_path = ""
        if language and normalized_path:
            # 构建第三级路径：/canadasite/{language}/footer
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 2:
                # 保持站点名称
                site_name = parts[0]
                third_level_path = f"/{site_name}/{language}/footer"
        
        # 第二步：尝试第二级（通用）
        second_level_path = ""
        if normalized_path:
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 1 and parts[0]:  # 确保站点名称不为空
                site_name = parts[0]
                second_level_path = f"/{site_name}/footer"
        
        # 查询优先级：第三级 -> 第二级
        footer_path = None
        footer_content = None
        
        # 先查第三级
        if third_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (third_level_path,))
            result = cursor.fetchone()
            if result:
                footer_path = third_level_path
                footer_content = result["content"]
        
        # 如果第三级没找到，查第二级
        if not footer_content and second_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (second_level_path,))
            result = cursor.fetchone()
            if result:
                footer_path = second_level_path
                footer_content = result["content"]
        
        if not footer_content:
            # 都没有找到，返回空内容
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
        raise HTTPException(status_code=500, detail=f"内部错误: {e}")
    finally:
        conn.close()


@router.get("/getmegamenu")
async def get_megamenu(path: str = ""):
    """
    获取megamenu组件内容
    回退逻辑：先在第三级找（语言特定），如果没有找到再到第二级找（通用）
    
    例如：对于路径 /canadasite/en/about
    1. 先尝试 /canadasite/en/megamenu
    2. 如果没找到，尝试 /canadasite/megamenu
    
    规则与header和footer相同
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 规范化路径
        normalized_path = normalize_path(path) if path else ""
        
        # 提取语言
        language = extract_language_from_path(normalized_path)
        
        # 第一步：尝试第三级（语言特定）
        third_level_path = ""
        if language and normalized_path:
            # 构建第三级路径：/canadasite/{language}/megamenu
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 2:
                # 保持站点名称
                site_name = parts[0]
                third_level_path = f"/{site_name}/{language}/megamenu"
        
        # 第二步：尝试第二级（通用）
        second_level_path = ""
        if normalized_path:
            parts = normalized_path.strip('/').split('/')
            if len(parts) >= 1 and parts[0]:  # 确保站点名称不为空
                site_name = parts[0]
                second_level_path = f"/{site_name}/megamenu"
        
        # 查询优先级：第三级 -> 第二级
        megamenu_path = None
        megamenu_content = None
        
        # 先查第三级
        if third_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (third_level_path,))
            result = cursor.fetchone()
            if result:
                megamenu_path = third_level_path
                megamenu_content = result["content"]
        
        # 如果第三级没找到，查第二级
        if not megamenu_content and second_level_path:
            cursor.execute("SELECT content FROM webbot_page WHERE id = ? AND status = 'published'", (second_level_path,))
            result = cursor.fetchone()
            if result:
                megamenu_path = second_level_path
                megamenu_content = result["content"]
        
        if not megamenu_content:
            # 都没有找到，返回空内容
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
        raise HTTPException(status_code=500, detail=f"内部错误: {e}")
    finally:
        conn.close()

@router.get("/by-path", response_model=PageResponse)
async def get_page_by_path(path: str = Query(..., description="完整页面路径，如 /en/contact", alias="path")):
    """通过完整路径获取页面（如 /en/contact）
    
    直接使用path字段查询，无需解析id和parent_path。
    支持多语言相同页面名，例如：
    - /en/contact → 英语contact页面
    - /fr/contact → 法语contact页面
    
    路径格式: /{language}/{page} 或 /{site}/{language}/{page} 或任意层次
    """
    import sys, json
    from fastapi import Query
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 规范化路径
        normalized_path = normalize_path(path)
        print(f"DEBUG get_page_by_path: input='{path}', normalized='{normalized_path}'", file=sys.stderr)
        sys.stderr.flush()
        
        # 硬编码特定路径: /boarding/content/dam
        if normalized_path == '/boarding/content/dam':
            print(f"DEBUG: Returning hardcoded page for /boarding/content/dam", file=sys.stderr)
            sys.stderr.flush()
            # 创建硬编码的页面响应
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
        
        # 如果路径是根路径，返回合成页面
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
        
        # 直接使用path字段查询（简化版重构）
        sql = "SELECT * FROM webbot_page WHERE path = ?"
        params = (normalized_path,)
        print(f"DEBUG: SQL='{sql}', params={params}", file=sys.stderr)
        sys.stderr.flush()
        
        cursor.execute(sql, params)
        page = cursor.fetchone()
        print(f"DEBUG: found page={page}", file=sys.stderr)
        sys.stderr.flush()
        
        if not page:
            # 未找到页面
            print(f"DEBUG: Page not found, raising 404", file=sys.stderr)
            sys.stderr.flush()
            raise HTTPException(status_code=404, detail=f"页面路径未找到: {path}")
        
        # 转换为字典并返回
        page_dict = dict(page)
        # 解析metadata字段
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}
        
        print(f"DEBUG: Returning page with id={page_dict.get('id')}, path={page_dict.get('path')}", file=sys.stderr)
        sys.stderr.flush()
        return PageResponse(**page_dict)
        
    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()

@router.get("/by-path/{path:path}/children", response_model=List[PageResponse])
async def get_page_children_by_path(path: str = ""):
    """通过路径获取页面的直接子页面列表
    
    更直观的接口：通过完整路径获取子页面，无需处理parent_path参数。
    例如: /api/v1/pages/by-path/en/children 返回所有父路径为/en的子页面
    
    参数:
    - path: 父页面的完整路径，如 /en 或 /en/contact
    
    返回:
    - 所有父路径为指定路径的直接子页面
    """
    import sys
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 规范化路径
        normalized_path = normalize_path(path)
        print(f"DEBUG get_page_children_by_path: path='{path}', normalized='{normalized_path}'", file=sys.stderr)
        
        # 如果路径是根路径（空或单个斜杠），特殊处理
        if normalized_path == '/' or normalized_path == '':
            print("DEBUG: Root path requested, returning pages with parent_path IS NULL", file=sys.stderr)
            # 根路径：查找所有parent_path为NULL的页面
            cursor.execute("""
                SELECT * FROM webbot_page 
                WHERE parent_path IS NULL
                ORDER BY title ASC
            """)
        else:
            # 通过路径找到父页面
            clean_path = normalized_path.lstrip('/')
            path_parts = clean_path.split('/') if clean_path else []
            
            if len(path_parts) == 0:
                raise HTTPException(status_code=400, detail="路径不能为空")
            
            # 最后一部分是页面ID
            page_id = path_parts[-1]
            # 父ID（如果有）
            parent_path = path_parts[-2] if len(path_parts) >= 2 else None
            
            print(f"DEBUG: Looking for parent page: id={page_id}, parent_path={parent_path}", file=sys.stderr)
            
            # 查询父页面以确认存在
            if parent_path is None:
                cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
            else:
                cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path = ?", (page_id, parent_path))
            
            parent_page = cursor.fetchone()
            if not parent_page:
                raise HTTPException(status_code=404, detail=f"父页面路径未找到: {normalized_path}")
            
            # 查询所有parent_path等于该页面ID的子页面
            cursor.execute("""
                SELECT * FROM webbot_page 
                WHERE parent_path = ?
                ORDER BY title ASC
            """, (page_id,))
        
        children = cursor.fetchall()
        result = []
        
        for child in children:
            child_dict = dict(child)
            # 解析metadata字段
            if child_dict.get("metadata") and isinstance(child_dict["metadata"], str):
                try:
                    child_dict["metadata"] = json.loads(child_dict["metadata"])
                except json.JSONDecodeError:
                    child_dict["metadata"] = {}
            elif child_dict.get("metadata") is None:
                child_dict["metadata"] = {}
            result.append(PageResponse(**child_dict))
        
        print(f"DEBUG: Returning {len(result)} child pages", file=sys.stderr)
        return result
        
    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()

@router.get("/by-path/{full_path:path}", response_model=PageResponse)
async def get_page_by_path_param(full_path: str):
    """通过完整路径获取页面（路径参数版本）
    
    支持路径参数格式：/api/v1/pages/by-path/boarding/content/dam
    直接使用path字段查询，无需解析id和parent_path。
    """
    import sys, json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 规范化路径
        normalized_path = normalize_path(full_path)
        print(f"DEBUG get_page_by_path_param: input='{full_path}', normalized='{normalized_path}'", file=sys.stderr)
        sys.stderr.flush()
        
        # 硬编码特定路径: /boarding/content/dam
        if normalized_path == '/boarding/content/dam':
            print(f"DEBUG: Returning hardcoded page for /boarding/content/dam", file=sys.stderr)
            sys.stderr.flush()
            # 创建硬编码的页面响应
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
        
        # 如果路径是根路径，返回合成页面
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
        
        # 直接使用path字段查询（简化版重构）
        sql = "SELECT * FROM webbot_page WHERE path = ?"
        params = (normalized_path,)
        print(f"DEBUG: SQL='{sql}', params={params}", file=sys.stderr)
        sys.stderr.flush()
        
        cursor.execute(sql, params)
        page = cursor.fetchone()
        print(f"DEBUG: found page={page}", file=sys.stderr)
        sys.stderr.flush()
        
        if not page:
            # 未找到页面
            print(f"DEBUG: Page not found, raising 404", file=sys.stderr)
            sys.stderr.flush()
            raise HTTPException(status_code=404, detail=f"页面路径未找到: {full_path}")
        
        # 转换为字典并返回
        page_dict = dict(page)
        # 解析metadata字段
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}
        
        print(f"DEBUG: Returning page with id={page_dict.get('id')}, path={page_dict.get('path')}", file=sys.stderr)
        sys.stderr.flush()
        return PageResponse(**page_dict)
        
    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()

@router.get("/{page_id:path}/children", response_model=List[PageResponse])
async def get_page_children(page_id: str, 
                            parent_path: Optional[str] = Query(None, description="父页面路径或ID，如 /en。")):
    """获取页面的直接子页面列表
    
    在导航树中，需要按需加载子页面而不是一次性加载所有页面。
    通过此接口可以获取指定页面的直接子页面，用于懒加载导航树。
    
    参数:
    - page_id: 父页面的ID或路径
    - parent_path: 父页面的路径或ID，如 /en 或页面ID
    
    返回:
    - 所有parent_path等于指定page_id的页面列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        target_parent_path = None
        
        # 优先使用parent_path参数
        if parent_path is not None:
            # 使用parent_path查找父页面
            # 首先尝试将parent_path作为路径查找父页面
            cursor.execute("SELECT id, path FROM webbot_page WHERE path = ?", (parent_path.rstrip('/'),))
            parent_page = cursor.fetchone()
            
            if parent_page:
                # 找到了父页面，使用其ID作为target_parent_path
                target_parent_path = parent_page['id']
            else:
                # 如果parent_path不是完整路径，可能是父页面ID
                cursor.execute("SELECT id, path FROM webbot_page WHERE id = ?", (parent_path,))
                parent_page = cursor.fetchone()
                if parent_page:
                    target_parent_path = parent_page['id']
                else:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"父页面未找到: parent_path='{parent_path}'"
                    )
            
            # 现在根据page_id和target_parent_path查找具体的父页面
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path = ?", (page_id, target_parent_path))
            actual_parent = cursor.fetchone()
            if not actual_parent:
                # 如果找不到，尝试将page_id作为路径查找
                path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
                cursor.execute("SELECT id, parent_path FROM webbot_page WHERE path = ?", (path_to_try.rstrip('/'),))
                actual_parent = cursor.fetchone()
                if actual_parent:
                    target_parent_path = actual_parent['id']
                else:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"父页面未找到: id='{page_id}', parent_path='{parent_path}'"
                    )
        
        else:
            # 未指定父标识符，需要找到具体的父页面
            # 首先尝试将page_id作为路径查找父页面
            path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
            cursor.execute("SELECT id, parent_path FROM webbot_page WHERE path = ?", (path_to_try.rstrip('/'),))
            parent_page = cursor.fetchone()
            
            if parent_page:
                # 找到了页面，使用其ID作为target_parent_path
                target_parent_path = parent_page['id']
            else:
                # 查找parent_path为NULL的页面（根页面）
                cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
                parent_page = cursor.fetchone()
                if parent_page:
                    target_parent_path = page_id
                else:
                    # 查找第一个匹配的页面
                    cursor.execute("SELECT id FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                    parent_page = cursor.fetchone()
                    if not parent_page:
                        raise HTTPException(status_code=404, detail=f"页面未找到: id='{page_id}'")
                    target_parent_path = page_id
        
        # 查询所有parent_path等于目标ID的子页面
        cursor.execute("""
            SELECT * FROM webbot_page 
            WHERE parent_path = ? 
            ORDER BY title ASC
        """, (target_parent_path,))
        
        children = cursor.fetchall()
        result = []
        
        for child in children:
            child_dict = dict(child)
            # 解析metadata字段
            if child_dict.get("metadata") and isinstance(child_dict["metadata"], str):
                try:
                    child_dict["metadata"] = json.loads(child_dict["metadata"])
                except json.JSONDecodeError:
                    child_dict["metadata"] = {}
            elif child_dict.get("metadata") is None:
                child_dict["metadata"] = {}
            result.append(PageResponse(**child_dict))
        
        return result
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()


@router.get("/{page_id:path}/properties", response_model=PagePropertiesResponse)
async def get_page_properties(page_id: str, 
                   parent_path: Optional[str] = Query(None, description="父页面路径或ID，如 /en 或页面ID。")):
    """获取页面属性（不包含content字段）
    
    增强版智能页面查找逻辑：
    1. 首先尝试将page_id作为路径查询（path字段）
    2. 如果找不到，尝试使用parent_path参数查找（如果提供）
    
    支持以下格式：
    - 路径格式: GET /api/v1/pages/en/contact/properties → 直接查询path="/en/contact"
    - GET /api/v1/pages/contact/properties?parent_path=/en → 查询id="contact" AND parent_path="/en"
    - 完整路径: GET /api/v1/pages/canadasite/en/contact-us-page/properties → path="/canadasite/en/contact-us-page"
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        page = None
        
        # 步骤1: 尝试将page_id作为路径查询（最常见情况）
        # 确保路径以/开头（如果page_id不以/开头，添加/）
        path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
        normalized_path = path_to_try.rstrip('/')
        
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (normalized_path,))
        page = cursor.fetchone()
        
        # 步骤2: 如果没找到，且page_id不以/开头，尝试使用parent_path参数
        if not page and not page_id.startswith('/'):
            if parent_path is not None:
                # 使用parent_path参数查找
                # parent_path可能是完整路径如"/en"，也可能是父页面ID
                # 首先尝试直接查询：id = ? AND parent_path = ?
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?", 
                             (page_id, parent_path))
                page = cursor.fetchone()
                
                if not page:
                    # 如果parent_path是父页面ID（如"en"），而不是完整路径，尝试转换
                    # 查询父页面的路径
                    cursor.execute("SELECT path FROM webbot_page WHERE id = ? LIMIT 1", (parent_path,))
                    parent_row = cursor.fetchone()
                    if parent_row:
                        actual_parent_path = parent_row['path']
                        cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?", 
                                     (page_id, actual_parent_path))
                        page = cursor.fetchone()
            
            # 步骤3: 如果还没有找到，尝试查找parent_path为NULL的页面（根页面）
            if not page and parent_path is None:
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
                page = cursor.fetchone()
                
                # 步骤5: 作为最后手段，查找第一个匹配的页面
                if not page:
                    cursor.execute("SELECT * FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                    page = cursor.fetchone()
        
        if not page:
            # 提供有用的错误信息
            error_details = []
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            
            error_msg = f"页面未找到: id='{page_id}'"
            if error_details:
                error_msg += f", {', '.join(error_details)}"
            error_msg += f"。尝试的路径: '{normalized_path}'"
            
            raise HTTPException(status_code=404, detail=error_msg)
        
        page_dict = dict(page)
        # 解析metadata字段（数据库存储为JSON字符串）
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}
        # 移除content字段，因为它可能很大
        page_dict.pop("content", None)
        return PagePropertiesResponse(**page_dict)
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()


@router.get("/{page_id:path}", response_model=PageResponse)
async def get_page(page_id: str, 
                   parent_path: Optional[str] = Query(None, description="父页面路径或ID，如 /en 或页面ID。")):
    """获取单个页面
    
    增强版智能页面查找逻辑：
    1. 首先尝试将page_id作为路径查询（path字段）
    2. 如果找不到，尝试使用parent_path参数查找（如果提供）
    
    支持以下格式：
    - 路径格式: GET /api/v1/pages/en/contact → 直接查询path="/en/contact"
    - GET /api/v1/pages/contact?parent_path=/en → 查询id="contact" AND parent_path="/en"
    - 完整路径: GET /api/v1/pages/canadasite/en/contact-us-page → path="/canadasite/en/contact-us-page"
    """
    # 根路径 / 特殊处理：返回合成根页面
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
        
        # 步骤1: 尝试将page_id作为路径查询（最常见情况）
        # 确保路径以/开头（如果page_id不以/开头，添加/）
        path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
        normalized_path = path_to_try.rstrip('/')
        
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (normalized_path,))
        page = cursor.fetchone()
        
        # 步骤2: 如果没找到，且page_id不以/开头，尝试使用parent_path参数
        if not page and not page_id.startswith('/'):
            if parent_path is not None:
                # 使用parent_path参数查找
                # parent_path可能是完整路径如"/en"，也可能是父页面ID
                # 首先尝试直接查询：id = ? AND parent_path = ?
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?", 
                             (page_id, parent_path))
                page = cursor.fetchone()
                
                if not page:
                    # 如果parent_path是父页面ID（如"en"），而不是完整路径，尝试转换
                    # 查询父页面的路径
                    cursor.execute("SELECT path FROM webbot_page WHERE id = ? LIMIT 1", (parent_path,))
                    parent_row = cursor.fetchone()
                    if parent_row:
                        actual_parent_path = parent_row['path']
                        cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?", 
                                     (page_id, actual_parent_path))
                        page = cursor.fetchone()
            
            # 步骤3: 如果还没有找到，尝试查找parent_path为NULL的页面（根页面）
            if not page and parent_path is None:
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
                page = cursor.fetchone()
                
                # 步骤5: 作为最后手段，查找第一个匹配的页面
                if not page:
                    cursor.execute("SELECT * FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                    page = cursor.fetchone()
        
        if not page:
            # 提供有用的错误信息
            error_details = []
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            
            error_msg = f"页面未找到: id='{page_id}'"
            if error_details:
                error_msg += f", {', '.join(error_details)}"
            error_msg += f"。尝试的路径: '{normalized_path}'"
            
            raise HTTPException(status_code=404, detail=error_msg)
        
        page_dict = dict(page)
        # 解析metadata字段（数据库存储为JSON字符串）
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}
        return PageResponse(**page_dict)
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()



@router.put("/{page_id:path}", response_model=PageResponse)
async def update_page(page_id: str, page_update: PageUpdate, 
                     parent_path: Optional[str] = Query(None, description="父页面路径或ID，如 /en 或页面ID。")):
    """更新页面
    
    增强版智能页面查找逻辑（与GET端点保持一致）：
    1. 首先尝试将page_id作为路径查询（path字段）
    2. 如果找不到，尝试使用parent_path参数查找（如果提供）
    
    支持以下格式：
    - 路径格式: PUT /api/v1/pages/en/contact → 直接更新path="/en/contact"的页面
    - PUT /api/v1/pages/contact?parent_path=/en → 更新id="contact" AND parent_path="/en"的页面
    
    当更新parent_path字段时，会自动重新计算页面路径。
    """
    import sys
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 智能页面查找逻辑（与GET和DELETE端点保持一致）
        existing_page = None
        target_parent_path = None
        target_parent_path = None
        actual_page_id = page_id  # 实际用于WHERE条件的页面ID
        
        # 步骤1: 尝试将page_id作为路径查询（最常见情况）
        # 确保路径以/开头（如果page_id不以/开头，添加/）
        path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
        normalized_path = path_to_try.rstrip('/')
        
        print(f"DEBUG update_page: page_id='{page_id}', path_to_try='{path_to_try}', normalized_path='{normalized_path}'", file=sys.stderr)
        sys.stderr.flush()
        
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (normalized_path,))
        existing_page = cursor.fetchone()
        print(f"DEBUG update_page: existing_page found via path={existing_page is not None}", file=sys.stderr)
        sys.stderr.flush()
        
        # 步骤2: 如果没找到，且page_id不以/开头，尝试使用parent_path参数
        if not existing_page and not page_id.startswith('/'):
            if parent_path is not None:
                # 使用parent_path参数查找
                target_parent_path = parent_path
                # parent_path可能是完整路径如"/en"，也可能是父页面ID
                # 首先尝试直接查询：id = ? AND parent_path = ?
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?", 
                             (page_id, parent_path))
                existing_page = cursor.fetchone()
                
                if not existing_page:
                    # 如果parent_path是父页面ID（如"en"），而不是完整路径，尝试转换
                    # 查询父页面的路径
                    cursor.execute("SELECT path FROM webbot_page WHERE id = ? LIMIT 1", (parent_path,))
                    parent_row = cursor.fetchone()
                    if parent_row:
                        actual_parent_path = parent_row['path']
                        target_parent_path = actual_parent_path
                        cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path = ?", 
                                     (page_id, actual_parent_path))
                        existing_page = cursor.fetchone()
            
            # 步骤3: 如果还没有找到，尝试查找parent_path为NULL的页面（根页面）
            if not existing_page and parent_path is None:
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
                existing_page = cursor.fetchone()
                
                # 步骤5: 作为最后手段，查找第一个匹配的页面
                if not existing_page:
                    cursor.execute("SELECT * FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                    existing_page = cursor.fetchone()
        
        if not existing_page:
            # 提供有用的错误信息
            error_details = []
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            if parent_path:
                error_details.append(f"parent_path='{parent_path}'")
            
            error_msg = f"页面未找到: id='{page_id}'"
            if error_details:
                error_msg += f", {', '.join(error_details)}"
            error_msg += f"。尝试的路径: '{normalized_path}'"
            
            raise HTTPException(status_code=404, detail=error_msg)
        
        # 确定目标父标识符用于后续更新
        # 如果通过参数找到了页面，使用相应的标识符
        # 否则使用页面本身的parent_path或parent_path
        if not target_parent_path and not target_parent_path:
            # 从现有页面获取实际ID和父标识符
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
            # 通过参数找到页面，使用传入的page_id
            actual_page_id = page_id
        
        print(f"DEBUG update_page: actual_page_id='{actual_page_id}', target_parent_path='{target_parent_path}', target_parent_path='{target_parent_path}'", file=sys.stderr)
        sys.stderr.flush()
        
        # 构建更新字段
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
            update_values.append(page_update.language.value)
        
        if page_update.parent_path is not None:
            update_fields.append("parent_path = ?")
            update_values.append(page_update.parent_path)
        
        if page_update.parent_path is not None:
            update_fields.append("parent_path = ?")
            update_values.append(page_update.parent_path)
        
        if page_update.other_language_path is not None:
            update_fields.append("other_language_path = ?")
            update_values.append(page_update.other_language_path)
        
        if page_update.status is not None:
            update_fields.append("status = ?")
            update_values.append(page_update.status.value)
        
        if page_update.metadata is not None:
            update_fields.append("metadata = ?")
            update_values.append(json.dumps(page_update.metadata))
        
        if page_update.hide_in_navigation is not None:
            update_fields.append("hide_in_navigation = ?")
            update_values.append(1 if page_update.hide_in_navigation else 0)
        
        # 如果没有更新字段，直接返回原页面
        if not update_fields:
            return PageResponse(**dict(existing_page))
        
        # 添加最后修改时间
        update_fields.append("last_modified = ?")
        update_values.append(datetime.now().isoformat())
        
        print(f"DEBUG update_page: update_fields={update_fields}", file=sys.stderr)
        sys.stderr.flush()
        print(f"DEBUG update_page: update_values={update_values}", file=sys.stderr)
        sys.stderr.flush()
        
        # 执行更新 - 使用智能标识符
        # 构建WHERE条件：优先使用parent_path，其次parent_path
        
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
            # 使用parent_path作为标识符（向后兼容）
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
            # 没有父标识符，查找parent_path为NULL的页面（根页面）
            update_values.append(actual_page_id)  # WHERE条件: id = ?
            update_query = f"UPDATE webbot_page SET {', '.join(update_fields)} WHERE id = ? AND parent_path IS NULL"
            print(f"DEBUG update_page: Executing query: {update_query}", file=sys.stderr)
            print(f"DEBUG update_page: With values: {update_values}", file=sys.stderr)
            sys.stderr.flush()
            cursor.execute(update_query, update_values)
        
        # 检查是否需要更新路径
        need_path_update = False
        if page_update.parent_path is not None or page_update.parent_path is not None or page_update.language is not None:
            need_path_update = True
        
        # 如果需要更新路径，重新计算path和other_language_path
        # TODO: 实现完整的路径重新计算逻辑，支持parent_path
        # 当前版本简化处理，仅记录日志
        if need_path_update:
            print(f"PATH UPDATE NEEDED for page {page_id}: parent_path={page_update.parent_path}, parent_path={page_update.parent_path}, language={page_update.language}")
            # 简化处理：暂时不重新计算路径，避免复杂逻辑错误
            # 完整实现将在后续版本中添加
            pass
        
        conn.commit()
        
        print(f"DEBUG update_page: Fetching updated page with actual_page_id='{actual_page_id}', target_parent_path='{target_parent_path}', target_parent_path='{target_parent_path}'", file=sys.stderr)
        sys.stderr.flush()
        
        # 获取更新后的页面 - 使用智能标识符
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
            # 如果找不到更新后的页面，返回原始页面（至少更新应该成功了）
            print(f"WARNING: Could not fetch updated page after update. Returning original page.", file=sys.stderr)
            sys.stderr.flush()
            updated_page = existing_page
        
        # 解析metadata字段（数据库存储为JSON字符串）
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
        raise HTTPException(status_code=500, detail=f"更新失败: {e}")
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
    finally:
        conn.close()

@router.delete("/{page_id:path}")
async def delete_page(page_id: str, 
                      parent_path: Optional[str] = Query(None, description="父页面路径或ID，如 /en 或页面ID。")):
    """删除页面
    
    示例：
    - DELETE /api/v1/pages/contact?parent_path=/en → 删除英语contact页面（父路径为/en）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 优先使用parent_path参数
        target_parent_path = None
        target_parent_path = None
        
        if parent_path is not None:
            # 使用parent_path参数
            target_parent_path = parent_path
            # 查找页面：id = ? AND parent_path = ?
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path = ?", (page_id, parent_path))
        else:
            # 未指定父标识符，先尝试查找parent_path为NULL的页面（根页面）
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
            if not cursor.fetchone():
                # 如果没有parent_path为NULL的页面，查找第一个匹配的页面
                cursor.execute("SELECT id FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="页面未找到")
            # 重置游标
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
        
        # 检查是否找到了页面
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="页面未找到")
        
        # 删除页面 - 根据使用的参数选择条件
        if target_parent_path is not None:
            cursor.execute("DELETE FROM webbot_page WHERE id = ? AND parent_path = ?", (page_id, target_parent_path))
        else:
            cursor.execute("DELETE FROM webbot_page WHERE id = ? AND parent_path IS NULL", (page_id,))
        
        conn.commit()
        
        # 返回响应
        response_data = {"message": "页面删除成功", "page_id": page_id}
        if target_parent_path:
            response_data["parent_path"] = target_parent_path
        if target_parent_path:
            response_data["parent_path"] = target_parent_path
        
        return response_data
        
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")
    finally:
        conn.close()


# ==================== 模板相关API ====================

@router.get("/templates", response_model=List[PageResponse])
async def list_templates():
    """获取所有模板页面"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询所有以 /templates/ 开头的页面
        cursor.execute("""
            SELECT * FROM webbot_page 
            WHERE id LIKE '/templates/%'
            ORDER BY created_at DESC
        """)
        
        templates = cursor.fetchall()
        result = []
        
        for template in templates:
            template_dict = dict(template)
            # 解析metadata字段
            if template_dict.get("metadata") and isinstance(template_dict["metadata"], str):
                try:
                    template_dict["metadata"] = json.loads(template_dict["metadata"])
                except json.JSONDecodeError:
                    template_dict["metadata"] = {}
            elif template_dict.get("metadata") is None:
                template_dict["metadata"] = {}
            result.append(PageResponse(**template_dict))
        
        return result
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()


# ==================== 双语页面创建API ====================

# 双语创建请求模型（临时定义，后续可移到models.py）
from pydantic import BaseModel, Field

class BilingualTemplateCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=100, description="文件名（不含路径）")
    description: str = Field(..., min_length=1, max_length=1000, description="页面描述")
    template_id: str = Field(..., description="模板页面ID，如 /templates/standard-page")
    input_language: str = Field("en", description="输入语言代码 (en, fr, zh)")
    auto_translate: bool = Field(True, description="是否自动翻译")


def _preserve_case(original: str, translated: str) -> str:
    """保持原始文本的大小写格式"""
    if not original or not translated:
        return translated
    
    # 如果原始文本全部大写
    if original.isupper():
        return translated.upper()
    # 如果原始文本是标题格式（每个单词首字母大写）
    elif original.istitle():
        return translated.title()
    # 如果原始文本首字母大写
    elif original[0].isupper() and not original[1:].isupper():
        return translated[0].upper() + translated[1:] if translated else translated
    # 其他情况保持小写
    else:
        return translated.lower()


def translate_with_ollama(text: str, source_lang: str = "en", target_lang: str = "fr") -> str:
    """使用Ollama进行多语言翻译（支持en↔fr, en↔zh, fr↔zh）"""
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
        
        # 尝试多个模型，从最小的开始（现在有了tinyllama）
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
                        print(f"翻译返回空或相同文本，尝试下一个模型")
                else:
                    error_msg = response.json().get("error", "Unknown error") if response.text else "No error message"
                    print(f"模型 {model} 失败: {response.status_code} - {error_msg}")
                    
            except Exception as model_error:
                print(f"模型 {model} 异常: {model_error}")
                continue
        
        # 所有模型都失败，尝试简单回退翻译
        print(f"所有Ollama模型失败，使用简单回退翻译")
        
        # 多语言回退词典（简化版）
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
                "information": "信息",
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
                "information": "信息",
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
                "信息": "information",
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
        
        # 然后尝试部分匹配（包含关系）
        for source_word, target_word in lang_dict.items():
            if source_word in text_lower:
                # 如果匹配的是整个单词（有空格边界或字符串边界）
                import re
                pattern = r'(^|\s)' + re.escape(source_word) + r'(\s|$)'
                if re.search(pattern, text_lower):
                    # 替换匹配的部分
                    result = re.sub(r'(^|\s)' + re.escape(source_word) + r'(\s|$)', 
                                   r'\1' + target_word + r'\2', 
                                   text_lower, 
                                   flags=re.IGNORECASE)
                    # 恢复原始大小写格式
                    return _preserve_case(text, result)
        
        # 没有匹配的简单翻译，返回原文本
        return text
            
    except Exception as e:
        print(f"翻译异常: {e}")
        return text

@router.post("/bilingual-template", response_model=Dict[str, Any])
async def create_bilingual_template(page_data: BilingualTemplateCreate):
    """
    根据模板创建双语页面
    
    工作流程:
    1. 获取模板页面内容
    2. 翻译文件名和描述
    3. 生成双语路径
    4. 创建英文页面
    5. 创建法文页面
    6. 设置页面关联
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # ========== 步骤1: 获取模板 ==========
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (page_data.template_id,))
        template = cursor.fetchone()
        
        if not template:
            raise HTTPException(status_code=404, detail=f"模板未找到: {page_data.template_id}")
        
        template_dict = dict(template)
        
        # ========== 步骤2: 翻译处理 ==========
        # 准备英文数据
        english_title = page_data.filename.replace('-', ' ').title()
        english_description = page_data.description
        
        # 翻译为法文
        french_title = english_title
        french_description = english_description
        
        if page_data.auto_translate:
            # 翻译标题
            french_title = translate_with_ollama(english_title, "en", "fr")
            # 翻译描述
            french_description = translate_with_ollama(english_description, "en", "fr")
        
        # ========== 步骤3: 生成路径 ==========
        # 生成基础文件名（URL友好格式）
        import re
        english_filename = re.sub(r'[^a-zA-Z0-9]', '-', page_data.filename.lower()).strip('-')
        french_filename = re.sub(r'[^a-zA-Z0-9]', '-', french_title.lower()).strip('-')
        
        # 生成路径
        english_path = f"/canadasite/en/{english_filename}"
        french_path = generate_french_path(english_path)
        
        # 如果翻译后的路径与英文路径相同，使用备用方案
        if french_path == english_path:
            french_path = f"/canadasite/fr/{french_filename}"
        
        # ========== 步骤4: 创建英文页面 ==========
        now = datetime.now().isoformat()
        
        # 准备页面数据
        english_page_data = {
            "id": english_path,
            "title": english_title,
            "content": template_dict.get("content", ""),
            "language": "en",
            "parent_path": extract_parent_path_from_path(english_path),
            "other_language_path": french_path,  # 关联法文页面
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
        
        # ========== 步骤5: 创建法文页面 ==========
        french_page_data = {
            "id": french_path,
            "title": french_title,
            "content": template_dict.get("content", ""),
            "language": "fr",
            "parent_path": extract_parent_path_from_path(french_path),
            "other_language_path": english_path,  # 关联英文页面
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
        
        # ========== 步骤6: 获取创建的页面 ==========
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (english_path,))
        english_page = dict(cursor.fetchone())
        
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (french_path,))
        french_page = dict(cursor.fetchone())
        
        # 解析metadata字段
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
            raise HTTPException(status_code=400, detail="页面路径已存在，请使用不同的文件名")
        raise HTTPException(status_code=500, detail=f"数据库约束错误: {e}")
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"数据库错误: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败: {e}")
    finally:
        conn.close()

@router.get("/test-debug")
async def test_debug():
    """测试端点，确认路由工作"""
    import sys
    print("DEBUG: test_debug endpoint called", file=sys.stderr)
    sys.stderr.flush()
    return {"message": "测试端点工作正常", "status": "ok"}

@router.get("/test-path-param")
async def test_path_param(path: str = Query(..., description="测试路径参数")):
    """测试Query参数接收"""
    import sys
    print(f"DEBUG: test_path_param called with path={path}", file=sys.stderr)
    sys.stderr.flush()
    return {"received_path": path, "status": "success"}


