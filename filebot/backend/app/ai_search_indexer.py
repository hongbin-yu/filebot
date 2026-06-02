"""
AI Search Indexer — Phase 1
============================
Read WebBot canada.ca services pages → chunk by <h2> → embed → store in pgvector

Usage:
  cd /home/hongb/.openclaw/workspace/filebot/backend
  ../venv/bin/python -m app.ai_search_indexer

Or with whisper venv (has torch):
  /home/hongb/.local/venv/whisper/bin/python -m app.ai_search_indexer
"""

import os
import re
import sys
import sqlite3
import html as html_mod
from datetime import datetime

# --- Configuration ---
WEBBOT_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),  # app/
    "..", "..", "..", "webbot", "app", "webbot.db"
)
WEBBOT_DB = os.path.normpath(WEBBOT_DB)

# PostgreSQL — matches .env for filebot backend
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "filebot")
DB_USER = os.environ.get("DB_USER", "filebot")
DB_PASS = os.environ.get("DB_PASS", "filebot")

# Embedding config
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
EMBEDDING_DIM = 384  # e5-small output dimension
CHUNK_MIN_CHARS = 50
CHUNK_OVERLAP_CHARS = 120  # slightly more overlap for bge-m3

# --- Configuration: which paths to index ---
# Each entry: (path_pattern, exact_match_paths)
#   path_pattern: SQL LIKE pattern for sub-pages
#   exact_match_paths: exact paths to include (the root itself)
DEFAULT_SCOPES = [
    {
        "label": "services",
        "like": ["/canadasite/en/services/%", "/canadasite/fr/services/%"],
        "exact": ["/canadasite/en/services", "/canadasite/fr/services"],
    },
    {
        "label": "auditor-general",
        "like": [
            "/canadasite/en/auditor-general/%",
            "/canadasite/fr/verificateur-general/%",
        ],
        "exact": [
            "/canadasite/en/auditor-general",
            "/canadasite/fr/verificateur-general",
        ],
        "exclude": [  # pages to skip (user's own pages, not OAG content)
            "/canadasite/en/auditor-general/ai-search",
        ],
    },
]


# --- Step 1: Fetch pages from WebBot ---
def fetch_webbot_pages(db_path, scopes=None):
    """Fetch pages matching given scopes from WebBot DB."""
    if scopes is None:
        scopes = DEFAULT_SCOPES

    if not os.path.exists(db_path):
        print(f"❌ WebBot DB not found: {db_path}")
        sys.exit(1)

    sql_conditions = []
    sql_params = []
    exclude_paths = []

    for scope in scopes:
        for pattern in scope.get("like", []):
            sql_conditions.append("path LIKE ?")
            sql_params.append(pattern)
        for exact in scope.get("exact", []):
            sql_conditions.append("path = ?")
            sql_params.append(exact)
        for excl in scope.get("exclude", []):
            exclude_paths.append(("path != ?", excl))

    # Build WHERE clause
    where_clause = " OR ".join(sql_conditions)
    if exclude_paths:
        for clause, val in exclude_paths:
            where_clause = f"({where_clause}) AND {clause}"
            sql_params.append(val)

    where_clause = f"({where_clause}) AND content IS NOT NULL AND length(content) > 100"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    sql = f"""
        SELECT path, title, content, language,
               COALESCE(description, '') as description,
               COALESCE(keywords, '') as keywords
        FROM webbot_page
        WHERE {where_clause}
        ORDER BY path
    """

    labels = [s["label"] for s in scopes]
    print(f"🔍 Scopes: {', '.join(labels)}")
    c.execute(sql, sql_params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    print(f"📄 Fetched {len(rows)} pages from WebBot")
    return rows


# --- Step 2: Chunking by <h2> ---
def strip_html_tags(text):
    """Remove HTML tags, keep text. Also strips nav/footer boilerplate/survey."""
    text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)
    text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL)
    text = re.sub(r'<aside[^>]*>.*?</aside>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html_mod.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_h2_chunks(page):
    """Split HTML content by <h2> tags. Returns list of chunks with metadata."""
    content = page["content"]
    path = page["path"]
    lang = page["language"]
    title = page["title"]

    # Split by <h2> tags (handle various formats: <h2>, <h2 class="...">, </h2>)
    # Pattern: match everything up to and including an opening <h2...> tag
    sections = re.split(r'<h2[^>]*>', content, flags=re.IGNORECASE)

    chunks = []
    for i, section in enumerate(sections):
        if not section.strip():
            continue

        # Extract the heading text (everything up to </h2>)
        heading = ""
        heading_match = re.match(r'(.*?)</h2>', section, re.DOTALL)
        if heading_match:
            heading = strip_html_tags(heading_match.group(1)).strip()

        # The body is everything after </h2>
        body = section
        if heading_match:
            body = section[heading_match.end():]

        body_text = strip_html_tags(body).strip()

        if len(body_text) < CHUNK_MIN_CHARS:
            continue

        # Build canonical URL (for source citations)
        # /canadasite/en/services/health → https://www.canada.ca/en/services/health
        service_path = path.replace("/canadasite", "https://www.canada.ca")
        if heading:
            anchor = heading.lower().replace(" ", "-").replace("—", "").replace("–", "")
            anchor = re.sub(r'[^a-z0-9\-]', '', anchor)
            service_path += f"#{anchor}"

        chunks.append({
            "page_path": path,
            "page_title": title,
            "language": lang,
            "heading": heading or f"Section {i}",
            "heading_level": 2,
            "section_index": i,
            "text": body_text,
            "source_url": service_path,
            "char_count": len(body_text),
        })

    return chunks


# --- Step 3: Embedding ---
def get_embedding_model(model_name):
    """Load sentence-transformers model."""
    from sentence_transformers import SentenceTransformer

    print(f"🔄 Loading embedding model: {model_name}...")
    model = SentenceTransformer(model_name)
    print(f"   ✅ Model loaded. Device: {model.device}, Dim: {model.get_sentence_embedding_dimension()}")
    return model


def embed_chunks(model, chunks, batch_size=32):
    """Generate embeddings for all chunks."""
    # No prefix needed for BGE-M3 (unlike E5 which requires 'passage: ' prefix)
    texts = [c['text'] for c in chunks]

    print(f"🔄 Generating embeddings for {len(texts)} chunks (batch_size={batch_size})...")
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)

    for i, emb in enumerate(embeddings):
        chunks[i]["embedding"] = emb.tolist()

    print(f"   ✅ Embeddings generated")
    return chunks


# --- Step 4: Store in pgvector ---
def ensure_table(conn):
    """Create the search_chunks table if it doesn't exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_chunks (
            id SERIAL PRIMARY KEY,
            page_path TEXT NOT NULL,
            page_title TEXT,
            language TEXT NOT NULL,
            heading TEXT,
            heading_level INTEGER DEFAULT 2,
            section_index INTEGER,
            text TEXT NOT NULL,
            source_url TEXT,
            char_count INTEGER,
            embedding vector(%d),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """ % EMBEDDING_DIM)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_chunks_lang ON search_chunks(language);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_chunks_page ON search_chunks(page_path);
    """)
    conn.commit()
    print(f"   ✅ Table search_chunks ready (dim={EMBEDDING_DIM})")


def store_chunks(conn, chunks, clear_first=True):
    """Insert chunks with embeddings into pgvector."""
    import psycopg2.extras

    cur = conn.cursor()

    if clear_first:
        cur.execute("TRUNCATE search_chunks")
        print("   🧹 Cleared existing chunks")

    # Insert in batches
    batch_size = 100
    inserted = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        values = []
        for c in batch:
            values.append((
                c["page_path"],
                c["page_title"],
                c["language"],
                c["heading"],
                c["heading_level"],
                c["section_index"],
                c["text"],
                c["source_url"],
                c["char_count"],
                c["embedding"],
            ))

        # Use execute_values for bulk insert
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO search_chunks
                (page_path, page_title, language, heading, heading_level,
                 section_index, text, source_url, char_count, embedding)
            VALUES %s
            """,
            values,
            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)",
        )
        inserted += len(batch)
        print(f"   📦 Inserted {inserted}/{len(chunks)} chunks")

    conn.commit()
    print(f"   ✅ All {inserted} chunks stored!")


# --- Step 5: Search (for testing) ---
def search_chunks(conn, query, lang="en", top_k=5):
    """Simple search to verify the pipeline works."""
    from sentence_transformers import SentenceTransformer
    import psycopg2.extras

    # Load model and embed query
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_emb = model.encode(f"query: {query}", normalize_embeddings=True)

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT page_title, heading, text, source_url, char_count,
               1 - (embedding <=> %s::vector) as similarity
        FROM search_chunks
        WHERE language = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_emb.tolist(), lang, query_emb.tolist(), top_k)
    )
    results = cur.fetchall()
    cur.close()
    return results


# --- Main ---
def main():
    print("=" * 60)
    print("🔍 AI Search Indexer — Phase 1")
    print(f"   Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # Step 1: Fetch pages
    print("\n📥 Step 1: Fetching pages from WebBot...")
    pages = fetch_webbot_pages(WEBBOT_DB) # uses DEFAULT_SCOPES

    # Step 2: Chunk
    print(f"\n✂️  Step 2: Chunking by <h2>...")
    all_chunks = []
    en_count = fr_count = 0
    for page in pages:
        chunks = extract_h2_chunks(page)
        all_chunks.extend(chunks)
        if page["language"] == "en":
            en_count += len(chunks)
        else:
            fr_count += len(chunks)

    print(f"   Total chunks: {len(all_chunks)} (EN: {en_count}, FR: {fr_count})")

    if not all_chunks:
        print("❌ No chunks generated. Check WebBot data.")
        sys.exit(1)

    # Show samples
    print("\n   Sample chunks:")
    for c in all_chunks[:3]:
        print(f"     📄 {c['page_title']} > {c['heading']}")
        print(f"        ({c['char_count']} chars, {c['language']})")
        print(f"        🔗 {c['source_url']}")

    # Step 3: Embed
    print(f"\n🧠 Step 3: Generating embeddings...")
    model = get_embedding_model(EMBEDDING_MODEL)
    all_chunks = embed_chunks(model, all_chunks)

    # Step 4: Store
    print(f"\n💾 Step 4: Storing in pgvector...")
    import psycopg2
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    ensure_table(conn)
    store_chunks(conn, all_chunks, clear_first=True)
    conn.close()

    # Step 5: Test search
    print(f"\n🧪 Step 5: Testing search...")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    test_queries = [
        ("en", "how to apply for EI benefits"),
        ("en", "file income tax return"),
        ("en", "apply for Canadian passport"),
        ("fr", "comment faire une demande de passeport"),
        ("fr", "déclaration de revenus"),
    ]
    for lang, query in test_queries:
        print(f"\n   🔎 [{lang}] \"{query}\":")
        results = search_chunks(conn, query, lang=lang, top_k=3)
        for r in results:
            sim = r["similarity"] * 100
            text_preview = r["text"][:120].replace("\n", " ")
            print(f"      [{sim:.0f}%] {r['page_title']} > {r['heading']}")
            print(f"             {text_preview}...")
            print(f"             🔗 {r['source_url']}")

    conn.close()

    print(f"\n{'=' * 60}")
    print("✅ AI Search Indexer complete!")
    print(f"   {len(all_chunks)} chunks indexed from {len(pages)} pages")
    print(f"   EN: {en_count} chunks | FR: {fr_count} chunks")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
