"""
页面管理路由
"""

from fastapi import APIRouter, HTTPException, Depends, Query
import sqlite3
import json
import uuid
import requests
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.models import PageCreate, PageUpdate, PageResponse, PageStatus

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
    
    # 验证是否为支持的语言
    if lang in ['en', 'fr']:
        return lang
    
    # 默认返回英语
    return "en"

def get_ancestor_file_path(parent_id: Optional[str], conn) -> Optional[str]:
    """
    递归获取祖先页面的file_path。
    从父页面开始，向上查询直到找到file_path或到达根页面。
    """
    if not parent_id:
        return None
    
    current_id = parent_id
    visited = set()  # 防止循环
    
    while current_id and current_id not in visited:
        visited.add(current_id)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata, parent_id FROM webbot_page WHERE id = ?", (current_id,))
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
        current_id = row["parent_id"]
    
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

def extract_parent_id_from_path(path: str) -> Optional[str]:
    """
    从路径推断父页面ID
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
                parent_id = path_parts[-2]
            else:
                parent_id = None
            
            # 从路径中提取语言代码（覆盖提供的语言）
            language_from_path = extract_language_from_path(page.path)
        else:
            # 生成基于标题的页面ID
            page_id = generate_page_id(page.title)
            parent_id = page.parent_id
            language_from_path = page.language.value
        
        # 检查 (id, parent_id) 组合是否已存在（唯一性约束）
        # 注意：parent_id 可能为 None（根页面）
        if parent_id is None:
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_id IS NULL", (page_id,))
        else:
            cursor.execute("SELECT id FROM webbot_page WHERE id = ? AND parent_id = ?", (page_id, parent_id))
        
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
                    detail=f"页面ID '{page_id}' 在父页面 '{parent_id}' 下已存在。请使用不同的ID或父页面。"
                )
        
        # 确定file_path：如果提供则使用，否则从祖先获取
        file_path = None
        if page.file_path:
            file_path = page.file_path
        elif parent_id:
            # 从祖先页面获取file_path
            file_path = get_ancestor_file_path(parent_id, conn)
        
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
        
        # 插入数据库
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO webbot_page 
            (id, title, description, keywords, content, language, parent_id, other_lang_page_id, status, metadata, hide_in_navigation, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page_id,
            page.title,
            page.description or "",
            page.keywords or "",
            page.content or "",
            language_from_path,  # 使用从路径提取的语言或原始语言
            parent_id,
            page.other_lang_page_id,
            page.status.value,
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

@router.get("/", response_model=List[PageResponse])
async def list_pages(skip: int = 0, limit: int = 100):
    """获取页面列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM webbot_page 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (limit, skip))
        
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
    
    支持多语言相同页面名，例如：
    - /en/contact → id="contact", parent_id="en"
    - /fr/contact → id="contact", parent_id="fr"
    
    路径格式应为: /{language}/{page} 或 /{language}/{section}/{page}
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
                parent_id="content",
                other_lang_page_id=None,
                status="published",
                metadata={"hardcoded": True, "path": "/boarding/content/dam", "source": "hardcoded-special-route"},
                hide_in_navigation=False,
                tags=["boarding", "content", "dam"],
                created_by="system",
                created_at=now,
                last_modified=now,
                last_published=now
            )
        
        # 如果路径是根路径，特殊处理
        if normalized_path == '/':
            raise HTTPException(status_code=400, detail="根路径需要指定页面")
        
        # 移除开头的斜杠，分割路径部分
        clean_path = normalized_path.lstrip('/')
        path_parts = clean_path.split('/') if clean_path else []
        print(f"DEBUG: clean_path='{clean_path}', path_parts={path_parts}", file=sys.stderr)
        sys.stderr.flush()
        
        if len(path_parts) == 0:
            raise HTTPException(status_code=400, detail="路径不能为空")
        
        # 确定页面ID和父ID
        # 最后一部分是页面ID
        page_id = path_parts[-1]
        # 如果有父级，倒数第二部分是父ID
        parent_id = path_parts[-2] if len(path_parts) >= 2 else None
        print(f"DEBUG: page_id='{page_id}', parent_id='{parent_id}'", file=sys.stderr)
        sys.stderr.flush()
        
        # 查询页面
        if parent_id is None:
            sql = "SELECT * FROM webbot_page WHERE id = ? AND parent_id IS NULL"
            params = (page_id,)
        else:
            sql = "SELECT * FROM webbot_page WHERE id = ? AND parent_id = ?"
            params = (page_id, parent_id)
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
        
        print(f"DEBUG: Returning page with id={page_dict.get('id')}", file=sys.stderr)
        sys.stderr.flush()
        return PageResponse(**page_dict)
        
    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()

@router.get("/by-path/{full_path:path}", response_model=PageResponse)
async def get_page_by_path_param(full_path: str):
    """通过完整路径获取页面（路径参数版本）
    
    支持路径参数格式：/api/v1/pages/by-path/boarding/content/dam
    这是查询参数版本的替代形式
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
                parent_id="content",
                other_lang_page_id=None,
                status="published",
                metadata={"hardcoded": True, "path": "/boarding/content/dam", "source": "hardcoded-special-route"},
                hide_in_navigation=False,
                tags=["boarding", "content", "dam"],
                created_by="system",
                created_at=now,
                last_modified=now,
                last_published=now
            )
        
        # 如果路径是根路径，特殊处理
        if normalized_path == '/':
            raise HTTPException(status_code=400, detail="根路径需要指定页面")
        
        # 移除开头的斜杠，分割路径部分
        clean_path = normalized_path.lstrip('/')
        path_parts = clean_path.split('/') if clean_path else []
        print(f"DEBUG: clean_path='{clean_path}', path_parts={path_parts}", file=sys.stderr)
        sys.stderr.flush()
        
        if len(path_parts) == 0:
            raise HTTPException(status_code=400, detail="路径不能为空")
        
        # 确定页面ID和父ID
        # 最后一部分是页面ID
        page_id = path_parts[-1]
        # 如果有父级，倒数第二部分是父ID
        parent_id = path_parts[-2] if len(path_parts) >= 2 else None
        print(f"DEBUG: page_id='{page_id}', parent_id='{parent_id}'", file=sys.stderr)
        sys.stderr.flush()
        
        # 查询页面
        if parent_id is None:
            sql = "SELECT * FROM webbot_page WHERE id = ? AND parent_id IS NULL"
            params = (page_id,)
        else:
            sql = "SELECT * FROM webbot_page WHERE id = ? AND parent_id = ?"
            params = (page_id, parent_id)
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
        
        print(f"DEBUG: Returning page with id={page_dict.get('id')}", file=sys.stderr)
        sys.stderr.flush()
        return PageResponse(**page_dict)
        
    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
    finally:
        conn.close()

@router.get("/{page_id}", response_model=PageResponse)
async def get_page(page_id: str, parent_id: Optional[str] = Query(None, description="父页面ID，用于区分多语言版本。如果不提供，将查找parent_id为NULL或第一个匹配的页面。")):
    """获取单个页面
    
    由于复合主键(id, parent_id)允许相同ID在不同父页面下存在（多语言支持），
    建议总是提供parent_id参数来明确指定要获取哪个语言版本。
    
    示例：
    - GET /api/v1/pages/contact?parent_id=en → 英语contact页面
    - GET /api/v1/pages/contact?parent_id=fr → 法语contact页面
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 构建查询：根据是否提供parent_id进行不同的查询
        if parent_id is not None:
            # 明确指定parent_id，精确查找
            cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_id = ?", (page_id, parent_id))
        else:
            # 未指定parent_id，先尝试查找parent_id为NULL的页面（根页面）
            cursor.execute("SELECT * FROM webbot_page WHERE id = ? AND parent_id IS NULL", (page_id,))
            page = cursor.fetchone()
            if not page:
                # 如果没有parent_id为NULL的页面，查找第一个匹配的页面（保持向后兼容）
                cursor.execute("SELECT * FROM webbot_page WHERE id = ? LIMIT 1", (page_id,))
        
        page = cursor.fetchone()
        
        if not page:
            if parent_id is not None:
                raise HTTPException(
                    status_code=404, 
                    detail=f"页面未找到: id='{page_id}', parent_id='{parent_id}'。请检查路径或使用/by-path端点。"
                )
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"页面未找到: id='{page_id}'。建议使用parent_id参数指定语言版本，或使用/by-path端点。"
                )
        
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

@router.put("/{page_id}", response_model=PageResponse)
async def update_page(page_id: str, page_update: PageUpdate):
    """更新页面"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查页面是否存在
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (page_id,))
        existing_page = cursor.fetchone()
        
        if not existing_page:
            raise HTTPException(status_code=404, detail="页面未找到")
        
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
        
        if page_update.parent_id is not None:
            update_fields.append("parent_id = ?")
            update_values.append(page_update.parent_id)
        
        if page_update.other_lang_page_id is not None:
            update_fields.append("other_lang_page_id = ?")
            update_values.append(page_update.other_lang_page_id)
        
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
        
        # 执行更新
        update_values.append(page_id)  # WHERE条件
        update_query = f"UPDATE webbot_page SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(update_query, update_values)
        
        conn.commit()
        
        # 获取更新后的页面
        cursor.execute("SELECT * FROM webbot_page WHERE id = ?", (page_id,))
        updated_page = cursor.fetchone()
        
        # 解析metadata字段（数据库存储为JSON字符串）
        page_dict = dict(updated_page)
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}
        
        return PageResponse(**page_dict)
        
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {e}")
    finally:
        conn.close()

@router.delete("/{page_id}")
async def delete_page(page_id: str):
    """删除页面"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查页面是否存在
        cursor.execute("SELECT id FROM webbot_page WHERE id = ?", (page_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="页面未找到")
        
        # 删除页面
        cursor.execute("DELETE FROM webbot_page WHERE id = ?", (page_id,))
        conn.commit()
        
        return {"message": "页面删除成功", "page_id": page_id}
        
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


def translate_with_ollama(text: str, source_lang: str = "en", target_lang: str = "fr") -> str:
    """使用Ollama进行翻译"""
    try:
        # 简单的提示词
        prompt = f"Translate the following {source_lang} text to {target_lang}. Only return the translation, no explanation:\n\n{text}"
        
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "deepseek-r1:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            translation = result.get("response", "").strip()
            # 清理可能的额外文本
            translation = translation.split('\n')[0].strip()
            return translation if translation else text
        else:
            print(f"Ollama翻译失败: {response.status_code}")
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
            "parent_id": extract_parent_id_from_path(english_path),
            "other_lang_page_id": french_path,  # 关联法文页面
            "status": "draft",
            "metadata": json.dumps({"template_source": page_data.template_id}),
            "created_at": now,
            "last_modified": now
        }
        
        cursor.execute("""
            INSERT INTO webbot_page 
            (id, title, content, language, parent_id, other_lang_page_id, status, metadata, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            english_page_data["id"],
            english_page_data["title"],
            english_page_data["content"],
            english_page_data["language"],
            english_page_data["parent_id"],
            english_page_data["other_lang_page_id"],
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
            "parent_id": extract_parent_id_from_path(french_path),
            "other_lang_page_id": english_path,  # 关联英文页面
            "status": "draft",
            "metadata": json.dumps({"template_source": page_data.template_id}),
            "created_at": now,
            "last_modified": now
        }
        
        cursor.execute("""
            INSERT INTO webbot_page 
            (id, title, content, language, parent_id, other_lang_page_id, status, metadata, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            french_page_data["id"],
            french_page_data["title"],
            french_page_data["content"],
            french_page_data["language"],
            french_page_data["parent_id"],
            french_page_data["other_lang_page_id"],
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


