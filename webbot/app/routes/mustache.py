"""
Mustache template rendering routes
Supports rendering from page configuration and loading static templates
"""
from fastapi import APIRouter, HTTPException, Request, Form, Query
from fastapi.responses import Response, HTMLResponse
import sqlite3
import json
import os
import re
import traceback
import urllib.parse
from typing import Optional

router = APIRouter(prefix="", tags=["mustache"])

# 数据库路径
WEBBOT_DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)

# mustache 渲染输出大小限制（默认 20MB）
# 环境变量 MUSTACHE_MAX_OUTPUT_SIZE_BYTES 可覆盖
MUSTACHE_MAX_OUTPUT_SIZE_BYTES = int(os.environ.get(
    "MUSTACHE_MAX_OUTPUT_SIZE_BYTES",
    20 * 1024 * 1024  # 20MB
))

# Mustache template文件目录
MUSTACHE_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..",
    "frontend",
    "mustache-templates"
)

# {{{>partial}}} 引用解析（Mustache partials）
PARTIAL_RE = re.compile(r"\{\{\s*>\s*([^}]+?)\s*\}\}")
PARTIAL_MAX_DEPTH = 10

# i18n 动态 key 展开（与 pages.py render_mustache_template 一致）
#   {{labels.KEY[page.language]}} -> {{labels.KEY.en}}
#   {{labels.KEY['fr']}}          -> {{labels.KEY.fr}}
_I18N_LANG_RE = re.compile(r"\{\{\s*([^{}]+?)\[(?:page\.)?language\]\s*\}\}")
_I18N_LITERAL_RE = re.compile(r'\{\{\s*([^{}]+?)\[["\'](en|fr)["\']\]\s*\}\}')

def _infer_lang(data) -> str:
    """从渲染数据推断语言（en/fr），默认 en。datasource 返回 list 时 data 可能是 list，安全降级。"""
    if isinstance(data, dict):
        for src in (data, data.get("page") or {}, data.get("language_level") or {}):
            lang = src.get("language") if isinstance(src, dict) else None
            if lang in ("en", "fr"):
                return lang
    return "en"


def expand_i18n_keys(template: str, lang: str) -> str:
    """把 legacy @i18n 动态 key 语法展开为 chevron 支持的点号路径。"""
    template = _I18N_LANG_RE.sub(lambda m: "{{" + m.group(1) + "." + lang + "}}", template)
    template = _I18N_LITERAL_RE.sub(
        lambda m: "{{" + m.group(1) + "." + m.group(2) + "}}", template
    )
    return template


def _enrich_label_fields(ctx: dict) -> None:
    """数据层自动查表：labels.{field} 是 dict 且数据行有同名 field → 每行注入 {field}_label。

    mustache 不支持动态键（{{labels.status[status]}} 会把 [status] 当字面 key），
    查表在数据层完成：{{status_label}} 直接可用。
    """
    labels = ctx.get("labels")
    data = ctx.get("data")
    if not isinstance(labels, dict) or not isinstance(data, list):
        return
    for field, mapping in labels.items():
        if not isinstance(mapping, dict):
            continue
        for row in data:
            if isinstance(row, dict) and field in row:
                v = row[field]
                if isinstance(v, (str, int)):
                    row[f"{field}_label"] = mapping.get(v, v)


_DYN_ROW_KEY_RE = re.compile(
    r"\{\{\s*labels\.([A-Za-z_][A-Za-z0-9_]*)\[([A-Za-z_][A-Za-z0-9_]*)\]\s*\}\}"
)


def _expand_row_dynamic_keys(template: str, ctx: dict) -> str:
    """把 {{labels.M[F]}} 动态键展开：F 是数据行字段（渲染前未知，如 status）。

    [page.language] 类由 expand_i18n_keys 在渲染前展开（已知 lang）；
    行字段动态键在数据层展开：每行注入 __dyn_M_F = labels.M.get(row[F], row[F])，
    模板替换为 {{__dyn_M_F}}，chevron 在行上下文直接命中。
    """
    pairs = set(_DYN_ROW_KEY_RE.findall(template))
    if not pairs:
        return template
    labels = ctx.get("labels")
    data = ctx.get("data")
    if isinstance(labels, dict) and isinstance(data, list):
        for mapping_name, row_field in pairs:
            mapping = labels.get(mapping_name)
            if not isinstance(mapping, dict):
                continue
            for row in data:
                if isinstance(row, dict) and row_field in row:
                    v = row[row_field]
                    if isinstance(v, (str, int)):
                        row[f"__dyn_{mapping_name}_{row_field}"] = mapping.get(v, v)
    return _DYN_ROW_KEY_RE.sub(
        lambda m: "{{__dyn_%s_%s}}" % (m.group(1), m.group(2)), template
    )


def resolve_partial_config(name: str, cursor) -> Optional[dict]:
    """按 partial 名从 DB 加载 mustache 模板页的完整配置（template/datasource/data）。

    解析约定：
      {{>header}}                        -> /canadasite/mustache-templates/header
      {{>header/logo}}                   -> /canadasite/mustache-templates/header/logo
      {{>mustache-templates/header}}     -> /canadasite/mustache-templates/header
      {{>/canadasite/mustache-templates/header}} -> 绝对路径原样使用
      {{>getheader?path=.}}              -> 查询参数（?path=...）不参与路径匹配，
                                            由 render_template 解析注入 partial 上下文
    返回配置 dict（含 template 字段）或 None。
    """
    name = name.strip().strip("/")
    # 查询参数（?path=...）仅用于传参，不参与路径解析
    name = name.split("?", 1)[0].strip().strip("/")
    if not name:
        return None
    variants = []
    if name.startswith("canadasite/"):
        variants.append(f"/{name}")
    elif name.startswith("mustache-templates/"):
        variants.append(f"/canadasite/{name}")
    else:
        variants.append(f"/canadasite/mustache-templates/{name}")
        # 兼容裸名子路径
        variants.append(f"/canadasite/mustache-templates/{name}")
    for pv in variants:
        try:
            cursor.execute("SELECT content FROM webbot_page WHERE path = ?", (pv,))
            row = cursor.fetchone()
        except Exception:
            return None
        if not row:
            continue
        raw = row[0] if isinstance(row, (dict, sqlite3.Row)) else row[0]
        if not raw:
            continue
        try:
            cfg = json.loads(raw, strict=False)
        except json.JSONDecodeError:
            # 容错：从 HTML 内容里提取 JSON
            if "{" in raw and "}" in raw:
                try:
                    cfg = json.loads(raw[raw.find("{"):raw.rfind("}") + 1], strict=False)
                except json.JSONDecodeError:
                    continue
            else:
                continue
        if isinstance(cfg, dict) and cfg.get("template"):
            return cfg
    return None


def resolve_partial_template(name: str, cursor) -> Optional[str]:
    """按 partial 名从 DB 加载 mustache 模板页的 template 字段（完整配置见 resolve_partial_config）。"""
    cfg = resolve_partial_config(name, cursor)
    return cfg["template"] if cfg else None


def build_partials_dict(template: str, cursor, _seen=None, _depth: int = 0, lang: str = "en") -> dict:
    """递归扫描模板中的 {{>name}} 引用，构建 chevron partials_dict。

    支持 partial 嵌套 partial（深度上限 PARTIAL_MAX_DEPTH 防循环）。
    每个 partial 模板都做 i18n 动态 key 展开（{{labels.X[page.language]}}）。
    """
    if _depth > PARTIAL_MAX_DEPTH:
        return {}
    if _seen is None:
        _seen = set()
    partials = {}
    for name in PARTIAL_RE.findall(template):
        name = name.strip()
        if not name or name in _seen:
            continue
        sub_tpl = resolve_partial_template(name, cursor)
        if sub_tpl is None:
            continue
        _seen.add(name)
        partials[name] = expand_i18n_keys(sub_tpl, lang)
        nested = build_partials_dict(sub_tpl, cursor, _seen, _depth + 1, lang)
        partials.update(nested)
    return partials


async def _render_param_partials(template: str, data: dict, cursor, lang: str,
                                 current_path: Optional[str], _depth: int = 0,
                                 request: Optional[Request] = None,
                                 base_url: Optional[str] = None) -> str:
    """预渲染 partial 调用：带参数 {{>name?path=...}} 或带 datasource 的无参 {{>name}}。

    无参数且无 datasource 的 {{>name}} 留给 chevron partials_dict 处理（继承父上下文）；
    带参数的 {{>name?path=.}} 视为组件调用：解析参数（. = 当前页面路径，
    .. = 父级路径），加载 partial 完整配置（template/datasource/data），
    datasource URL 中的 {path}/{参数名} 占位符替换为传入参数后拉取数据，
    与 data + 参数合并为上下文递归渲染后替换进模板。
    无参数但配置了 datasource 的 {{>name}} 同样预渲染：{path} 占位符默认取当前页面路径。
    找不到的 partial 渲染为空。
    """
    if _depth > PARTIAL_MAX_DEPTH:
        return template
    out = []
    last = 0
    for m in PARTIAL_RE.finditer(template):
        out.append(template[last:m.start()])
        ref = m.group(1).strip()
        base, sep, qs = ref.partition("?")
        if not sep:
            # 无参 partial：有 datasource 配置则预渲染（自动拉数据），否则交给 chevron
            _cfg = resolve_partial_config(base, cursor)
            _ds = (_cfg or {}).get("datasource") or (_cfg or {}).get("dataresource")
            if _cfg is not None and _ds and isinstance(_ds, str) and _ds.strip():
                out.append(await _render_param_partial(base, {}, data, cursor, lang,
                                                       current_path, _depth, request, base_url))
            else:
                out.append(m.group(0))  # 普通 partial，交给 chevron
        else:
            params = dict(urllib.parse.parse_qsl(qs))
            p = (params.get("path") or "").replace(" ", "")
            if p in (".", "./", "self"):
                params["path"] = current_path or ""
            elif p == "..":
                # 父级路径：去掉当前路径最后一段
                base_p = (current_path or "").strip("/")
                if base_p:
                    parts = base_p.split("/")
                    params["path"] = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
                else:
                    params["path"] = ""
            else:
                params["path"] = p
            out.append(await _render_param_partial(base, params, data, cursor, lang,
                                                   current_path, _depth, request, base_url))
        last = m.end()
    out.append(template[last:])
    return "".join(out)


async def _render_param_partial(base: str, params: dict, data: dict, cursor, lang: str,
                                current_path: Optional[str], _depth: int,
                                request: Optional[Request],
                                base_url: Optional[str]) -> str:
    """渲染单个带参数 partial：完整配置 + datasource（参数替换占位符后拉取）+ 上下文合并。"""
    import chevron
    import aiohttp
    cfg = resolve_partial_config(base, cursor)
    if cfg is None:
        return ""
    sub_tpl = expand_i18n_keys(cfg.get("template", ""), lang)
    if isinstance(data, dict):
        ctx = {**data, **params}
    else:
        # 顶层 datasource 返回 list 时 data 可能是 list（{{#.}} 迭代语义）：
        # 不展开 list，保留参数，list 放进 items 供 partial 使用
        ctx = {**params}
        if isinstance(data, list):
            ctx["items"] = data
    cfg_data = cfg.get("data")
    if isinstance(cfg_data, dict):
        ctx = {**ctx, **cfg_data}
    # datasource：{path}/{参数名} 占位符替换为传入参数后拉取
    ds = cfg.get("datasource", cfg.get("dataresource"))
    if ds and isinstance(ds, str) and ds.strip():
        try:
            url = ds
            # {path} 占位符：显式参数优先，否则默认当前页面路径（与顶层 datasource 行为一致）
            replace_map = dict(params)
            if "path" not in replace_map:
                replace_map["path"] = current_path or ""
            for k, v in replace_map.items():
                url = url.replace("{" + k + "}", str(v))
            if not url.startswith("http"):
                if request is not None:
                    base_url = str(request.base_url).rstrip("/")
                url = f"{base_url or ''}{url}"
            ds_data = None
            parsed = urllib.parse.urlparse(url)
            # 本地 /api/v1/pages/ 端点直查 SQL（跳过 HTTP + 认证）
            if parsed.path.startswith("/api/v1/pages/") or parsed.path == "/api/v1/pages":
                ds_data = _query_local_api(parsed.path, urllib.parse.parse_qs(parsed.query), cursor)
            if ds_data is not None:
                ctx["datasource_loaded"] = True
                ctx["datasource_raw"] = ds_data
                if isinstance(ds_data, dict):
                    ctx = {**ctx, **ds_data}
                else:
                    ctx["items"] = ds_data
            else:
                # 远程/其他端点：HTTP 拉取，透传 Authorization
                headers = {}
                if request is not None:
                    auth_header = request.headers.get("Authorization")
                    if auth_header:
                        headers["Authorization"] = auth_header
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=10) as resp:
                        if resp.status == 200:
                            ds_data = await resp.json()
                            ctx["datasource_loaded"] = True
                            ctx["datasource_raw"] = ds_data
                            if isinstance(ds_data, dict):
                                ctx = {**ctx, **ds_data}
                            else:
                                ctx["items"] = ds_data
                        else:
                            raise RuntimeError(f"Datasource HTTP {resp.status}: {url}")
        except Exception as e:
            ctx["datasource_loaded"] = False
            ctx["datasource_error"] = str(e)
    # 数据层自动查表：labels.{field} dict + 行内同名 field → {field}_label
    _enrich_label_fields(ctx)
    # 行字段动态键 {{labels.M[F]}} → 数据层展开（partial 自带 ctx）
    sub_tpl = _expand_row_dynamic_keys(sub_tpl, ctx)
    # 递归处理嵌套带参 partial；普通 partial 由 build_partials_dict 收集
    sub_tpl = await _render_param_partials(sub_tpl, ctx, cursor, lang, current_path,
                                           _depth + 1, request, base_url)
    partials = build_partials_dict(sub_tpl, cursor, lang=lang)
    partials = {k: _expand_row_dynamic_keys(v, ctx) for k, v in partials.items()}
    try:
        return chevron.render(sub_tpl, ctx, partials_dict=partials)
    except Exception:
        return chevron.render(sub_tpl, ctx)


async def render_template(template: str, data: dict, cursor, lang: Optional[str] = None,
                          current_path: Optional[str] = None,
                          request: Optional[Request] = None,
                          base_url: Optional[str] = None) -> str:
    """渲染 mustache 模板，自动解析并注入 DB 中的 {{>partial}} 引用。

    lang 用于展开 legacy i18n 动态 key（{{labels.X[page.language]}}）；
    不传时从 data 推断（data.language / page.language / language_level.language），默认 en。
    current_path：当前页面路径，用于 {{>name?path=.}} 中 . 的解析。
    request/base_url：带参数 partial 的 datasource 相对路径拼接与认证头透传。
    """
    import chevron
    if lang is None:
        lang = _infer_lang(data)
    if isinstance(data, dict):
        # 数据层自动查表：labels.{field} dict + data 行同名 field → 行内 {field}_label
        _enrich_label_fields(data)
    template = expand_i18n_keys(template, lang)
    # 行字段动态键 {{labels.M[F]}} → 数据层展开
    if isinstance(data, dict):
        template = _expand_row_dynamic_keys(template, data)
    template = await _render_param_partials(template, data, cursor, lang, current_path, 0, request, base_url)
    partials = build_partials_dict(template, cursor, lang=lang)
    if isinstance(data, dict):
        partials = {k: _expand_row_dynamic_keys(v, data) for k, v in partials.items()}
    try:
        return chevron.render(template, data, partials_dict=partials)
    except Exception:
        # 无 partials 兜底（兼容旧行为）
        return chevron.render(template, data)


def get_db_connection():
    """Get WebBot database connection"""
    conn = sqlite3.connect(WEBBOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_static_template(template_path: str) -> Optional[str]:
    """Load template file from static mustache templates directory"""
    # 清理路径 - 移除多余的 mustache-templates/ 目录前缀
    # 因为 MUSTACHE_TEMPLATES_DIR 已经包含了 mustache-templates/
    # URL: /mustache/en/mustache-templates/images.html
    # path: en/mustache-templates/images.html
    # File: mustache-templates/en/images.html
    clean_path = template_path.strip("/")
    
    # 移除路径中的 mustache-templates/ 部分（因为目录本身就已 mustache-templates）
    if clean_path.startswith("mustache-templates/"):
        clean_path = clean_path[len("mustache-templates/"):]
    elif "/mustache-templates/" in clean_path:
        idx = clean_path.find("/mustache-templates/")
        clean_path = clean_path[:idx] + "/" + clean_path[idx + len("/mustache-templates/"):]
    
    # 尝试在静态目录中查找
    static_path = os.path.join(MUSTACHE_TEMPLATES_DIR, clean_path)
    
    if os.path.exists(static_path) and os.path.isfile(static_path):
        with open(static_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # 尝试添加常见后缀
    for ext in (".html", ".xml"):
        if not clean_path.endswith(ext):
            static_path_ext = static_path + ext
            if os.path.exists(static_path_ext) and os.path.isfile(static_path_ext):
                with open(static_path_ext, "r", encoding="utf-8") as f:
                    return f.read()
    
    return None


def _query_local_api(path: str, params: dict, cursor) -> Optional[list]:
    """
    Handle local /api/v1/ datasource requests via direct SQL (skip HTTP + auth).
    Returns data or None if the path is not handled.
    """
    import json
    
    # /api/v1/pages/ 与 /api/v1/pages/path — list pages (direct children by parent_path)
    if path in ("/api/v1/pages", "/api/v1/pages/", "/api/v1/pages/path"):
        path_val = params.get("path", [None])[0]
        if path == "/api/v1/pages/path":
            # 与 GET /api/v1/pages/path 路由语义一致：parent_path 精确匹配直接子页面
            if path_val is None or path_val == "":
                cursor.execute(
                    "SELECT * FROM webbot_page WHERE parent_path = '/' OR parent_path IS NULL ORDER BY title ASC")
            else:
                normalized = path_val.rstrip("/")
                cursor.execute(
                    "SELECT * FROM webbot_page WHERE parent_path = ? ORDER BY title ASC",
                    (normalized,))
        else:
            limit = int(params.get("limit", ["100"])[0])
            skip = int(params.get("skip", ["0"])[0])
            prefix_val = params.get("prefix", [None])[0]

            if prefix_val:
                normalized = prefix_val.rstrip("/") + "/"
                cursor.execute(
                    "SELECT * FROM webbot_page WHERE path LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (normalized + "%", limit, skip)
                )
            elif path_val is None or path_val == "":
                cursor.execute(
                    "SELECT * FROM webbot_page WHERE parent_path IS NULL ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, skip)
                )
            else:
                normalized = path_val.rstrip("/")
                cursor.execute(
                    "SELECT * FROM webbot_page WHERE parent_path = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (normalized, limit, skip)
                )
        
        columns = [d[0] for d in cursor.description]
        rows = []
        for row in cursor.fetchall():
            page_dict = dict(zip(columns, row))
            if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
                try:
                    page_dict["metadata"] = json.loads(page_dict["metadata"])
                except json.JSONDecodeError:
                    page_dict["metadata"] = {}
            rows.append(page_dict)
        return rows

    # /api/v1/tags/oag-bvg — OAG/BVG custom tag categories + properties
    if path == "/api/v1/tags/oag-bvg":
        from .tags import fetch_oag_bvg_tags
        return fetch_oag_bvg_tags(cursor)

    # /api/v1/tags/page-properties?path=... — page 中引用的 custom tag 属性
    if path == "/api/v1/tags/page-properties":
        page_path = params.get("path", [None])[0]
        if page_path:
            from .tags import fetch_page_tag_properties
            return fetch_page_tag_properties(cursor, page_path)

    # ── 2026-08-28: 同机直查扩展（webbot/filebot 同机，内部 datasource 不走公网）──
    # 与 GET /api/v1/pages/metadata 路由语义一致：当前页 + 语言级 + 机构级 + dcterms tags。
    if path == "/api/v1/pages/metadata":
        from .pages import normalize_path, _parse_page_dict
        path_val = params.get("path", [None])[0]
        if not path_val:
            return None
        normalized = normalize_path(path_val)
        path_parts = normalized.strip('/').split('/')

        def _fetch_page(p):
            cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (p,))
            row = cursor.fetchone()
            if row is None:
                return None
            d = dict(zip([c[0] for c in cursor.description], row))
            _parse_page_dict(d)
            return d

        page_data = _fetch_page(normalized)
        lang_level_data = None
        inst_level_data = None
        if len(path_parts) >= 2:
            lang_level_data = _fetch_page('/' + '/'.join(path_parts[:2]))
        if len(path_parts) >= 3:
            inst_path = '/' + '/'.join(path_parts[:3])
            if inst_path != normalized:
                inst_level_data = _fetch_page(inst_path)

        def _populate_dcterms(d):
            if not d or not d.get("id"):
                return d
            tag_rows = cursor.execute("""
                SELECT t.type, t.title_en FROM webbot_tag t
                INNER JOIN webbot_page_tags pt ON pt.tag_id = t.id
                WHERE pt.page_id = ?
            """, (d["id"],)).fetchall()
            subjects, audiences, type_val = [], [], None
            for r in tag_rows:
                tt, te = r["type"], r["title_en"]
                if tt == "subject":
                    subjects.append(te)
                elif tt == "audience":
                    audiences.append(te)
                elif tt == "type":
                    type_val = te
            md = d.get("metadata") or {}
            if subjects:
                d["subjects"] = ";".join(subjects)
            elif md.get("subjects"):
                d["subjects"] = md["subjects"]
            if audiences:
                d["audience"] = ";".join(audiences)
            elif md.get("audience"):
                d["audience"] = md["audience"]
            if type_val:
                d["type"] = type_val
            elif md.get("type"):
                d["type"] = md["type"]
            return d

        if page_data:
            _populate_dcterms(page_data)
        if inst_level_data:
            _populate_dcterms(inst_level_data)
        if lang_level_data:
            _populate_dcterms(lang_level_data)

        def _strip_content(d):
            if d and "content" in d:
                d = {k: v for k, v in d.items() if k != "content"}
            return d

        return {
            "page": _strip_content(page_data) if page_data else None,
            "institution_level": _strip_content(inst_level_data) if inst_level_data else None,
            "language_level": _strip_content(lang_level_data) if lang_level_data else None,
            "path": normalized,
            "path_depth": len(path_parts),
        }

    # 与 GET /api/v1/pages/parents 路由语义一致：祖先链 + 当前页 + header/megamenu 回退链。
    if path == "/api/v1/pages/parents":
        from .pages import normalize_path, _parse_page_dict, _compute_is_republish, _unwrap_component, extract_language_from_path
        path_val = params.get("path", [None])[0]
        if not path_val:
            return None
        normalized = normalize_path(path_val)
        path_parts = normalized.strip("/").split("/")
        depth = len(path_parts)

        ancestor_paths = ["/" + "/".join(path_parts[:d]) for d in range(2, depth + 1)]
        row_map = {}
        parents = []
        page = None
        if ancestor_paths:
            placeholders = ",".join(["?"] * len(ancestor_paths))
            cursor.execute(
                f"SELECT * FROM webbot_page WHERE path IN ({placeholders}) ORDER BY LENGTH(path)",
                ancestor_paths)
            cols = [c[0] for c in cursor.description]
            for row in cursor.fetchall():
                d = dict(zip(cols, row))
                row_map[d["path"]] = d

        for d in range(2, depth + 1):
            ancestor_path = "/" + "/".join(path_parts[:d])
            row = row_map.get(ancestor_path)
            if row is None:
                continue
            page_dict = dict(row)
            _parse_page_dict(page_dict)
            page_dict["is_republish"] = _compute_is_republish(
                page_dict.get("last_modified"), page_dict.get("last_published"))
            item = dict(page_dict)
            # 去掉 site 前缀（如 /canadasite）的面包屑路径
            stripped_parts = path_parts[1:d]
            item["path"] = "/" + "/".join(stripped_parts)
            if d == depth:
                page = item
                if page.get("other_language_path") == "/canadasite":
                    page["other_language_path"] = None
            else:
                is_root = d == 2
                if is_root or not page_dict.get('hide_in_navigation', False):
                    parents.append(item)

        language = extract_language_from_path(normalized)
        parts = normalized.strip('/').split('/')
        site_name = parts[0] if parts else "canadasite"
        dept = parts[2] if len(parts) >= 3 else None

        def _fetch_content_by_id(pid):
            cursor.execute("SELECT content FROM webbot_page WHERE id = ?", (pid,))
            r = cursor.fetchone()
            return r[0] if r else None

        header = None
        if language and dept and len(parts) >= 3:
            l4 = f"/{site_name}/{language}/{dept}/header"
            content = _fetch_content_by_id(l4)
            if content:
                header = {"success": True, "content": _unwrap_component(content), "path_used": l4, "fallback_level": "fourth", "language": language}
        if not header and language:
            l3 = f"/{site_name}/{language}/header"
            content = _fetch_content_by_id(l3)
            if content:
                header = {"success": True, "content": _unwrap_component(content), "path_used": l3, "fallback_level": "third", "language": language}
        if not header:
            header = {"success": False, "message": "Header not found", "content": "", "path_used": None, "fallback_level": None}

        megamenu = None
        if normalized:
            l1 = f"{normalized}/menu"
            content = _fetch_content_by_id(l1)
            if content:
                megamenu = {"success": True, "content": _unwrap_component(content), "path_used": l1, "fallback_level": "path", "language": language}
        if not megamenu and language and dept and len(parts) >= 3:
            l4 = f"/{site_name}/{language}/{dept}/megamenu"
            content = _fetch_content_by_id(l4)
            if content:
                megamenu = {"success": True, "content": _unwrap_component(content), "path_used": l4, "fallback_level": "fourth", "language": language}
        if not megamenu and language:
            l3 = f"/{site_name}/{language}/megamenu"
            content = _fetch_content_by_id(l3)
            if content:
                megamenu = {"success": True, "content": _unwrap_component(content), "path_used": l3, "fallback_level": "third", "language": language}
        if not megamenu:
            megamenu = {"success": False, "message": "Megamenu not found", "content": "", "path_used": None, "fallback_level": None}

        return {"parents": parents, "page": page, "header": header, "megamenu": megamenu}

    # 与 GET /api/v1/pages/by-path/{full_path} 路由语义一致：按完整路径取单页。
    if path.startswith("/api/v1/pages/by-path/"):
        from .pages import normalize_path, _compute_out_of_sync, _compute_is_republish, get_ancestor_file_path
        full_path = path[len("/api/v1/pages/by-path/"):]
        if not full_path:
            return None
        normalized = normalize_path(full_path)
        if normalized == '/':
            return {
                "id": 'root', "title": 'Root', "description": 'Root page', "keywords": '',
                "content": '', "language": 'en', "parent_path": None, "other_language_path": None,
                "status": 'published', "metadata": {}, "hide_in_navigation": False,
                "navigation_title": None, "tags": [], "created_by": 'system',
                "created_at": None, "last_modified": None, "last_published": None,
            }
        cursor.execute("SELECT * FROM webbot_page WHERE path = ?", (normalized,))
        row = cursor.fetchone()
        if row is None:
            return None
        page_dict = dict(zip([c[0] for c in cursor.description], row))
        if page_dict.get("metadata") and isinstance(page_dict["metadata"], str):
            try:
                page_dict["metadata"] = json.loads(page_dict["metadata"])
            except json.JSONDecodeError:
                page_dict["metadata"] = {}
        elif page_dict.get("metadata") is None:
            page_dict["metadata"] = {}
        if not page_dict.get('file_path'):
            inherited_fp = get_ancestor_file_path(normalized, cursor.connection)
            if inherited_fp:
                page_dict['file_path'] = inherited_fp
        page_dict["out_of_sync"] = _compute_out_of_sync(
            cursor.connection, page_dict.get("other_language_path"), page_dict.get("last_modified"))
        page_dict["is_republish"] = _compute_is_republish(
            page_dict.get("last_modified"), page_dict.get("last_published"))
        return page_dict

    return None


@router.get("/mustache/{path:path}")
async def render_mustache(path: str, request: Request):
    """
    Render Mustache template
    
    Supports two modes:
    1. Load from database page configurationion中加载（pagecontent为包含 template/datasource/data 的JSON）
    2. 从静态文件加载（前端Edit器侧边栏使用的模板）
    """
    import chevron
    
    # 先尝试从静态模板目录加载
    static_content = load_static_template(path)
    if static_content is not None:
        return HTMLResponse(content=static_content, status_code=200)
    
    # If静态模板不存在，从数据库page加载
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 尝试匹配各种Path format
    path_variants = [path]
    if not path.startswith("/"):
        path_variants.append(f"/{path}")
    if not path.startswith("/mustache/"):
        path_variants.append(f"/mustache/{path}")
        path_variants.append(f"/mustache/{path if path.startswith('/') else '/' + path}")

    # Also try with /canadasite/{lang}/mustache-templates/ prefix (DB template convention)
    if "/" in path and not path.startswith("/"):
        path_variants.append(f"/canadasite/{path}")
    # DB 模板惯例：/canadasite/mustache-templates/{name}
    if not path.startswith("/") and "mustache-templates" not in path:
        path_variants.append(f"/canadasite/mustache-templates/{path}")
    
    page = None
    for pv in path_variants:
        cursor.execute(
            "SELECT id, content FROM webbot_page WHERE path = ? OR path = ?",
            (pv, pv.lower())
        )
        page = cursor.fetchone()
        if page:
            print(f"调试: Mustache找到Configurationpage: id={page['id']}, path匹配: {pv}")
            break
    
    if not page:
        conn.close()
        return HTMLResponse(
            content=f"<!-- Mustache template not found: {path} --><div class='alert alert-warning'>Template not found: {path}</div>",
            status_code=200
        )
    
    # 解析Configuration
    raw_content = page["content"]
    if not raw_content:
        conn.close()
        return HTMLResponse(
            content="<div class='alert alert-danger'>Config page content is empty</div>",
            status_code=200
        )
    
    # 从HTML内容中Extract JSON
    config_json = raw_content
    if "{" in raw_content and "}" in raw_content:
        start_idx = raw_content.find("{")
        end_idx = raw_content.rfind("}") + 1
        if start_idx < end_idx:
            extracted = raw_content[start_idx:end_idx]
            try:
                json.loads(extracted, strict=False)
                config_json = extracted
            except json.JSONDecodeError:
                pass
    
    try:
        config = json.loads(config_json, strict=False)
    except json.JSONDecodeError as e:
        conn.close()
        return HTMLResponse(
            content=f"<div class='alert alert-danger'>Invalid config JSON: {str(e)}</div>",
            status_code=200
        )
    
    # Get template
    template = config.get("template", "")
    if not template:
        conn.close()
        return HTMLResponse(
            content="<div class='alert alert-danger'>Missing template field in config</div>",
            status_code=200
        )
    
    # 初始化数据
    data = config.get("data", {})
    
    # 从 config data 读取输出设置（在 datasource 合并之前保存）
    EXTENSION_TO_MIME = {
        ".xml": "text/xml;charset=utf-8",
        ".json": "application/json;charset=utf-8",
        ".html": "text/html;charset=utf-8",
        ".txt": "text/plain;charset=utf-8",
        ".csv": "text/csv;charset=utf-8",
    }
    def _ci_get(d, *names, default=""):
        """大小写不敏感 + 拼写别名取值（content-type / extesion 兼容）"""
        if not isinstance(d, dict):
            return default
        lk = {str(k).lower(): v for k, v in d.items()}
        for n in names:
            if n.lower() in lk:
                return lk[n.lower()]
        return default

    config_output_ct = _ci_get(data, "content-type", "Content-type", "Content-Type", "contentType", "content_type")
    config_output_ext = _ci_get(data, "extension", "extesion")
    # 如果 extension 设置了但没有 Content-type，自动派生
    if not config_output_ct and config_output_ext:
        config_output_ct = EXTENSION_TO_MIME.get(config_output_ext, "text/html;charset=utf-8")
    if not config_output_ct:
        config_output_ct = "text/html;charset=utf-8"
    
    # 获取数据源
    datasource = config.get("datasource", config.get("dataresource"))
    query_datasource = request.query_params.get("datasource")
    if query_datasource:
        datasource = query_datasource
    
    # 将 request 的所有 query params 替换 datasource 的整个 query string
    # 保留的 params (datasource, token) 不传递给 datasource
    passthrough_params = {
        k: v for k, v in request.query_params.items()
        if k not in ("datasource", "token")
    }
    if datasource and passthrough_params:
        # 合并 request params 到 datasource query：datasource 已有参数保留，同名被 request 覆盖
        base, _, existing_qs = datasource.partition("?")
        merged = dict(urllib.parse.parse_qsl(existing_qs)) if existing_qs else {}
        merged.update(passthrough_params)
        datasource = f"{base}?{urllib.parse.urlencode(merged)}"
    
    # 将 query params 也注入模板数据，方便模板直接引用
    data["query"] = dict(request.query_params)
    
    # 从数据源获取数据
    if datasource and datasource.strip():
        try:
            import aiohttp
            
            # Build full URL
            url = datasource
            if not url.startswith("http"):
                base_url = str(request.base_url).rstrip("/")
                url = f"{base_url}{url}"
            
            # Substitute {path} placeholder: request query path param first, else template path
            url = url.replace("{path}", request.query_params.get("path") or pv)
            
            # Try direct DB query for local /api/v1/ endpoints (skip auth)
            datasource_data = None
            parsed = urllib.parse.urlparse(url)
            if parsed.path.startswith("/api/v1/pages/") or parsed.path == "/api/v1/pages":
                params = urllib.parse.parse_qs(parsed.query)
                datasource_data = _query_local_api(parsed.path, params, cursor)
            
            if datasource_data is not None:
                data["datasource_loaded"] = True
                data["datasource_raw"] = datasource_data
                if isinstance(datasource_data, dict):
                    data = {**data, **datasource_data}
                elif isinstance(datasource_data, list):
                    if "{{#items}}" in template or "{{# items}}" in template:
                        # 模板用 {{#items}} 遍历 → 按服务端 partial 契约放入 items
                        data["items"] = datasource_data
                    else:
                        # 模板用 {{#.}} 遍历根 list（sitemap 等）→ 保持根 list 语义
                        data = datasource_data
                else:
                    data["items"] = datasource_data
            else:
                # Forward Authorization header from original request
                headers = {}
                auth_header = request.headers.get("Authorization")
                if auth_header:
                    headers["Authorization"] = auth_header
                else:
                    token_param = request.query_params.get("token")
                    if token_param:
                        headers["Authorization"] = f"Bearer {token_param}"

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=10) as resp:
                        if resp.status == 200:
                            datasource_data = await resp.json()
                            data["datasource_loaded"] = True
                            data["datasource_raw"] = datasource_data

                            # 合并数据
                            if isinstance(datasource_data, dict):
                                data = {**data, **datasource_data}
                            elif isinstance(datasource_data, list):
                                if "{{#items}}" in template or "{{# items}}" in template:
                                    data["items"] = datasource_data
                                else:
                                    data = datasource_data
                            else:
                                data["items"] = datasource_data
                        elif isinstance(datasource_data, list):
                            # If数据源返回数组,直接赋值给根上下文
                            # 这样模板中的 {{#.}} 可以迭代数组项
                            # 同时保留 datasource_raw 以供调试
                            if "{{#items}}" in template or "{{# items}}" in template:
                                data["items"] = datasource_data
                            else:
                                data = datasource_data
                        else:
                            data["items"] = datasource_data
        except Exception as e:
            print(f"调试: 数据源获取失败: {datasource} - {str(e)}")
            data["datasource_loaded"] = False
            data["datasource_error"] = str(e)
    
    # JSON 输出模板安全化：字符串字段 JSON 转义 + 渲染后清理尾逗号
    is_json_output = 'json' in config_output_ct.lower() or (template.lstrip().startswith(('{', '[')) and not template.lstrip().startswith('{{'))
    if is_json_output:
        import json as _json
        def _json_safe(value):
            if isinstance(value, str):
                return _json.dumps(value, ensure_ascii=False)[1:-1]
            if isinstance(value, dict):
                return {k: _json_safe(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_json_safe(v) for v in value]
            return value
        data = _json_safe(data)

    # 渲染模板（conn 在渲染后关闭，partials 需要活 cursor）
    try:
        result = await render_template(template, data, cursor, current_path=pv, request=request)

        if is_json_output:
            import re as _re
            result = _re.sub(r',(\s*[}\]])', r'\1', result)

        # 检查输出大小上限
        output_bytes = len(result.encode("utf-8"))
        if output_bytes > MUSTACHE_MAX_OUTPUT_SIZE_BYTES:
            max_mb = MUSTACHE_MAX_OUTPUT_SIZE_BYTES / (1024 * 1024)
            actual_mb = output_bytes / (1024 * 1024)
            error_msg = (
                f"<html><body><h1>Mustache Output Too Large</h1>"
                f"<p>Rendered output size ({actual_mb:.1f} MB) exceeds the maximum allowed ({max_mb:.0f} MB).</p>"
                f"</body></html>"
            )
            conn.close()
            return HTMLResponse(content=error_msg, status_code=413)
        
        # Use config's Content-type if non-default, otherwise let FastAPI use default HTML
        if config_output_ct != "text/html;charset=utf-8":
            conn.close()
            return Response(content=result, headers={"Content-Type": config_output_ct}, status_code=200)
        conn.close()
        return HTMLResponse(content=result, status_code=200)
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return Response(
            content=f"Render error: {str(e)}",
            status_code=500
        )


@router.post("/render-mustache")
async def render_mustache_template(request: Request):
    """
    Render Mustache template (direct POST call)
    Uses custom max_part_size (20MB) to handle large form data.
    """
    import chevron
    import re
    
    # 使用自定义 max_part_size (20MB) 以避免 FastAPI 默认的 1MB 限制
    # 旧版 starlette 不支持 max_part_size，降级为默认 request.form()
    try:
        form = await request.form(max_part_size=20 * 1024 * 1024)
    except TypeError:
        form = await request.form()
    template = form.get("template", "")
    json_data = form.get("json_data", "{}")
    escape_html = form.get("escape_html", "true")
    if isinstance(escape_html, str):
        escape_html = escape_html.lower() in ("true", "1", "yes")
    
    try:
        # 解析JSON data
        data = json.loads(json_data)
        
        # 渲染模板（支持从 DB 解析 {{>partial}}）；form 可带 path 字段供 ?path=. 解析
        conn = get_db_connection()
        try:
            result = await render_template(template, data, conn.cursor(),
                                           current_path=form.get("path") or None,
                                           request=request)
        finally:
            conn.close()
        
        return {
            "success": True,
            "html": result,
            "error": None
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "html": "",
            "error": f"JSON解析错误: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "html": "",
            "error": f"Render error: {str(e)}"
        }


@router.get("/api/v1/render-partial")
async def render_partial_api(request: Request):
    """编辑器 WYSIWYG 预渲染：{{>name?params}} → HTML 片段。

    name = partial 名；path = 当前页面路径（用于 ?path=. 解析与 datasource {path} 默认值）；
    其余 query 参数透传为 partial 参数（前端把 ref 里的 path=. 已替换为实际路径）。
    """
    qp = dict(request.query_params)
    name = qp.pop("name", "")
    if not name:
        raise HTTPException(400, "name required")
    current_path = qp.pop("path", "") or ""
    # path 参数已在 query 中（前端替换后的实际路径），直接保留为 partial 参数
    p = qp.get("path", "")
    if p in (".", "./", "self"):
        qp["path"] = current_path
    elif not p:
        qp.pop("path", None)
    lang = "fr" if re.search(r"/(fr)(/|$)", current_path) else "en"
    conn = get_db_connection()
    try:
        html = await _render_param_partial(name, qp, {}, conn.cursor(), lang,
                                           current_path, 0, request, None)
    finally:
        conn.close()
    return HTMLResponse(html)
