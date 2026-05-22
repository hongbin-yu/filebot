"""Import Canada.ca AEM tags into webbot_tag system.

AEM export format is a nested JSON where each cq:Tag node contains:
  - jcr:title → English title
  - jcr:title.fr → French title
  - nested children (also cq:Tag nodes)

Maps AEM namespaces to our dcterms types:
  - themes-and-topics, subjects → "subject"
  - audience → "audience"
  - content-types → "type"
  - georegions, institutions, ministers, page-context, custom → name-as-type
"""

import json, re, sys, os

# ── Config ──────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "webbot.db")
TAG_ROOT = "/canadasite/tags"  # all tags live under this prefix

# Map AEM namespace → our dcterms type
TYPE_MAP = {
    "themes-and-topics": "subject",
    "subjects": "subject",
    "audience": "audience",
    "content-types": "type",
}

# ── Helpers ─────────────────────────────────────────

def slugify(text):
    """Turn any text into a url-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def make_id(parts):
    """Build a unique short ID from the path parts."""
    return "-".join(slugify(p) for p in parts if p)


def make_path(parts):
    """Build the full tag path. Empty parts returns the root."""
    if not parts or not any(parts):
        return TAG_ROOT
    return TAG_ROOT + "/" + "/".join(slugify(p) for p in parts if p)


def walk_tags(node, path_parts, collected):
    """
    Walk a cq:Tag JSON node recursively.
    
    path_parts: list of key names from root to current node
    collected:  list of dicts {id, path, parent_path, title_en, title_fr, type}
    Returns the type string for the root of this sub-tree.
    """
    title_en = node.get("jcr:title", path_parts[-1])
    title_fr = node.get("jcr:title.fr", title_en)

    # Determine type from top-most category
    tag_type = TYPE_MAP.get(path_parts[0], path_parts[0])

    tag_id = make_id(path_parts)
    tag_path = make_path(path_parts)
    parent_path = make_path(path_parts[:-1]) if len(path_parts) > 1 else TAG_ROOT

    collected.append({
        "id": tag_id,
        "path": tag_path,
        "parent_path": parent_path,
        "title_en": title_en,
        "title_fr": title_fr,
        "type": tag_type,
    })

    # Recurse into children
    for key, child in node.items():
        if isinstance(child, dict) and child.get("jcr:primaryType") == "cq:Tag":
            walk_tags(child, path_parts + [key], collected)


# ── Main ────────────────────────────────────────────

def main():
    # Load AEM export
    src = "/mnt/c/Users/hongb/Downloads/tags.txt"
    if not os.path.exists(src):
        print(f"❌ File not found: {src}")
        sys.exit(1)

    with open(src, "r", encoding="utf-8") as f:
        aem_data = json.load(f)

    print(f"📦 Loaded AEM export ({len(aem_data)} top-level keys)")

    # Extract only cq:Tag top-level entries (skip jcr:primaryType etc.)
    categories = {}
    for key, val in aem_data.items():
        if isinstance(val, dict) and val.get("jcr:primaryType") == "cq:Tag":
            categories[key] = val

    print(f"📂 Found {len(categories)} tag namespaces: {', '.join(categories.keys())}")
    print()

    # Walk all tags
    all_tags = []
    for ns_name, ns_node in categories.items():
        walk_tags(ns_node, [ns_name], all_tags)

    print(f"🏷️  Total tags parsed: {len(all_tags)}")
    
    # Stats by type
    by_type = {}
    for t in all_tags:
        by_type.setdefault(t["type"], []).append(t)
    for ttype, tags in sorted(by_type.items()):
        print(f"   {ttype:12s}: {len(tags)} tags")
    print()

    # ── Import into DB ─────────────────────────────
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Check existing tags
    existing = conn.execute("SELECT id FROM webbot_tag").fetchall()
    existing_ids = {r["id"] for r in existing}
    print(f"🗄️  Existing tags in DB: {len(existing_ids)}")

    # Get existing page_tags to preserve relationships if re-importing
    existing_page_tags = conn.execute("SELECT tag_id FROM webbot_page_tags").fetchall()
    existing_page_tag_ids = {r["tag_id"] for r in existing_page_tags}

    # Clear all existing tags and page relationships
    conn.execute("DELETE FROM webbot_page_tags")
    conn.execute("DELETE FROM webbot_tag")
    print("🗑️  Cleared existing tags and page-tag relationships")
    
    # Insert in batches
    inserted = 0
    skipped = 0
    for tag in all_tags:
        try:
            conn.execute(
                """INSERT INTO webbot_tag (id, path, parent_path, title_en, title_fr, type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tag["id"], tag["path"], tag["parent_path"],
                 tag["title_en"], tag["title_fr"], tag["type"])
            )
            inserted += 1
        except sqlite3.IntegrityError as e:
            print(f"⚠️  Duplicate/error: {tag['id']} — {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"✅ Imported: {inserted} tags")
    print(f"⚠️  Skipped: {skipped}")
    
    # Summary of important mappings
    print()
    print("=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print()
    print("Type mappings:")
    for ns, ttype in sorted(TYPE_MAP.items()):
        count = len(by_type.get(ttype, []))
        print(f"  {ns:25s} → {ttype:12s} ({len(by_type.get(ttype, []))} total in type)")
    for ns in sorted(categories):
        if ns not in TYPE_MAP:
            count = len(by_type.get(ns, []))
            print(f"  {ns:25s} → {ns:12s} ({count} tags)")
    
    print()
    print("Sample tags:")
    conn2 = sqlite3.connect(DB_PATH)
    for row in conn2.execute(
        "SELECT id, path, type, title_en, title_fr FROM webbot_tag LIMIT 10"
    ).fetchall():
        print(f"  {row[0]:30s} type={row[2]:12s} EN={row[3]:40s} FR={row[4]}")
    conn2.close()


if __name__ == "__main__":
    main()
