"""
Mustache 模板渲染路由
支持从页面配置渲染 Mustache 模板，以及静态 mustache 模板的加载
"""
from fastapi import APIRouter, HTTPException, Request, Form, Query
from fastapi.responses import Response, HTMLResponse
import sqlite3
import json
import os
import traceback
from typing import Optional

router = APIRouter(prefix="", tags=["mustache"])

# 数据库路径
FILEBOT_DB_PATH = os.environ.get(
    "FILEBOT_DB_PATH",
    "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
)

# Mustache模板文件目录
MUSTACHE_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..",
    "frontend",
    "mustache-templates"
)

def get_db_connection():
    """获取SQLite数据库连接"""
    conn = sqlite3.connect(FILEBOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_static_template(template_path: str) -> Optional[str]:
    """尝试从静态mustache模板目录加载模板文件"""
    # 清理路径 - 移除多余的 mustache-templates/ 目录前缀
    # 因为 MUSTACHE_TEMPLATES_DIR 已经包含了 mustache-templates/
    # URL: /mustache/en/mustache-templates/images.html
    # path: en/mustache-templates/images.html
    # File: mustache-templates/en/images.html
    clean_path = template_path.strip("/")
    
    # 移除路径中的 mustache-templates/ 部分（因为目录本身就已是 mustache-templates）
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
    
    # 尝试添加 .html 后缀
    if not clean_path.endswith(".html"):
        static_path_html = static_path + ".html"
        if os.path.exists(static_path_html) and os.path.isfile(static_path_html):
            with open(static_path_html, "r", encoding="utf-8") as f:
                return f.read()
    
    return None


@router.get("/mustache/{path:path}")
async def render_mustache(path: str, request: Request):
    """
    渲染Mustache模板
    
    支持两种模式：
    1. 从数据库页面配置中加载（页面content为包含 template/datasource/data 的JSON）
    2. 从静态文件加载（前端编辑器侧边栏使用的模板）
    """
    import chevron
    
    # 先尝试从静态模板目录加载
    static_content = load_static_template(path)
    if static_content is not None:
        return HTMLResponse(content=static_content, status_code=200)
    
    # 如果静态模板不存在，从数据库页面加载
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 尝试匹配各种路径格式
    path_variants = [path]
    if not path.startswith("/"):
        path_variants.append(f"/{path}")
    if not path.startswith("/mustache/"):
        path_variants.append(f"/mustache/{path}")
        path_variants.append(f"/mustache/{path if path.startswith('/') else '/' + path}")
    
    page = None
    for pv in path_variants:
        cursor.execute(
            "SELECT id, content FROM webbot_page WHERE path = ? OR path = ?",
            (pv, pv.lower())
        )
        page = cursor.fetchone()
        if page:
            print(f"调试: Mustache找到配置页面: id={page['id']}, path匹配: {pv}")
            break
    
    if not page:
        conn.close()
        return HTMLResponse(
            content=f"<!-- Mustache template not found: {path} --><div class='alert alert-warning'>Template not found: {path}</div>",
            status_code=200
        )
    
    # 解析配置
    raw_content = page["content"]
    if not raw_content:
        conn.close()
        return HTMLResponse(
            content="<div class='alert alert-danger'>Config page content is empty</div>",
            status_code=200
        )
    
    # 从HTML内容中提取JSON
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
    
    # 获取模板
    template = config.get("template", "")
    if not template:
        conn.close()
        return HTMLResponse(
            content="<div class='alert alert-danger'>Missing template field in config</div>",
            status_code=200
        )
    
    # 初始化数据
    data = config.get("data", {})
    
    # 获取数据源
    datasource = config.get("datasource", config.get("dataresource"))
    query_datasource = request.query_params.get("datasource")
    if query_datasource:
        datasource = query_datasource
    
    # 从数据源获取数据
    if datasource:
        try:
            import aiohttp
            
            # 构建完整URL
            url = datasource
            if not url.startswith("http"):
                base_url = str(request.base_url).rstrip("/")
                url = f"{base_url}{url}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        datasource_data = await resp.json()
                        data["datasource_loaded"] = True
                        data["datasource_raw"] = datasource_data
                        
                        # 合并数据
                        if isinstance(datasource_data, dict):
                            data = {**data, **datasource_data}
                        else:
                            data["items"] = datasource_data
        except Exception as e:
            print(f"调试: 数据源获取失败: {datasource} - {str(e)}")
            data["datasource_loaded"] = False
            data["datasource_error"] = str(e)
    
    conn.close()
    
    # 渲染模板
    try:
        result = chevron.render(template, data)
        return HTMLResponse(content=result, status_code=200)
    except Exception as e:
        return HTMLResponse(
            content=f"<div class='alert alert-danger'>Render error: {str(e)}</div>",
            status_code=200
        )


@router.post("/render-mustache")
async def render_mustache_template(
    template: str = Form(..., description="Mustache模板"),
    json_data: str = Form(..., description="JSON数据"),
    escape_html: bool = Form(True, description="是否HTML转义")
):
    """
    渲染Mustache模板（直接POST调用）
    """
    import chevron
    import re
    
    try:
        # 解析JSON数据
        data = json.loads(json_data)
        
        # 渲染模板
        result = chevron.render(template, data)
        
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
            "error": f"渲染错误: {str(e)}"
        }
