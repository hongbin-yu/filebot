"""
AI Search Incremental Index Worker — P3
=========================================
Consumes the publish→pending queue on webbot_page and incrementally updates
search_chunks in pgvector, one page at a time. No full rebuild, no TRUNCATE.

Run with the whisper venv (the ONLY env with torch, per the 6/21~7/2 full-index
environment — see ai_search_indexer.py header):

  /home/hongb/.local/venv/whisper/bin/python -m app.ai_search_worker [--once]

PostgreSQL target (search_chunks lives on prod):
  DB_HOST / DB_PORT default to localhost:5432. From the dev machine, tunnel to
  prod postgres first:
    ssh -L 5433:127.0.0.1:5432 production
    DB_PORT=5433 /home/hongb/.local/venv/whisper/bin/python -m app.ai_search_worker

Status transitions (webbot_page.ai_index_status):
  pending  → indexed | skipped | error
  error    → retried as pending by re-running (or manual reset)
"""
import os
import sys
import time
import sqlite3
from datetime import datetime

from .ai_search_indexer import (
    WEBBOT_DB,
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS,
    EMBEDDING_MODEL,
    get_embedding_model,
    is_in_scope,
    reindex_page,
    set_page_ai_index_status,
    ensure_table,
)

POLL_INTERVAL = int(os.environ.get("AI_INDEX_POLL_INTERVAL", "30"))  # seconds


def fetch_pending(db_path: str):
    """Return paths with ai_index_status='pending' (oldest first)."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT path FROM webbot_page "
            "WHERE ai_index_status = 'pending' ORDER BY last_published ASC"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def fetch_page(db_path: str, path: str):
    """Load a single page the same way fetch_webbot_pages does."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT path, title, content, language, "
            "       COALESCE(description, '') as description, "
            "       COALESCE(keywords, '') as keywords "
            "FROM webbot_page WHERE path = ?",
            (path,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def run_once(model) -> int:
    """Process all currently-pending pages. Returns how many were handled."""
    import psycopg2

    pending = fetch_pending(WEBBOT_DB)
    if not pending:
        print(f"⏸️  [{datetime.now().isoformat()}] No pending pages")
        return 0

    print(f"📥 [{datetime.now().isoformat()}] {len(pending)} pending page(s)")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )
    ensure_table(conn)  # idempotent — creates/self-heals search_chunks (incl. description col)
    handled = 0
    try:
        for path in pending:
            print(f"\n📄 {path}")
            page = fetch_page(WEBBOT_DB, path)
            if page is None:
                print("   ⚠️  page vanished — marking error")
                set_page_ai_index_status(WEBBOT_DB, path, "error")
                handled += 1
                continue

            if not is_in_scope(path):
                print("   🚫 out of scope → skipped")
                set_page_ai_index_status(WEBBOT_DB, path, "skipped")
                handled += 1
                continue

            chunk_count, err = reindex_page(page, conn, model=model)
            if err:
                print(f"   ❌ {err}")
                set_page_ai_index_status(WEBBOT_DB, path, "error")
            else:
                print(f"   ✅ {chunk_count} chunk(s) indexed")
                set_page_ai_index_status(
                    WEBBOT_DB, path, "indexed",
                    indexed_at=datetime.now().isoformat(),
                )
            handled += 1
    finally:
        conn.close()
    return handled


def main():
    print("=" * 60)
    print("🤖 AI Search Incremental Index Worker — P3")
    print(f"   Model: {EMBEDDING_MODEL}")
    print(f"   DB:    {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"   WebBot: {WEBBOT_DB}")
    print("=" * 60)

    model = get_embedding_model(EMBEDDING_MODEL)

    if "--once" in sys.argv:
        run_once(model)
        return

    print(f"🔄 Polling every {POLL_INTERVAL}s (Ctrl+C to stop)...")
    while True:
        try:
            run_once(model)
        except KeyboardInterrupt:
            print("\n👋 Stopped")
            break
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            print(f"💥 Worker error: {type(exc).__name__}: {exc}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
