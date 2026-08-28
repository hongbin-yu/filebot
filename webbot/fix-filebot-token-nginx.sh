#!/usr/bin/env bash
# Fix: /api/v1/auth/filebot-token must route to WebBot (8000), not FileBot (8001)
# Exact-match location wins over the prefix match /api/v1/auth -> 8001.
# Safe to run twice (idempotent). Creates .bak-20260802 backups.
set -euo pipefail

FILES=(
  /etc/nginx/sites-enabled/webbot
  /etc/nginx/sites-enabled/webbot-http
)

INSERT='location = /api/v1/auth/filebot-token { proxy_pass http://127.0.0.1:8000; proxy_http_version 1.1; proxy_set_header Host \$host; proxy_set_header X-Real-IP \$remote_addr; proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto https; }'

for f in "${FILES[@]}"; do
  [ -f "$f" ] || { echo "SKIP (not a file): $f"; continue; }
  if grep -q 'location = /api/v1/auth/filebot-token' "$f"; then
    echo "ALREADY PATCHED: $f"
    continue
  fi
  cp "$f" "$f.bak-20260802"
  perl -0pi -e 's|( *)location /api/v1/auth |$1'"$INSERT"'\n$1location /api/v1/auth |g' "$f"
  echo "PATCHED: $f"
done

echo "--- nginx config test ---"
nginx -t

echo "--- reload nginx ---"
nginx -s reload
echo "DONE"
