#!/usr/bin/env python3
"""Set per-environment 'domain' in template static data.

Templates: getheader-preview + page-template. The frontend editor reads
data.domain (falls back to labels.live_site, then a hardcoded default) to
build published-page URLs.

Usage: python3 set_publish_domain.py <db_path> <domain>
"""
import sqlite3
import json
import sys

TEMPLATES = [
    '/canadasite/mustache-templates/getheader-preview',
    '/canadasite/mustache-templates/page-template',
]


def main(db_path: str, domain: str) -> None:
    domain = domain.rstrip('/')
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute('PRAGMA busy_timeout=30000')
    cur = conn.cursor()
    try:
        for path in TEMPLATES:
            row = cur.execute(
                'SELECT content FROM webbot_page WHERE path=?', (path,)
            ).fetchone()
            if not row:
                print(f'[SKIP] not found: {path}')
                continue
            raw = row[0]
            try:
                cfg = json.loads(raw)
            except Exception as e:
                print(f'[ERR] parse failed {path}: {e}')
                continue
            data = cfg.get('data')
            if not isinstance(data, dict):
                data = {}
            old = data.get('domain')
            data['domain'] = domain
            cfg['data'] = data
            new_raw = json.dumps(cfg, ensure_ascii=False)
            cur.execute(
                'UPDATE webbot_page SET content=? WHERE path=?',
                (new_raw, path),
            )
            print(f'[OK] {path}: domain {old!r} -> {domain!r}')
        conn.commit()
    finally:
        conn.close()
    print('DONE')


if __name__ == '__main__':
    import os
    db_path = os.environ.get('PUBLISH_DB')
    domain = os.environ.get('PUBLISH_DOMAIN')
    if len(sys.argv) == 3:
        db_path, domain = sys.argv[1], sys.argv[2]
    if not db_path or not domain:
        print('usage: set_publish_domain.py <db_path> <domain>')
        print('   or: PUBLISH_DB=<db> PUBLISH_DOMAIN=<domain> python3 set_publish_domain.py')
        sys.exit(2)
    main(db_path, domain)
