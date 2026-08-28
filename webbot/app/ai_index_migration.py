"""
P0 — AI Search incremental index: add tracking columns to webbot_page
========================================================================
Plan: /opt/webfilebot/workspace/docs/ai-search-incremental-index-plan.md

Adds:
  ai_index_status TEXT DEFAULT NULL   (NULL=never indexed, pending, indexed, skipped, error)
  ai_indexed_at  TIMESTAMP            (last successful index time)

Idempotent — safe to run repeatedly. Run against dev first, then prod (P4):
  python3 app/ai_index_migration.py
  WEBBOT_DB_PATH=/path/to/webbot.db python3 app/ai_index_migration.py
"""
import os
import sqlite3
import sys

DB_PATH = os.environ.get(
    "WEBBOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "webbot.db"),
)


def migrate(db_path: str) -> None:
    if not os.path.exists(db_path):
        print(f"❌ WebBot DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(webbot_page)")]
        if "ai_index_status" not in cols:
            conn.execute(
                "ALTER TABLE webbot_page ADD COLUMN ai_index_status TEXT DEFAULT NULL"
            )
            print("✅ added column: ai_index_status")
        else:
            print("⏭️  ai_index_status already exists")

        if "ai_indexed_at" not in cols:
            conn.execute(
                "ALTER TABLE webbot_page ADD COLUMN ai_indexed_at TIMESTAMP"
            )
            print("✅ added column: ai_indexed_at")
        else:
            print("⏭️  ai_indexed_at already exists")

        conn.commit()
        cols = [r[1] for r in conn.execute("PRAGMA table_info(webbot_page)")]
        print(f"📋 webbot_page now has {len(cols)} columns")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate(DB_PATH)
