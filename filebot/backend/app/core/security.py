from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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


def check_user_permission(user: User, resource_type: str, resource_id: str, required_level: str) -> bool:
    """检查用户权限
    
    Args:
        user: 用户对象
        resource_type: 资源类型 (app, drawer, folder, document)
        resource_id: 资源ID
        required_level: 所需权限级别 (read, write, admin, owner)
    
    Returns:
        bool: 是否有权限
    """
    # 超级用户拥有所有权限
    if user.is_superuser:
        return True
    
    # TODO: 实现详细的权限检查逻辑
    # 这里先实现简单的检查，后续需要结合权限表
    
    # 临时实现：用户只能访问自己的资源
    # 实际项目中需要根据权限表进行复杂检查
    return True  # 暂时返回True，后续完善
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
