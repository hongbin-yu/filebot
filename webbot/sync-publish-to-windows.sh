#!/bin/bash
# sync-publish-to-windows.sh
# 将 WSL2 的 publish 数据同步到 Windows 文件系统
# 由 cron 每 2 分钟执行，也可在 publish 后手动触发

SRC="/home/hongb/.openclaw/workspace/filebot/backend/data/publish/"
DST="/mnt/c/webbot/publish/"

if [ ! -d "$SRC" ]; then
    echo "[ERROR] Source not found: $SRC"
    exit 1
fi

mkdir -p "$DST"

rsync -av --delete --exclude='__pycache__' "$SRC" "$DST"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Synced $SRC → $DST"
