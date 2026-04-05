from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import logging

from app.db.database import get_db, init_db
from app.core.config import settings
from app.core.security import create_first_superuser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OAuth2 方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("启动 FileBot 应用...")
    
    # 初始化数据库
    init_db()
    
    # 创建默认超级用户
    db = next(get_db())
    try:
        create_first_superuser(db)
        logger.info("默认用户初始化完成")
    except Exception as e:
        logger.warning(f"创建默认用户时出错: {e}")
    finally:
        db.close()
    
    yield
    
    # 关闭时
    logger.info("关闭 FileBot 应用...")


# 创建FastAPI应用
app = FastAPI(
    title="FileBot API",
    description="文档管理和转换系统",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174", 
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根端点，健康检查"""
    return {
        "message": "Welcome to FileBot API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health"
    }


@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """健康检查端点"""
    from app.core.config import settings
    from sqlalchemy import text
    import os
    import shutil
    
    # 检查数据库连接
    database_status = "connected"
    try:
        # 执行一个简单的查询来测试数据库连接
        result = db.execute(text("SELECT 1")).fetchone()
        if result and result[0] == 1:
            database_status = "connected"
        else:
            database_status = "disconnected"
            logger.error("数据库查询返回异常结果")
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        database_status = "disconnected"
    
    # 检查存储路径
    storage_status = {"available": False}
    try:
        # 检查主存储路径
        storage_path = settings.FILE_STORAGE_PATH
        temp_path = settings.TEMP_STORAGE_PATH
        
        # 确保存储目录存在
        os.makedirs(storage_path, exist_ok=True)
        os.makedirs(temp_path, exist_ok=True)
        
        # 检查是否可写
        test_file = os.path.join(temp_path, ".health_check")
        with open(test_file, "w") as f:
            f.write("health check")
        os.remove(test_file)
        
        # 获取磁盘空间信息
        total, used, free = shutil.disk_usage(storage_path)
        
        storage_status = {
            "available": True,
            "free_space": free,
            "total_space": total,
            "used_space": used
        }
    except Exception as e:
        logger.error(f"存储检查失败: {e}")
        storage_status = {"available": False}
    
    # 确定整体状态
    overall_status = "ok"  # 前端期望 'ok'
    if database_status != "connected" or not storage_status["available"]:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "service": "filebot-api",
        "database": database_status,
        "storage": storage_status
    }


# 导入路由
from app.routers import auth, users, apps, documents, search, conversion, file_naming_rules, device, ai, features, folders, export

# 注册路由
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["认证"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["用户"])
app.include_router(apps.router, prefix=f"{settings.API_V1_STR}/apps", tags=["应用"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["文档"])
app.include_router(search.router, prefix=f"{settings.API_V1_STR}/search", tags=["搜索"])
app.include_router(conversion.router, prefix=f"{settings.API_V1_STR}/conversion", tags=["转换"])
app.include_router(file_naming_rules.router, prefix=f"{settings.API_V1_STR}", tags=["文件命名规则"])
app.include_router(device.router, prefix=f"{settings.API_V1_STR}/devices", tags=["设备管理"])
app.include_router(ai.router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI功能"])
app.include_router(features.router, prefix=f"{settings.API_V1_STR}/features", tags=["特性管理"])
app.include_router(folders.router, prefix=f"{settings.API_V1_STR}/folders", tags=["文件夹"])
app.include_router(export.router, prefix=f"{settings.API_V1_STR}/export", tags=["导出"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )