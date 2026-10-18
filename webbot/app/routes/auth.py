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
    decode_access_token,
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


@router.get("/sso")
async def sso_login(token: str, redirect: str = "/static/navigation.html"):
    """带 token 的免登录入口（demo/评委场景）。

    链接形如 /api/v1/auth/sso?token=<jwt>：验证通过后种下
    filebot_token cookie（HttpOnly，与 token 同过期时间），302 跳转编辑器。
    之后所有写操作 API 自动携带 cookie 通过中间件认证。
    """
    import time
    from fastapi.responses import RedirectResponse

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="链接无效或已过期")

    user = get_user_by_id(payload["sub"])
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    exp = payload.get("exp", 0)
    max_age = int(exp - time.time())
    if max_age <= 0:
        raise HTTPException(status_code=401, detail="链接已过期")

    # 仅允许站内相对路径，防开放重定向
    if not redirect.startswith("/") or redirect.startswith("//"):
        redirect = "/static/navigation.html"

    # 前端 webbot-auth.js 的 tokenParam 流程：URL 带 token/user 时写入
    # localStorage（FileBot 同款 key），并自动清理 URL 参数。
    import json as _json
    from urllib.parse import quote
    user_pub = {k: user.get(k) for k in ("id", "username", "email", "full_name", "role", "is_superuser")}
    user_qs = quote(_json.dumps(user_pub, ensure_ascii=False))
    sep = "&" if "?" in redirect else "?"
    redirect = f"{redirect}{sep}token={token}&user={user_qs}"

    # 非 HttpOnly：webbot-auth.js 的 getToken() 用 document.cookie 读取
    # filebot_token 作为 fallback（FileBot 登录 cookie 同款行为）。
    resp = RedirectResponse(url=redirect, status_code=302)
    resp.set_cookie(
        "filebot_token", token,
        max_age=max_age, httponly=False, path="/",
        samesite="lax",
    )
    return resp

