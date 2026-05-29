"""
WebBot Auth Security
Shared security utilities using FileBot's user database and JWT compatible with FileBot tokens.

FileBot uses: python-jose (HS256), passlib (pbkdf2_sha256, 30000 rounds)
WebBot runs on system Python, requires: python-jose, passlib
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

# Try to read FileBot's .env for shared SECRET_KEY
_filebot_env = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..",
    "filebot", "backend", ".env"
)

_shared_secret = os.environ.get("JWT_SECRET_KEY")
if not _shared_secret and os.path.exists(_filebot_env):
    with open(_filebot_env) as f:
        for line in f:
            if line.startswith("SECRET_KEY="):
                _shared_secret = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

# Final fallback — must match FileBot's .env value
SECRET_KEY = _shared_secret or os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days (matching FileBot)

# ── FileBot DB path (matching webbot main.py) ──────────────────────────────

FILEBOT_DB_PATH = os.environ.get(
    "FILEBOT_DB_PATH",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..",
        "filebot", "backend", "filebot.db"
    )
)

# ── Password hashing (compatible with FileBot's passlib config) ────────────

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    pbkdf2_sha256__default_rounds=30000,
    deprecated="auto"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against pbkdf2-sha256 hash (FileBot compatible)."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using pbkdf2-sha256 (FileBot compatible)."""
    return pwd_context.hash(password)


# ── JWT utilities (FileBot compatible: python-jose, HS256) ─────────────────

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token (same format as FileBot)."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


# ── User lookup from shared FileBot DB ─────────────────────────────────────

def get_filebot_db() -> Optional[sqlite3.Connection]:
    """Open read-only connection to shared filebot.db."""
    try:
        conn = sqlite3.connect(FILEBOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except sqlite3.Error as e:
        logger.error(f"FileBot DB connection error: {e}")
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Look up a user by UUID string from filebot.db's users table."""
    conn = get_filebot_db()
    if not conn:
        return None
    try:
        row = conn.execute(
            "SELECT id, username, email, full_name, role, is_active, is_superuser FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        logger.error(f"User lookup error: {e}")
        return None
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Look up a user by username from filebot.db's users table."""
    conn = get_filebot_db()
    if not conn:
        return None
    try:
        row = conn.execute(
            "SELECT id, username, email, full_name, password_hash, role, is_active, is_superuser FROM users WHERE username = ? OR email = ?",
            (username, username)
        ).fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        logger.error(f"User lookup error: {e}")
        return None
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user against filebot.db."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    if not user["is_active"]:
        return None
    return user


# ── FastAPI dependency injection ───────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """FastAPI dependency: extract current user from JWT Bearer token."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """FastAPI dependency: ensure current user is active."""
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户未激活"
        )
    return current_user


async def get_current_user_optional(
    request: Request,
) -> Optional[Dict[str, Any]]:
    """Optional auth — extract user if token is present, otherwise return None.
    
    Useful for endpoints that work both with and without authentication.
    """
    authorization = request.headers.get("Authorization")
    token = None
    if authorization:
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer":
            token = param

    if not token:
        token = request.query_params.get("token")

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return get_user_by_id(user_id)
