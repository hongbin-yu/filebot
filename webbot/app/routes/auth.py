"""
WebBot Auth 路由
直接使用共享 filebot.db 进行认证（不依赖 FileBot API）
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import os
import logging

from .auth_security import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_user_by_id,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ── Keep backward compatibility: proxy endpoint for external tools ─────────

FILEBOT_BASE_URL = os.environ.get("FILEBOT_BASE_URL", "http://localhost:8001")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@router.get("/filebot-token")
async def get_filebot_token():
    """[Legacy] 获取 FileBot JWT 令牌（转发 FileBot 登录响应）
    
    Kept for backward compatibility with auto-token.html and external tools.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{FILEBOT_BASE_URL}/api/v1/auth/login",
                data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="FileBot login failed")

            data = resp.json()
            if not data.get("access_token"):
                raise HTTPException(status_code=500, detail="No access_token in FileBot response")

            return data
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"FileBot connection failed: {str(e)}")


# ── New auth endpoints (direct DB, no FileBot dependency) ─────────────────

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录 — 直接验证共享 filebot.db"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email", ""),
            "role": user.get("role", "user"),
            "full_name": user.get("full_name", ""),
        }
    }


@router.get("/me")
async def get_me(current_user=Depends(get_current_active_user)):
    """获取当前登录用户信息"""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user.get("email", ""),
        "role": current_user.get("role", "user"),
        "full_name": current_user.get("full_name", ""),
        "is_superuser": bool(current_user.get("is_superuser", False)),
    }


@router.post("/refresh")
async def refresh_token(current_user=Depends(get_current_active_user)):
    """刷新访问令牌"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user["id"]},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout():
    """用户退出（客户端删除 token 即可）"""
    # JWT 是无状态的，只需客户端清除 token
    return {"message": "登出成功"}
