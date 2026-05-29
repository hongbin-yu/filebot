"""
Permission utility functions for Webbot — folder-level access control.

Since webbot has only one app (Boarding/Canada.ca), app-level filtering is
too coarse. This module implements folder-level permission checks directly
on page paths.

Permission model (inheritance):
  - A user has a permission (read/write) on a folder path
  - That folder and ALL descendants inherit the full permission level
  - ANCESTORS of the permitted folder are visible (for navigation to it)
    but NOT writable and do NOT grant access to sibling folders
  - Superusers (is_superuser=true in users table) bypass all checks

Path mapping:
  - FileBot folders use /boarding/canadasite/... paths
  - Webbot pages use /canadasite/... paths
  - This module normalises both by stripping /boarding prefix when comparing
"""

import sqlite3
import os
from typing import Set, Optional, List, Dict, Tuple, Any

FILEBOT_DB_PATH = os.environ.get(
    "FILEBOT_DB_PATH",
    "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
)


def get_filebot_db_connection() -> sqlite3.Connection:
    """Get read-only connection to filebot.db"""
    conn = sqlite3.connect(f"file:{FILEBOT_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _normalise_path(path: str) -> str:
    """Strip /boarding prefix so folder paths match page paths.

    Folder path: /boarding/canadasite/en/services
    Page path:   /canadasite/en/services
    Both →      /canadasite/en/services
    """
    if path.startswith("/boarding"):
        return path[len("/boarding"):] or "/"
    return path


def get_user_folder_permissions(user_id: str) -> Dict[str, str]:
    """
    Get all folder-level permissions for a user (direct + group-based).

    Returns:
        {normalised_folder_path: max_permission_level}
        e.g. {"/canadasite/en/services": "write", ...}

    Permission levels (highest to lowest):
        owner > admin > write > read
    """
    level_rank = {"none": 0, "read": 1, "write": 2, "admin": 3, "owner": 4}

    try:
        conn = get_filebot_db_connection()
        cursor = conn.cursor()

        # 1. Superuser check — shortcut
        cursor.execute("SELECT is_superuser FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user and user["is_superuser"]:
            conn.close()
            return {"*": "owner"}  # Wildcard marker

        # 2. Direct user → folder permissions
        cursor.execute("""
            SELECT resource_id, permission_level FROM permissions
            WHERE resource_type = 'folder' AND user_id = ?
        """, (user_id,))
        perms: Dict[str, str] = {}
        for row in cursor.fetchall():
            normalised = _normalise_path(row["resource_id"])
            existing = perms.get(normalised, "none")
            if level_rank.get(row["permission_level"], 0) > level_rank.get(existing, 0):
                perms[normalised] = row["permission_level"]

        # 3. Group-based folder permissions
        cursor.execute("""
            SELECT p.resource_id, p.permission_level FROM permissions p
            JOIN group_members gm ON p.group_id = gm.group_id
            WHERE p.resource_type = 'folder' AND gm.user_id = ?
        """, (user_id,))
        for row in cursor.fetchall():
            normalised = _normalise_path(row["resource_id"])
            existing = perms.get(normalised, "none")
            if level_rank.get(row["permission_level"], 0) > level_rank.get(existing, 0):
                perms[normalised] = row["permission_level"]

        conn.close()
        return perms

    except Exception as e:
        print(f"[permission_utils] Error checking folder permissions: {e}")
        return {"*": "owner"}  # Fail open — allow everything on error


def _is_page_accessible(page_path: str, permitted_folders: Dict[str, str],
                        require_write: bool = False) -> bool:
    """
    Check if a page path is accessible based on folder permissions.

    A page is accessible (visible/readable) if:
      - It matches a permitted folder exactly, OR
      - It is a descendant of a permitted folder, OR
      - It is an ancestor of a permitted folder (route to it)

    A page is writable if:
      - It matches a write-permitted folder exactly, OR
      - It is a descendant of a write-permitted folder
      (Ancestors are NOT writable — consistent with inheritance rule)
    """
    # Wildcard check
    if "*" in permitted_folders:
        level = permitted_folders["*"]
        is_writable_global = level in ("write", "admin", "owner")
        if require_write:
            return is_writable_global
        return True

    level_rank = {"none": 0, "read": 1, "write": 2, "admin": 3, "owner": 4}

    for fpath, flevel in permitted_folders.items():
        # Root is always accessible for navigation if user has any permission
        if page_path == "/":
            return True

        # Page is under or equals the permitted folder
        if page_path == fpath or page_path.startswith(fpath + "/"):
            if require_write:
                # Only writable if the permitted folder has write permission
                return level_rank.get(flevel, 0) >= level_rank["write"]
            return True

        # Page is an ANCESTOR of the permitted folder (for navigation route)
        if not require_write and fpath.startswith(page_path + "/"):
            return True

    return False


def user_can_see_page(user_id: str, page_path: str) -> bool:
    """Check if a user can SEE a page based on folder permissions."""
    perms = get_user_folder_permissions(user_id)
    return _is_page_accessible(page_path, perms, require_write=False)


def user_can_write_page(user_id: str, page_path: str) -> bool:
    """Check if a user can WRITE (edit/delete) a page."""
    perms = get_user_folder_permissions(user_id)
    return _is_page_accessible(page_path, perms, require_write=True)


def filter_pages_by_permission(
    pages: List[Any],
    user_id: str,
    path_attr: str = "path",
    require_write: bool = False
) -> List[Any]:
    """
    Filter a list of page objects/dicts, keeping only those the user can
    see (or write) based on folder-level permissions.

    Parameters:
        pages: List of page objects (dict-like with a path attribute)
        user_id: The user's UUID
        path_attr: The attribute name for page path (default 'path')
        require_write: If True, only return pages user can write

    Returns:
        Filtered list of pages
    """
    perms = get_user_folder_permissions(user_id)

    def _get_path(p: Any) -> str:
        if isinstance(p, dict):
            return p.get(path_attr, "")
        return getattr(p, path_attr, "")

    return [p for p in pages
            if _is_page_accessible(_get_path(p), perms, require_write=require_write)]
