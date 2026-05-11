"""
WebBot API路由模块
"""

from .pages import router as pages_router
from .ai import router as ai_router

try:
    from .files import router as files_router
    FILES_ENABLED = True
except ImportError as e:
    print(f"⚠️  文件路由导入失败: {e}，文件Management功能将不可用")
    FILES_ENABLED = False
    files_router = None

try:
    from .components import router as components_router
    COMPONENTS_ENABLED = True
except ImportError:
    print("⚠️  Component route import failed, component functionality will be unavailable")
    COMPONENTS_ENABLED = False
    components_router = None

try:
    from .mustache import router as mustache_router
    MUSTACHE_ENABLED = True
except ImportError:
    print("⚠️  Mustache route import failed, Mustache functionality will be unavailable")
    MUSTACHE_ENABLED = False
    mustache_router = None

try:
    from .auth import router as auth_router
    AUTH_ENABLED = True
except ImportError:
    print("⚠️  Auth route import failed")
    AUTH_ENABLED = False
    auth_router = None

try:
    from .search import router as search_router
    SEARCH_ENABLED = True
except ImportError as e:
    print(f"⚠️  Search route import failed: {e}")
    SEARCH_ENABLED = False
    search_router = None

__all__ = ["pages_router", "ai_router", "files_router", "components_router", "mustache_router", "auth_router", "search_router", "COMPONENTS_ENABLED", "FILES_ENABLED", "MUSTACHE_ENABLED", "AUTH_ENABLED", "SEARCH_ENABLED"]