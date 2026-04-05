"""
WebBot - AI增强的网站内容管理系统
基于FileBot基础设施，提供AI辅助创页、修正、删页、审查功能
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import sqlite3
import os

# 导入路由
try:
    from .routes import pages_router, ai_router, files_router, components_router, COMPONENTS_ENABLED, FILES_ENABLED
except ImportError:
    # 备用导入方式
    from routes import pages_router, ai_router, files_router, components_router, COMPONENTS_ENABLED, FILES_ENABLED

# 数据库路径
FILEBOT_DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    print("🚀 WebBot启动中...")
    init_database()
    print("✅ 数据库初始化完成")
    yield
    # 关闭时清理资源
    print("🛑 WebBot关闭中...")

# 创建FastAPI应用
app = FastAPI(
    title="WebBot API",
    description="AI增强的网站内容管理系统",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = sqlite3.connect(FILEBOT_DB_PATH)
        conn.row_factory = sqlite3.Row  # 返回字典格式的结果
        return conn
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        raise

def init_database():
    """初始化数据库表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已有webbot_page表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_page'")
        if not cursor.fetchone():
            print("📦 创建webbot_page表...")
            cursor.execute("""
                CREATE TABLE webbot_page (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    language TEXT DEFAULT 'en',
                    parent_id TEXT,
                    other_lang_page_id TEXT,
                    status TEXT DEFAULT 'draft',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_published TIMESTAMP,
                    metadata TEXT  -- JSON格式的元数据
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX idx_webbot_page_parent ON webbot_page(parent_id)")
            cursor.execute("CREATE INDEX idx_webbot_page_language ON webbot_page(language)")
            cursor.execute("CREATE INDEX idx_webbot_page_status ON webbot_page(status)")
            
            print("✅ webbot_page表创建完成")
        
        # 检查是否已有webbot_tasks表 (AI任务)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_tasks'")
        if not cursor.fetchone():
            print("🤖 创建webbot_tasks表...")
            cursor.execute("""
                CREATE TABLE webbot_tasks (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,  -- create, optimize, review, delete
                    page_id TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
                    ai_model TEXT,
                    prompt TEXT,
                    result TEXT,
                    error_message TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            print("✅ webbot_tasks表创建完成")
        
        # 检查组件表（如果启用了组件功能）
        if COMPONENTS_ENABLED:
            component_tables = [
                "component_templates", "component_versions", "component_instances",
                "ai_configurations", "component_current_versions"
            ]
            
            missing_tables = []
            for table in component_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"⚠️  缺少组件表: {', '.join(missing_tables)}")
                print("💡 请运行组件迁移脚本: python3 app/db_migration_components.py")
            else:
                print("✅ 组件表检查完成")
        
        conn.commit()
        conn.close()
        print("📊 数据库初始化完成")
        
    except sqlite3.Error as e:
        print(f"数据库初始化错误: {e}")
        raise

# 包含路由
app.include_router(pages_router)
app.include_router(ai_router)

# 包含文件路由（如果可用）
if FILES_ENABLED and files_router:
    app.include_router(files_router)
    print("✅ 文件路由已加载")
else:
    print("⚠️  文件路由未加载")

# 包含组件路由（如果可用）
if COMPONENTS_ENABLED and components_router:
    app.include_router(components_router)
    print("✅ 组件路由已加载")
else:
    print("⚠️  组件路由未加载")

# 添加静态文件服务（前端界面）
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    # 添加编辑器路径后缀路由（在静态文件服务之前）
    @app.get("/static/editor.html/{path:path}")
    async def serve_editor_with_path(path: str = ""):
        """
        提供带有路径参数的编辑器页面
        格式: /static/editor.html/en/contact → 返回编辑器页面，前端JS会处理路径
        """
        from fastapi.responses import FileResponse
        import os
        
        # 返回编辑器HTML文件
        editor_path = os.path.join(frontend_dir, "editor.html")
        if os.path.exists(editor_path):
            return FileResponse(editor_path, media_type="text/html")
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Editor file not found"}, status_code=404)
    
    app.mount("/static", StaticFiles(directory=frontend_dir, html=True), name="static")
    print(f"📁 静态文件目录: {frontend_dir}")
else:
    print(f"⚠️  前端目录不存在: {frontend_dir}")

# 添加GCWeb/WET-BOEW静态文件服务 (加拿大政府网站标准)
gcweb_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(gcweb_dir):
    app.mount("/gcweb", StaticFiles(directory=gcweb_dir, html=True), name="gcweb")
    print(f"📁 GCWeb静态文件目录: {gcweb_dir}")
else:
    print(f"⚠️  GCWeb目录不存在: {gcweb_dir}")

@app.get("/")
async def root():
    """根端点，重定向到前端界面或返回API信息"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/navigation.html")


@app.get("/editor.html")
async def editor_redirect():
    """重定向 /editor.html 到 /static/editor.html 以保持向后兼容性"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/editor.html")


@app.get("/filebot-picker.html")
async def filebot_picker_redirect():
    """重定向 /filebot-picker.html 到 /static/filebot-picker.html 以保持向后兼容性"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/filebot-picker.html")


@app.get("/api")
async def api_info():
    """API信息端点"""
    return {
        "name": "WebBot API",
        "version": "1.0.0",
        "description": "AI增强的网站内容管理系统",
        "status": "running",
        "database": "connected" if os.path.exists(FILEBOT_DB_PATH) else "not_found",
        "endpoints": {
            "pages": "/api/v1/pages",
            "ai_tasks": "/api/v1/ai/tasks",
            "ai_create": "/api/v1/ai/create-page",
            "ai_optimize": "/api/v1/ai/optimize-page",
            "ai_review": "/api/v1/ai/review-page",
            "ai_delete": "/api/v1/ai/suggest-deletion",
            "files": "/api/v1/files" if FILES_ENABLED else "disabled",
            "components": "/api/v1/components" if COMPONENTS_ENABLED else "disabled"
        }
    }

@app.get("/favicon.ico")
async def favicon():
    """返回一个空favicon以避免404错误"""
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🌐 启动WebBot服务器...")
    print(f"📁 数据库路径: {FILEBOT_DB_PATH}")
    print("🔗 API地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("🤖 AI功能: 创页、修正、审查、删除建议")
    uvicorn.run(app, host="0.0.0.0", port=8000)