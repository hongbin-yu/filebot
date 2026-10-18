"""WebBot → FileBot import-url GET proxy.

One-click import of a canada.ca page. The editor builds
`https://www.canada.ca{path}.html` from the current page path and calls
this GET endpoint, which forwards to FileBot's POST /api/v1/import-url
(server-side fetch + import + push back to WebBot).

Why a proxy: FileBot's import-url is a POST endpoint that authenticates
via `get_current_active_user_allow_query` (Bearer token / query token).
The WebBot editor is same-origin and authenticated via cookie, so we
generate a FileBot-compatible JWT server-side (shared SECRET_KEY) and
forward the request — the browser never touches FileBot auth directly.
"""
import os
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from .auth_security import create_access_token, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["import-url"])

FILEBOT_BASE_URL = os.environ.get("FILEBOT_BASE_URL", "http://localhost:8001")
# Server-side fetch of canada.ca + import + push to WebBot can be slow.
IMPORT_TIMEOUT_SECONDS = float(os.environ.get("IMPORT_URL_TIMEOUT", "90"))


@router.get("/import-canada-url")
async def import_url_proxy(
    url: str = Query(..., description="Full canada.ca URL to import"),
    title: str = Query("", description="Optional title override (auto-extracted if empty)"),
    folder_path: str = Query("", description="Optional target folder path in FileBot"),
    redirect_to: str = Query("", description="Optional redirect target"),
    current_user: dict = Depends(get_current_active_user),
):
    """GET proxy → FileBot POST /api/v1/import-url (one-shot import)."""
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    # Generate a FileBot-compatible JWT for the current WebBot user
    # (WebBot and FileBot share SECRET_KEY + user table, HS256).
    try:
        token = create_access_token(data={"sub": current_user["id"]})
    except KeyError:
        raise HTTPException(status_code=401, detail="用户缺少 id 字段")

    payload = {"url": url}
    if title:
        payload["title"] = title
    if folder_path:
        payload["folder_path"] = folder_path
    if redirect_to:
        payload["redirect_to"] = redirect_to

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(IMPORT_TIMEOUT_SECONDS)) as client:
            resp = await client.post(
                f"{FILEBOT_BASE_URL}/api/v1/import-url",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="FileBot import-url timed out")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"FileBot unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"FileBot import-url failed ({resp.status_code}): {resp.text[:500]}",
        )

    try:
        return resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="FileBot returned non-JSON response")
