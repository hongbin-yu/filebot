from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
import logging

from .config import settings
from app.models.user import User
from app.db.database import get_db

# OAuth2密码承载令牌方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

logger = logging.getLogger(__name__)

# 密码哈希上下文
# 临时使用pbkdf2_sha256绕过bcrypt兼容性问题
# 生产环境建议使用argon2或bcrypt
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    pbkdf2_sha256__default_rounds=30000,
    deprecated="auto"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    if not password:
        raise ValueError("密码不能为空")
    
    # bcrypt限制72字节，确保密码不超过限制
    # 将密码编码为UTF-8检查字节长度
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # 截断到72字节，确保截断在字符边界
        # 反向查找最后一个完整字符的边界
        truncated = password_bytes[:72]
        while truncated[-1] & 0x80 and not (truncated[-1] & 0x40):
            # 这是UTF-8序列的中间字节，需要继续截断
            truncated = truncated[:-1]
        password = truncated.decode('utf-8', errors='ignore')
        logger.warning(f"密码过长，已截断为72字节")
    
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"JWT解码错误: {e}")
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """用户认证"""
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user:
        logger.warning(f"用户不存在: {username}")
        return None
    
    if not verify_password(password, user.password_hash):
        logger.warning(f"密码错误: {username}")
        return None
    
    if not user.is_active:
        logger.warning(f"用户未激活: {username}")
        return None
    
    return user


def get_current_user(db: Session, token: str) -> Optional[User]:
    """从令牌获取当前用户"""
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        return None
    
    try:
        # 用户ID已经是字符串格式，直接查询
        # 注意：User模型使用String(36)存储ID，不需要转换为UUID对象
        user = db.query(User).filter(User.id == user_id_str).first()
        return user
    except (ValueError, TypeError) as e:
        logger.error(f"无效的用户ID格式: {user_id_str} - {e}")
        return None


def create_first_superuser(db: Session) -> None:
    """创建默认超级用户（如果不存在）"""
    # 检查是否已存在管理员
    admin = db.query(User).filter(
        (User.username == settings.DEFAULT_SUPERUSER_USERNAME) |
        (User.email == settings.DEFAULT_SUPERUSER_EMAIL)
    ).first()
    
    if admin:
        logger.info(f"管理员用户已存在: {admin.username}")
        return
    
    # 创建新管理员
    admin = User(
        username=settings.DEFAULT_SUPERUSER_USERNAME,
        email=settings.DEFAULT_SUPERUSER_EMAIL,
        password_hash=get_password_hash(settings.DEFAULT_SUPERUSER_PASSWORD),
        full_name="系统管理员",
        is_active=True,
        is_superuser=True,
        role="admin",
    )
    
    db.add(admin)
    db.commit()
    logger.info(f"创建默认管理员用户: {admin.username}")


from app.models.permission import Permission, ResourceType, PermissionLevel
from app.models.group import GroupMember


_LEVEL_RANK = {
    PermissionLevel.READ: 0,
    PermissionLevel.WRITE: 1,
    PermissionLevel.ADMIN: 2,
    PermissionLevel.OWNER: 3,
}


def _get_level_rank(level: str) -> int:
    """将字符串权限级别转换为排名数值"""
    try:
        pl = PermissionLevel(level)
        return _LEVEL_RANK.get(pl, -1)
    except ValueError:
        return -1


def check_user_permission(
    user: User,
    resource_type: str,
    resource_id: str,
    required_level: str,
    db: Session = None
) -> bool:
    """检查用户权限
    
    Args:
        user: 用户对象
        resource_type: 资源类型 (app, drawer, folder, document)
        resource_id: 资源ID
        required_level: 所需权限级别 (read, write, admin, owner)
        db: 数据库会话（可选，不提供时返回True以保持兼容）
    
    Returns:
        bool: 是否有权限
    """
    # 超级用户拥有所有权限
    if user.is_superuser:
        return True

    if db is None:
        # 无数据库会话时返回True保持兼容（旧调用方不会报错）
        return True

    try:
        res_type = ResourceType(resource_type)
        req_level = PermissionLevel(required_level)
    except ValueError:
        return False

    required_rank = _LEVEL_RANK.get(req_level, -1)

    # 1. 查 direct user permissions
    direct_perms = db.query(Permission).filter(
        Permission.user_id == user.id,
        Permission.resource_type == res_type,
        Permission.resource_id == resource_id,
    ).all()

    # 2. 查 group-based permissions
    user_group_ids = [
        row[0] for row in db.query(GroupMember.group_id)
        .filter(GroupMember.user_id == user.id)
        .all()
    ]
    group_perms = []
    if user_group_ids:
        group_perms = db.query(Permission).filter(
            Permission.group_id.in_(user_group_ids),
            Permission.resource_type == res_type,
            Permission.resource_id == resource_id,
        ).all()

    # 3. 层级继承: 如果 resource_type 是 folder, 检查父 app 权限
    if res_type == ResourceType.FOLDER:
        from app.models.folder import Folder
        folder = db.query(Folder).filter(Folder.path == resource_id).first()
        if folder:
            # 检查 app 级别的权限（用户直接权限）
            app_direct = db.query(Permission).filter(
                Permission.user_id == user.id,
                Permission.resource_type == ResourceType.APP,
                Permission.resource_id == folder.app_id,
            ).all()
            if user_group_ids:
                app_group = db.query(Permission).filter(
                    Permission.group_id.in_(user_group_ids),
                    Permission.resource_type == ResourceType.APP,
                    Permission.resource_id == folder.app_id,
                ).all()
                app_direct = app_direct + app_group
            all_perms = direct_perms + group_perms + app_direct
        else:
            all_perms = direct_perms + group_perms
    else:
        all_perms = direct_perms + group_perms

    if not all_perms:
        return False

    best_rank = max(_LEVEL_RANK.get(p.permission_level, -1) for p in all_perms)
    return best_rank >= required_rank


def has_app_access(user: User, app_id: str, level: str = "read", db: Session = None) -> bool:
    """检查用户是否有权访问指定 app
    
    Args:
        user: 用户对象
        app_id: 应用ID
        level: 所需权限级别 (read, write, admin, owner)
        db: 数据库会话
    
    Returns:
        bool: 是否有权限
    """
    if user.is_superuser:
        return True

    # App owner 总是有所有权限
    from app.models.app import App
    app = db.query(App).filter(App.id == app_id).first()
    if app and app.owner_id == user.id:
        return True

    return check_user_permission(user, "app", app_id, level, db)


def has_folder_access(user: User, folder_path: str, level: str = "read", db: Session = None) -> bool:
    """检查用户是否有权访问指定 folder
    
    同时检查 folder 权限和上级 app 权限（层级继承）。
    如果用户没有 folder 级别的显式权限，做 app 级别权限的回退检查。
    
    Args:
        user: 用户对象
        folder_path: 文件夹路径
        level: 所需权限级别 (read, write, admin, owner)
        db: 数据库会话
    
    Returns:
        bool: 是否有权限
    """
    if user.is_superuser:
        return True

    # 1) 先检查 folder 级别权限
    if check_user_permission(user, "folder", folder_path, level, db):
        return True

    # 2) 如果没有 folder 权限，尝试 app 级别权限回退
    #    通过文件夹路径找到所属 app（路径格式 /{app_slug}/...）
    if not folder_path:
        return False

    # 路径格式为 /{app_slug}/...，提取第一段作为 app_slug
    parts = folder_path.strip("/").split("/")
    if not parts:
        return False
    app_slug = parts[0]

    from app.models.app import App
    app = db.query(App).filter(App.slug == app_slug).first()
    if not app:
        return False

    # 检查用户是否有 app 级别权限
    return has_app_access(user, app.id, level, db)
async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """获取当前活跃用户（依赖注入）"""
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户未激活"
        )
    return user


async def get_current_active_user_allow_query(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """获取当前活跃用户 - 支持Authorization header或token查询参数
    
    用于需要在iframe中加载的端点（如HTML预览），因为iframe无法设置Authorization header。
    手动从请求header或query参数中提取token，不依赖OAuth2PasswordBearer（它会直接抛出401）。
    """
    # 手动从Authorization header提取token
    authorization = request.headers.get("Authorization")
    token = None
    if authorization:
        from fastapi.security.utils import get_authorization_scheme_param
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer":
            token = param
    
    # 如果header里没有，尝试query参数
    if not token:
        token = request.query_params.get("token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户未激活"
        )
    return user
