"""
WebBot API路由模块
"""

from .pages import router as pages_router
from .ai import router as ai_router

try:
    from .files import router as files_router
    FILES_ENABLED = True
except ImportError as e:
    print(f"⚠️  文件路由导入失败: {e}，文件管理功能将不可用")
    FILES_ENABLED = False
    files_router = None

try:
    from .components import router as components_router
    COMPONENTS_ENABLED = True
except ImportError:
    print("⚠️  组件路由导入失败，组件功能将不可用")
    COMPONENTS_ENABLED = False
    components_router = None

__all__ = ["pages_router", "ai_router", "files_router", "components_router", "COMPONENTS_ENABLED", "FILES_ENABLED"]