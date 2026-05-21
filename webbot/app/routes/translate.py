"""
Content translation routes — uses DeepSeek API to translate HTML content
while preserving tags, attributes, and structure.
"""

from fastapi import APIRouter, HTTPException, Query
import uuid
import sqlite3
import os
import re
import json
import time
import asyncio
from typing import Optional, List

import logging

router = APIRouter(prefix="/api/v1/translate", tags=["translate"])

logger = logging.getLogger(__name__)

WEBBOT_DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db")
)

# DeepSeek API config — read from OpenClaw config
_CONFIG_CACHE = None

def _get_api_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE:
        return _CONFIG_CACHE
    try:
        oc_json = os.path.expanduser("~/.openclaw/openclaw.json")
        with open(oc_json) as f:
            cfg = json.load(f)
        provider = cfg.get("models", {}).get("providers", {}).get("custom-api-deepseek-com", {})
        _CONFIG_CACHE = {
            "base_url": provider.get("baseUrl", "https://api.deepseek.com"),
            "api_key": provider.get("apiKey", ""),
            "model": "deepseek-v4-flash",
        }
        return _CONFIG_CACHE
    except Exception as e:
        logger.warning(f"Failed to read API config: {e}")
        return {"base_url": "https://api.deepseek.com", "api_key": "", "model": "deepseek-v4-flash"}


def _get_db():
    conn = sqlite3.connect(WEBBOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def _call_llm(system_prompt: str, user_content: str) -> str:
    """Call DeepSeek API with the given prompts. Returns the response text."""
    cfg = _get_api_config()
    if not cfg["api_key"]:
        raise HTTPException(500, "Translation service not configured (no API key)")

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,  # low temp for consistent translation
        "max_tokens": 16384,
    }

    import httpx
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{cfg['base_url']}/chat/completions",
            headers=headers,
            json=payload,
        )
        if resp.status_code != 200:
            raise HTTPException(502, f"LLM API error ({resp.status_code}): {resp.text[:200]}")
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip()


def _extract_translatable_text(html: str) -> str:
    """Extract text content from HTML, marking structure for reconstruction."""
    return html  # For now, send full HTML to LLM with instructions to preserve tags


# ── Translation endpoint: single page ──────────────────────────────────────

@router.post("/page")
async def translate_page(
    path: str = Query(..., description="Source page path, e.g. /canadasite/en/components/badges"),
    source_lang: str = Query("en"),
    target_lang: str = Query("fr"),
    dry_run: bool = Query(False, description="If true, return translation without saving"),
):
    """
    Translate a page/component from source_lang to target_lang.
    Source: /canadasite/{source_lang}/...  →  Target: /canadasite/{target_lang}/...
    """
    db = _get_db()
    try:
        # Read source content + title
        row = db.execute("SELECT content, title FROM webbot_page WHERE path = ?", (path,)).fetchone()
        if not row:
            raise HTTPException(404, f"Page not found: {path}")

        source_content = row["content"]
        source_title = row["title"] or ""
        if not source_content or len(source_content.strip()) < 10:
            raise HTTPException(400, "Source content too short or empty")

        # Derive target path
        target_path = path.replace(f"/{source_lang}/", f"/{target_lang}/", 1)
        if target_path == path:
            raise HTTPException(400, f"Cannot derive target path — ensure path contains /{source_lang}/")

        # System prompt for HTML-safe translation
        # System prompt for HTML-safe translation
        source = source_lang.upper()
        target = target_lang.upper()
        system_prompt = (
            "You are a professional translator specializing in Government of Canada web content. "
            f"Translate the following HTML content from {source} to {target} (Canadian French).\n\n"
            "CRITICAL RULES:\n"
            "1. PRESERVE ALL HTML tags, attributes, CSS classes, and IDs exactly as-is\n"
            "2. Only translate visible text content between tags\n"
            "3. Do NOT translate: URLs, href attributes, src attributes, data-* attributes, aria-* attributes\n"
            "4. Preserve all {{mustache}} and {{{triple-mustache}}} variables exactly — do NOT translate variable names\n"
            "5. Use Canadian French spelling and terminology (e.g., 'courriel' not 'email', 'cliquez' not 'clique')\n"
            "6. Preserve lang=\"en\" attribute — do NOT change it\n"
            "7. Return ONLY the translated HTML — no explanations, no markdown wrappers\n"
            "8. Preserve all whitespace and indentation as much as possible"
        )
        translated = await _call_llm(system_prompt, source_content)

        # Verify we got valid content back
        if not translated or len(translated) < 10:
            raise HTTPException(502, "Translation returned empty content")

        if dry_run:
            return {
                "source_path": path,
                "target_path": target_path,
                "source_length": len(source_content),
                "translated_length": len(translated),
                "translated_content": translated,
            }

        # Save to target path
        existing = db.execute("SELECT path FROM webbot_page WHERE path = ?", (target_path,)).fetchone()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        if existing:
            db.execute(
                "UPDATE webbot_page SET content = ?, title = ?, last_modified = ? WHERE path = ?",
                (translated, source_title, now, target_path),
            )
        else:
            # Create new FR page record
            db.execute(
                "INSERT INTO webbot_page (id, path, title, content, created_at, last_modified) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), target_path, source_title, translated, now, now),
            )
        db.commit()

        return {
            "status": "success",
            "source_path": path,
            "target_path": target_path,
            "source_length": len(source_content),
            "translated_length": len(translated),
            "translated_content": translated,
            "created": not existing,
            "updated": bool(existing),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Translation failed: {e}")
    finally:
        db.close()


# ── Batch translation ─────────────────────────────────────────────────────

@router.post("/batch/components")
async def batch_translate_components(
    dry_run: bool = Query(False, description="Report what would be translated without actually doing it"),
    limit: int = Query(0, description="Max components to translate (0 = all)"),
):
    """
    Find all EN components missing FR versions and translate them.
    Only translates paths under /canadasite/en/components/...
    """
    db = _get_db()
    try:
        # Find all EN component pages
        rows = db.execute(
            "SELECT path FROM webbot_page WHERE path LIKE '/canadasite/en/components/%'"
        ).fetchall()

        en_paths = [r["path"] for r in rows]
        fr_expected = {p.replace("/en/", "/fr/", 1) for p in en_paths}

        # Find which FR versions exist
        existing_fr_rows = db.execute(
            "SELECT path FROM webbot_page WHERE path LIKE '/canadasite/fr/components/%'"
        ).fetchall()
        existing_fr = {r["path"] for r in existing_fr_rows}

        # Missing FR = expected but not existing
        missing = sorted(fr_expected - existing_fr)
        # Also check EN pages that have substantial content
        missing_with_content = []
        for fr_path in missing:
            en_path = fr_path.replace("/fr/", "/en/", 1)
            row = db.execute(
                "SELECT LENGTH(content) FROM webbot_page WHERE path = ?", (en_path,)
            ).fetchone()
            if row and row[0] > 50:  # Only if content is substantial
                missing_with_content.append(en_path)

        if not missing_with_content:
            return {"status": "ok", "message": "All components already have FR versions", "total": 0}

        if dry_run:
            return {
                "status": "dry_run",
                "total_en_components": len(en_paths),
                "total_fr_components": len(existing_fr),
                "missing_fr_versions": len(missing),
                "missing_with_content": len(missing_with_content),
                "sample_paths": missing_with_content[:10],
            }

        # Apply limit
        to_translate = missing_with_content
        if limit > 0:
            to_translate = to_translate[:limit]

        results = []
        for i, en_path in enumerate(to_translate):
            try:
                fr_path = en_path.replace("/en/", "/fr/", 1)
                result = await translate_page(path=en_path, dry_run=False)
                results.append(result)
                logger.info(f"[{i+1}/{len(to_translate)}] Translated: {en_path} → {fr_path}")
            except Exception as e:
                results.append({"path": en_path, "error": str(e)})
                logger.error(f"[{i+1}/{len(to_translate)}] Failed: {en_path}: {e}")
            # Small delay between requests to avoid rate limiting
            if i < len(to_translate) - 1:
                await asyncio.sleep(1)

        success_count = sum(1 for r in results if r.get("status") == "success")
        fail_count = sum(1 for r in results if "error" in r)

        return {
            "status": "completed",
            "total_requested": len(to_translate),
            "success": success_count,
            "failed": fail_count,
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Batch translation failed: {e}")
    finally:
        db.close()


# ── Translation status / reports ──────────────────────────────────────────

@router.get("/status")
async def translation_status():
    """Show translation coverage statistics."""
    db = _get_db()
    try:
        en_comp = db.execute(
            "SELECT COUNT(*) FROM webbot_page WHERE path LIKE '/canadasite/en/components/%'"
        ).fetchone()[0]
        fr_comp = db.execute(
            "SELECT COUNT(*) FROM webbot_page WHERE path LIKE '/canadasite/fr/components/%'"
        ).fetchone()[0]
        en_pages = db.execute(
            "SELECT COUNT(*) FROM webbot_page WHERE path LIKE '/canadasite/en/%' AND path NOT LIKE '%/components/%'"
        ).fetchone()[0]
        fr_pages = db.execute(
            "SELECT COUNT(*) FROM webbot_page WHERE path LIKE '/canadasite/fr/%' AND path NOT LIKE '%/components/%'"
        ).fetchone()[0]

        return {
            "components": {"en": en_comp, "fr": fr_comp, "missing_fr": max(0, en_comp - fr_comp)},
            "pages": {"en": en_pages, "fr": fr_pages, "missing_fr": max(0, en_pages - fr_pages)},
        }
    finally:
        db.close()
