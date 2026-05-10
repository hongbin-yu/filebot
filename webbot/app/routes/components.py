"""
Component management routes
Supports WET-BOEW component registration, management, versioning, and AI integration
"""

from fastapi import APIRouter, HTTPException, Depends, Query
import sqlite3
import json
import uuid
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# 导入组件模型
try:
    from app.models_components import (
        ComponentTemplateCreate, ComponentTemplateUpdate, ComponentTemplateResponse,
        ComponentVersionCreate, ComponentVersionResponse,
        ComponentInstanceCreate, ComponentInstanceUpdate, ComponentInstanceResponse,
        AIConfigurationCreate, AIConfigurationUpdate, AIConfigurationResponse,
        ComponentAIRequest, ComponentAIResponse,
        VersionComparisonRequest, VersionComparisonResponse,
        ComponentCategory, ComponentStatus, AIMode
    )
except ImportError:
    print("⚠️ Warning: Component model import failed, using simplified model")
    # If导入失败，使用简化模型（仅用于开发）
    from pydantic import BaseModel
    from enum import Enum
    
    class ComponentCategory(str, Enum):
        BASIC = "basic"
        FORM = "form"
        NAVIGATION = "navigation"
        CONTENT = "content"
        LAYOUT = "layout"
        WET_BOEW = "wet_boew"
        CUSTOM = "custom"
    
    class ComponentStatus(str, Enum):
        DRAFT = "draft"
        PUBLISHED = "published"
        DEPRECATED = "deprecated"
    
    class AIMode(str, Enum):
        LOCAL_LLM = "local_llm"
        OPENAI_API = "openai_api"
        HYBRID = "hybrid"
    
    class ComponentTemplateBase(BaseModel):
        name: str
        display_name: str
        category: ComponentCategory = ComponentCategory.BASIC
        description: Optional[str] = None
        icon: Optional[str] = None
        html_template: str
        css_template: Optional[str] = None
        js_template: Optional[str] = None
        properties: Dict[str, Any] = {}
        dependencies: List[Dict[str, Any]] = []
        wet_boew_compliant: bool = False
        accessibility_checked: bool = False
        tags: List[str] = []
        author: Optional[str] = None
        version: str = "1.0.0"
    
    class ComponentTemplateCreate(ComponentTemplateBase):
        pass
    
    class ComponentTemplateUpdate(BaseModel):
        display_name: Optional[str] = None
        category: Optional[ComponentCategory] = None
        description: Optional[str] = None
        icon: Optional[str] = None
        html_template: Optional[str] = None
        css_template: Optional[str] = None
        js_template: Optional[str] = None
        properties: Optional[Dict[str, Any]] = None
        dependencies: Optional[List[Dict[str, Any]]] = None
        wet_boew_compliant: Optional[bool] = None
        accessibility_checked: Optional[bool] = None
        tags: Optional[List[str]] = None
        version: Optional[str] = None
    
    class ComponentTemplateResponse(ComponentTemplateBase):
        id: str
        status: ComponentStatus
        created_by: Optional[str]
        created_at: datetime
        updated_at: datetime
        usage_count: int = 0
    
    # 其他简化模型...
    # 为了简洁，这里省略其他简化模型定义

router = APIRouter(prefix="/api/v1/components", tags=["components"])

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

def generate_component_id(name: str) -> str:
    """Generate component ID from name"""
    import re
    # 移除特殊字符，只保留字母数字和连字符
    cleaned = re.sub(r'[^a-zA-Z0-9\-]', '', name.replace(' ', '-'))
    # Transform为小写
    component_id = cleaned.lower()
    # If为空，Generate随机ID
    if not component_id:
        component_id = f"comp-{uuid.uuid4().hex[:8]}"
    return component_id

# ============ Component templateAPI ============

@router.post("/templates", response_model=ComponentTemplateResponse)
def create_component_template(
    template: ComponentTemplateCreate,
    user_id: str = Query("system", description="User ID")
):
    """
    Create new component template
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # GenerateComponent ID
        component_id = generate_component_id(template.name)
        
        # 检查Name已存在
        cursor.execute("SELECT id FROM component_templates WHERE name = ?", (template.name,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"组件Name '{template.name}' 已存在")
        
        # 准备数据
        now = datetime.now().isoformat()
        properties_json = json.dumps(template.properties, ensure_ascii=False)
        dependencies_json = json.dumps(template.dependencies, ensure_ascii=False)
        tags_json = json.dumps(template.tags, ensure_ascii=False)
        
        # 插入数据
        cursor.execute("""
            INSERT INTO component_templates 
            (id, name, display_name, category, description, icon, html_template, 
             css_template, js_template, properties_json, dependencies_json,
             wet_boew_compliant, accessibility_checked, tags_json, author, version,
             status, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            component_id,
            template.name,
            template.display_name,
            template.category.value if hasattr(template.category, 'value') else template.category,
            template.description,
            template.icon,
            template.html_template,
            template.css_template,
            template.js_template,
            properties_json,
            dependencies_json,
            1 if template.wet_boew_compliant else 0,
            1 if template.accessibility_checked else 0,
            tags_json,
            template.author,
            template.version,
            "draft",  # Initial state
            user_id,
            now,
            now
        ))
        
        # Get created template
        cursor.execute("SELECT * FROM component_templates WHERE id = ?", (component_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="Component creation failed")
        
        conn.commit()
        
        # TransformFor response model
        return row_to_template_response(row)
        
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@router.get("/templates", response_model=List[ComponentTemplateResponse])
def list_component_templates(
    category: Optional[ComponentCategory] = None,
    status: Optional[ComponentStatus] = None,
    wet_boew: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    List component templates, supports filtering
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM component_templates WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category.value if hasattr(category, 'value') else category)
        
        if status:
            query += " AND status = ?"
            params.append(status.value if hasattr(status, 'value') else status)
        
        if wet_boew is not None:
            query += " AND wet_boew_compliant = ?"
            params.append(1 if wet_boew else 0)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [row_to_template_response(row) for row in rows]
        
    finally:
        conn.close()

@router.get("/templates/{component_id}", response_model=ComponentTemplateResponse)
def get_component_template(component_id: str):
    """
    Get a specific component template
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM component_templates WHERE id = ?", (component_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"组件 '{component_id}' 不存在")
        
        return row_to_template_response(row)
        
    finally:
        conn.close()

@router.put("/templates/{component_id}", response_model=ComponentTemplateResponse)
def update_component_template(
    component_id: str,
    template_update: ComponentTemplateUpdate,
    user_id: str = Query("system", description="User ID")
):
    """
    Update component template
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if component exists
        cursor.execute("SELECT id FROM component_templates WHERE id = ?", (component_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"组件 '{component_id}' 不存在")
        
        # Build update statement
        update_fields = []
        params = []
        
        if template_update.display_name is not None:
            update_fields.append("display_name = ?")
            params.append(template_update.display_name)
        
        if template_update.category is not None:
            update_fields.append("category = ?")
            params.append(template_update.category.value if hasattr(template_update.category, 'value') else template_update.category)
        
        if template_update.description is not None:
            update_fields.append("description = ?")
            params.append(template_update.description)
        
        if template_update.icon is not None:
            update_fields.append("icon = ?")
            params.append(template_update.icon)
        
        if template_update.html_template is not None:
            update_fields.append("html_template = ?")
            params.append(template_update.html_template)
        
        if template_update.css_template is not None:
            update_fields.append("css_template = ?")
            params.append(template_update.css_template)
        
        if template_update.js_template is not None:
            update_fields.append("js_template = ?")
            params.append(template_update.js_template)
        
        if template_update.properties is not None:
            update_fields.append("properties_json = ?")
            params.append(json.dumps(template_update.properties, ensure_ascii=False))
        
        if template_update.dependencies is not None:
            update_fields.append("dependencies_json = ?")
            params.append(json.dumps(template_update.dependencies, ensure_ascii=False))
        
        if template_update.wet_boew_compliant is not None:
            update_fields.append("wet_boew_compliant = ?")
            params.append(1 if template_update.wet_boew_compliant else 0)
        
        if template_update.accessibility_checked is not None:
            update_fields.append("accessibility_checked = ?")
            params.append(1 if template_update.accessibility_checked else 0)
        
        if template_update.tags is not None:
            update_fields.append("tags_json = ?")
            params.append(json.dumps(template_update.tags, ensure_ascii=False))
        
        if template_update.version is not None:
            update_fields.append("version = ?")
            params.append(template_update.version)
        
        # IfNo update fields
        if not update_fields:
            cursor.execute("SELECT * FROM component_templates WHERE id = ?", (component_id,))
            row = cursor.fetchone()
            return row_to_template_response(row)
        
        # Add updated time和更New者
        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        
        # Execute update
        update_query = f"UPDATE component_templates SET {', '.join(update_fields)} WHERE id = ?"
        params.append(component_id)
        
        cursor.execute(update_query, params)
        
        # Get updated data
        cursor.execute("SELECT * FROM component_templates WHERE id = ?", (component_id,))
        row = cursor.fetchone()
        
        conn.commit()
        
        return row_to_template_response(row)
        
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@router.delete("/templates/{component_id}")
def delete_component_template(
    component_id: str,
    permanent: bool = Query(False, description="Permanently delete?")
):
    """
    Delete component template
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if component exists
        cursor.execute("SELECT id FROM component_templates WHERE id = ?", (component_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"组件 '{component_id}' 不存在")
        
        if permanent:
            # Permanently delete
            cursor.execute("DELETE FROM component_templates WHERE id = ?", (component_id,))
        else:
            # Soft delete: mark as deprecated
            cursor.execute("""
                UPDATE component_templates 
                SET status = 'deprecated', updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), component_id))
        
        conn.commit()
        
        return {"success": True, "message": f"组件 '{component_id}' 已Delete"}
        
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

# ============ Version control API (simple history) ============

@router.post("/templates/{component_id}/versions", response_model=ComponentVersionResponse)
def create_component_version(
    component_id: str,
    change_description: str = Query(..., description="Change description"),
    user_id: str = Query("system", description="User ID")
):
    """
    Create new component version
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if component exists
        cursor.execute("SELECT * FROM component_templates WHERE id = ?", (component_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"组件 '{component_id}' 不存在")
        
        # 获取当前最高Version号
        cursor.execute("""
            SELECT MAX(version_number) as max_version 
            FROM component_versions 
            WHERE component_id = ?
        """, (component_id,))
        result = cursor.fetchone()
        next_version = (result['max_version'] or 0) + 1
        
        # Create version content（完整组件Configuration）
        version_content = {
            "component_id": component_id,
            "template_data": dict(row),
            "created_at": datetime.now().isoformat(),
            "created_by": user_id,
            "change_description": change_description
        }
        
        # Insert version record
        cursor.execute("""
            INSERT INTO component_versions 
            (component_id, version_number, content_json, change_description, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (
            component_id,
            next_version,
            json.dumps(version_content, ensure_ascii=False),
            change_description,
            user_id
        ))
        
        version_id = cursor.lastrowid
        
        # Update current version pointer
        cursor.execute("""
            INSERT OR REPLACE INTO component_current_versions 
            (component_id, current_version_id)
            VALUES (?, ?)
        """, (component_id, version_id))
        
        # Get created version
        cursor.execute("SELECT * FROM component_versions WHERE id = ?", (version_id,))
        version_row = cursor.fetchone()
        
        conn.commit()
        
        return row_to_version_response(version_row)
        
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@router.get("/templates/{component_id}/versions", response_model=List[ComponentVersionResponse])
def list_component_versions(
    component_id: str,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    List component version history
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if component exists
        cursor.execute("SELECT id FROM component_templates WHERE id = ?", (component_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"组件 '{component_id}' 不存在")
        
        cursor.execute("""
            SELECT * FROM component_versions 
            WHERE component_id = ? 
            ORDER BY version_number DESC 
            LIMIT ? OFFSET ?
        """, (component_id, limit, offset))
        
        rows = cursor.fetchall()
        
        return [row_to_version_response(row) for row in rows]
        
    finally:
        conn.close()

@router.get("/templates/{component_id}/versions/{version_id}", response_model=ComponentVersionResponse)
def get_component_version(component_id: str, version_id: int):
    """
    Get a specific version
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM component_versions 
            WHERE component_id = ? AND id = ?
        """, (component_id, version_id))
        
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Version does not exist")
        
        return row_to_version_response(row)
        
    finally:
        conn.close()

@router.post("/templates/{component_id}/revert")
def revert_component_version(
    component_id: str,
    version_id: int,
    reason: str = Query(..., description="Revert reason"),
    user_id: str = Query("system", description="User ID")
):
    """
    Revert to a specific version
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取目标Version
        cursor.execute("""
            SELECT * FROM component_versions 
            WHERE component_id = ? AND id = ?
        """, (component_id, version_id))
        
        version_row = cursor.fetchone()
        
        if not version_row:
            raise HTTPException(status_code=404, detail="Version does not exist")
        
        # Parse version content
        version_content = json.loads(version_row['content_json'])
        template_data = version_content.get('template_data', {})
        
        # 创建NewVersion（回滚Version）
        cursor.execute("""
            SELECT MAX(version_number) as max_version 
            FROM component_versions 
            WHERE component_id = ?
        """, (component_id,))
        result = cursor.fetchone()
        next_version = (result['max_version'] or 0) + 1
        
        # Create revert version content
        revert_content = {
            "component_id": component_id,
            "template_data": template_data,
            "reverted_from": version_id,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
            "created_by": user_id,
            "change_description": f"回滚到Version {version_id}: {reason}"
        }
        
        # Insert revert version
        cursor.execute("""
            INSERT INTO component_versions 
            (component_id, version_number, content_json, change_description, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (
            component_id,
            next_version,
            json.dumps(revert_content, ensure_ascii=False),
            f"回滚到Version {version_id}: {reason}",
            user_id
        ))
        
        revert_version_id = cursor.lastrowid
        
        # Update current version pointer
        cursor.execute("""
            INSERT OR REPLACE INTO component_current_versions 
            (component_id, current_version_id)
            VALUES (?, ?)
        """, (component_id, revert_version_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"已回滚到Version {version_id}",
            "new_version_id": revert_version_id
        }
        
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

# ============ Helper functions ============

def row_to_template_response(row) -> Dict[str, Any]:
    """Convert database row to template response"""
    return {
        "id": row['id'],
        "name": row['name'],
        "display_name": row['display_name'],
        "category": row['category'],
        "description": row['description'],
        "icon": row['icon'],
        "html_template": row['html_template'],
        "css_template": row['css_template'],
        "js_template": row['js_template'],
        "properties": json.loads(row['properties_json']) if row['properties_json'] else {},
        "dependencies": json.loads(row['dependencies_json']) if row['dependencies_json'] else [],
        "wet_boew_compliant": bool(row['wet_boew_compliant']),
        "accessibility_checked": bool(row['accessibility_checked']),
        "tags": json.loads(row['tags_json']) if row['tags_json'] else [],
        "author": row['author'],
        "version": row['version'],
        "status": row['status'],
        "created_by": row['created_by'],
        "created_at": datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        "updated_at": datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
        "usage_count": row['usage_count'] or 0
    }

def row_to_version_response(row) -> Dict[str, Any]:
    """Convert database row to version response"""
    content = json.loads(row['content_json']) if row['content_json'] else {}
    
    return {
        "id": row['id'],
        "component_id": row['component_id'],
        "version_number": row['version_number'],
        "content": content,
        "change_description": row['change_description'],
        "created_by": row['created_by'],
        "created_at": datetime.fromisoformat(row['created_at']) if row['created_at'] else None
    }

# ============ Health check endpoint ============

@router.get("/health")
def components_health():
    """
    Component system health check
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查所有表存在
        tables = ["component_templates", "component_versions", "component_instances", 
                  "ai_configurations", "component_current_versions"]
        
        missing_tables = []
        for table in tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                missing_tables.append(table)
        
        if missing_tables:
            return {
                "status": "degraded",
                "message": f"Missing table: {', '.join(missing_tables)}",
                "tables": {table: "missing" for table in missing_tables}
            }
        
        # 检查Example数据
        cursor.execute("SELECT COUNT(*) as count FROM component_templates")
        template_count = cursor.fetchone()['count']
        
        return {
            "status": "healthy",
            "message": f"Component system OK，现有 {template_count} 个Component template",
            "tables": {table: "ok" for table in tables},
            "template_count": template_count
        }
        
    finally:
        conn.close()

# ============ Initialize endpoint ============

@router.post("/initialize")
def initialize_components_system(
    create_samples: bool = Query(True, description="Create sample components?")
):
    """
    Initialize component system (development/demo only)
    """
    # 这里可以Add更多初始化逻辑
    # 目前表已通过迁移脚本创建
    
    response = {
        "success": True,
        "message": "组件系统已初始化",
        "tables_created": True,
        "sample_data_created": create_samples
    }
    
    if create_samples:
        # Example数据已在迁移脚本中创建
        response["sample_components"] = [
            {
                "id": "wet-button-primary",
                "name": "主要按钮 (WET-BOEW)",
                "category": "wet_boew",
                "description": "加拿大政府Standard主要按钮"
            },
            {
                "id": "wet-input-text",
                "name": "文本输入框 (WET-BOEW)",
                "category": "form",
                "description": "可访问性友好的文本输入框"
            }
        ]
    
    return response


# ============ page渲染端点 ============

# page渲染请求模型
class PageRenderRequest(BaseModel):
    """Page rendering request data model"""
    component_instances: List[Dict[str, Any]]
    page_title: str = "WebBot Generate的page"
    include_wet_boew: bool = True
    include_accessibility: bool = True
    include_admin_resources: bool = False  # Include adminAdd的CSS/JS资源
    include_header_footer: bool = True  # 包含WET-BOEWStandard的header和footer


@router.post("/render-page")
async def render_page_from_components(
    render_request: PageRenderRequest
):
    """
    Render component instances as a complete HTML page
    """
    try:
        component_instances = render_request.component_instances
        page_title = render_request.page_title
        include_wet_boew = render_request.include_wet_boew
        include_accessibility = render_request.include_accessibility
        include_admin_resources = render_request.include_admin_resources
        include_header_footer = render_request.include_header_footer
        # 1. 收集所有需要的Component template
        conn = get_db_connection()
        cursor = conn.cursor()
        
        rendered_components = []
        component_ids = [inst.get("template_id") for inst in component_instances if inst.get("template_id")]
        
        if not component_ids:
            return {
                "success": False,
                "error": "No component instances to render",
                "html": ""
            }
        
        # 查询所有相关Component template
        placeholders = ','.join(['?'] * len(component_ids))
        cursor.execute(f"""
            SELECT id, name, html_template, css_template, js_template, 
                   dependencies_json, wet_boew_compliant
            FROM component_templates 
            WHERE id IN ({placeholders})
        """, component_ids)
        
        templates = {row['id']: dict(row) for row in cursor.fetchall()}
        
        # 2. Render each component
        for instance in component_instances:
            template_id = instance.get("template_id")
            if not template_id or template_id not in templates:
                continue
                
            template = templates[template_id]
            config = instance.get("configuration", {})
            
            # 获取HTML模板
            html_template = template.get("html_template", "")
            if not html_template:
                continue
            
            # Simplified Handlebars template rendering
            rendered_html = html_template
            
            # Replace variables {{variable}}
            for key, value in config.items():
                if value is None:
                    continue
                # Replace {{key}}
                rendered_html = rendered_html.replace(f"{{{{{key}}}}}", str(value))
                # Replace {{ key }} (带空格的Version)
                rendered_html = rendered_html.replace(f"{{{{ {key} }}}}", str(value))
            
            # Handle conditional statements {{#if condition}}...{{/if}}
            import re
            
            # 首先处理所有条件语句，多次处理以确保嵌套或复杂的条件
            for _ in range(3):  # 最多处理3次，处理可能的嵌套
                # 处理 {{#if var}}...{{/if}} - 更宽松的匹配，处理跨行和空格
                if_pattern = r'\{\{\s*#if\s+(\w+)\s*\}\}(.*?)\{\{\s*/if\s*\}\}'
                matches = list(re.finditer(if_pattern, rendered_html, re.DOTALL))
                if not matches:
                    break
                
                for match in matches:
                    var_name = match.group(1).strip()
                    content = match.group(2)
                    if config.get(var_name):
                        # Condition is true, keep content
                        rendered_html = rendered_html.replace(match.group(0), content)
                    else:
                        # Condition is false, remove content
                        rendered_html = rendered_html.replace(match.group(0), "")
            
            # 处理 {{#unless var}}...{{/unless}}
            for _ in range(3):
                unless_pattern = r'\{\{\s*#unless\s+(\w+)\s*\}\}(.*?)\{\{\s*/unless\s*\}\}'
                matches = list(re.finditer(unless_pattern, rendered_html, re.DOTALL))
                if not matches:
                    break
                
                for match in matches:
                    var_name = match.group(1).strip()
                    content = match.group(2)
                    if not config.get(var_name):
                        # 条件为假（unless为真），保留内容
                        rendered_html = rendered_html.replace(match.group(0), content)
                    else:
                        # 条件为真（unless为假），移除内容
                        rendered_html = rendered_html.replace(match.group(0), "")
            
            # Clean up any remaining {{/if}} 或 {{/unless}}
            rendered_html = rendered_html.replace("{{/if}}", "").replace("{{/unless}}", "")
            
            # 根据Include admin资源决定Add outer wrapper
            if include_admin_resources:
                # Admin模式：Add outer wrapper用于Edit
                component_html = f"""
                <!-- 组件: {template.get('name', template_id)} (Edit mode) -->
                <div class="webot-component webot-admin-wrapper" data-component-id="{template_id}" data-instance-id="{instance.get('id', '')}">
                    {rendered_html}
                </div>
                """
            else:
                # ClientMode: render component directly, no wrapper
                component_html = f"""
                <!-- 组件: {template.get('name', template_id)} (Publish mode) -->
                {rendered_html}
                """
            
            rendered_components.append({
                "template_id": template_id,
                "component_name": template.get("name", template_id),
                "html": component_html,
                "position": instance.get("position", {}),
                "alignment": instance.get("alignment", "left")
            })
        
        # 3. Generate完整HTMLpage
        # Collect all CSS和JSDependencies
        css_deps = []
        js_deps = []
        
        # 只在admin模式包含组件特定的CSS/JS
        if include_admin_resources:
            for template in templates.values():
                if template.get("css_template"):
                    css_deps.append(f"<style>\n{template['css_template']}\n</style>")
                if template.get("js_template"):
                    js_deps.append(f"<script>\n{template['js_template']}\n</script>")
                
                # 处理外部Dependencies
                deps_json = template.get("dependencies_json")
                if deps_json:
                    try:
                        deps = json.loads(deps_json)
                        for dep in deps:
                            dep_type = dep.get("type", "")
                            dep_url = dep.get("url", "")
                            if dep_type == "css" and dep_url:
                                css_deps.append(f'<link rel="stylesheet" href="{dep_url}">')
                            elif dep_type == "js" and dep_url:
                                js_deps.append(f'<script src="{dep_url}"></script>')
                    except:
                        pass
        
        # Always include WET-BOEWStandardDependencies（Ifinclude_wet_boew为True）
        
        # WET-BOEWDependencies (使用GCWebTheme，与canada.ca一致)
        if include_wet_boew:
            wet_css = """
            <!-- GCWebThemeCSS (Canada.caStandard) - 本地Version -->
            <link rel="stylesheet" href="/etc/designs/canada/wet-boew/css/theme.min.css">
            <noscript><link rel="stylesheet" href="/etc/designs/canada/wet-boew/css/noscript.min.css" /></noscript>
            <link rel="stylesheet" href="/etc/designs/canada/wet-boew/css/all.css" crossorigin="anonymous">
            """
            wet_js = """
            <!-- GCWebThemeJS (Canada.caStandard) - 本地Version -->
            <script src="/etc/designs/canada/wet-boew/js/jquery/2.2.4/jquery.min.js"></script>
            <script src="/etc/designs/canada/wet-boew/js/wet-boew.min.js"></script>
            <script src="/etc/designs/canada/wet-boew/js/theme.min.js"></script>
            """
            css_deps.insert(0, wet_css)
            js_deps.insert(0, wet_js)
        
        # Accessibility enhancements
        if include_accessibility:
            accessibility_js = """
            <!-- Accessibility enhancements -->
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                // Add skip link
                const skipLink = document.createElement('a');
                skipLink.href = '#main-content';
                skipLink.className = 'wb-inv';
                skipLink.textContent = 'Skip to main content';
                document.body.insertBefore(skipLink, document.body.firstChild);
                
                // Add main content area
                const mainContent = document.createElement('main');
                mainContent.id = 'main-content';
                mainContent.setAttribute('role', 'main');
                document.body.appendChild(mainContent);
                
                // 将所有组件移动到主要内容区域
                const components = document.querySelectorAll('.webot-component');
                components.forEach(comp => {
                    mainContent.appendChild(comp);
                });
            });
            </script>
            """
            js_deps.append(accessibility_js)
        
        # Organize components by alignment
        left_components = []
        center_components = []
        right_components = []
        
        for comp in rendered_components:
            alignment = comp.get("alignment", "left")
            if alignment == "center":
                center_components.append(comp)
            elif alignment == "right":
                right_components.append(comp)
            else:
                left_components.append(comp)
        
        # Generate组件HTML部分
        components_html = ""
        if left_components:
            components_html += '<div class="webot-alignment-left">\n'
            for comp in left_components:
                components_html += comp["html"] + "\n"
            components_html += '</div>\n'
        
        if center_components:
            components_html += '<div class="webot-alignment-center">\n'
            for comp in center_components:
                components_html += comp["html"] + "\n"
            components_html += '</div>\n'
        
        if right_components:
            components_html += '<div class="webot-alignment-right">\n'
            for comp in right_components:
                components_html += comp["html"] + "\n"
            components_html += '</div>\n'
        
        # 完整HTMLpage
        # 定义WET-BOEWStandard的header和footer（使用GCWeb/canada.caTheme）
        wet_header_html = '''<header role="banner">
    <div id="wb-bnr" class="container">
        <div class="row">
            <!-- 语言选择 -->
            <section id="wb-lng" class="col-xs-3 col-sm-12 pull-right text-right">
                <h2 class="wb-inv">Language selection</h2>
                <ul class="list-inline mrgn-bttm-0">
                    <li>
                        <a lang="fr" hreflang="fr" href="https://www.canada.ca/fr.html">
                            <span class="hidden-xs" translate="no">Français</span>
                            <abbr title="Français" translate="no" class="visible-xs h3 mrgn-tp-sm mrgn-bttm-0 text-uppercase">fr</abbr>
                        </a>
                    </li>
                </ul>
            </section>

            <!-- 政府品牌 -->
            <div class="brand col-xs-9 col-sm-5 col-md-4" property="publisher" typeof="GovernmentOrganization">
                <a href="https://www.canada.ca/en.html" property="url">
                    <img src="https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/assets/sig-blk-en.svg" alt="Government of Canada" property="logo" />
                    <span class="wb-inv"> / <span lang="fr">Gouvernement du Canada</span></span>
                </a>
                <meta property="name" content="Government of Canada">
                <meta property="areaServed" typeof="Country" content="Canada" />
                <link property="logo" href="https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/assets/wmms-blk.svg" />
            </div>

            <!-- Search框 -->
            <section id="wb-srch" class="col-lg-offset-4 col-md-offset-4 col-sm-offset-2 col-xs-12 col-sm-5 col-md-4">
                <h2>Search</h2>
                <form action="https://www.canada.ca/en/sr/srb.html" method="get" name="cse-search-box" role="search">
                    <div class="form-group wb-srch-qry">
                        <label for="wb-srch-q" class="wb-inv">Search Canada.ca</label>
                        <input id="wb-srch-q" list="wb-srch-q-ac" class="wb-srch-q form-control" name="q" type="search" value="" size="34" maxlength="170" placeholder="Search Canada.ca" />
                        <datalist id="wb-srch-q-ac"></datalist>
                    </div>
                    <div class="form-group submit">
                        <button type="submit" id="wb-srch-sub" class="btn btn-primary btn-small" name="wb-srch-sub">
                            <span class="glyphicon-search glyphicon"></span>
                            <span class="wb-inv">Search</span>
                        </button>
                    </div>
                </form>
            </section>
        </div>
    </div>
</header>'''

        wet_footer_html = '''<footer role="contentinfo" id="wb-info">
    <h2 class="wb-inv">About this site</h2>

    <div class="gc-main-footer">
        <div class="container">
            <nav>
                <h3>Government of Canada</h3>
                <ul class="list-col-xs-1 list-col-sm-2 list-col-md-3">
                    <li><a href="https://www.canada.ca/en/contact.html">All contacts</a></li>
                    <li><a href="https://www.canada.ca/en/government/dept.html">Departments and agencies</a></li>
                    <li><a href="https://www.canada.ca/en/government/system.html">About government</a></li>
                </ul>
                <h4><span class="wb-inv">Themes and topics</span></h4>
                <ul class="list-unstyled colcount-sm-2 colcount-md-3">
                    <li><a href="https://www.canada.ca/en/services/jobs.html">Jobs</a></li>
                    <li><a href="https://www.canada.ca/en/services/immigration-citizenship.html">Immigration and citizenship</a></li>
                    <li><a href="https://travel.gc.ca/">Travel and tourism</a></li>
                    <li><a href="https://www.canada.ca/en/services/business.html">Business</a></li>
                    <li><a href="https://www.canada.ca/en/services/benefits.html">Benefits</a></li>
                    <li><a href="https://www.canada.ca/en/services/health.html">Health</a></li>
                    <li><a href="https://www.canada.ca/en/services/taxes.html">Taxes</a></li>
                    <li><a href="https://www.canada.ca/en/services/environment.html">Environment and natural resources</a></li>
                    <li><a href="https://www.canada.ca/en/services/defence.html">National security and defence</a></li>
                    <li><a href="https://www.canada.ca/en/services/culture.html">Culture, history and sport</a></li>
                    <li><a href="https://www.canada.ca/en/services/policing.html">Policing, justice and emergencies</a></li>
                    <li><a href="https://www.canada.ca/en/services/transport.html">Transport and infrastructure</a></li>
                    <li><a href="https://www.international.gc.ca/world-monde/index.aspx?lang=eng">Canada and the world</a></li>
                    <li><a href="https://www.canada.ca/en/services/finance.html">Money and finances</a></li>
                    <li><a href="https://www.canada.ca/en/services/science.html">Science and innovation</a></li>
                    <li><a href="https://www.canada.ca/en/services/indigenous-peoples.html">Indigenous Peoples</a></li>
                    <li><a href="https://www.canada.ca/en/services/veterans-military.html">Veterans and military</a></li>
                    <li><a href="https://www.canada.ca/en/services/youth.html">Youth</a></li>
                    <li><a href="https://www.canada.ca/en/services/life-events.html">Manage life events</a></li>
                </ul>
            </nav>
        </div>
    </div>

    <div class="gc-sub-footer">
        <div class="container d-flex align-items-center">
            <nav>
                <h3 class="wb-inv">Government of Canada Corporate</h3>
                <ul>
                    <li><a href="https://www.canada.ca/en/social.html">Social media</a></li>
                    <li><a href="https://www.canada.ca/en/mobile.html">Mobile applications</a></li>
                    <li><a href="https://canada.ca/en/government/about-canada-ca.html">About Canada.ca</a></li>
                    <li><a href="https://www.canada.ca/en/transparency/terms.html">Terms and conditions</a></li>
                    <li><a href="https://www.canada.ca/en/transparency/privacy.html">Privacy</a></li>
                </ul>
            </nav>
            <div class="wtrmrk align-self-end">
                <img src="https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/assets/wmms-blk.svg" alt="Symbol of the Government of Canada" />
            </div>
        </div>
    </div>
</footer>'''

        # 根据SettingsGeneratebody内容
        if include_header_footer and include_wet_boew:
            # 使用WET-BOEWStandard结构
            body_content = f"""
{wet_header_html}

<main role="main" class="container">
    <div class="webot-page-container">
        <div class="webot-page-header">
            <h1 class="webot-page-title">{page_title}</h1>
            <div class="webot-page-meta">
                由WebBot WET-BOEWComponent editorGenerate | 符合加拿大政府网站Standard
            </div>
        </div>
        
        <div class="webot-components-area">
            {components_html}
        </div>
        
        <div class="webot-footer">
            <p>© 2026 WebBot Component editor | 此page使用WET-BOEW组件构建</p>
            <p>Generate时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</main>

{wet_footer_html}
"""
        else:
            # 使用原始结构
            body_content = f"""
    <div class="webot-page-container">
        <header class="webot-page-header">
            <h1 class="webot-page-title">{page_title}</h1>
            <div class="webot-page-meta">
                由WebBot WET-BOEWComponent editorGenerate | 符合加拿大政府网站Standard
            </div>
        </header>
        
        <main class="webot-components-area">
            {components_html}
        </main>
        
        <footer class="webot-footer">
            <p>© 2026 WebBot Component editor | 此page使用WET-BOEW组件构建</p>
            <p>Generate时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
"""

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <meta name="description" content="由WebBotComponent editorGenerate的page">
    <meta name="generator" content="WebBot WET-BOEW Component Editor">
    
    <!-- Basic styles -->
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .webot-page-container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .webot-page-header {{
            border-bottom: 2px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .webot-page-title {{
            color: #003366;
            margin: 0 0 10px 0;
        }}
        .webot-page-meta {{
            color: #666;
            font-size: 0.9em;
        }}
        .webot-components-area {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 30px;
        }}
        .webot-alignment-left {{
            flex: 1;
            min-width: 300px;
        }}
        .webot-alignment-center {{
            flex: 1;
            min-width: 300px;
            text-align: center;
        }}
        .webot-alignment-right {{
            flex: 1;
            min-width: 300px;
            text-align: right;
        }}
        .webot-component {{
            margin-bottom: 20px;
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background: #fafafa;
        }}
        .webot-footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 0.9em;
            text-align: center;
        }}
        @media (max-width: 768px) {{
            .webot-components-area {{
                flex-direction: column;
            }}
            .webot-alignment-left,
            .webot-alignment-center,
            .webot-alignment-right {{
                text-align: left;
            }}
        }}
    </style>
    
    <!-- Component CSSDependencies -->
    {''.join(css_deps)}
</head>
<body>
{body_content}
    
    <!-- Component JSDependencies -->
    {''.join(js_deps)}
</body>
</html>"""
        
        conn.close()
        
        return {
            "success": True,
            "html": full_html,
            "component_count": len(rendered_components),
            "templates_used": list(templates.keys()),
            "alignment_stats": {
                "left": len(left_components),
                "center": len(center_components),
                "right": len(right_components)
            },
            "render_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "html": f"<html><body><h1>Render error</h1><p>{str(e)}</p></body></html>"
        }