"""
Page management routes
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
import json
import uuid
import os
import requests
import re
import traceback
import logging
from datetime import datetime, timezone
import html.parser
import urllib.parse
from typing import List, Optional, Dict, Any
from fastapi import Request as FastAPIRequest

from app.models import PageCreate, PageUpdate, PageResponse, PageListItem, PageMetadataItem, PreviewRequest, PagePropertiesResponse, PageMetadataResponse, PageStatus
from app.routes.permission_utils import filter_pages_by_permission, user_can_write_page, user_can_see_page
from app.routes.auth_security import get_current_active_user
from app.routes.mustache import render_template as render_mustache_tpl

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pages", tags=["pages"])

# 2026-08-28: webbot 与 filebot 同机，内部 datasource 一律本机直连（不走公网/Cloudflare 隧道）。
# 相对路径 datasource（/api/v1/...）拼 LOCAL_API_BASE；绝对 http(s) URL（外部数据源）保持原样。
LOCAL_API_BASE = os.environ.get("WEBBOT_LOCAL_API_BASE", "http://127.0.0.1:8000")

# Separate router for top-level /api/v1 endpoints (no /pages/ segment)
router_v1 = APIRouter(prefix="/api/v1", tags=["pages_v1"])

WEBBOT_DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)

def get_db_connection():
    """Get WebBot database connection"""
    try:
        conn = sqlite3.connect(WEBBOT_DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")

_MUSTACHE_ENTITY_MAP = {"gt": ">", "lt": "<", "amp": "&", "quot": '"', "#39": "'", "#x27": "'"}
_MUSTACHE_ENTITY_RE = re.compile(r"\{\{&(gt|lt|amp|quot|#39|#x27);")


def _unescape_mustache_entities(content: str) -> str:
    """Restore HTML-escaped entities inside mustache tags.

    Editors (TinyMCE) store '>' as '&gt;' in page content, so a partial written
    as {{>name?path=.}} is persisted as {{&gt;name?path=.}} and chevron treats it
    as an undefined variable (renders empty). This restores only entities that
    appear right after '{{', leaving the rest of the HTML untouched.
    """
    if not content or "{{" not in content:
        return content
    return _MUSTACHE_ENTITY_RE.sub(
        lambda m: "{{" + _MUSTACHE_ENTITY_MAP[m.group(1)], content)


def generate_page_id(title: str) -> str:
    """Generate page ID from title"""
    import re, hashlib
    # 保留 Unicode 字母数字(含中文等), 只移除标点/符号; 空格转连字符, 转小写
    cleaned = re.sub(r'[^\w\s-]', '', title, flags=re.UNICODE)
    page_id = re.sub(r'\s+', '-', cleaned.strip()).lower()
    # If为空(纯标点/符号标题), 用 title 的确定性 hash 而非随机 ID, 保证同名可检测重复
    if not page_id:
        page_id = f"page-{hashlib.sha1(title.encode('utf-8')).hexdigest()[:8]}"
    return page_id

def remove_pagedetails_sections(html: str) -> str:
    """
    Remove any HTML element whose class contains 'pagedetails', handling nested elements
    by tracking tag depth. Removes footer/section/div elements with pagedetails in attributes.
    """
    # Pattern: opening tag with pagedetails in attributes
    import re
    tag_pat = re.compile(r'<(footer|section|div)(\s[^>]*)?\bpagedetails\b[^>]*>', re.IGNORECASE)
    close_pat_cache = {}

    def get_close_pat(tag: str) -> re.Pattern:
        if tag not in close_pat_cache:
            close_pat_cache[tag] = re.compile(r'</' + tag + r'\s*>', re.IGNORECASE)
        return close_pat_cache[tag]

    def get_open_pat(tag: str) -> re.Pattern:
        return re.compile(r'<' + tag + r'[^>]*>', re.IGNORECASE)

    result = []
    i = 0
    while i < len(html):
        match = tag_pat.search(html, i)
        if match and match.start() == i:
            tag_name = match.group(1).lower()
            depth = 1
            j = match.end()
            open_pat = get_open_pat(tag_name)
            close_pat = get_close_pat(tag_name)
            while j < len(html) and depth > 0:
                closer = close_pat.search(html, j)
                opener = open_pat.search(html, j)
                # Take whichever comes first
                if closer is not None and (opener is None or closer.start() < opener.start()):
                    depth -= 1
                    j = closer.end()
                elif opener is not None:
                    depth += 1
                    j = opener.end()
                else:
                    # No more tags found, move to end
                    j = len(html)
                    break
            i = j
        else:
            # No match at this position, advance
            if match:
                result.append(html[i:match.start()])
                i = match.start()
            else:
                result.append(html[i:])
                break
    return ''.join(result)


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

def get_ancestor_auto_image_path(page_path: Optional[str], conn) -> Optional[bool]:
    """
    Get auto_image_path from ancestor pages.
    Walk up from the current page until auto_image_path is found or root is reached.
    Returns None if no ancestor has auto_image_path set.
    """
    if not page_path:
        return None

    current_path = page_path
    visited = set()

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
                if metadata and "auto_image_path" in metadata:
                    val = metadata.get("auto_image_path")
                    if val is not None:
                        return bool(val)
            except json.JSONDecodeError:
                pass

        # 继续向上查询父page
        current_path = extract_parent_path_from_path(current_path)

    return None


def _parse_ts(value: Optional[str]):
    """Parse last_modified/updated_at into comparable datetime. Handles both
    SQLite CURRENT_TIMESTAMP ('YYYY-MM-DD HH:MM:SS') and isoformat strings.
    Always returns timezone-aware UTC datetime (naive inputs assumed UTC) so
    comparisons never mix naive/aware. Returns None if unparseable."""
    if not value:
        return None
    s = str(value).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass
    else:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _compute_out_of_sync(conn, self_path: Optional[str], self_ts: Optional[str]) -> bool:
    """True if this page's latest edit is newer than its linked other-language
    page has published — i.e. the twin has not yet published a version at least
    as new as this page's last edit.

    Comparison is date-only: EN/FR pages saved/published on the same calendar
    day are considered in sync (timestamps will never be identical due to save
    order). Re-publishing the twin clears the badge because last_published then
    covers this page's last_modified date.
    """
    if not self_path or not self_ts:
        return False
    t_self = _parse_ts(self_ts)
    if not t_self:
        return False
    row = conn.execute(
        "SELECT last_modified, last_published, status FROM webbot_page WHERE path = ?",
        (self_path,),
    ).fetchone()
    if not row or not row["last_modified"]:
        return False
    # Only published pages show the badge: draft pages are not live yet,
    # so an out-of-sync warning has no meaning for them.
    if row["status"] != "published":
        return False
    t_other = _parse_ts(row["last_modified"])
    if not t_other:
        return False
    if t_self.date() <= t_other.date():
        return False
    # Twin published after this page's last edit → content is in sync.
    t_other_pub = _parse_ts(row["last_published"])
    if t_other_pub and t_other_pub.date() >= t_self.date():
        return False
    return True


def _compute_is_republish(last_modified: Optional[str], last_published: Optional[str]) -> bool:
    """True if the page was modified after its last publish (needs republish).

    Never-published pages (last_published is None) return False: they need a
    first Publish, not a Republish."""
    if not last_modified or not last_published:
        return False
    t_lm = _parse_ts(last_modified)
    t_lp = _parse_ts(last_published)
    if t_lm is None or t_lp is None:
        return False
    return t_lm > t_lp


def _mark_ai_index_pending(conn, path: str) -> None:
    """P1 of the incremental AI-index plan: mark a just-published page as pending.

    Called inside the publish transaction (before commit) so the marker is atomic
    with the publish itself. Only pages with last_published set are marked (i.e.
    truly published). The ai-search index worker consumes this queue and flips the
    status to indexed / skipped / error.

    Defensive: if the P0 columns are missing (pre-migration DB), this is a no-op
    with a warning instead of crashing the publish.
    """
    try:
        conn.execute(
            "UPDATE webbot_page SET ai_index_status = 'pending' "
            "WHERE path = ? AND last_published IS NOT NULL",
            (path,),
        )
    except sqlite3.OperationalError:
        logger.warning(
            "ai_index_status column missing (run app/ai_index_migration.py, P0); "
            "skipping AI-index marker for %s",
            path,
            exc_info=True,
        )


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
    """Translate English text to French using DeepSeek LLM (was GoogleTranslator — unreliable, frequently blocked/rate-limited)."""
    from app.routes.translate import _call_llm
    try:
        system_prompt = (
            "You are a professional translator specializing in Government of Canada web content. "
            "Translate the given text from English to Canadian French.\n"
            "CRITICAL RULES:\n"
            "1. Return ONLY the translated text — no explanations, no quotes, no markdown wrappers\n"
            "2. Translate title/heading text naturally and concisely\n"
            "3. Use Canadian French spelling and terminology (e.g., 'courriel' not 'email', 'cliquez' not 'clique')"
        )
        translated = await _call_llm(system_prompt, text)
        if not translated or not translated.strip():
            raise HTTPException(status_code=502, detail="Translation returned empty content")
        return {"original": text, "translated": translated.strip()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation failed: {str(e)}")


@router.post("/", response_model=PageResponse)
async def create_page(page: PageCreate, current_user: dict = Depends(get_current_active_user)):
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

        # Permission check: verify user has write access to the parent path
        if not user_can_write_page(current_user["id"], page_id):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to create pages under: {page_id}"
            )

        # Check if page path already exists
        cursor.execute("SELECT id, path, title, language FROM webbot_page WHERE path = ?", (page_id,))
        existing = cursor.fetchone()

        import json
        if existing:
            if page.skip_if_exists:
                # Return existing page data instead of error
                cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (page_id,))
                full_page = cursor.fetchone()
                if full_page:
                    page_data = dict(full_page)
                    # Parse JSON string fields to dict if needed
                    for field in ['metadata', 'tags']:
                        if field in page_data and isinstance(page_data[field], str):
                            try:
                                page_data[field] = json.loads(page_data[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    return PageResponse(**page_data)
                return {"id": page_id, "title": "", "content": "", "language": "en", "status": "", "path": page_id}
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
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO webbot_page
            (id, title, description, keywords, content, language, parent_path, path, other_language_path, status, metadata, hide_in_navigation, navigation_title, created_at, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            page.status.value if isinstance(page.status, PageStatus) else (page.status or "draft"),
            json.dumps(metadata_dict) if metadata_dict else "{}",
            1 if page.hide_in_navigation else 0,
            page.navigation_title if page.navigation_title else None,
            now,
            now
        ))

        conn.commit()

        # Auto-scan references for this page
        try:
            from app.services.references import scan_page_references
            scan_page_references(page_path, page.content or "")
        except Exception as ref_err:
            print(f"⚠️  Reference scan failed for {page_path}: {ref_err}", file=__import__('sys').stderr)

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
                        created_at = datetime.now(timezone.utc).isoformat()
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
            SELECT t.id
            FROM webbot_tag t
            JOIN webbot_page_tag pt ON t.id = pt.tag_id
            WHERE pt.page_id = ?
            ORDER BY t.id
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
async def get_pages_by_path(
    path: str = Query(..., description="Parent page path, returns all direct children. e.g. path=/en returns pages with parent_path=/en. path=/ returns root pages (parent_path IS NULL)。"),
    current_user: dict = Depends(get_current_active_user)
):
    """Get pages by parent path

    Get all pages under a specific path (direct children).
    Simplified version of /api/v1/pages?path=..., designed for path filtering.
    Results are filtered by the current user's app permissions.

    Example:
    - GET /api/v1/pages/path?path=/en → returns all pages with parent_path=/en
    - GET /api/v1/pages/path?path=/ → returns root pages
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        normalized_path = path.rstrip('/')
        if normalized_path == '':
            # Root path: parent_path = '/' OR IS NULL (backward compatible)
            cursor.execute("SELECT * FROM webbot_page WHERE parent_path = '/' OR parent_path IS NULL ORDER BY title ASC")
        else:
            # 查找parent_path等于指定路径的page
            cursor.execute("SELECT * FROM webbot_page WHERE parent_path = ? ORDER BY title ASC", (normalized_path,))

        pages = cursor.fetchall()
        result = []

        for page in pages:
            page_dict = dict(page)
            # 解析metadata field(数据库存储为JSON字符串)
            meta = {}
            if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
                try:
                    meta = json.loads(page_dict["metadata"])
                except json.JSONDecodeError:
                    meta = {}
            elif isinstance(page_dict.get("metadata"), dict):
                meta = page_dict["metadata"]
            # Extract lock_status from metadata
            page_dict["lock_status"] = meta.get("lock_status", "unlocked")
            # Extract redirectTo from metadata
            page_dict["redirectTo"] = meta.get("redirect_to", None)
            # Out-of-sync detection (bilingual pairs)
            page_dict["out_of_sync"] = _compute_out_of_sync(
                cursor, page_dict.get("other_language_path"), page_dict.get("last_modified"))
            result.append(PageListItem(**page_dict))

        # Filter by user's app permissions
        filtered = filter_pages_by_permission(result, current_user["id"], path_attr="path")
        return filtered

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()

@router.get("/", response_model=List[PageListItem])
async def list_pages(
    skip: int = 0,
    limit: int = 100,
    path: Optional[str] = Query(None, description="Parent page path, returns all direct children under this path. e.g. path=/en returns pages with parent_path=/en. If omitted, returns all pagese。"),
    prefix: Optional[str] = Query(None, description="Path prefix filter, returns all pages whose path starts with this prefix. e.g. prefix=/canadasite/en/components/ returns all component pages recursively.\nWhen both prefix and path are provided, prefix takes precedence."),
    current_user: dict = Depends(get_current_active_user)
):
    """Get page list

    Supports filtering by parent path, returns all pages under a specific path (direct children).
    Results are filtered by the current user's app permissions.

    Example:
    - GET /api/v1/pages?path=/en → returns pages with parent_path=/en
    - GET /api/v1/pages?path=/ → returns root pages (parent_path IS NULL)
    - GET /api/v1/pages?path= → returns all pages
    - GET /api/v1/pages?prefix=/canadasite/en/components/ → recursive path prefix match

    Parameters:
    - skip: Records to skip (pagination)
    - limit: Records to return (pagination)
    - path: Parent page path, e.g. /en or /en/contact. If provided, filters by parent_path field.
    - prefix: Path prefix for recursive match. Overrides path if both provided.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT * FROM webbot_page"
        params = []

        if prefix is not None:
            # Prefix filter: use range query (>= / <) instead of LIKE to utilize path index
            normalized_prefix = prefix.rstrip('/') + '/'
            query += " WHERE path >= ? AND path < printf('%s~', ?)"
            params.append(normalized_prefix)
            params.append(normalized_prefix)
        elif path is not None:
            normalized_path = path.rstrip('/')
            if normalized_path == '':
                query += " WHERE parent_path = '/' OR parent_path IS NULL"
            else:
                query += " WHERE parent_path = ?"
                params.append(normalized_path)

        # Add Sort and Pagination
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        cursor.execute(query, tuple(params))

        pages = cursor.fetchall()
        result = []

        for page in pages:
            page_dict = dict(page)
            # 解析metadata field(数据库存储为JSON字符串)
            meta = {}
            if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
                try:
                    meta = json.loads(page_dict["metadata"])
                except json.JSONDecodeError:
                    meta = {}
            elif isinstance(page_dict.get("metadata"), dict):
                meta = page_dict["metadata"]
            # Extract lock_status from metadata
            page_dict["lock_status"] = meta.get("lock_status", "unlocked")
            # Extract redirectTo from metadata
            page_dict["redirectTo"] = meta.get("redirect_to", None)
            # Out-of-sync detection (bilingual pairs)
            page_dict["out_of_sync"] = _compute_out_of_sync(
                cursor, page_dict.get("other_language_path"), page_dict.get("last_modified"))
            result.append(PageListItem(**page_dict))

        # Filter by user's app permissions
        filtered = filter_pages_by_permission(result, current_user["id"], path_attr="path")
        return filtered

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()

@router.get("/getheader")
async def get_header(path: str = ""):
    """
    Get header component content
    Fallback: department-specific (level 4) → language-level (level 3)

    Example: for path /canadasite/en/government/about
    1. First try /canadasite/en/government/header
    2. If not found, try /canadasite/en/header
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        normalized_path = normalize_path(path) if path else ""
        language = extract_language_from_path(normalized_path)
        parts = normalized_path.strip('/').split('/') if normalized_path else []
        site_name = parts[0] if parts else "canadasite"
        dept = parts[2] if len(parts) >= 3 else None

        content = None
        path_used = None
        fallback_level = None

        # level 4: /canadasite/{lang}/{dept}/header
        if language and dept:
            l4 = f"/{site_name}/{language}/{dept}/header"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l4,))
            r = cursor.fetchone()
            if r:
                content = _unwrap_component(r["content"])
                path_used = l4
                fallback_level = "fourth"

        # level 3: /canadasite/{lang}/header
        if not content and language:
            l3 = f"/{site_name}/{language}/header"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l3,))
            r = cursor.fetchone()
            if r:
                content = _unwrap_component(r["content"])
                path_used = l3
                fallback_level = "third"

        if not content:
            return {
                "success": False,
                "message": "Header not found",
                "content": "",
                "path_used": None,
                "fallback_level": None
            }

        return {
            "success": True,
            "content": content,
            "path_used": path_used,
            "fallback_level": fallback_level,
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
    Lookup order:
    1. {path}/menu (current path's own menu) — NEW, highest priority
    2. department-specific megamenu (level 4): /{site}/{lang}/{dept}/megamenu
    3. language-level megamenu (level 3): /{site}/{lang}/megamenu

    Example: for path /canadasite/en/government/about
    1. First try /canadasite/en/government/about/menu
    2. If not found, try /canadasite/en/government/megamenu
    3. If not found, try /canadasite/en/megamenu

    Same rules as header
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        normalized_path = normalize_path(path) if path else ""
        language = extract_language_from_path(normalized_path)
        parts = normalized_path.strip('/').split('/') if normalized_path else []
        site_name = parts[0] if parts else "canadasite"
        dept = parts[2] if len(parts) >= 3 else None

        content = None
        path_used = None
        fallback_level = None

        # level 1 (NEW): {path}/menu — current path's own menu
        if normalized_path:
            l1 = f"{normalized_path}/menu"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l1,))
            r = cursor.fetchone()
            if r:
                content = _unwrap_component(r["content"])
                path_used = l1
                fallback_level = "path"

        # level 4: /{site}/{lang}/{dept}/megamenu
        if not content and language and dept:
            l4 = f"/{site_name}/{language}/{dept}/megamenu"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l4,))
            r = cursor.fetchone()
            if r:
                content = _unwrap_component(r["content"])
                path_used = l4
                fallback_level = "fourth"

        # level 3: /{site}/{lang}/megamenu
        if not content and language:
            l3 = f"/{site_name}/{language}/megamenu"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l3,))
            r = cursor.fetchone()
            if r:
                content = _unwrap_component(r["content"])
                path_used = l3
                fallback_level = "third"

        if not content:
            return {
                "success": False,
                "message": "Megamenu not found",
                "content": "",
                "path_used": None,
                "fallback_level": None
            }

        return {
            "success": True,
            "content": content,
            "path_used": path_used,
            "fallback_level": fallback_level,
            "language": language
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    finally:
        conn.close()

@router.get("/by-path", response_model=PageResponse)
async def get_page_by_path(path: str = Query(..., description="Full page path, e.g. /en/contact", alias="path"), current_user: dict = Depends(get_current_active_user)):
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
            now = datetime.now(timezone.utc).isoformat()
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
                navigation_title=None,
                tags=["boarding", "content", "dam"],
                created_by="system",
                created_at=now,
                last_modified=now,
                last_published=now
            )

        # If路径Root path,返回合成page
        if normalized_path == '/':
            from datetime import datetime
            now = datetime.now(timezone.utc).isoformat()
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
                navigation_title=None,
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

        # Permission check: verify user can read this page
        if not user_can_see_page(current_user["id"], page_dict["path"]):
            raise HTTPException(status_code=404, detail=f"Page not found: {page_dict['path']}")

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

        # Republish flag: modified after last publish
        page_dict["is_republish"] = _compute_is_republish(
            page_dict.get("last_modified"), page_dict.get("last_published"))

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
async def get_page_children_by_path(
    path: str = "",
    title: Optional[str] = Query(None),
    limit: int = Query(30),
    redirectTo: Optional[str] = Query(None, description="Filter by redirect target (LIKE match). Use ?redirectTo=1 or ?redirectTo=true to return all pages with redirect. Use ?redirectTo=/en/contact to match specific target.")
):
    """Get children of a page by path

    When title is provided, searches ALL descendants (any level) matching title
    and path prefix. Otherwise returns direct children only.

    When redirectTo is set, only returns pages that have a redirect_to
    parameter in their metadata (useful for building redirect sitemap).

    Example: /api/v1/pages/by-path/canadasite/en/children
             /api/v1/pages/by-path/canadasite/en/children?title=Illness
             /api/v1/pages/by-path/canadasite/en/mustache-templates/children
             /api/v1/pages/by-path/canadasite/en/children?redirectTo=1
    """
    import sys
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalize path
        normalized_path = normalize_path(path)
        print(f"DEBUG get_page_children_by_path: path='{path}', normalized='{normalized_path}', title_filter='{title}', limit={limit}, redirectTo_filter={redirectTo}", file=sys.stderr)

        if title:
            # Title search: return ALL descendants (any level) matching both path prefix and title
            if normalized_path == '/' or normalized_path == '':
                # Root search - match all pages
                cursor.execute("""
                    SELECT * FROM webbot_page
                    WHERE title LIKE ?
                    ORDER BY last_modified DESC, title ASC
                    LIMIT ?
                """, (f"%{title}%", limit))
            else:
                # Use range query (>= / <) instead of LIKE for path prefix to utilize index
                cursor.execute("""
                    SELECT * FROM webbot_page
                    WHERE path >= ? AND path < printf('%s~', ?) AND title LIKE ?
                    ORDER BY last_modified DESC, title ASC
                    LIMIT ?
                """, (normalized_path, normalized_path, f"%{title}%", limit))
        else:
            # No title filter: direct children only (existing behavior)
            if normalized_path == '/' or normalized_path == '':
                cursor.execute("""
                    SELECT * FROM webbot_page
                    WHERE parent_path = '/' OR parent_path IS NULL
                    ORDER BY last_modified DESC, title ASC
                """)
            else:
                # 直接通过 path 列查找page(支持任意层级的路径)
                cursor.execute("SELECT id, path FROM webbot_page WHERE path = ?", (normalized_path,))
                parent_page = cursor.fetchone()
                if not parent_page:
                    raise HTTPException(status_code=404, detail=f"Parent page path not found: {normalized_path}")

                parent_path = parent_page['path']
                cursor.execute("""
                    SELECT * FROM webbot_page
                    WHERE parent_path = ?
                    ORDER BY last_modified DESC, title ASC
                """, (parent_path,))

        children = cursor.fetchall()
        result = []

        for child in children:
            child_dict = dict(child)
            # 解析metadata field
            meta = {}
            if child_dict.get("metadata") and isinstance(child_dict["metadata"], str):
                try:
                    meta = json.loads(child_dict["metadata"])
                except json.JSONDecodeError:
                    meta = {}
            elif isinstance(child_dict.get("metadata"), dict):
                meta = child_dict["metadata"]
            # Extract lock_status from metadata
            child_dict["lock_status"] = meta.get("lock_status", "unlocked")
            # Extract redirectTo from metadata (for response field)
            child_dict["redirectTo"] = meta.get("redirect_to", None)
            # Out-of-sync detection (bilingual pairs)
            child_dict["out_of_sync"] = _compute_out_of_sync(
                cursor, child_dict.get("other_language_path"), child_dict.get("last_modified"))
            # If redirectTo filter active, match redirect target with LIKE
            if redirectTo:
                if not child_dict["redirectTo"]:
                    continue
                if redirectTo not in ["1", "true", "yes"]:
                    # redirectTo is a search term - LIKE match against redirect target
                    if redirectTo.lower() not in child_dict["redirectTo"].lower():
                        continue
            result.append(PageListItem(**child_dict))

        print(f"DEBUG: Returning {len(result)} child pages", file=sys.stderr)
        return result

    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()

@router.get("/by-path/{full_path:path}", response_model=PageResponse)
async def get_page_by_path_param(full_path: str, current_user: dict = Depends(get_current_active_user)):
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
            now = datetime.now(timezone.utc).isoformat()
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
                navigation_title=None,
                tags=["boarding", "content", "dam"],
                created_by="system",
                created_at=now,
                last_modified=now,
                last_published=now
            )

        # If路径Root path,返回合成page
        if normalized_path == '/':
            from datetime import datetime
            now = datetime.now(timezone.utc).isoformat()
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
                navigation_title=None,
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

        # Permission check: verify user can read this page
        if not user_can_see_page(current_user["id"], page_dict["path"]):
            raise HTTPException(status_code=404, detail=f"Page not found: {page_dict['path']}")

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

        # Out-of-sync detection (bilingual pairs)
        page_dict["out_of_sync"] = _compute_out_of_sync(
            conn, page_dict.get("other_language_path"), page_dict.get("last_modified"))

        # Republish flag: modified after last publish
        page_dict["is_republish"] = _compute_is_republish(
            page_dict.get("last_modified"), page_dict.get("last_published"))

        print(f"DEBUG: Returning page with id={page_dict.get('id')}, path={page_dict.get('path')}", file=sys.stderr)
        sys.stderr.flush()
        return PageResponse(**page_dict)

    except sqlite3.Error as e:
        print(f"DEBUG: SQL error: {e}", file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()


@router.get("/property-forms/{form_name}")
async def get_property_form(form_name: str):
    """Get a property form definition by name

    Form definitions are stored as JSON files in webbot/property-forms/
    """
    import os
    forms_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "property-forms")
    form_path = os.path.join(forms_dir, f"{form_name}.json")
    if not os.path.exists(form_path):
        raise HTTPException(status_code=404, detail=f"Property form '{form_name}' not found")
    try:
        with open(form_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load form: {e}")


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

        # Helper: populate subjects/audience/type from linked tags (with metadata fallback)
        def populate_dcterms(d):
            if not d:
                return d
            page_id = d.get("id")
            if not page_id:
                return d
            # Fetch linked tags for this page
            tag_rows = conn.execute("""
                SELECT t.type, t.title_en FROM webbot_tag t
                INNER JOIN webbot_page_tags pt ON pt.tag_id = t.id
                WHERE pt.page_id = ?
            """, (page_id,)).fetchall()
            subjects = []
            audiences = []
            type_val = None
            for r in tag_rows:
                tag_type = r["type"]
                title_en = r["title_en"]
                if tag_type == "subject":
                    subjects.append(title_en)
                elif tag_type == "audience":
                    audiences.append(title_en)
                elif tag_type == "type":
                    type_val = title_en
            if subjects:
                d["subjects"] = ";".join(subjects)
            elif d.get("metadata") and d["metadata"].get("subjects"):
                d["subjects"] = d["metadata"]["subjects"]
            if audiences:
                d["audience"] = ";".join(audiences)
            elif d.get("metadata") and d["metadata"].get("audience"):
                d["audience"] = d["metadata"]["audience"]
            if type_val:
                d["type"] = type_val
            elif d.get("metadata") and d["metadata"].get("type"):
                d["type"] = d["metadata"]["type"]
            return d

        # Populate dcterms for all levels
        if page_data:
            populate_dcterms(page_data)
        if inst_level_data:
            populate_dcterms(inst_level_data)
        if lang_level_data:
            populate_dcterms(lang_level_data)

        # Strip content field from each page dict before passing to PageMetadataItem
        def strip_content(d):
            if d and "content" in d:
                d = {k: v for k, v in d.items() if k != "content"}
            return d

        return PageMetadataResponse(
            page=PageMetadataItem(**strip_content(page_data)) if page_data else None,
            institution_level=PageMetadataItem(**strip_content(inst_level_data)) if inst_level_data else None,
            language_level=PageMetadataItem(**strip_content(lang_level_data)) if lang_level_data else None,
            path=normalized,
            path_depth=len(path_parts)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata query failed: {e}")
    finally:
        conn.close()


def _unwrap_component(content: str) -> str:
    """Strip <html><head>...</head><body> wrapper from component HTML."""
    if not content:
        return content
    import re
    content = re.sub(r'<html[^>]*>.*?</head><body[^>]*>', '', content, count=1, flags=re.DOTALL)
    content = re.sub(r'</body>\s*</html>\s*$', '', content, count=1, flags=re.DOTALL | re.MULTILINE)
    return content.strip()


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
        depth = len(path_parts)
        
        # Build all ancestor paths in one list
        ancestor_paths = []
        for d in range(2, depth + 1):
            ancestor_paths.append("/" + "/".join(path_parts[:d]))
        
        # Single query: fetch all ancestors at once (uses path index)
        placeholders = ",".join(["?"] * len(ancestor_paths))
        cursor.execute(f"SELECT * FROM webbot_page WHERE path IN ({placeholders}) ORDER BY LENGTH(path)", ancestor_paths)
        rows = cursor.fetchall()
        
        # Map rows by path
        row_map = {r["path"]: r for r in rows}
        
        parents = []
        page = None
        
        for d in range(2, depth + 1):
            ancestor_path = "/" + "/".join(path_parts[:d])
            row = row_map.get(ancestor_path)
            if row:
                page_dict = dict(row)
                _parse_page_dict(page_dict)
                page_dict["is_republish"] = _compute_is_republish(
                    page_dict.get("last_modified"), page_dict.get("last_published"))
                item = PageListItem(**page_dict)
                # Strip the site prefix (e.g. /canadasite) from breadcrumb path
                stripped_parts = path_parts[1:d]
                item.path = "/" + "/".join(stripped_parts)
                if d == depth:
                    page = item
                    # Remove invalid /canadasite other_language_path
                    if page.other_language_path == "/canadasite":
                        page.other_language_path = None
                else:
                    # Always include root (Home), but skip other pages with hide_in_navigation
                    is_root = d == 2
                    if is_root or not page_dict.get('hide_in_navigation', False):
                        parents.append(item)
        
        # ─── Fetch header ──────────────────────────────────────────────
        # Fallback: department-specific (level 4) → language-level (level 3)
        language = extract_language_from_path(normalized)
        parts = normalized.strip('/').split('/')
        site_name = parts[0] if parts else "canadasite"
        dept = parts[2] if len(parts) >= 3 else None

        header = None
        # level 4: /canadasite/{lang}/{dept}/header
        if language and dept and len(parts) >= 3:
            l4 = f"/{site_name}/{language}/{dept}/header"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l4,))
            r = cursor.fetchone()
            if r:
                header = {"success": True, "content": _unwrap_component(r["content"]), "path_used": l4, "fallback_level": "fourth", "language": language}
        # level 3: /canadasite/{lang}/header
        if not header and language:
            l3 = f"/{site_name}/{language}/header"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l3,))
            r = cursor.fetchone()
            if r:
                header = {"success": True, "content": _unwrap_component(r["content"]), "path_used": l3, "fallback_level": "third", "language": language}
        if not header:
            header = {"success": False, "message": "Header not found", "content": "", "path_used": None, "fallback_level": None}

        # ─── Fetch megamenu ────────────────────────────────────────────
        megamenu = None
        # level 1 (NEW): {path}/menu — current path's own menu
        if normalized:
            l1 = f"{normalized}/menu"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l1,))
            r = cursor.fetchone()
            if r:
                megamenu = {"success": True, "content": _unwrap_component(r["content"]), "path_used": l1, "fallback_level": "path", "language": language}
        # level 4: /canadasite/{lang}/{dept}/megamenu
        if not megamenu and language and dept and len(parts) >= 3:
            l4 = f"/{site_name}/{language}/{dept}/megamenu"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l4,))
            r = cursor.fetchone()
            if r:
                megamenu = {"success": True, "content": _unwrap_component(r["content"]), "path_used": l4, "fallback_level": "fourth", "language": language}
        # level 3: /canadasite/{lang}/megamenu
        if not megamenu and language:
            l3 = f"/{site_name}/{language}/megamenu"
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (l3,))
            r = cursor.fetchone()
            if r:
                megamenu = {"success": True, "content": _unwrap_component(r["content"]), "path_used": l3, "fallback_level": "third", "language": language}
        if not megamenu:
            megamenu = {"success": False, "message": "Megamenu not found", "content": "", "path_used": None, "fallback_level": None}

        return {"parents": parents, "page": page, "header": header, "megamenu": megamenu}
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
                # 找到了父page,使用其path作为target_parent_path
                target_parent_path = parent_page['path']
            else:
                # Ifparent_path不Full path,可能父Page ID
                cursor.execute("SELECT id, path FROM webbot_page WHERE id = ?", (parent_path,))
                parent_page = cursor.fetchone()
                if parent_page:
                    target_parent_path = parent_page['path']
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
                cursor.execute("SELECT id, path, parent_path FROM webbot_page WHERE path = ?", (path_to_try.rstrip('/'),))
                actual_parent = cursor.fetchone()
                if actual_parent:
                    target_parent_path = actual_parent['path']
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Parent page not found: id='{page_id}', parent_path='{parent_path}'"
                    )

        else:
            # 未指定父标识符,需要找到具体的父page
            # 首先尝试将page_id作为路径查找父page
            path_to_try = page_id if page_id.startswith('/') else f'/{page_id}'
            cursor.execute("SELECT id, path, parent_path FROM webbot_page WHERE path = ?", (path_to_try.rstrip('/'),))
            parent_page = cursor.fetchone()

            if parent_page:
                # 找到page,使用其path作为target_parent_path
                target_parent_path = parent_page['path']
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
            meta = {}
            if child_dict.get("metadata") and isinstance(child_dict["metadata"], str):
                try:
                    meta = json.loads(child_dict["metadata"])
                except json.JSONDecodeError:
                    meta = {}
            elif isinstance(child_dict.get("metadata"), dict):
                meta = child_dict["metadata"]
            # Extract lock_status from metadata
            child_dict["lock_status"] = meta.get("lock_status", "unlocked")
            # Extract redirectTo from metadata
            child_dict["redirectTo"] = meta.get("redirect_to", None)
            # Out-of-sync detection (bilingual pairs)
            child_dict["out_of_sync"] = _compute_out_of_sync(
                cursor, child_dict.get("other_language_path"), child_dict.get("last_modified"))
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

        # auto_image_path 继承: 当前页未设置时向上查找
        if page_dict["metadata"].get("auto_image_path") is None:
            inherited = get_ancestor_auto_image_path(page_dict["path"], conn)
            if inherited is not None:
                page_dict["metadata"]["auto_image_path"] = inherited

        # 映射字段名: DB用last_modified/last_published, 响应模型用updated_at/published_at
        if "last_modified" in page_dict and "updated_at" not in page_dict:
            page_dict["updated_at"] = page_dict.pop("last_modified")
        if "last_published" in page_dict and "published_at" not in page_dict:
            page_dict["published_at"] = page_dict.pop("last_published")

        # Load page tags from junction table
        try:
            cursor.execute("""
                SELECT t.path FROM webbot_tag t
                JOIN webbot_page_tags pt ON pt.tag_id = t.id
                WHERE pt.page_id = ?
            """, (page_dict.get("id"),))
            page_dict["tags"] = [row["path"] for row in cursor.fetchall()]
        except Exception:
            page_dict["tags"] = []

        # Extract redirect_to from metadata to top-level field
        page_dict["redirect_to"] = page_dict.get("metadata", {}).get("redirect_to", None)
        # Out-of-sync detection (bilingual pairs)
        page_dict["out_of_sync"] = _compute_out_of_sync(
            conn, page_dict.get("other_language_path"), page_dict.get("updated_at") or page_dict.get("last_modified"))

        return PagePropertiesResponse(**page_dict)

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    finally:
        conn.close()


# ============================================================================
# Preview endpoint — render page using publish_template (registered before
# catch-all to ensure priority over /{page_id:path})
# ============================================================================
@router.get("/preview", response_model=None)
async def preview_page_get(
    request: FastAPIRequest,
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact")
):
    """
    Get preview of a page using the publish_template (GET version — uses DB content).
    Called from navigation tree Preview button which opens a new window.
    """
    return await _render_preview(request, path, content_override=None)


@router.post("/preview", response_model=None)
async def preview_page_post(
    request: FastAPIRequest,
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact"),
    body: Optional[PreviewRequest] = Body(None, description="Optional JSON body with content override")
):
    """
    Preview a page: same as publish but returns rendered HTML directly instead of writing to file.
    POST version — accepts unsaved editor content via JSON body.
    """
    content_override = body.content if body and body.content else None
    return await _render_preview(request, path, content_override=content_override)


async def _render_preview(
    request: FastAPIRequest,
    path: str,
    content_override: Optional[str] = None
) -> HTMLResponse:
    import chevron
    import aiohttp

    now = datetime.now(timezone.utc)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Load the page
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (path,))
        page = cursor.fetchone()
        if not page:
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        page = dict(page)
        page_content = content_override if content_override is not None else page.get("content", "")
        page_title = page.get("title", "Untitled")
        page_language = page.get("language", "en")
        page_publish_template = page.get("publish_template", None)
        page_last_modified = page.get("last_modified", now.isoformat())
        if page_last_modified:
            if isinstance(page_last_modified, str):
                try:
                    dt = datetime.fromisoformat(page_last_modified.replace("Z", "+00:00"))
                    date_modified_str = dt.strftime("%Y-%m-%d")
                except:
                    date_modified_str = page_last_modified[:10] if len(page_last_modified) >= 10 else now.strftime("%Y-%m-%d")
            else:
                date_modified_str = now.strftime("%Y-%m-%d")
        else:
            date_modified_str = now.strftime("%Y-%m-%d")

        base_url = str(request.base_url).rstrip("/")

        # Helper: render a mustache template config from DB
        async def render_mustache_template(template_path: str, data_source_path: str, extra_data: Optional[dict] = None) -> str:
            # Substitute {path} placeholder with the current page path for dynamic datasources
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (template_path,))
            row = cursor.fetchone()
            if not row:
                return f"<!-- Template not found: {template_path} -->"
            try:
                config = json.loads(row[0])
            except json.JSONDecodeError:
                raw = row[0]
                if "{" in raw and "}" in raw:
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    try:
                        config = json.loads(raw[start:end], strict=False)
                    except:
                        return f"<!-- Invalid JSON in template: {template_path} -->"
                else:
                    return f"<!-- No JSON config in template: {template_path} -->"

            template = config.get("template", "")
            data = config.get("data", {})
            datasource = config.get("datasource", config.get("dataresource"))

            # i18n: expand {{labels.KEY[language]}} -> {{labels.KEY.<lang>}} (legacy @i18n syntax)
            _lang_parts = data_source_path.strip('/').split('/')
            lang = _lang_parts[1] if len(_lang_parts) > 1 else 'en'
            if lang not in ('en', 'fr'):
                lang = 'en'
            if isinstance(data, dict):
                data.setdefault('language', lang)
                data.setdefault('is_en', lang == 'en')
                data.setdefault('is_fr', lang == 'fr')
            template = re.sub(
                r'\{\{\s*([^{}]+?)\[(?:page\.)?language\]\s*\}\}',
                lambda m: '{{' + m.group(1) + '.' + lang + '}}',
                template
            )
            template = re.sub(
                r'\{\{\s*([^{}]+?)\[["\'](en|fr)["\']\]\s*\}\}',
                lambda m: '{{' + m.group(1) + '.' + m.group(2) + '}}',
                template
            )

            if datasource:
                # Replace {path} placeholder with the actual page being rendered
                url = datasource.replace("{path}", data_source_path)
                if not url.startswith("http"):
                    # 2026-08-28: 内部端点本机直连，不走公网
                    url = f"{LOCAL_API_BASE}{url}"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=5) as resp:
                            if resp.status == 200:
                                ds_data = await resp.json()
                                data["datasource_loaded"] = True
                                if isinstance(ds_data, dict):
                                    data = {**data, **ds_data}
                                elif isinstance(ds_data, list):
                                    data = ds_data
                                else:
                                    data["items"] = ds_data
                except Exception as e:
                    data["datasource_loaded"] = False
                    data["datasource_error"] = str(e)

            if extra_data:
                data.update(extra_data)
            try:
                return await render_mustache_tpl(template, data, cursor, lang=lang, current_path=data_source_path, base_url=base_url)
            except Exception as e:
                return f"<!-- Mustache render error: {e} -->"

        # 2. Render head, header, footer
        head_html = await render_mustache_template("/canadasite/mustache-templates/gethead", path)

        # Unified i18n header (getheader/getheader-preview only — legacy getheader_en/fr removed).
        # Approval workflow: unpublished pages render with getheader-preview so the approver
        # sees edit/approve/publish links on prod.webfilebot.com/{path}. Published pages use
        # the clean public getheader.
        _page_status = page.get("status", "")
        _page_approved = 1 if page.get("approved") else 0
        _page_is_republish = _compute_is_republish(page.get("last_modified"), page.get("last_published"))
        if _page_status == "published" and not _page_is_republish:
            # Clean public header for live, in-sync pages.
            header_html = await render_mustache_template(
                "/canadasite/mustache-templates/getheader", path,
                extra_data={"is_approved": _page_approved, "is_published": True, "is_republish": False}
            )
        else:
            # Preview header: unpublished pages get the approval banner, and
            # published-but-modified pages get the republish banner — both are
            # rendered by the getheader-preview template (data-driven).
            header_html = await render_mustache_template(
                "/canadasite/mustache-templates/getheader-preview", path,
                extra_data={
                    "is_approved": _page_approved,
                    "is_published": _page_status == "published",
                    "is_republish": _page_is_republish,
                }
            )

        # Get footer — walk up path to find nearest footer, then language-level, then site-level
        # For /canadasite/en/auditor-general/our-work/2026-report:
        #   1. Walk up: /canadasite/en/auditor-general/our-work/2026-report/footer (skip)
        #   2. Walk up: /canadasite/en/auditor-general/our-work/footer (skip)
        #   3. Walk up: /canadasite/en/auditor-general/footer (found ✓)
        #   4. Fallback to /canadasite/{language}/footer
        #   5. Fallback to /canadasite/footer
        def _find_footer(search_path: str) -> str:
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (search_path,))
            row = cursor.fetchone()
            if row:
                raw = row[0]
                # Strip outer <html><head><body> wrapper — DB content is stored as full HTML doc
                f_match = re.search(r'<footer[^>]*>.*?</footer>', raw, re.DOTALL | re.IGNORECASE)
                if f_match:
                    return f_match.group(0)
                b_match = re.search(r'<body[^>]*>(.*?)</body>', raw, re.DOTALL | re.IGNORECASE)
                if b_match:
                    return b_match.group(1).strip()
                return raw
            return ""

        footer_html = ""
        # Step 1: Walk up from full path to find nearest institution footer
        path_parts = path.strip('/').split('/')
        lang_footer_path = f"/canadasite/{page_language}/footer"
        if len(path_parts) >= 3:
            # Walk up from deepest level to just below language level
            for i in range(len(path_parts), 2, -1):
                candidate = '/' + '/'.join(path_parts[:i]) + '/footer'
                if candidate == lang_footer_path:
                    continue  # skip language-level, we handle it in Step 2
                footer_html = _find_footer(candidate)
                if footer_html:
                    break

        # Step 2: Fallback to language-level footer
        if not footer_html:
            footer_html = _find_footer(lang_footer_path)

        # Step 3: Fallback to site-level footer
        if not footer_html:
            footer_html = _find_footer("/canadasite/footer")

        # Step 4: Fallback to extracting from raw content
        if not footer_html:
            footer_match = re.search(r'<footer[^>]*id=[\"\']wb-info[\"\'][^>]*>.*?</footer>', page.get("content", ""), re.DOTALL | re.IGNORECASE)
            if footer_match:
                footer_html = footer_match.group(0)

        # Get contextual-footer — from /canadasite/{lang}/{institution}/contextual-footer
        contextual_footer = ""
        if len(path_parts) >= 3:
            ctx_path = f"/canadasite/{page_language}/{path_parts[2]}/contextual-footer"
            ctx_row = cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (ctx_path,)).fetchone()
            if ctx_row:
                raw = ctx_row[0]
                b_match = re.search(r'<body[^>]*>(.*?)</body>', raw, re.DOTALL | re.IGNORECASE)
                if b_match:
                    contextual_footer = b_match.group(1).strip()
                else:
                    contextual_footer = raw.strip()

        # 3. Clean content
        def extract_content(raw_content: str) -> str:
            if not raw_content:
                return ""
            main_match = re.search(r'<main[^>]*>(.*)</main>', raw_content, re.DOTALL | re.IGNORECASE)
            if main_match:
                raw_content = main_match.group(1)
            else:
                body_match = re.search(r'<body[^>]*>(.*)</body>', raw_content, re.DOTALL | re.IGNORECASE)
                if body_match:
                    raw_content = body_match.group(1)
            raw_content = remove_pagedetails_sections(raw_content)
            return raw_content.strip()

        cleaned_content = extract_content(page_content)

        # 4. Date modified
        date_modified_html = (
            '<footer class="pagedetails container">\n'
            '    <h2 class="wb-inv">Page details</h2>\n'
            '    <div class="row">\n'
            '        <div class="col-sm-8 col-md-9 col-lg-9">\n'
            f'            <p>Date modified: {date_modified_str}</p>\n'
            '        </div>\n'
            '    </div>\n'
            '</footer>'
        )

        # 5. Render with template or default
        # Helper: try to render a page template from DB, returns None if not found
        async def render_page_template(template_path, head, header, footer, content, date_modified, lang, title, page_path, header_en=None, header_fr=None, page_metadata=None, contextual_footer=""):
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (template_path,))
            tmpl_row = cursor.fetchone()
            if not tmpl_row:
                return None
            try:
                tmpl_config = json.loads(tmpl_row[0])
                tmpl = tmpl_config.get("template", tmpl_row[0])
                tmpl_data = tmpl_config.get("data", {})
                if not isinstance(tmpl_data, dict):
                    tmpl_data = {}
            except json.JSONDecodeError:
                tmpl = tmpl_row[0]
                tmpl_data = {}
                tmpl_config = {}
            render_data = {
                "content": content,
                "head": head,
                "header": header,
                "footer": footer,
                "contextual-footer": contextual_footer,
                "date_modified": date_modified,
                "language": lang,
                "title": title,
                "path": page_path,
                "header_en": header_en or header,
                "header_fr": header_fr or header,
                "is_en": lang == "en",
                "is_fr": lang == "fr",
            }
            # Merge template static data (labels etc.) into render context
            render_data.update(tmpl_data)
            # Inject page context (for {{page.xxx}} and partials like {{>getheader}})
            page_ctx = {
                "path": page_path,
                "title": title,
                "language": lang,
                "other_language_url": None,
            }
            if isinstance(page_metadata, dict):
                olp = page_metadata.get("other_language_path") or page_metadata.get("other_language_url")
                if olp:
                    page_ctx["other_language_url"] = olp
            if not page_ctx["other_language_url"]:
                parts = page_path.strip("/").split("/")
                # Handle both /en/xxx and /canadasite/en/xxx path formats
                lang_idx = None
                for idx, seg in enumerate(parts):
                    if seg in ("en", "fr"):
                        lang_idx = idx
                        break
                if lang_idx is not None:
                    parts[lang_idx] = "fr" if parts[lang_idx] == "en" else "en"
                    page_ctx["other_language_url"] = "/" + "/".join(parts)
            render_data["page"] = page_ctx
            # Load template datasource so partials like {{>getheader}} get parents/page/header/megamenu context
            tmpl_ds = tmpl_config.get("datasource", tmpl_config.get("dataresource"))
            if tmpl_ds and isinstance(tmpl_ds, str) and tmpl_ds.strip():
                ds_url = tmpl_ds.replace("{path}", page_path)
                if not ds_url.startswith("http"):
                    # 2026-08-28: 内部端点本机直连，不走公网
                    ds_url = f"{LOCAL_API_BASE}{ds_url}"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(ds_url, timeout=5) as resp:
                            if resp.status == 200:
                                ds_data = await resp.json()
                                if isinstance(ds_data, dict):
                                    render_data = {**render_data, **ds_data}
                                elif isinstance(ds_data, list):
                                    render_data["items"] = ds_data
                except Exception as e:
                    render_data["datasource_error"] = str(e)
            # has_feedback from page metadata (compat: metadata may be str or dict)
            if page_metadata:
                if isinstance(page_metadata, str):
                    try:
                        page_metadata = json.loads(page_metadata)
                    except json.JSONDecodeError:
                        page_metadata = {}
                if isinstance(page_metadata, dict) and page_metadata.get("has_feedback") is not None:
                    render_data["has_feedback"] = page_metadata["has_feedback"]
            # NEW (2026-08-19): render page content as a Mustache template too, so dynamic
            # blocks ({{>template?path=.}}, datasource, {{labels...}}) work inside page content.
            content = _unescape_mustache_entities(content)
            if content and "{{" in content:
                _content_ctx = {k: v for k, v in render_data.items() if k != "content"}
                try:
                    content = await render_mustache_tpl(content, _content_ctx, cursor, lang=lang, current_path=page_path, base_url=base_url)
                    render_data["content"] = content
                except Exception as e:
                    logger.warning(f"Content mustache render degraded for {page_path}: {e}")
            return await render_mustache_tpl(tmpl, render_data, cursor, lang=lang, current_path=page_path, base_url=base_url)

        def default_rendered(lang, head, header, footer, content, date_modified):
            return (
                "<!DOCTYPE html>\n"
                f"<html lang=\"{lang}\">\n"
                f"{head}\n"
                f"{header}\n"
                "<body>\n"
                '<main property="mainContentOfPage" resource="#wb-main" typeof="WebPageElement" class="container">\n'
                f"{content}\n"
                f"{date_modified}\n"
                "</main>\n"
                f"{footer}\n"
                "</body>\n"
                "</html>"
            )

        # Try per-page template first, then default DB template, then hardcoded fallback
        rendered = None
        if page_publish_template:
            rendered = await render_page_template(
                page_publish_template, head_html, header_html, footer_html,
                cleaned_content, date_modified_str, page_language, page_title, path,
                page_metadata=page.get("metadata"),
                contextual_footer=contextual_footer
            )

        if not rendered:
            # Try default language-specific template from DB
            rendered = await render_page_template(
                "/canadasite/mustache-templates/page-template", head_html, header_html, footer_html,
                cleaned_content, date_modified_str, page_language, page_title, path,
                page_metadata=page.get("metadata"),
                contextual_footer=contextual_footer
            )

        if not rendered:
            # Ultimate hardcoded fallback
            rendered = default_rendered(
                page_language, head_html, header_html, footer_html,
                cleaned_content, date_modified_str
            )

        conn.close()

        # Inject AnalyBot tracking SDK before </head>
        # Config is external (analy-config.js) so changes don't require republishing
        analybot_sdk = '''<script src="/etc/designs/canada/analytics/analy-config.js" defer></script>
<script src="/etc/designs/canada/analytics/analy_v2.js" defer></script>'''
        rendered = rendered.replace('</head>', analybot_sdk + '\n</head>', 1) if rendered else rendered

        # NOTE: clientlib-base.min.css (Adobe AEM artifact) is intentionally NOT injected.

        # Cache-bust theme.min.css (Cloudflare/browser may hold the older version)
        rendered = rendered.replace('css/theme.min.css"', 'css/theme.min-20260801.css"') if rendered else rendered

        # Inject tracking script before </body>
        track_script = '<script src="/api/v1/track/track.js"></script>'
        rendered = rendered.replace('</body>', track_script + '\n</body>', 1) if rendered else rendered

        # Inject A/B experiment beacon for the demo experiment page (variant B = live DB render)
        # Reads wb_ab cookie set by nginx split_clients; reports pageview + CTA clicks to /api/v1/track/ab
        if path == "/canadasite/en/demo/test-page":
            ab_script = '''<script>
(function(){
  function abCookie(){var m=document.cookie.match(/wb_ab=([AB])/);return m?m[1]:'';}
  function abSend(ev){try{navigator.sendBeacon('/api/v1/track/ab',new Blob([JSON.stringify({experiment_id:'exp-testpage',variant:abCookie(),event_name:ev,path:location.pathname})],{type:'application/json'}));}catch(e){}}
  abSend('pageview');
  document.addEventListener('click',function(e){
    var t=e.target.closest('a.btn,.btn,button,a[role=button]');
    if(t)abSend('CTA Click');
  });
})();
</script>'''
            rendered = rendered.replace('</body>', ab_script + '\n</body>', 1) if rendered else rendered

        # NOTE: the republish PREVIEW banner (yellow, with Republish button + live
        # link) is no longer injected here — it is rendered by the
        # getheader-preview mustache template (see _render_preview header selection
        # above), so banner markup stays in one data-driven place.

        return HTMLResponse(content=rendered, status_code=200)
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.get("/template-data")
async def get_template_data(
    request: FastAPIRequest,
    path: str = Query(..., description="Template page path, e.g. /canadasite/mustache-templates/getheader"),
    page: str = Query("", description="Page path used to substitute {path} in datasource URL"),
):
    """
    Return template static data + datasource merged JSON (i18n labels etc.).
    Useful for frontend JS to consume template labels/data directly.
    """
    import aiohttp

    conn = get_db_connection()
    try:
        row = conn.execute("SELECT content FROM webbot_page WHERE path = ?", (path,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Template not found: {path}")
        try:
            config = json.loads(row[0])
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail=f"Template content is not JSON: {path}")

        static_data = config.get("data", {})
        if not isinstance(static_data, dict):
            static_data = {}
        datasource = config.get("datasource", config.get("dataresource"))
        ds_data = None
        merged = dict(static_data)
        if datasource:
            url = datasource.replace("{path}", page) if page else datasource
            if not url.startswith("http"):
                # 2026-08-28: 内部端点本机直连，不走公网
                url = f"{LOCAL_API_BASE}{url}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as resp:
                        if resp.status == 200:
                            ds_data = await resp.json()
                            if isinstance(ds_data, dict):
                                merged = {**merged, **ds_data}
                            elif isinstance(ds_data, list):
                                merged["items"] = ds_data
                            else:
                                merged["items"] = ds_data
                            merged["datasource_loaded"] = True
            except Exception as e:  # noqa: BLE001
                merged["datasource_loaded"] = False
                merged["datasource_error"] = str(e)

        return {
            "template_path": path,
            "data": static_data,
            "datasource": ds_data,
            "merged": merged,
        }
    finally:
        conn.close()


@router.get("/template-assets")
async def get_template_assets(path: str = Query(...)):
    """
    Extract template-specific CSS/JS URLs and body class for a given page path.
    Used by the editor to make TinyMCE content area styling match the published page.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        norm_path = path if path.startswith('/') else f'/{path}'
        cursor.execute("SELECT publish_template, path FROM webbot_page WHERE path = ?", (norm_path,))
        page = cursor.fetchone()
        if not page:
            return {"css_urls": [], "js_urls": [], "body_class": ""}

        template_path = page["publish_template"] if page["publish_template"] else None

        css_urls = []
        js_urls = []
        body_class = ""

        if template_path:
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (template_path,))
            template_row = cursor.fetchone()
            if template_row:
                raw = template_row[0]

                # Templates are stored as JSON with a "template" key containing HTML
                if raw.strip().startswith('{'):
                    try:
                        parsed = json.loads(raw)
                        html = parsed.get("template", "")
                    except json.JSONDecodeError:
                        html = raw
                else:
                    html = raw

                # Extract CSS <link rel="stylesheet" href="...">
                css_matches = re.findall(
                    r'<link[^>]*rel=[\"\']stylesheet[\"\'][^>]*href=[\"\']([^\"\']+)[\"\'][^>]*/?>',
                    html, re.IGNORECASE
                )
                css_urls = list(set(css_matches))

                # Extract JS <script src="...">
                js_matches = re.findall(
                    r'<script[^>]*src=[\"\']([^\"\']+)[\"\'][^>]*>',
                    html, re.IGNORECASE
                )
                js_urls = list(set(js_matches))

                # Extract body class from <body class="...">
                body_match = re.search(
                    r'<body[^>]*class=[\"\']([^\"\']+)[\"\']',
                    html, re.IGNORECASE
                )
                if body_match:
                    body_class = body_match.group(1)

        return {
            "css_urls": css_urls,
            "js_urls": js_urls,
            "body_class": body_class
        }

    except Exception:
        return {"css_urls": [], "js_urls": [], "body_class": ""}
    finally:
        conn.close()
@router.get("/resolve-file-path", response_model=dict)
@router_v1.get("/pages/resolve-file-path", response_model=dict)
async def resolve_file_path(
    page_path: str = Query(..., description="页面路径，如 /canadasite/en/some-page"),
    current_user: dict = Depends(get_current_active_user),
):
    """
    根据页面路径，向上递归查找有效的 file_path（FileBot image location）。
    从当前页开始，如果 metadata.file_path 不存在，则向上找父页面。
    用于 Resources Images 的路径输入框。
    """
    def _find_file_path(cursor, path: str, depth: int = 0) -> dict:
        if depth > 20:
            return {"file_path": None, "source": "max depth reached"}
        if not path:
            return {"file_path": None, "source": "no path"}
        cursor.execute(
            "SELECT metadata, parent_path FROM webbot_page WHERE path = ?",
            (path,)
        )
        row = cursor.fetchone()
        if not row:
            return {"file_path": None, "source": f"page not found: {path}"}
        meta = row["metadata"]
        if meta and isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        file_path = (meta or {}).get("file_path")
        if file_path:
            return {"file_path": file_path, "source": path}
        parent = row["parent_path"]
        if parent and parent != "/":
            result = _find_file_path(cursor, parent, depth + 1)
            if result["file_path"]:
                return result
        return {"file_path": None, "source": f"no file_path in hierarchy from {path}"}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Normalize path
        path = page_path.strip()
        if not path.startswith("/"):
            path = "/" + path

        result = _find_file_path(cursor, path)
        return {
            "page_path": page_path,
            "effective_file_path": result["file_path"],
            "source": result["source"],
        }
    except Exception as e:
        logger.error(f"resolve_file_path failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.api_route("/publish-staged", methods=["GET", "POST"], response_model=None)
async def publish_staged_page(
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact"),
    redirect: bool = Query(False, description="Redirect back to the public page after staging")
):
    """Public DB-only staged publish for the approval workflow (no auth required).

    Approver clicks the Publish link on prod.webfilebot.com/{path} -> this marks the
    page as published in the DB only (no static files are written). The dynamic render
    then switches from the preview header (with links) to the clean public header.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, approved FROM webbot_page WHERE path = ?", (path,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        if not row["approved"]:
            raise HTTPException(status_code=403, detail=f"Page '{path}' is not approved yet.")
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE webbot_page SET status = 'published', last_published = ?, last_modified = ? WHERE path = ?",
            (now, now, path)
        )
        # AI-search incremental index: page truly published → queue for indexing
        _mark_ai_index_pending(conn, path)
        conn.commit()
        if redirect:
            public_path = path.replace("/canadasite", "", 1)
            return RedirectResponse(url=public_path, status_code=302)
        return {"success": True, "path": path, "published_at": now}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Publish staged failed: {str(e)}")
    finally:
        conn.close()


@router.get("/{page_id:path}", response_model=PageResponse)
async def get_page(page_id: str,
                   parent_path: Optional[str] = Query(None, description="Parent page path or ID, e.g. /en or page ID."),
                   current_user: dict = Depends(get_current_active_user)):
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
        # 权限检查：验证用户是否有权看到此页面
        if not user_can_see_page(current_user["id"], page_dict["path"]):
            raise HTTPException(status_code=404, detail=f"Page not found: {page_dict['path']}")

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
                     parent_path: Optional[str] = Query(None, description="Parent page path or ID, e.g. /en or page ID."),
                     current_user: dict = Depends(get_current_active_user),
                     background_tasks: BackgroundTasks = None):
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

        # Permission check: verify user has write access to this page
        print(f"DEBUG update_page permission: path='{existing_page['path']}', user='{current_user['id']}'", file=sys.stderr)
        sys.stderr.flush()
        if not user_can_write_page(current_user["id"], existing_page["path"]):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to edit this page: {existing_page['path']}"
            )

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

        if page_update.status is not None:
            update_fields.append("status = ?")
            update_values.append(page_update.status)

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

        if page_update.navigation_title is not None:
            update_fields.append("navigation_title = ?")
            update_values.append(page_update.navigation_title)

        if page_update.publish_template is not None:
            update_fields.append("publish_template = ?")
            update_values.append(page_update.publish_template)

        # IfNo update fields,直接返回原page
        if not update_fields:
            return PageResponse(**dict(existing_page))

        # Add最后修改时间
        update_fields.append("last_modified = ?")
        update_values.append(datetime.now(timezone.utc).isoformat())

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

        # Auto-scan references (if content was updated) — run in BACKGROUND so the
        # save response never waits for it. page_references is not needed in real time.
        # (Previously it blocked ~5s on the uncommitted write lock; moved after commit,
        # and now fully async via BackgroundTasks.)
        if page_update.content is not None and background_tasks is not None:
            from app.services.references import scan_page_references
            background_tasks.add_task(scan_page_references, normalized_path, page_update.content)

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
                                (parent_other, datetime.now(timezone.utc).isoformat(), parent_path_col)
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
    except HTTPException:
        # Re-raise FastAPI HTTPExceptions (e.g. 403 permission denied) as-is
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
    finally:
        conn.close()

def _sync_filebot_delete(page_path: str, metadata_json) -> list:
    """Best-effort sync: delete matching FileBot rows via the FileBot API.

    Called AFTER the webbot row is already deleted (webbot is the source of
    truth for the editor tree). Failures never block the webbot delete — they
    are collected and returned as warning strings.

    - Folder node (metadata.is_folder)  -> DELETE /folders/{path}?recursive=true
      (FileBot folder path = "/boarding" + webbot path)
    - Page node -> DELETE /documents/by-source-url/{source_url}
      (FileBot docs are matched by document_metadata.source_url)
    """
    warnings = []
    try:
        meta = {}
        if metadata_json:
            try:
                meta = json.loads(metadata_json) if isinstance(metadata_json, str) else dict(metadata_json or {})
            except Exception:
                meta = {}

        api_base = os.getenv("FILEBOT_API_BASE", "http://127.0.0.1:8001/api/v1").rstrip("/")
        token = os.getenv("FILEBOT_JWT_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        timeout = 30

        if meta.get("is_folder") is True:
            fb_folder = "/boarding" + page_path
            resp = requests.delete(
                f"{api_base}/folders/{urllib.parse.quote(fb_folder.lstrip('/'), safe='/')}",
                params={"recursive": "true"},
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code == 404:
                warnings.append(f"FileBot folder not found: {fb_folder}")
            elif resp.status_code >= 400:
                warnings.append(f"FileBot folder delete failed ({resp.status_code}): {resp.text[:200]}")
        else:
            source_url = meta.get("source_url") or meta.get("url") or meta.get("original_url")
            if not source_url:
                warnings.append(f"No source_url in metadata for {page_path}; skipped FileBot doc sync")
            else:
                resp = requests.delete(
                    f"{api_base}/documents/by-source-url/{urllib.parse.quote(source_url, safe='')}",
                    headers=headers,
                    timeout=timeout,
                )
                if resp.status_code >= 400:
                    warnings.append(f"FileBot doc delete failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        warnings.append(f"FileBot sync error for {page_path}: {e}")
    return warnings


@router.delete("/{page_id:path}")
async def delete_page(
    page_id: str,
    delete_other_language: bool = Query(False, description="Also delete the other language page"),
    other_language_path: Optional[str] = Query(None, description="Explicit other language path to delete"),
    force: bool = Query(False, description="Skip reference warning and force delete"),
    current_user: dict = Depends(get_current_active_user)
):
    """Delete page

    page_id is now the full path (e.g. /canadasite/en/contact), queried directly by path.
    If other pages link to this one, a 409 Conflict is returned with the list of
    referencing pages (unless ?force=true is set).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Normalise page path to ensure leading slash
        normalized_path = page_id if page_id.startswith('/') else f'/{page_id}'
        normalized_path = normalized_path.rstrip('/')

        # Look up page directly by path
        cursor.execute("SELECT id, other_language_path, path, metadata FROM webbot_page WHERE path = ?", (normalized_path,))
        page_row = cursor.fetchone()
        if not page_row:
            raise HTTPException(status_code=404, detail="Page not found")
        page_metadata = page_row["metadata"]

        # Permission check: verify user has write access
        if not user_can_write_page(current_user["id"], page_row["path"]):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to delete this page"
            )

        # Check for incoming references (pages that link to this one)
        if not force:
            try:
                from app.services.references import get_page_references
                refs = get_page_references(normalized_path)
                if refs["incoming_count"] > 0:
                    # Return warning with reference list instead of deleting
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "message": f"This page is referenced by {refs['incoming_count']} other page(s)",
                            "referenced_by": refs["linked_from"],
                            "count": refs["incoming_count"],
                        }
                    )
            except HTTPException:
                raise
            except Exception as ref_err:
                print(f"⚠️  Reference check failed for {normalized_path}: {ref_err}", file=__import__('sys').stderr)

        # Determine the other language path to also delete
        target_other_path = other_language_path or page_row['other_language_path']

        # Clean up page references before deletion
        try:
            from app.services.references import remove_references_for
            remove_references_for(normalized_path)
        except Exception as ref_err:
            print(f"⚠️  Reference cleanup failed for {normalized_path}: {ref_err}", file=__import__('sys').stderr)

        # Delete main page
        cursor.execute("DELETE FROM webbot_page WHERE path = ?", (normalized_path,))

        # Delete other language page if requested
        deleted_other = None
        other_metadata = None
        if delete_other_language and target_other_path:
            cursor.execute("SELECT id, metadata FROM webbot_page WHERE path = ?", (target_other_path,))
            other_row = cursor.fetchone()
            if other_row:
                other_metadata = other_row["metadata"]
                cursor.execute("DELETE FROM webbot_page WHERE path = ?", (target_other_path,))
                deleted_other = target_other_path

        conn.commit()

        result = {"message": "Page deleted successfully", "page_id": page_id}
        if deleted_other:
            result["other_deleted"] = deleted_other

        # Best-effort sync to FileBot (never blocks/rolls back the webbot delete)
        sync_warnings = _sync_filebot_delete(normalized_path, page_metadata)
        if deleted_other:
            sync_warnings += _sync_filebot_delete(target_other_path, other_metadata)
        if sync_warnings:
            result["filebot_sync_warnings"] = sync_warnings
        return result

    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
    except HTTPException:
        conn.rollback()
        raise
    finally:
        conn.close()


# ==================== Batch String Replace ====================

@router.post("/batch-replace")
async def batch_string_replace(
    request: FastAPIRequest,
    path: str = Query(..., description="Page path prefix to match, e.g. /canadasite/en"),
    source: str = Query(..., description="String to find"),
    replace: str = Query("", description="Replacement string"),
    write_static: bool = Query(False, description="Re-render affected PUBLISHED pages to static files (live). Default False = DB-only staged replace."),
    concurrency: int = Query(8, ge=1, le=50, description="Max parallel static syncs"),
    dry_run: bool = Query(False, description="Only count affected pages without applying"),
    current_user: dict = Depends(get_current_active_user),
):
    """Batch find-and-replace in page content for all pages matching path prefix.

    Efficient: uses SQLite REPLACE() directly, no per-page Python loops.
    Only touches pages where INSTR(content, source) > 0.

    Two-stage (same as AI batch publish):
      - Default (write_static=False): DB-only. Verify on prod.webfilebot.com/en..
        (dynamic render reads the DB, so the replace is immediately visible there).
      - write_static=True (--sync): after verification, re-render affected
        published pages to the static publish directory (live). Draft pages
        stay DB-only.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Count how many pages match and will be affected
        cursor.execute('''
            SELECT COUNT(*) as total_matched,
                   SUM(CASE WHEN content IS NOT NULL AND INSTR(content, ?) > 0 THEN 1 ELSE 0 END) as total_affected
            FROM webbot_page
            WHERE path LIKE ? || '%'
        ''', (source, path))
        stats = cursor.fetchone()
        total_matched = stats['total_matched']
        total_affected = stats['total_affected'] or 0

        # Collect affected paths BEFORE the update (needed for optional static sync)
        cursor.execute('''
            SELECT path, status FROM webbot_page
            WHERE path LIKE ? || '%'
              AND content IS NOT NULL
              AND INSTR(content, ?) > 0
        ''', (path, source))
        affected_rows = cursor.fetchall()

        if dry_run:
            result = {
                "dry_run": True,
                "message": f"Would replace '{source}' with '{replace}' in {len(affected_rows)} page(s)",
                "path_prefix": path,
                "source": source,
                "replace": replace,
                "pages_matched": total_matched,
                "pages_affected": len(affected_rows),
                "write_static": write_static,
            }
            if write_static:
                cursor.execute('''
                    SELECT COUNT(*) as n FROM webbot_page
                    WHERE path LIKE ? || '%' AND status = 'published'
                ''', (path,))
                result["sync"] = {
                    "would_sync": cursor.fetchone()["n"],
                    "scope": "all published pages under prefix",
                }
            return result

        # Perform the replacement
        cursor.execute('''
            UPDATE webbot_page
            SET content = REPLACE(content, ?, ?),
                last_modified = datetime('now')
            WHERE path LIKE ? || '%'
              AND content IS NOT NULL
              AND INSTR(content, ?) > 0
        ''', (source, replace, path, source))
        conn.commit()

        result = {
            "message": f"Replaced '{source}' with '{replace}' in {total_affected} page(s)",
            "path_prefix": path,
            "source": source,
            "replace": replace,
            "pages_matched": total_matched,
            "pages_affected": total_affected,
            "write_static": write_static,
        }

        # Optional stage 2: sync PUBLISHED pages under prefix to static files (live).
        # IMPORTANT: do NOT match on INSTR(content, source) here — after a DB-only
        # replace the old source string may already be gone, so affected=0 and the
        # static files would never be updated. The DB is the source of truth, so
        # sync re-renders ALL published pages under the prefix (idempotent).
        if write_static:
            import asyncio

            cursor.execute('''
                SELECT path FROM webbot_page
                WHERE path LIKE ? || '%' AND status = 'published'
            ''', (path,))
            sync_paths = [r["path"] for r in cursor.fetchall()]
            sem = asyncio.Semaphore(concurrency)

            async def _sync_one(p: str):
                async with sem:
                    last_err = None
                    for attempt in range(3):
                        try:
                            await publish_page(request, path=p, output_dir=None, current_user=current_user, strict=True, write_static=True)
                            return (p, None)
                        except Exception as exc:  # noqa: BLE001 - collect all failures
                            last_err = exc
                            sc = getattr(exc, "status_code", None)
                            if sc in (403, 404) or attempt == 2:
                                break
                            await asyncio.sleep(1.0 + attempt)
                    detail = getattr(last_err, "detail", None)
                    return (p, f"{type(last_err).__name__}[{getattr(last_err, 'status_code', '?')}]: {detail or last_err}")

            results = await asyncio.gather(*(_sync_one(p) for p in sync_paths))
            failed = [{"path": p, "error": err} for p, err in results if err is not None]
            result["sync"] = {
                "synced": len(sync_paths) - len(failed),
                "scope": "all published pages under prefix",
                "failed": failed,
            }

        return result

    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Batch replace failed: {e}")
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
        now = datetime.now(timezone.utc).isoformat()

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
    except HTTPException:
        conn.rollback()
        raise
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


@router.post("/publish")
async def publish_page(
    request: FastAPIRequest,
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/contact"),
    output_dir: Optional[str] = Query(None, description="Output directory for static HTML"),
    strict: bool = Query(False, description="Raise on template/datasource errors instead of degrading silently (used by publish-batch)"),
    write_static: bool = Query(True, description="Write static file via FileBot publish API (False = DB-only staged publish)"),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Publish a page: generate complete HTML with head, header, content, date-modified, and footer.
    """
    import chevron
    import asyncio
    import aiohttp

    now = datetime.now(timezone.utc)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Load the page content
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (path,))
        page = cursor.fetchone()
        if not page:
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")
        page = dict(page)

        # Permission check: verify user can write to this page
        if not user_can_write_page(current_user["id"], page["path"]):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to publish this page"
            )
        page_content = page.get("content", "")
        page_title = page.get("navigation_title") or page.get("title", "Untitled")
        page_language = page.get("language", "en")
        page_publish_template = page.get("publish_template", None)
        # 2026-08-28: publish resets last_modified to publish time (user decision:
        # re-publishing a bilingual pair keeps both pages' last_modified in sync
        # on the new date). Rendering uses the new timestamp so the published
        # HTML shows the fresh date modified.
        page_last_modified = now.isoformat()
        # Load page metadata (includes properties entered via the editor form)
        raw_metadata = page.get("metadata", {})
        if isinstance(raw_metadata, str):
            try:
                page_metadata = json.loads(raw_metadata)
            except json.JSONDecodeError:
                page_metadata = {}
        elif isinstance(raw_metadata, dict):
            page_metadata = raw_metadata
        else:
            page_metadata = {}

        # 2. Check approval
        page_approved = page.get("approved", 0)
        if not page_approved:
            raise HTTPException(
                status_code=403,
                detail=f"Page '{path}' is not approved. Approve it first before publishing."
            )
        if page_last_modified:
            if isinstance(page_last_modified, str):
                try:
                    dt = datetime.fromisoformat(page_last_modified.replace("Z", "+00:00"))
                    date_modified_str = dt.strftime("%Y-%m-%d")
                except:
                    date_modified_str = page_last_modified[:10] if len(page_last_modified) >= 10 else now.strftime("%Y-%m-%d")
            else:
                date_modified_str = now.strftime("%Y-%m-%d")
        else:
            date_modified_str = now.strftime("%Y-%m-%d")

        # 2. Build the internal API base URL
        base_url = str(request.base_url).rstrip("/")

        # Helper: render a mustache template config from DB
        async def render_mustache_template(template_path: str, data_source_path: str) -> str:
            # Substitute {path} placeholder with the current page path
            # Load config from DB
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (template_path,))
            row = cursor.fetchone()
            if not row:
                if strict:
                    raise RuntimeError(f"Template not found: {template_path}")
                return f"<!-- Template not found: {template_path} -->"
            try:
                config = json.loads(row[0])
            except json.JSONDecodeError:
                # Try extracting JSON from HTML content
                raw = row[0]
                if "{" in raw and "}" in raw:
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    try:
                        config = json.loads(raw[start:end], strict=False)
                    except:
                        if strict:
                            raise RuntimeError(f"Invalid JSON in template: {template_path}")
                        return f"<!-- Invalid JSON in template: {template_path} -->"
                else:
                    if strict:
                        raise RuntimeError(f"No JSON config in template: {template_path}")
                    return f"<!-- No JSON config in template: {template_path} -->"

            template = config.get("template", "")
            data = config.get("data", {})
            datasource = config.get("datasource", config.get("dataresource"))

            # i18n: expand {{labels.KEY[language]}} -> {{labels.KEY.<lang>}} (legacy @i18n syntax)
            _lang_parts = data_source_path.strip('/').split('/')
            lang = _lang_parts[1] if len(_lang_parts) > 1 else 'en'
            if lang not in ('en', 'fr'):
                lang = 'en'
            if isinstance(data, dict):
                data.setdefault('language', lang)
                data.setdefault('is_en', lang == 'en')
                data.setdefault('is_fr', lang == 'fr')
            template = re.sub(
                r'\{\{\s*([^{}]+?)\[(?:page\.)?language\]\s*\}\}',
                lambda m: '{{' + m.group(1) + '.' + lang + '}}',
                template
            )
            template = re.sub(
                r'\{\{\s*([^{}]+?)\[["\'](en|fr)["\']\]\s*\}\}',
                lambda m: '{{' + m.group(1) + '.' + m.group(2) + '}}',
                template
            )

            if datasource:
                # Replace {path} placeholder with the actual page being rendered
                url = datasource.replace("{path}", data_source_path)
                if not url.startswith("http"):
                    # 2026-08-28: 内部端点本机直连，不走公网
                    url = f"{LOCAL_API_BASE}{url}"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=5) as resp:
                            if resp.status == 200:
                                ds_data = await resp.json()
                                data["datasource_loaded"] = True
                                if isinstance(ds_data, dict):
                                    data = {**data, **ds_data}
                                elif isinstance(ds_data, list):
                                    data = ds_data
                                else:
                                    data["items"] = ds_data
                            else:
                                raise RuntimeError(f"Datasource HTTP {resp.status}: {url}")
                except Exception as e:
                    if strict:
                        raise RuntimeError(f"Datasource failed for {template_path} ({url}): {e}") from e
                    logger.warning(f"Datasource degraded for {template_path} ({url}): {e}")
                    data["datasource_loaded"] = False
                    data["datasource_error"] = str(e)

            try:
                return await render_mustache_tpl(template, data, cursor, lang=lang, current_path=data_source_path, base_url=base_url)
            except Exception as e:
                if strict:
                    raise RuntimeError(f"Mustache render error in {template_path}: {e}") from e
                logger.warning(f"Mustache render error in {template_path}: {e}")
                return f"<!-- Mustache render error: {e} -->"

        # 3. Render head via gethead template
        head_html = await render_mustache_template("/canadasite/mustache-templates/gethead", path)

        # 4. Render header via getheader template (legacy getheader_en/fr removed)
        header_html = await render_mustache_template("/canadasite/mustache-templates/getheader", path)

        # 5. Get footer — try institution-level first, then language-level, then site-level
        def _find_footer_publish(search_path: str) -> str:
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (search_path,))
            row = cursor.fetchone()
            if row:
                raw = row[0]
                # Strip outer <html><head><body> wrapper — DB content is stored as full HTML doc
                f_match = re.search(r'<footer[^>]*>.*?</footer>', raw, re.DOTALL | re.IGNORECASE)
                if f_match:
                    return f_match.group(0)
                b_match = re.search(r'<body[^>]*>(.*?)</body>', raw, re.DOTALL | re.IGNORECASE)
                if b_match:
                    return b_match.group(1).strip()
                return raw
            return ""

        footer_html = ""
        # Step 1: Walk up path segments to find best institution-level footer
        # e.g. /canadasite/en/auditor-general/environmental-petitions
        #   → try /canadasite/en/auditor-general/footer
        #   → try /canadasite/en/footer (skip — language level)
        #   → try /canadasite/footer
        lang_path = f"/canadasite/{page_language}/footer"
        path_parts = path.strip('/').split('/')
        for i in range(len(path_parts), 0, -1):
            candidate = f"/{'/'.join(path_parts[:i])}/footer"
            if candidate == lang_path:
                continue  # skip language-level — try a deeper institution path first
            footer_html = _find_footer_publish(candidate)
            if footer_html:
                break

        # Step 2: Fallback to language-level footer
        if not footer_html:
            footer_html = _find_footer_publish(lang_path)

        # Step 3: Fallback to site-level footer
        if not footer_html:
            site_path = "/canadasite/footer"
            footer_html = _find_footer_publish(site_path)

        # # Step 4: Fallback to extracting from raw content
        if not footer_html:
            footer_match = re.search(r'<footer[^>]*id=[\"\']wb-info[\"\'][^>]*>.*?</footer>', page_content or "", re.DOTALL | re.IGNORECASE)
            if footer_match:
                footer_html = footer_match.group(0)

        # Get contextual-footer — from /canadasite/{lang}/{institution}/contextual-footer
        contextual_footer = ""
        if len(path_parts) >= 3:
            ctx_path = f"/canadasite/{page_language}/{path_parts[2]}/contextual-footer"
            ctx_row = cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (ctx_path,)).fetchone()
            if ctx_row:
                raw = ctx_row[0]
                b_match = re.search(r'<body[^>]*>(.*?)</body>', raw, re.DOTALL | re.IGNORECASE)
                if b_match:
                    contextual_footer = b_match.group(1).strip()
                else:
                    contextual_footer = raw.strip()

        # 6. Clean page content: extract meaningful body/main content from the raw content

        # 6. Clean page content: extract meaningful body/main content from the raw content
        #    (AEM imported pages contain full HTML documents with their own <html>, <head>, <body>)
        def extract_content(raw_content: str) -> str:
            # Extract inner content of <main> tag from AEM-imported pages
            main_match = re.search(r'<main[^>]*>(.*)</main>', raw_content, re.DOTALL | re.IGNORECASE)
            if main_match:
                raw_content = main_match.group(1)
            else:
                # Fallback: extract <body> inner content
                body_match = re.search(r'<body[^>]*>(.*)</body>', raw_content, re.DOTALL | re.IGNORECASE)
                if body_match:
                    raw_content = body_match.group(1)
            # Remove any pagedetails sections (we'll add our own)
            raw_content = remove_pagedetails_sections(raw_content)
            return raw_content.strip()

        cleaned_content = extract_content(page_content)

        # 7. Build pagedetails (date-modified) section
        date_modified_html = (
            '<footer class="pagedetails container">\n'
            '    <h2 class="wb-inv">Page details</h2>\n'
            '    <div class="row">\n'
            '        <div class="col-sm-8 col-md-9 col-lg-9">\n'
            f'            <p>Date modified: {date_modified_str}</p>\n'
            '        </div>\n'
            '    </div>\n'
            '</footer>'
        )

        # 8. Assemble full HTML
        #    If page has a publish_template set, use it as a single Mustache template
        #    Otherwise, try default DB template, then hardcoded fallback

        # Helper: try to render a page template from DB
        async def render_page_template_fb(template_path, head, header, footer, content, date_modified, lang, title, page_path, header_en=None, header_fr=None, page_metadata=None, contextual_footer=""):
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (template_path,))
            tmpl_row = cursor.fetchone()
            if not tmpl_row:
                return None
            try:
                tmpl_config = json.loads(tmpl_row[0])
                tmpl = tmpl_config.get("template", tmpl_row[0])
                # Also extract template data for render context
                tmpl_data = tmpl_config.get("data", {})
                if not isinstance(tmpl_data, dict):
                    tmpl_data = {}
            except json.JSONDecodeError:
                tmpl = tmpl_row[0]
                tmpl_data = {}
                tmpl_config = {}
            render_data = {
                "content": content,
                "head": head,
                "header": header,
                "footer": footer,
                "contextual-footer": contextual_footer,
                "date_modified": date_modified,
                "language": lang,
                "title": title,
                "path": page_path,
                "header_en": header_en or header,
                "header_fr": header_fr or header,
                "is_en": lang == "en",
                "is_fr": lang == "fr",
            }
            # Merge template data into render context (properties, extension, etc.)
            render_data.update(tmpl_data)
            # Inject page context (for {{page.xxx}} and partials like {{>getheader}})
            page_ctx = {
                "path": page_path,
                "title": title,
                "language": lang,
                "other_language_url": None,
            }
            if isinstance(page_metadata, dict):
                olp = page_metadata.get("other_language_path") or page_metadata.get("other_language_url")
                if olp:
                    page_ctx["other_language_url"] = olp
            if not page_ctx["other_language_url"]:
                parts = page_path.strip("/").split("/")
                # Handle both /en/xxx and /canadasite/en/xxx path formats
                lang_idx = None
                for idx, seg in enumerate(parts):
                    if seg in ("en", "fr"):
                        lang_idx = idx
                        break
                if lang_idx is not None:
                    parts[lang_idx] = "fr" if parts[lang_idx] == "en" else "en"
                    page_ctx["other_language_url"] = "/" + "/".join(parts)
            render_data["page"] = page_ctx
            # Load template datasource so partials like {{>getheader}} get parents/page/header/megamenu context
            tmpl_ds = tmpl_config.get("datasource", tmpl_config.get("dataresource"))
            if tmpl_ds and isinstance(tmpl_ds, str) and tmpl_ds.strip():
                ds_url = tmpl_ds.replace("{path}", page_path)
                if not ds_url.startswith("http"):
                    # 2026-08-28: 内部端点本机直连，不走公网
                    ds_url = f"{LOCAL_API_BASE}{ds_url}"
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(ds_url, timeout=5) as resp:
                            if resp.status == 200:
                                ds_data = await resp.json()
                                if isinstance(ds_data, dict):
                                    render_data = {**render_data, **ds_data}
                                elif isinstance(ds_data, list):
                                    render_data["items"] = ds_data
                except Exception as e:
                    print(f"调试: 页面模板datasource加载失败: {tmpl_ds} - {str(e)}")
            # Merge page metadata into render context (includes properties entered via form)
            if page_metadata and isinstance(page_metadata, dict):
                # Put raw metadata fields at top level (for mustache access)
                if page_metadata.get("properties"):
                    render_data["page_properties"] = page_metadata["properties"]
                if page_metadata.get("file_path"):
                    render_data["file_path"] = page_metadata["file_path"]
                if page_metadata.get("redirect_to"):
                    render_data["redirect_to"] = page_metadata["redirect_to"]
                if page_metadata.get("has_feedback") is not None:
                    render_data["has_feedback"] = page_metadata["has_feedback"]
                # Also pass full metadata as 'metadata' for template use
                render_data["metadata"] = page_metadata
            # NEW (2026-08-19): render page content as a Mustache template too, so dynamic
            # blocks ({{>template?path=.}}, datasource, {{labels...}}) work inside page content.
            content = _unescape_mustache_entities(content)
            if content and "{{" in content:
                _content_ctx = {k: v for k, v in render_data.items() if k != "content"}
                try:
                    content = await render_mustache_tpl(content, _content_ctx, cursor, lang=lang, current_path=page_path, base_url=base_url)
                    render_data["content"] = content
                except Exception as e:
                    if strict:
                        raise RuntimeError(f"Content mustache render error in {page_path}: {e}") from e
                    logger.warning(f"Content mustache render degraded for {page_path}: {e}")
            # 2026-08-28: 修复重复渲染 —— 同一模板只渲染一次
            return await render_mustache_tpl(tmpl, render_data, cursor, lang=lang, current_path=page_path, base_url=base_url)

        full_html = None
        publish_ext = ".html"  # default extension

        # Helper to render a template AND extract extension from its config
        async def render_and_get_ext(template_path, *args, **kwargs):
            # Load template config to check for extension field
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (template_path,))
            tmpl_row = cursor.fetchone()
            ext = ".html"
            if tmpl_row:
                try:
                    tmpl_config = json.loads(tmpl_row[0])
                    # Check extension in data dict (user's "static data") or top-level config
                    data = tmpl_config.get("data", {})
                    if isinstance(data, dict):
                        ext = data.get("extension", tmpl_config.get("extension", ".html"))
                    else:
                        ext = tmpl_config.get("extension", ".html")
                    if not ext.startswith("."):
                        ext = f".{ext}"
                except (json.JSONDecodeError, Exception):
                    pass
            html = await render_page_template_fb(template_path, *args, **kwargs)
            # Also load page metadata properties into render_and_get_ext's return if template has properties
            # (properties are already handled inside render_page_template_fb via page_metadata param)
            return html, ext

        # 0) Redirect: if page has redirect_to set, use redirect template
        if page_metadata.get("redirect_to"):
            full_html, publish_ext = await render_and_get_ext(
                "/canadasite/mustache-templates/page-template/redirect-template", head_html, header_html, footer_html,
                cleaned_content, date_modified_str, page_language, page_title, path,
                page_metadata=page_metadata,
                contextual_footer=contextual_footer
            )

        # 1) Try per-page publish_template
        if not full_html and page_publish_template:
            full_html, publish_ext = await render_and_get_ext(
                page_publish_template, head_html, header_html, footer_html,
                cleaned_content, date_modified_str, page_language, page_title, path,
                page_metadata=page_metadata,
                contextual_footer=contextual_footer
            )

        # 2) Try default language-specific template from DB
        if not full_html:
            full_html, publish_ext = await render_and_get_ext(
                "/canadasite/mustache-templates/page-template", head_html, header_html, footer_html,
                cleaned_content, date_modified_str, page_language, page_title, path,
                page_metadata=page_metadata,
                contextual_footer=contextual_footer
            )

        # 3) Ultimate hardcoded fallback
        if not full_html:
            full_html = (
                "<!DOCTYPE html>\n"
                f"<html lang=\"{page_language}\">\n"
                f"{head_html}\n"
                f"{header_html}\n"
                "<body>\n"
                '<main property="mainContentOfPage" resource="#wb-main" typeof="WebPageElement" class="container">\n'
                f"{cleaned_content}\n"
                f"{date_modified_html}\n"
                "</main>\n"
                f"{footer_html}\n"
                "</body>\n"
                "</html>"
            )
            publish_ext = ".html"

        # Inject AnalyBot tracking SDK before </head>
        # Config is external (analy-config.js) so changes don't require republishing
        analybot_sdk = '''<script src="/etc/designs/canada/analytics/analy-config.js" defer></script>
<script src="/etc/designs/canada/analytics/analy_v2.js" defer></script>'''
        full_html = full_html.replace('</head>', analybot_sdk + '\n</head>', 1) if full_html else full_html

        # NOTE: clientlib-base.min.css (Adobe AEM artifact) is intentionally NOT injected.

        # Cache-bust theme.min.css (v19.1.0 -> v19.4.0; Cloudflare/browser may hold the old one)
        # Versioned URL = new cache key, guarantees visitors get the updated stylesheet
        full_html = full_html.replace('css/theme.min.css"', 'css/theme.min-20260801.css"') if full_html else full_html

        # Batch path rewrite for published static files:
        #   /content/canadasite/ -> /
        #   /canadasite/ -> /
        # Published site root == canadasite site root, so internal links must be root-relative.
        # Order matters: longest prefix first, so /content/canadasite/ is not mangled.
        if full_html:
            full_html = full_html.replace('/content/canadasite/', '/')
            full_html = full_html.replace('/canadasite/', '/')

        # 9. Save to FileBot publish directory via FileBot API
        # 调用FileBot的publish app接口来写入发布文件
        # Staged publish (write_static=False): DB-only — static files are LIVE, so AI batch
        # publish goes to the DB first, gets verified on prod.webfilebot.com/en.. (dynamic
        # render), and only then is synced to static files with write_static=True.
        output_file = ""
        if write_static:
            # FileBot backend (8001) runs uvicorn --limit-max-requests 120: workers
            # rotate after 120 requests, which briefly drops connections. Retry a
            # few times so a rotation window does not fail the user's publish.
            filebot_publish_url = "http://localhost:8001/api/v1/pages/publish"
            fb_params = {"path": path, "extension": publish_ext}
            if output_dir:
                fb_params["output_dir"] = output_dir
            last_fb_err: Optional[Exception] = None
            for attempt in range(1, 4):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            filebot_publish_url,
                            params=fb_params,
                            json={"html_content": full_html, "title": page_title},
                            headers={"X-WebBot-Access": "true"},
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as fb_resp:
                            if fb_resp.status != 200:
                                fb_error = await fb_resp.text()
                                logger.error(f"FileBot publish failed ({fb_resp.status}): {fb_error}")
                                raise HTTPException(
                                    status_code=502,
                                    detail=f"FileBot publish failed: {fb_error}"
                                )
                            fb_result = await fb_resp.json()
                            output_file = fb_result.get("output_file", "")
                            break
                except (aiohttp.ClientConnectionError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as e:
                    last_fb_err = e
                    logger.warning(f"FileBot publish attempt {attempt}/3 failed: {e}; retrying in {attempt}s...")
                    await asyncio.sleep(attempt)
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"FileBot publish failed after 3 attempts: {last_fb_err}"
                )

        # 10. Save version snapshot (非阻塞)
        try:
            from .. import versioning
            version = versioning.get_next_version(path)
            versioning.save_version(
                page_path=path,
                content=cleaned_content,  # 只存页面正文，不含 header/footer
                page_id=page["id"],
                page_title=page_title,
                page_language=page_language,
                version=version,
                author=page.get("created_by", "system"),
                notes=f"Published via WebBot"
            )
            # 更新 DB 版本号
            cursor.execute(
                "UPDATE webbot_page SET current_version = ? WHERE path = ?",
                (version, path)
            )
        except Exception as ve:
            logger.error(f"Version snapshot failed (non-fatal): {ve}")

        # 11. Update page status to "published". 2026-08-28: publish also resets
        # last_modified to the publish timestamp (user decision) so that
        # re-publishing a bilingual pair puts both pages on the same new date
        # and the Out-of-Sync badge clears. The twin page keeps its own
        # last_published untouched (it is updated when the twin is published).
        publish_ts = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE webbot_page SET status = 'published', last_published = ?, last_modified = ? WHERE path = ?",
            (publish_ts, now.isoformat(), path)
        )
        # AI-search incremental index: page truly published → queue for indexing
        _mark_ai_index_pending(conn, path)
        conn.commit()

        return {
            "success": True,
            "path": path,
            "output_file": output_file,
            "date_modified": date_modified_str,
            "published_at": publish_ts,
            "html_length": len(full_html)
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Publish failed: {str(e)}")
    finally:
        conn.close()


@router.post("/publish-batch", response_model=Dict[str, Any])
async def publish_batch(
    request: FastAPIRequest,
    lang: str = Query("both", description="Language filter: en, fr, or both"),
    prefix: str = Query("/canadasite", description="Publish all pages under this path prefix"),
    status: str = Query("published", description="Page status to republish (e.g. published, draft)"),
    dry_run: bool = Query(False, description="Only count pages without publishing"),
    concurrency: int = Query(8, ge=1, le=50, description="Max parallel publishes"),
    write_static: bool = Query(True, description="Write static files (True) or DB-only staged publish (False)"),
    current_user: dict = Depends(get_current_active_user),
):
    """Batch republish: all pages with a given status under a prefix (e.g. after shared header/footer changes).

    Reuses publish_page for every page so single-page behaviour stays identical.
    Only pages with status matching the `status` param are published (default: published).
    Pages with hide_in_navigation=true are skipped.
    Returns per-page failures so they can be inspected and retried.
    """
    import asyncio

    conn = get_db_connection()
    try:
        base = prefix.rstrip("/")
        if lang in ("en", "fr"):
            base = base + "/" + lang
        rows = conn.execute(
            "SELECT path FROM webbot_page WHERE status = ? AND COALESCE(hide_in_navigation, 0) != 1 AND (path = ? OR path LIKE ?)",
            (status, base, base + "/%"),
        ).fetchall()
        paths = [r["path"] for r in rows]
    finally:
        conn.close()

    total = len(paths)
    if dry_run:
        return {"dry_run": True, "total": total, "success": 0, "failed": []}

    sem = asyncio.Semaphore(concurrency)

    async def _publish_one(path: str):
        async with sem:
            last_err = None
            for attempt in range(3):
                try:
                    await publish_page(request, path=path, output_dir=None, current_user=current_user, strict=True, write_static=write_static)
                    return (path, None)
                except Exception as exc:  # noqa: BLE001 - collect all failures for the report
                    last_err = exc
                    sc = getattr(exc, "status_code", None)
                    if sc in (403, 404) or attempt == 2:
                        break
                    await asyncio.sleep(1.0 + attempt)  # backoff before retry
            detail = getattr(last_err, "detail", None)
            return (path, f"{type(last_err).__name__}[{getattr(last_err, 'status_code', '?')}]: {detail or last_err}")

    results = await asyncio.gather(*(_publish_one(p) for p in paths))
    failed = [{"path": p, "error": err} for p, err in results if err is not None]
    return {"dry_run": False, "total": total, "success": total - len(failed), "failed": failed, "write_static": write_static}


@router.post("/unpublish")
async def unpublish_page(
    request: FastAPIRequest,
    path: str = Query(..., description="Full page path, e.g. /canadasite/en/canadian-heritage"),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Unpublish a page: forward to FileBot to delete from /publish folder.
    """
    import aiohttp

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Permission check: verify user can write to this page before unpublishing
        if not user_can_write_page(current_user["id"], path):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to unpublish this page: {path}"
            )

        # 1. Forward to FileBot to delete the published file
        filebot_unpublish_url = "http://localhost:8001/api/v1/pages/unpublish"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                filebot_unpublish_url,
                params={"path": path},
                headers={"X-WebBot-Access": "true"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as fb_resp:
                if fb_resp.status != 200:
                    fb_error = await fb_resp.text()
                    logger.error(f"FileBot unpublish failed ({fb_resp.status}): {fb_error}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"FileBot unpublish failed: {fb_error}"
                    )
                fb_result = await fb_resp.json()

        # 2. Update WebBot page status to draft
        cursor.execute(
            "UPDATE webbot_page SET status = 'draft', last_published = NULL WHERE path = ?",
            (path,)
        )
        conn.commit()

        return {
            "success": True,
            "path": path,
            "file_deleted": fb_result.get("file_deleted", False),
            "db_updated": fb_result.get("db_updated", False),
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unpublish failed: {str(e)}")
    finally:
        conn.close()


@router_v1.post("/pages/move")
async def move_page(
    request: FastAPIRequest,
    path: str = Query(..., description="Current full page path, e.g. /canadasite/en/some-page"),
    new_parent_path: str = Query(None, description="New parent path, e.g. /canadasite/en/new-parent. Use empty or omit for root level."),
    new_name: str = Query(None, description="New page slug/name (optional). Defaults to current slug if omitted."),
    new_title: str = Query(None, description="New page title (optional). Leaves unchanged if omitted."),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Move a page to a new parent. Updates:
    - Page's own path and parent_path
    - Page title and slug/name if provided
    - All descendant pages' path and parent_path
    - other_language_path references to moved pages
    - Stores original_path in metadata
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Validate source page exists
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (path,))
        page = cursor.fetchone()
        if not page:
            raise HTTPException(status_code=404, detail=f"Page not found: {path}")

        # Permission check: verify user can write to this page
        if not user_can_write_page(current_user["id"], page["path"]):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to move this page"
            )

        # 2. Validate new parent exists (unless moving to root)
        if new_parent_path:
            new_parent_path = normalize_path(new_parent_path)
            if new_parent_path == path:
                raise HTTPException(status_code=400, detail="New parent path cannot be the same as the page path")
            cursor.execute("SELECT path FROM webbot_page WHERE path = ?", (new_parent_path,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Parent page not found: {new_parent_path}")

        old_path = normalize_path(path)
        page_id = new_name if new_name else old_path.rstrip('/').split('/')[-1]

        # 3. Calculate new path
        if new_parent_path:
            new_path = f"{new_parent_path.rstrip('/')}/{page_id}"
        else:
            new_path = f"/{page_id}"

        # 4. Validate no page exists at new path
        cursor.execute("SELECT path FROM webbot_page WHERE path = ?", (new_path,))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail=f"Target path already exists: {new_path}")

        # 5. Don't allow moving a page under itself
        if new_path.startswith(old_path.rstrip('/') + '/') or new_path == old_path:
            raise HTTPException(status_code=400, detail="Cannot move a page under itself")

        # 6. Store original path in metadata
        metadata = {}
        if page['metadata']:
            try:
                metadata = json.loads(page['metadata'])
            except json.JSONDecodeError:
                metadata = {}

        # Preserve existing metadata, add/update original_path
        metadata['original_path'] = old_path

        # 7. Update the page itself: path, parent_path, title (optional), metadata
        if new_title:
            cursor.execute("""
                UPDATE webbot_page
                SET id = ?, path = ?, parent_path = ?, title = ?, metadata = ?, last_modified = CURRENT_TIMESTAMP
                WHERE path = ?
            """, (new_path, new_path, new_parent_path, new_title, json.dumps(metadata), old_path))
        else:
            cursor.execute("""
                UPDATE webbot_page
                SET id = ?, path = ?, parent_path = ?, metadata = ?, last_modified = CURRENT_TIMESTAMP
                WHERE path = ?
            """, (new_path, new_path, new_parent_path, json.dumps(metadata), old_path))

        # 8. Recursively update all children's paths and parent_paths
        _rebuild_subtree_paths_and_parents(cursor, old_path, new_path)

        # 9. Update other_language_path references to moved pages
        _update_other_language_paths(cursor, old_path, new_path)

        # 10. Update page_references table (source_path + target_path)
        try:
            from app.services.references import move_references
            move_references(old_path, new_path)
        except Exception as ref_err:
            print(f"⚠️  Reference move failed for {old_path} -> {new_path}: {ref_err}", file=__import__('sys').stderr)

        conn.commit()

        return {
            "success": True,
            "old_path": old_path,
            "new_path": new_path,
            "new_parent_path": new_parent_path,
            "new_title": new_title if new_title else page['title'],
            "new_name": page_id,
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Move failed: {str(e)}")
    finally:
        conn.close()


def _rebuild_subtree_paths_and_parents(cursor, old_root: str, new_root: str):
    """
    Recursively update child page paths and parent_paths after a move.
    Processes one level of depth per call.
    """
    cursor.execute("""
        SELECT path, parent_path FROM webbot_page
        WHERE path LIKE ? || '/%'
          AND instr(substr(path, length(?) + 2), '/') = 0
    """, (old_root, old_root))
    children = cursor.fetchall()

    for child in children:
        child_path = child['path']
        suffix = child_path[len(old_root):]
        new_child_path = new_root + suffix

        cursor.execute("""
            UPDATE webbot_page
            SET id = ?, path = ?, parent_path = ?, last_modified = CURRENT_TIMESTAMP
            WHERE path = ?
        """, (new_child_path, new_child_path, new_root, child_path))

        # Recurse into grand-children
        _rebuild_subtree_paths_and_parents(cursor, child_path, new_child_path)


def _update_other_language_paths(cursor, old_prefix: str, new_prefix: str):
    """
    Update other_language_path references that pointed to any moved page.
    Handles both exact matches and path prefix matches.
    """
    # Exact match: other_language_path == old_prefix
    cursor.execute("""
        UPDATE webbot_page
        SET other_language_path = ?, last_modified = CURRENT_TIMESTAMP
        WHERE other_language_path = ?
    """, (new_prefix, old_prefix))

    # Prefix match: other_language_path starts with old_prefix + '/'
    cursor.execute("""
        UPDATE webbot_page
        SET other_language_path = ? || substr(other_language_path, length(?) + 1),
            last_modified = CURRENT_TIMESTAMP
        WHERE other_language_path LIKE ? || '/%'
    """, (new_prefix, old_prefix, old_prefix))


@router_v1.get("/getfooter")
async def get_footer_v2(path: str = ""):
    """
    Get footer content split into institution-level and language-level pages.

    Query pattern:
      - language_level:  /{site}/{language}/footer     (e.g. /canadasite/en/footer)
      - institution_level: /{site}/footer               (e.g. /canadasite/footer)

    Returns:
    ```json
    {
      "institution_level": { "content": "...", "path": "/canadasite/en/revenue-agency/footer" },
      "language_level":   { "content": "...", "path": "/canadasite/en/footer" }
    }
    ```
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        normalized_path = normalize_path(path) if path else ""
        language = extract_language_from_path(normalized_path)
        parts = normalized_path.strip('/').split('/') if normalized_path else []
        # First part is always the site name
        site_name = parts[0] if parts else ""

        # Language-level footer: always /{site}/{language}/footer
        language_path = f"/{site_name}/{language}/footer" if site_name and language else ""

        def clean_footer_content(raw_content: str) -> str:
            """Strip <html><head><body> wrapper AND the outer <footer> tag.
            The Mustache template provides the <footer id="wb-info"> wrapper,
            so we only return the inner div sections."""
            m = re.search(r'<footer[^>]*id=[\"\']wb-info[\"\'][^>]*>(.*?)</footer>', raw_content, re.DOTALL | re.IGNORECASE)
            if m:
                return m.group(1).strip()
            m = re.search(r'<body[^>]*>(.*)</body>', raw_content, re.DOTALL | re.IGNORECASE)
            if m:
                return m.group(1).strip()
            return raw_content

        def fetch_footer(search_path: str):
            cursor.execute("SELECT path, content FROM webbot_page WHERE path = ?", (search_path,))
            row = cursor.fetchone()
            if row:
                return {"path": row["path"], "content": clean_footer_content(row["content"])}
            return None

        # Institution-level footer: walk up from {path}/footer, excluding the language-level path
        # For /canadasite/en/revenue-agency:
        #   try /canadasite/en/revenue-agency/footer -> FOUND (institution)
        #   skip /canadasite/en/footer (language level)
        # For /canadasite/en:
        #   skip /canadasite/en/footer (language level)
        #   try /canadasite/footer -> EMPTY
        institution_level = {"path": "", "content": ""}
        if normalized_path:
            # Walk up the path building candidate footer paths
            current = normalized_path.strip('/')
            segments = current.split('/')  # e.g. ['canadasite', 'en', 'revenue-agency']
            for i in range(len(segments), 0, -1):
                candidate = '/' + '/'.join(segments[:i]) + '/footer'
                if candidate == language_path:
                    continue  # skip — this is the language level
                result = fetch_footer(candidate)
                if result:
                    institution_level = result
                    break

        language_level = {"path": "", "content": ""}
        if language_path:
            result = fetch_footer(language_path)
            if result:
                language_level = result

        return {
            "institution_level": institution_level,
            "language_level": language_level
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    finally:
        conn.close()


@router.post("/batch-fix-other-lang-paths", response_model=dict)
@router_v1.post("/pages/batch-fix-other-lang-paths", response_model=dict)
async def batch_fix_other_lang_paths(current_user: dict = Depends(get_current_active_user)):
    """
    Batch fix all pages where other_language_path IS NULL but content has #wb-lng.
    Parses the language switcher section to extract the alternate language path.
    """
    class _WbLngParser(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.alt_href = None
            self.alt_lang = None
            self._in_wb_lng = False
            self._depth = 0

        def handle_starttag(self, tag, attrs):
            d = dict(attrs)
            if tag == 'section' and d.get('id') == 'wb-lng':
                self._in_wb_lng = True
                self._depth = 1
                return
            if self._in_wb_lng:
                if tag == 'section':
                    self._depth += 1
                if tag == 'a' and d.get('lang') in ('fr', 'en'):
                    self.alt_href = d.get('href', '')
                    self.alt_lang = d.get('lang')

        def handle_endtag(self, tag):
            if self._in_wb_lng:
                if tag == 'section':
                    self._depth -= 1
                    if self._depth == 0:
                        self._in_wb_lng = False

    def _extract_path(html_content, page_path):
        if not html_content:
            return None
        p = _WbLngParser()
        try:
            p.feed(html_content)
        except Exception:
            return None
        if p.alt_href and p.alt_lang:
            # Only accept a link to the OTHER language (never the page's own language / own path)
            page_lang = page_path.split('/')[2] if page_path.startswith('/canadasite/') else None
            if p.alt_lang == page_lang:
                return None
            href = urllib.parse.urlparse(p.alt_href).path.rstrip('/')
            if href.endswith('.html'):
                href = href[:-5]
            alt_path = f'/canadasite{href}'
            if alt_path == page_path:
                return None
            return alt_path
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT path, content FROM webbot_page WHERE other_language_path IS NULL AND content IS NOT NULL AND content != ''"
        )
        rows = cursor.fetchall()

        fixed = []
        errors = []

        for row in rows:
            path = row['path']
            content = row['content']
            try:
                alt_path = _extract_path(content, path)
                if alt_path:
                    cursor.execute(
                        "UPDATE webbot_page SET other_language_path = ?, last_modified = datetime('now') WHERE path = ?",
                        (alt_path, path)
                    )
                    fixed.append({"path": path, "other_language_path": alt_path})
                else:
                    errors.append({"path": path, "reason": "no wb-lng link found"})
            except Exception as e:
                errors.append({"path": path, "error": str(e)})

        conn.commit()

        return {
            "status": "ok",
            "total_scanned": len(rows),
            "fixed": len(fixed),
            "errors": len(errors),
            "details": {
                "fixed": fixed[:50],
                "errors": errors[:20],
            }
        }
    except Exception as e:
        logger.error(f"batch_fix_other_lang_paths failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


