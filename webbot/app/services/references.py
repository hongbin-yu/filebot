"""
Page Reference Scanning & Resolution Service

Scans page content for internal links (href and src), normalizes paths,
and provides reference lookup (outgoing + incoming) with existence checks.
"""

import re
import os
import sqlite3
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# ── Constants ────────────────────────────────────────────────

_LANG_PREFIXES = {"en", "fr"}
_INTERNAL_HOSTS = {"", "localhost", "127.0.0.1", "0.0.0.0", "canada.ca", "www.canada.ca"}

# Match ALL local paths AND full canada.ca URLs in href attributes
HREF_RE = re.compile(
    r'href=["\'](https?://(?:www\.)?canada\.ca)?(/[^"\'#?]*)["\']',
    re.IGNORECASE
)

# Match src attributes
SRC_RE = re.compile(
    r'src=["\'](/[^"\'#?]*)["\']',
    re.IGNORECASE
)

BOILERPLATE_EXTENSIONS = {".css", ".js", ".json", ".xml", ".woff", ".woff2", ".ttf", ".eot"}
BOILERPLATE_PREFIXES = ("/gcweb-assets/", "/etc/designs/", "/content/dam/")

# ── Database helpers ──────────────────────────────────────────

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webbot.db")


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_table():
    conn = _get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS page_references (
                source_path TEXT NOT NULL,
                target_path TEXT NOT NULL,
                anchor_text TEXT DEFAULT '',
                scanned_at TEXT DEFAULT (datetime('now')),
                UNIQUE(source_path, target_path, anchor_text)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ref_source ON page_references(source_path)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ref_target ON page_references(target_path)
        """)
        conn.commit()
    finally:
        conn.close()


# ── Path helpers ─────────────────────────────────────────────

def _is_boilerplate(path: str) -> bool:
    """Check if a path is a boilerplate resource (CSS, JS, fonts, etc.)"""
    _, ext = os.path.splitext(path)
    if ext.lower() in BOILERPLATE_EXTENSIONS:
        return True
    if path.startswith(BOILERPLATE_PREFIXES):
        return True
    if "favicon" in path.lower():
        return True
    return False


def _extract_internal_links(source_path: str, html: str) -> list:
    """Extract internal links from page HTML content.

    Handles:
      - href="/en/services/..."          (relative)
      - href="https://www.canada.ca/en/..." (absolute canada.ca)
      - src="/content/dam/..."           (media assets)

    Returns list of dicts: {path, anchor, target_path (normalized)}
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    # Restrict scanning to <main> content only (skip header, footer, navigation)
    main_el = soup.find("main")
    if main_el:
        scan_html = str(main_el.decode_contents())
    else:
        scan_html = html

    seen = set()
    links = []

    def add_link(target_path: str, label: str):
        target_path = target_path.rstrip("/")
        if not target_path or target_path == "/":
            return
        if target_path in seen:
            return
        if _is_boilerplate(target_path):
            return
        # Skip external URLs (scheme but not canada.ca/localhost)
        if "://" in target_path:
            parsed = urlparse(target_path)
            if parsed.hostname and parsed.hostname not in _INTERNAL_HOSTS:
                return
            target_path = "/" + parsed.path.lstrip("/")  # strip hostname
        seen.add(target_path)
        links.append({
            "path": target_path,
            "anchor": label.strip() if label else "",
        })

    for match in HREF_RE.finditer(scan_html):
        href = match.group(0)
        href = href.split("'")[1] if "'" in href else href.split('"')[1]
        # Find surrounding text context (within <main> if present)
        search_root = main_el if main_el else soup
        context_el = search_root.find("a", href=re.compile(re.escape(href), re.IGNORECASE))
        label = context_el.get_text(strip=True) if context_el else ""
        add_link(href, label)

    for match in SRC_RE.finditer(scan_html):
        src = match.group(0)
        src = src.split("'")[1] if "'" in src else src.split('"')[1]
        filename = os.path.basename(src)
        add_link(src, f"[media: {filename}]")

    return links


def _normalize_target_path(target_path: str, source_path: str) -> str:
    """Normalize a target path relative to a source page's site prefix.

    - Strips file extensions (.html, .htm)
    - Handles /content/{site}/... AEM prefix (strips /content)
    - Prepends site prefix (e.g., /canadasite) for /en/..., /fr/... paths
    - Preserves paths already having the site prefix

    Examples:
      /en/services/benefits/ei.html  -> /canadasite/en/services/benefits/ei
      /fr/accueil                    -> /canadasite/fr/accueil
      /content/canadasite/en/home    -> /canadasite/en/home
      /canadasite/en/home            -> /canadasite/en/home  (unchanged)
      /content/dam/photo.jpg         -> /content/dam/photo.jpg (unchanged)
    """
    # Strip file extensions
    target_path = re.sub(r"\.(html?)$", "", target_path, flags=re.IGNORECASE)

    # Extract site prefix from source_path (first path segment)
    parts = source_path.strip("/").split("/")
    if len(parts) >= 2 and parts[1] in _LANG_PREFIXES:
        site_prefix = "/" + parts[0]

        # Strip /content/{site} AEM prefix (e.g., /content/canadasite/en/... -> /canadasite/en/...)
        content_prefix = "/content" + site_prefix
        if target_path.startswith(content_prefix + "/"):
            target_path = target_path[len("/content"):]
        elif target_path == content_prefix or target_path == content_prefix + "/":
            target_path = site_prefix

        # Check if target_path already has the site prefix
        if target_path.startswith(site_prefix):
            return target_path

        # For target paths like /en/..., /fr/..., add site prefix
        for lang_prefix in _LANG_PREFIXES:
            if target_path == "/" + lang_prefix:
                return site_prefix + "/" + lang_prefix
            if target_path.startswith("/" + lang_prefix + "/"):
                return site_prefix + target_path

    return target_path


def _strip_site_prefix(full_path: str) -> str:
    """Strip the site prefix from a path for user-facing display.

    Handles two prefix patterns:
      1. /canadasite/en/...  -> /en/...   (site prefix)
      2. /content/canadasite/en/... -> /en/...  (AEM /content/ prefix)

    Language paths like /en/... or /fr/... are left intact.
    System prefixes like /content/dam/, /publish/, /site/ are left intact.
    """
    if not full_path:
        return full_path

    parts = full_path.strip("/").split("/")

    # Handle /content/{site}/lang/... form (AEM prefix)
    if len(parts) >= 3 and parts[0] == "content" and parts[2] in _LANG_PREFIXES:
        return "/" + "/".join(parts[2:])

    # Handle /content/{site} (no lang)
    if len(parts) == 2 and parts[0] == "content":
        return "/" + parts[1]

    # Handle /{site}/lang/... form — only strip if second segment is a language code
    # This avoids falsely stripping system prefixes like /publish/, /content/dam/, /site/
    if len(parts) >= 2 and parts[1] in _LANG_PREFIXES:
        prefix = "/" + parts[0]
        if full_path.startswith(prefix + "/"):
            return full_path[len(prefix):]
        if full_path == prefix:
            return "/"

    return full_path


# ── Core scanning ─────────────────────────────────────────────

def scan_page_references(source_path: str, content: str):
    """Scan a page's content and store all internal references.

    Deletes old references for this page, then extracts and stores new ones.
    """
    ensure_table()
    links = _extract_internal_links(source_path, content)

    conn = _get_db()
    try:
        # Remove old references for this source
        conn.execute("DELETE FROM page_references WHERE source_path = ?", (source_path,))

        # Insert new references
        for link in links:
            target = _normalize_target_path(link["path"], source_path)
            if not target or target == "/":
                continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO page_references (source_path, target_path, anchor_text) VALUES (?, ?, ?)",
                    (source_path, target, link["anchor"])
                )
            except Exception:
                pass

        conn.commit()
    finally:
        conn.close()


def remove_references_for(source_path: str):
    """Remove all references for a deleted page."""
    ensure_table()
    conn = _get_db()
    try:
        conn.execute("DELETE FROM page_references WHERE source_path = ?", (source_path,))
        conn.commit()
    finally:
        conn.close()


def update_references_path(old_path: str, new_path: str):
    """Update the path in all references after a page rename."""
    ensure_table()
    old_path = old_path.rstrip("/")
    new_path = new_path.rstrip("/")

    conn = _get_db()
    try:
        # Update source_path: exact match
        conn.execute(
            "UPDATE page_references SET source_path = ? WHERE source_path = ?",
            (new_path, old_path)
        )

        # Update source_path: prefix match (subtree / descendants)
        conn.execute(
            "UPDATE page_references SET source_path = ? || substr(source_path, length(?) + 1) "
            "WHERE source_path LIKE ? || '/%'",
            (new_path, old_path, old_path)
        )

        # Update target_path: exact match
        conn.execute(
            "UPDATE page_references SET target_path = ? WHERE target_path = ?",
            (new_path, old_path)
        )

        # Update target_path: prefix match (subtree / descendants)
        conn.execute(
            "UPDATE page_references SET target_path = ? || substr(target_path, length(?) + 1) "
            "WHERE target_path LIKE ? || '/%'",
            (new_path, old_path, old_path, new_path, old_path)
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── API: get references ───────────────────────────────────────

def get_page_references(path: str) -> dict:
    """Get all references for a page: what it links to and what links to it.

    Lazily scans the page if no references exist yet.
    Each reference includes an `exists` field indicating whether the
    target/source page or asset is currently accessible locally.
    """
    ensure_table()

    # Lazy scan: if this page has never been scanned, do it now
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM page_references WHERE source_path = ?",
            (path,)
        )
        ref_count = cur.fetchone()[0]
    finally:
        conn.close()

    if ref_count == 0:
        conn = _get_db()
        try:
            cur = conn.execute(
                "SELECT content FROM webbot_page WHERE path = ?",
                (path,)
            )
            row = cur.fetchone()
        finally:
            conn.close()

        if row and row["content"]:
            scan_page_references(path, row["content"])

    conn = _get_db()
    try:
        # Fetch all outgoing refs
        cur = conn.execute(
            "SELECT target_path, anchor_text FROM page_references WHERE source_path = ? ORDER BY target_path",
            (path,)
        )
        links_to_raw = [{"path": r[0], "anchor": r[1]} for r in cur.fetchall()]

        # Fetch all incoming refs
        cur = conn.execute(
            "SELECT source_path, anchor_text FROM page_references WHERE target_path = ? ORDER BY source_path",
            (path,)
        )
        linked_from_raw = [{"path": r[0], "anchor": r[1]} for r in cur.fetchall()]

        # Check existence + status for each referenced path
        all_check_paths = set()
        for r in links_to_raw:
            all_check_paths.add(r["path"])
        for r in linked_from_raw:
            all_check_paths.add(r["path"])

        # Bulk query all page paths from webbot_page
        page_info = {}
        if all_check_paths:
            placeholders = ",".join(["?"] * len(all_check_paths))
            cur = conn.execute(
                f"SELECT path, status FROM webbot_page WHERE path IN ({placeholders})",
                list(all_check_paths)
            )
            for row in cur.fetchall():
                page_info[row["path"]] = {"exists": True, "status": row["status"]}

        # Paths not in webbot_page: check if they are known asset paths
        _ASSET_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
                             ".pdf", ".doc", ".docx", ".xls", ".xlsx",
                             ".ppt", ".pptx", ".zip", ".csv", ".xml", ".json",
                             ".mp4", ".mp3", ".ico", ".txt"}
        for p in all_check_paths:
            if p in page_info:
                continue
            p_lower = p.lower()
            if p_lower.startswith("/content/dam/") or any(
                p_lower.endswith(ext) for ext in _ASSET_EXTENSIONS
            ):
                page_info[p] = {"exists": True, "status": "file"}
            else:
                page_info[p] = {"exists": False, "status": None}

        links_to = []
        for r in links_to_raw:
            info = page_info.get(r["path"], {"exists": False, "status": None})
            r["exists"] = info["exists"]
            r["status"] = info["status"]
            r["path"] = _strip_site_prefix(r["path"])
            links_to.append(r)

        linked_from = []
        for r in linked_from_raw:
            info = page_info.get(r["path"], {"exists": False, "status": None})
            r["exists"] = info["exists"]
            r["status"] = info["status"]
            r["path"] = _strip_site_prefix(r["path"])
            linked_from.append(r)

        return {
            "path": _strip_site_prefix(path),
            "links_to": links_to,
            "linked_from": linked_from,
            "outgoing_count": len(links_to),
            "incoming_count": len(linked_from),
        }
    finally:
        conn.close()


# ── Bulk scan ──────────────────────────────────────────────────

def full_scan_all_pages(limit: int = 0, offset: int = 0):
    """Scan all existing pages and rebuild references table.

    Args:
        limit: Max pages to scan (0 = all)
        offset: Skip N pages
    """
    ensure_table()
    conn = _get_db()
    try:
        if limit > 0:
            cur = conn.execute(
                "SELECT path, content FROM webbot_page WHERE content IS NOT NULL AND content != '' "
                "ORDER BY path LIMIT ? OFFSET ?",
                (limit, offset)
            )
        else:
            cur = conn.execute(
                "SELECT path, content FROM webbot_page WHERE content IS NOT NULL AND content != '' ORDER BY path"
            )
        pages = cur.fetchall()
    finally:
        conn.close()

    scanned = 0
    errors = 0
    for row in pages:
        path = row["path"]
        content = row["content"]
        try:
            scan_page_references(path, content)
            scanned += 1
        except Exception as e:
            errors += 1

    return {
        "scanned": scanned,
        "errors": errors,
        "total_pages": len(pages),
    }


# ── Search API ────────────────────────────────────────────────

def _autoprefix(raw_prefix: str) -> str:
    """Auto-detect site prefix and prepend if needed."""
    prefix = raw_prefix if raw_prefix.startswith("/") else f"/{raw_prefix}"
    prefix = prefix.rstrip("/")
    if not prefix:
        return prefix
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT DISTINCT substr(source_path, 1, instr(substr(source_path, 2), '/') + 1) AS site "
            "FROM page_references LIMIT 1"
        )
        row = cur.fetchone()
        known_site = row["site"].rstrip("/") if row else "/canadasite"
    finally:
        conn.close()
    if not prefix.startswith(known_site + "/") and prefix != known_site:
        first_seg = prefix.strip("/").split("/")[0]
        if first_seg in _LANG_PREFIXES:
            prefix = known_site + prefix
    return prefix


def search_references(path_prefix: str, status: str = None, target_prefix: str = None) -> dict:
    """Search references by path prefix and optional filters.

    Args:
        path_prefix: Path prefix to search (e.g., /en/services)
        status: Filter by target status: published, draft, file, broken (optional)
        target_prefix: Filter by target path prefix (e.g., /content/dam to find image refs)

    Returns:
        dict with matched results and counts grouped by direction.
    """
    ensure_table()
    prefix = _autoprefix(path_prefix)
    t_prefix = _autoprefix(target_prefix) if target_prefix else None

    conn = _get_db()
    try:
        # Two queries: path as source (outgoing) or target (incoming)
        cur = conn.execute(
            """SELECT source_path, target_path, anchor_text, 'outgoing' AS direction
               FROM page_references WHERE source_path = ? OR source_path LIKE ?
               ORDER BY source_path, target_path""",
            (prefix, f"{prefix}/%")
        )
        outgoing_raw = cur.fetchall()

        cur = conn.execute(
            """SELECT source_path, target_path, anchor_text, 'incoming' AS direction
               FROM page_references WHERE target_path = ? OR target_path LIKE ?
               ORDER BY source_path, target_path""",
            (prefix, f"{prefix}/%")
        )
        incoming_raw = cur.fetchall()

        # Collect all unique paths for bulk status lookup
        all_paths = set()
        for r in outgoing_raw + incoming_raw:
            all_paths.add(r["source_path"])
            all_paths.add(r["target_path"])

        # Build status info for all referenced paths
        path_info = {}
        if all_paths:
            placeholders = ",".join(["?"] * len(all_paths))
            cur = conn.execute(
                f"SELECT path, status FROM webbot_page WHERE path IN ({placeholders})",
                list(all_paths)
            )
            for row in cur.fetchall():
                path_info[row["path"]] = {"exists": True, "status": row["status"]}

        # Asset extension set
        _ASSET_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
                             ".pdf", ".doc", ".docx", ".xls", ".xlsx",
                             ".ppt", ".pptx", ".zip", ".csv", ".xml", ".json",
                             ".mp4", ".mp3"}

        def _get_info(p: str) -> dict:
            if p in path_info:
                return path_info[p]
            p_lower = p.lower()
            if p_lower.startswith("/content/dam/") or any(
                p_lower.endswith(ext) for ext in _ASSET_EXTENSIONS
            ):
                return {"exists": True, "status": "file"}
            return {"exists": False, "status": "broken"}

        # Build results
        results = []
        for r in outgoing_raw + incoming_raw:
            if r["direction"] == "outgoing":
                check_path = r["target_path"]
            else:
                check_path = r["source_path"]

            info = _get_info(check_path)
            target_status = info["status"]

            # Filter by status
            if status and status != target_status:
                continue

            # Filter by target_prefix: for outgoing, check target_path; for incoming, check source_path
            if t_prefix:
                match_path = r["target_path"] if r["direction"] == "outgoing" else r["source_path"]
                if match_path != t_prefix and not match_path.startswith(t_prefix + "/"):
                    continue

            results.append({
                "source_path": _strip_site_prefix(r["source_path"]),
                "target_path": _strip_site_prefix(r["target_path"]),
                "anchor_text": r["anchor_text"],
                "direction": r["direction"],
                "target_status": target_status,
                "exists": info["exists"],
            })

        # Counts
        outgoing_count = sum(1 for r in results if r["direction"] == "outgoing")
        incoming_count = sum(1 for r in results if r["direction"] == "incoming")

        # Unique target paths array — covers both directions
        seen = set()
        targets = []
        for r in results:
            tp = r["target_path"]
            if tp not in seen:
                seen.add(tp)
                targets.append({"path": tp, "status": r["target_status"]})

        return {
            "query": {
                "path_prefix": path_prefix,
                "status": status,
                "target_prefix": target_prefix,
            },
            "results": results,
            "targets": targets,
            "outgoing_count": outgoing_count,
            "incoming_count": incoming_count,
            "total": len(results),
        }
    finally:
        conn.close()
