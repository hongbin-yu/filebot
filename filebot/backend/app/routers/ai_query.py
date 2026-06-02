"""
AI Query endpoint: semantic search + LLM answer generation with caching.

Endpoint: POST /api/v1/search/ai-query
Body: {"query": str, "lang": "en"|"fr", "site": str (optional), "top_k": int (default 5)}
Response: {"query": ..., "answer": ..., "sources": [...], "cached": bool}
"""

import json
import logging
import os
import re
import time
from typing import Optional

import httpx
import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sentence_transformers import SentenceTransformer
from app.routers.search import get_pg_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["ai-query"])

# Publish directory for saving Q&A pages
PUBLISH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "publish")

# --- Models ---

# Lazy-loaded: load on first request
_model: Optional[SentenceTransformer] = None
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:3.8b-mini-4k-instruct-q4_K_M"
OLLAMA_OPTIONS = {
    "num_predict": 512,
    "temperature": 0.1,
    "num_ctx": 1024,
}

# Third-party LLM API config (from env vars)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")  # ollama | deepseek | openai
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_URL = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _verify_auth(request: Request):
    """
    Auth check: allow X-WebBot-Access internal requests, otherwise validate Bearer token.
    """
    if request.headers.get("X-WebBot-Access") == "true":
        return True  # trusted internal request
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    from app.routers.auth import get_current_active_user
    from fastapi import Depends
    # Manual token validation
    token = auth[7:]
    try:
        from app.routers.auth import decode_access_token
        payload = decode_access_token(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True


EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")


def get_embedding_model():
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


class AIQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    lang: str = Field(default="en")
    site: Optional[str] = Field(default=None, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    provider: str = Field(default="", max_length=20)
    """LLM provider override: "" or "ollama" | "deepseek" | "openai". Empty = use LLM_PROVIDER env."""

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v):
        if v not in ("en", "fr"):
            raise ValueError("lang must be 'en' or 'fr'")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        if v and v not in ("ollama", "deepseek", "openai"):
            raise ValueError("provider must be 'ollama', 'deepseek', or 'openai'")
        return v


class SourceItem(BaseModel):
    page_title: str
    heading: str
    text: str
    source_url: str
    similarity: float


class AIQueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceItem]
    cached: bool
    elapsed_ms: int


# --- Helpers ---


def build_prompt_messages(query: str, chunks: list[dict], lang: str) -> tuple[str, str]:
    """
    Build system + user messages for LLM (works with Ollama, DeepSeek, OpenAI).
    Returns (system, user) tuple.
    """
    chunks_str = "\n---\n".join(
        f"[Source: {c['source_url']}]\n{c['page_title']} > {c['heading']}\n{c['text'][:500]}"
        for c in chunks
    )

    if lang == "fr":
        system = (
            "Tu es un assistant du gouvernement du Canada. "
            "Réponds à la question en te basant UNIQUEMENT sur les extraits ci-dessous. "
            "Cite les sources. Sois concis et précis."
        )
        user = f"Extraits du site Canada.ca :\n{chunks_str}\n\nQuestion: {query}\n\nRéponse:"
    else:
        system = (
            "You are a Government of Canada assistant. "
            "Answer the question based ONLY on the provided Canada.ca excerpts. "
            "Cite your sources. Be concise and accurate."
        )
        user = f"Canada.ca excerpts:\n{chunks_str}\n\nQuestion: {query}\n\nAnswer:"

    return system, user


def embed_query(text: str, model: SentenceTransformer) -> list[float]:
    """Compute embedding for cache lookup."""
    emb = model.encode(text, normalize_embeddings=True)
    return emb.tolist()


def search_chunks(
    conn, query_emb: list[float], lang: str, site: Optional[str], top_k: int
) -> list[dict]:
    """Semantic search in search_chunks."""
    emb_str = "[" + ",".join(str(x) for x in query_emb) + "]"

    sql = """
        SELECT page_title, heading, text, source_url,
               1 - (embedding <=> %s::vector) AS similarity
        FROM search_chunks
        WHERE language = %s
    """
    params: list = [emb_str, lang]

    if site:
        sql += " AND source_url LIKE '%%' || %s || '%%'"
        params.append(site)

    sql += """
        ORDER BY embedding <=> %s::vector ASC
        LIMIT %s
    """
    params += [emb_str, top_k]

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()

    return [
        {
            "page_title": r["page_title"],
            "heading": r["heading"],
            "text": r["text"],
            "source_url": r["source_url"],
            "similarity": round(r["similarity"] * 100, 1),
        }
        for r in rows
    ]


def check_cache(
    conn, query_emb: list[float], lang: str, site: Optional[str], provider: str = "", threshold: float = 0.95
) -> Optional[dict]:
    """Check qa_cache for a semantically similar question (provider-aware)."""
    emb_str = "[" + ",".join(str(x) for x in query_emb) + "]"
    site_val = site or ""

    sql = """
        SELECT query_text, answer_text, sources,
               1 - (query_embedding <=> %s::vector) AS sim
        FROM qa_cache
        WHERE language = %s
          AND (site_filter = %s OR (site_filter = '' AND %s = ''))
          AND provider = %s
          AND 1 - (query_embedding <=> %s::vector) >= %s
        ORDER BY query_embedding <=> %s::vector
        LIMIT 1
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, [emb_str, lang, site_val, site_val, provider, emb_str, threshold, emb_str])
    row = cur.fetchone()
    cur.close()

    if row:
        # Increment hit count
        cur2 = conn.cursor()
        cur2.execute(
            "UPDATE qa_cache SET hit_count = hit_count + 1, updated_at = NOW() WHERE query_text = %s",
            [row["query_text"]],
        )
        cur2.close()
        conn.commit()
        return {
            "query_text": row["query_text"],
            "answer_text": row["answer_text"],
            "sources": json.loads(row["sources"]) if isinstance(row["sources"], str) else row["sources"],
            "similarity": round(row["sim"] * 100, 1),
        }
    return None


def write_cache(conn, query_text: str, query_emb: list[float], answer: str, sources: list, lang: str, site: Optional[str], provider: str = ""):
    """Write to qa_cache."""
    emb_str = "[" + ",".join(str(x) for x in query_emb) + "]"
    site_val = site or ""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO qa_cache (query_embedding, query_text, answer_text, sources, language, site_filter, provider)
        VALUES (%s::vector, %s, %s, %s::jsonb, %s, %s, %s)
        """,
        [emb_str, query_text, answer, json.dumps(sources), lang, site_val, provider],
    )
    cur.close()
    conn.commit()


# --- LLM call ---


def _chat_messages(system: str, user: str) -> list:
    """Build chat message array for API-based providers."""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def call_llm_ollama(prompt: str, timeout_sec: int = 120) -> str:
    """Call ollama to generate answer."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": OLLAMA_OPTIONS,
    }
    try:
        resp = httpx.post(OLLAMA_URL, json=payload, timeout=timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except httpx.TimeoutException:
        logger.warning("Ollama timeout after %ss", timeout_sec)
        raise HTTPException(503, "LLM timeout - try again later")
    except Exception as e:
        logger.error("Ollama error: %s", e)
        raise HTTPException(503, f"LLM unavailable: {e}")


def call_llm_deepseek(system: str, user: str, timeout_sec: int = 120) -> str:
    """Call DeepSeek API chat completions."""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(503, "DeepSeek API key not configured (set DEEPSEEK_API_KEY)")
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": _chat_messages(system, user),
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except httpx.TimeoutException:
        logger.warning("DeepSeek timeout after %ss", timeout_sec)
        raise HTTPException(503, "LLM timeout - try again later")
    except Exception as e:
        logger.error("DeepSeek error: %s", e)
        raise HTTPException(503, f"LLM unavailable: {e}")


def call_llm_openai(system: str, user: str, timeout_sec: int = 120) -> str:
    """Call OpenAI-compatible API chat completions."""
    if not OPENAI_API_KEY:
        raise HTTPException(503, "OpenAI API key not configured (set OPENAI_API_KEY)")
    payload = {
        "model": OPENAI_MODEL,
        "messages": _chat_messages(system, user),
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.post(OPENAI_API_URL, json=payload, headers=headers, timeout=timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except httpx.TimeoutException:
        logger.warning("OpenAI timeout after %ss", timeout_sec)
        raise HTTPException(503, "LLM timeout - try again later")
    except Exception as e:
        logger.error("OpenAI error: %s", e)
        raise HTTPException(503, f"LLM unavailable: {e}")


def call_llm(system: str, user: str, provider: str = "", timeout_sec: int = 120) -> str:
    """Route to the correct LLM provider based on request or env default."""
    provider = provider or LLM_PROVIDER
    if provider == "deepseek":
        return call_llm_deepseek(system, user, timeout_sec)
    elif provider == "openai":
        return call_llm_openai(system, user, timeout_sec)
    else:
        # ollama: build instruct-style prompt from system+user
        prompt = f"<|system|>\n{system}<|end|>\n<|user|>\n{user}<|end|>\n<|assistant|>\n"
        return call_llm_ollama(prompt, timeout_sec)


# --- Endpoint ---


# ---------------------------------------------------------------------------
# Helpers for Q&A page creation
# ---------------------------------------------------------------------------


def _update_qa_index(lang: str, section: str):
    """Scan ai-qa directory and regenerate qa-index.json for this section."""
    qa_dir = os.path.join(PUBLISH_DIR, lang, section, "ai-qa")
    if not os.path.isdir(qa_dir):
        return

    entries = []
    for fname in os.listdir(qa_dir):
        if fname == "qa-index.json" or not fname.endswith(".html"):
            continue
        filepath = os.path.join(qa_dir, fname)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            # Extract metadata from HTML comments and meta tags
            title_match = re.search(r"<title>(.*?)</title>", content)
            desc_match = re.search(r'<meta name="description" content="(.*?)"', content)
            title = title_match.group(1) if title_match else fname
            question = title.replace("Q&A: ", "") if title.startswith("Q&A: ") else title
            description = desc_match.group(1) if desc_match else question
            slug = fname[:-5]  # remove .html
            entries.append({
                "slug": slug,
                "url": f"/{lang}/{section}/ai-qa/{slug}.html",
                "question": question,
                "description": description,
            })
        except Exception as e:
            logger.warning("Failed to read %s: %s", fname, e)

    # Sort by slug
    entries.sort(key=lambda x: x["slug"])

    index_path = os.path.join(qa_dir, "qa-index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"section": section, "language": lang, "entries": entries}, f, indent=2)
    logger.info("Q&A index updated: %s entries for %s/%s", len(entries), lang, section)


def slugify(text: str) -> str:
    """Convert text to URL-safe slug: lowercase, dashes, max 80 chars."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:80]


def render_qa_page(question: str, answer: str, sources: list, lang: str, section: str, slug: str) -> str:
    """Render a publishable HTML page for a Q&A entry."""
    # Title for the page
    title = f"Q&A: {question}"

    # Build sources section
    sources_html = ""
    if sources:
        items = "\n".join(
            f'        <li><a href="{s["source_url"]}">{s.get("page_title", "Source")}</a>'
            f' <small>(heading: {s.get("heading", "")}, relevance: {s.get("similarity", "")}%)</small></li>'
            for s in sources
        )
        lang_note = "Sources" if lang == "en" else "Sources"
        sources_html = f'''<section class="mrgn-tp-lg">
        <h2 id="sources">{lang_note}</h2>
        <ul>{items}</ul>
      </section>'''

    # Build answer (preserve line breaks)
    answer_paragraphs = "\n".join(
        f"      <p>{p.strip()}</p>"
        for p in answer.split("\n") if p.strip()
    )

    # Build page body
    body_class = f"{lang} {section} ai-qa-page"

    return f'''<!DOCTYPE html>
<html lang="{lang}" dir="ltr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="https://www.canada.ca/etc/designs/canada/wet-boew/css/wet-boew.min.css"/>
  <link rel="stylesheet" href="https://www.canada.ca/etc/designs/canada/cdts/v8_0_3/cdts/css/theme.min.css"/>
  <meta name="description" content="{question[:160]}">
  <meta name="dcterms.title" content="{title}">
  <meta name="dcterms.language" title="{lang}" content="{lang}">
  <!-- AI-generated Q&A page -->
  <!-- section: {section} -->
  <!-- slug: {slug} -->
</head>
<body>
  <div class="container">
    <nav class="provisional gc-subway">
      <h1 id="wb-cont">{question}</h1>
    </nav>
    <main property="mainContentOfPage" resource="#wb-main" typeof="WebPageElement">
      <div class="row">
        <div class="col-md-8">
{answer_paragraphs}
        </div>
      </div>
{sources_html}
      <div class="row mrgn-tp-lg">
        <div class="col-md-8">
          <p class="small"><em>AI-generated Q&A, reviewed by content author.</em></p>
        </div>
      </div>
    </main>
  </div>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Save endpoint: Author creates a publish page from AI-generated Q&A
# ---------------------------------------------------------------------------


class SaveQARequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1, max_length=10000)
    sources: list[dict] = Field(default_factory=list)
    section: str = Field(default="services", max_length=200)
    language: str = Field(default="en")
    slug: Optional[str] = Field(default=None, max_length=200)

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v):
        if v not in ("en", "fr"):
            raise ValueError("language must be 'en' or 'fr'")
        return v

    @field_validator("section")
    @classmethod
    def validate_section(cls, v):
        # Only allow safe path characters
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("section must be alphanumeric with dashes/underscores only")
        return v


class SaveQAResponse(BaseModel):
    url: str
    slug: str
    section: str
    language: str


@router.post("/ai-query/save", response_model=SaveQAResponse)
async def save_qa(
    req: SaveQARequest,
    request: Request,
):
    _verify_auth(request)
    # 1. Generate slug from question if not provided
    slug = req.slug or slugify(req.question)
    # Ensure no double dashes, limit length
    slug = re.sub(r"-+", "-", slug).strip("-")[:80]

    # 2. Build file path
    qa_dir = os.path.join(PUBLISH_DIR, req.language, req.section, "ai-qa")
    os.makedirs(qa_dir, exist_ok=True)
    filepath = os.path.join(qa_dir, f"{slug}.html")

    # 3. Handle slug conflicts: if file exists, append -1, -2
    if os.path.exists(filepath):
        base = slug
        counter = 1
        while os.path.exists(filepath):
            slug = f"{base}-{counter}"
            filepath = os.path.join(qa_dir, f"{slug}.html")
            counter += 1

    # 4. Render the Q&A page
    html = render_qa_page(req.question, req.answer, req.sources, req.language, req.section, slug)

    # 5. Write file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    # 6. Build public URL
    url = f"/{req.language}/{req.section}/ai-qa/{slug}.html"
    logger.info("Q&A page saved: %s", url)

    # 7. Record in PostgreSQL documents table so mustache page-list can find it
    try:
        pg_conn = get_pg_conn()
        pg_cursor = pg_conn.cursor()
        pg_path = f"/boarding/canadasite/{req.language}/{req.section}/ai-qa/{slug}"
        pg_parent = f"/boarding/canadasite/{req.language}/{req.section}/ai-qa"
        pg_title = req.question[:255] if req.question else slug
        file_size = os.path.getsize(filepath)
        # Default to admin user for FK constraint; webfront users go through proxy
        admin_id = "4dad6fa1-d521-417f-8877-efe95fcf1f04"
        pg_cursor.execute("""
            INSERT INTO documents (
                path, folder_path, parent_folder_path, title,
                original_filename, stored_filename, file_size, file_type, mime_type,
                uploaded_by, created_by
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, 'HTML', 'text/html',
                %s, %s
            )
            ON CONFLICT (path) DO UPDATE SET
                title = EXCLUDED.title,
                file_size = EXCLUDED.file_size,
                updated_at = NOW()
        """, (
            pg_path, pg_parent, pg_parent, pg_title,
            f"{slug}.html", f"{slug}.html", file_size,
            admin_id, admin_id
        ))
        pg_conn.commit()
        pg_conn.close()
    except Exception as e:
        logger.error("Failed to record Q&A page in documents table: %s", e)

    # 8. Update Q&A index (for front-end search)
    _update_qa_index(req.language, req.section)

    return SaveQAResponse(url=url, slug=slug, section=req.section, language=req.language)


@router.post("/ai-query", response_model=AIQueryResponse)
async def ai_query(
    req: AIQueryRequest,
    request: Request,
):
    _verify_auth(request)
    t0 = time.time()
    model = get_embedding_model()

    # 1. Embed query
    q_emb = embed_query(req.query, model)

    # 2. Open psycopg2 connection
    conn = get_pg_conn()
    try:
        # 3. Check cache (provider-specific)
        provider_key = req.provider or LLM_PROVIDER
        cached = check_cache(conn, q_emb, req.lang, req.site, provider_key)
        if cached:
            sources = [
                SourceItem(**s) if isinstance(s, dict) else SourceItem(**json.loads(s))
                for s in cached["sources"]
            ]
            elapsed = int((time.time() - t0) * 1000)
            return AIQueryResponse(
                query=req.query,
                answer=cached["answer_text"],
                sources=sources,
                cached=True,
                elapsed_ms=elapsed,
            )

        # 4. Search chunks
        chunks = search_chunks(conn, q_emb, req.lang, req.site, req.top_k)
        if not chunks:
            elapsed = int((time.time() - t0) * 1000)
            return AIQueryResponse(
                query=req.query,
                answer="No relevant content found in Canada.ca.",
                sources=[],
                cached=False,
                elapsed_ms=elapsed,
            )

        # 5. Build prompt (system + user) + call LLM
        system, user = build_prompt_messages(req.query, chunks, req.lang)
        answer = call_llm(system, user, req.provider)

        # 6. Write to cache
        try:
            write_cache(conn, req.query, q_emb, answer, chunks, req.lang, req.site, provider_key)
        except Exception as e:
            logger.warning("Cache write failed: %s", e)

        elapsed = int((time.time() - t0) * 1000)
        return AIQueryResponse(
            query=req.query,
            answer=answer,
            sources=[SourceItem(**c) for c in chunks],
            cached=False,
            elapsed_ms=elapsed,
        )
    finally:
        conn.close()
