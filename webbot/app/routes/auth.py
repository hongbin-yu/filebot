"""
Auth 路由 - FileBot 令牌管理
直接转发 FileBot 的登录响应，保持前端兼容性
"""

from fastapi import APIRouter, HTTPException
import httpx
import os

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

FILEBOT_BASE_URL = os.environ.get("FILEBOT_BASE_URL", "http://localhost:8001")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@router.get("/filebot-token")
async def get_filebot_token():
    """获取 FileBot JWT 令牌（转发 FileBot 登录响应）"""
    try:
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
            
            # Return FileBot's response directly (access_token, token_type, user)
            return data

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"FileBot connection failed: {str(e)}")
