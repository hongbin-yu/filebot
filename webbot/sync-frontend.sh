#!/bin/bash
# Sync frontend/ → static/ for WebBot
# Why: Server mounts /static/ → frontend/, but in practice both dirs exist
# and some files may be served from static/. Run after editing frontend/ files.

set -e

SRC="$(dirname "$0")/frontend"
DST="$(dirname "$0")/static"

echo "📁 Syncing $SRC → $DST"
rsync -av --delete \
  --exclude='node_modules' \
  --exclude='.git' \
  "$SRC/" "$DST/"

echo "✅ Done  $(date '+%H:%M:%S')"
