#!/usr/bin/env python3
"""
Import files that exist on disk but have no DB record.
These were copied by cp -a but never tracked in the boarding database.
"""
import sqlite3
import os
import mimetypes
import json
from datetime import datetime, timezone

conn = sqlite3.connect('filebot.db')
cur = conn.cursor()

PUBLISH_DIR = 'data/publish/content/dam'
NOW = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

# Get publish app ID
cur.execute("SELECT id FROM apps WHERE slug = 'publish'")
PUBLISH_APP_ID = cur.fetchone()[0]

inserted = 0
skipped = 0
errors = []

for root, dirs, files in os.walk(PUBLISH_DIR):
    for fname in files:
        full_path = os.path.join(root, fname)
        rel_path = os.path.relpath(full_path, PUBLISH_DIR)
        db_path = '/publish/content/dam/' + rel_path.replace(os.sep, '/')
        
        # Skip if already in DB
        cur.execute('SELECT path FROM documents WHERE path = ?', (db_path,))
        if cur.fetchone():
            skipped += 1
            continue
        
        # Determine metadata
        file_size = os.path.getsize(full_path)
        ext = os.path.splitext(fname)[1].lower().lstrip('.')
        mime_type, _ = mimetypes.guess_type(fname)
        if mime_type is None:
            # fallback for common types
            mime_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'svg': 'image/svg+xml',
                'gif': 'image/gif',
                'webp': 'image/webp',
                'html': 'text/html',
                'txt': 'text/plain',
                'xml': 'application/xml',
                'json': 'application/json',
            }
            mime_type = mime_map.get(ext, 'application/octet-stream')
        
        # Map file extension to uppercase FileType enum name
        filetype_map = {
            'tiff': 'TIFF', 'pdf': 'PDF', 'doc': 'DOC', 'docx': 'DOCX',
            'jpeg': 'JPEG', 'jpg': 'JPG', 'png': 'PNG',
            'txt': 'TXT', 'html': 'HTML', 'htm': 'HTM',
            'pcl': 'PCL', 'ps': 'PS',
        }
        file_type_enum = filetype_map.get(ext, 'OTHER') if ext else 'OTHER'

        # Derive folder_path from db_path
        folder_path = '/'.join(db_path.rstrip('/').split('/')[:-1])
        
        # Ensure parent folder exists
        cur.execute('SELECT path FROM folders WHERE path = ?', (folder_path,))
        if not cur.fetchone():
            # Create folder on the fly
            parts = folder_path.strip('/').split('/')
            name = parts[-1]
            parent_path = '/' + '/'.join(parts[:-1]) if len(parts) > 1 else None
            cur.execute("""
                INSERT OR IGNORE INTO folders (path, app_id, parent_folder_path, name, title, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (folder_path, PUBLISH_APP_ID, parent_path, name, name, NOW, 'system'))
        
        # Storage path on disk
        storage_path = full_path
        
        try:
            cur.execute("""
                INSERT INTO documents (
                    path, folder_path, title, description, status, type, publish_status,
                    original_filename, stored_filename, file_size, file_type, mime_type,
                    storage_path, parent_folder_path, document_metadata,
                    conversion_status, uploaded_by, created_at, created_by,
                    thumbnail_status, classification_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                db_path, folder_path, fname, '',
                'ACTIVE', 'GENERAL', 'PUBLISHED',
                fname, fname, file_size, file_type_enum, mime_type,
                storage_path, folder_path, '{}',
                'COMPLETED', 'system', NOW, 'system',
                'PENDING', 'UNCLASSIFIED'
            ))
            inserted += 1
        except Exception as e:
            errors.append((db_path, str(e)))
        
        # Commit in batches
        if inserted % 500 == 0:
            conn.commit()
            print(f'  Progress: {inserted} inserted...')

conn.commit()
print(f'\n✅ Done: {inserted} inserted, {skipped} skipped, {len(errors)} errors')
if errors:
    for p, e in errors[:10]:
        print(f'  ⚠️ {p}: {e}')
conn.close()
