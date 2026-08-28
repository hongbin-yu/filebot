"""
WebBot API路由模块
"""

from .pages import router as pages_router
from .pages import router_v1 as pages_v1_router
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

try:
    from .versions import router as versions_router
    VERSIONS_ENABLED = True
except ImportError as e:
    print(f"⚠️  Versions route import failed: {e}")
    VERSIONS_ENABLED = False
    versions_router = None

try:
    from .tags import router as tags_router
    TAGS_ENABLED = True
except ImportError as e:
    print(f"⚠️  Tags route import failed: {e}")
    TAGS_ENABLED = False
    tags_router = None

try:
    from .analytics import router as analytics_router
    ANALYTICS_ENABLED = True
except ImportError as e:
    print(f"⚠️  Analytics route import failed: {e}")
    ANALYTICS_ENABLED = False
    analytics_router = None

try:
    from .schedule import router as schedule_router
    SCHEDULE_ENABLED = True
except ImportError as e:
    print(f"⚠️  Schedule route import failed: {e}")
    SCHEDULE_ENABLED = False
    schedule_router = None

try:
    from .mail import router as mail_router
    MAIL_ENABLED = True
except ImportError as e:
    print(f"⚠️  Mail route import failed: {e}")
    MAIL_ENABLED = False
    mail_router = None

try:
    from .feedback import router as feedback_router
    FEEDBACK_ENABLED = True
except ImportError as e:
    print(f"⚠️  Feedback route import failed: {e}")
    FEEDBACK_ENABLED = False
    feedback_router = None

try:
    from .track import router as track_router
    TRACK_ENABLED = True
except ImportError as e:
    print(f"⚠️  Tracking route import failed: {e}")
    TRACK_ENABLED = False
    track_router = None

try:
    from .references import router as references_router
    REFERENCES_ENABLED = True
except ImportError as e:
    print(f"⚠️  References route import failed: {e}")
    REFERENCES_ENABLED = False
    references_router = None

try:
    from .translate import router as translate_router
    TRANSLATE_ENABLED = True
except ImportError as e:
    print(f"⚠️  Translate route import failed: {e}")
    TRANSLATE_ENABLED = False
    translate_router = None

try:
    from .experiments import router as experiments_router
    EXPERIMENTS_ENABLED = True
except ImportError as e:
    print(f"⚠️  Experiments route import failed: {e}")
    EXPERIMENTS_ENABLED = False
    experiments_router = None

try:
    from .io import router as io_router
    IO_ENABLED = True
except ImportError as e:
    print(f"⚠️  IO route import failed: {e}")
    IO_ENABLED = False
    io_router = None

__all__ = ["pages_router", "pages_v1_router", "ai_router", "files_router", "components_router", "mustache_router", "auth_router", "search_router", "tags_router", "analytics_router", "versions_router", "schedule_router", "mail_router", "feedback_router", "track_router", "references_router", "translate_router", "experiments_router", "io_router", "COMPONENTS_ENABLED", "FILES_ENABLED", "MUSTACHE_ENABLED", "AUTH_ENABLED", "SEARCH_ENABLED", "TAGS_ENABLED", "ANALYTICS_ENABLED", "VERSIONS_ENABLED", "SCHEDULE_ENABLED", "MAIL_ENABLED", "FEEDBACK_ENABLED", "TRACK_ENABLED", "REFERENCES_ENABLED", "TRANSLATE_ENABLED"]