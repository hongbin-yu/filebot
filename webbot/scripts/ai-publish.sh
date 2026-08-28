#!/bin/bash
# ai-publish.sh — AI 批量发布执行器（admin 全权限，无 403）
# 两阶段发布（staged publish）:
#   默认: 只发布到 publish 数据库 (write_static=false) → prod.webfilebot.com/en.. 动态渲染检验
#   --sync: 检验通过后，把 DB 渲染结果同步到静态文件 (live) → canadasite.webfilebot.com
# 用法:
#   ./ai-publish.sh --prefix=/canadasite --dry-run              # 全站预览
#   ./ai-publish.sh --prefix=/canadasite/en/services            # 发布到 DB（不碰静态文件）
#   ./ai-publish.sh --prefix=/canadasite/en/services --sync     # 检验后同步静态文件 (live)
#   ./ai-publish.sh --prefix=/canadasite --lang=fr --concurrency=16
#   ./ai-publish.sh --prefix=/canadasite --status=draft --dry-run     # 指定状态
# 参数:
#   --prefix=    路径前缀 (默认 /canadasite)
#   --lang=      en|fr|both (默认 both)
#   --status=    页面状态筛选 (默认 published; 可指定 draft 等)
#   --concurrency= 并发数 (默认 8, 1-50)
#   --sync       同步静态文件 (live)；默认只写 publish 数据库
#   --dry-run    只统计不发布
set -euo pipefail

PREFIX="/canadasite"
LANG_ARG="both"
STATUS="published"
CONC=8
DRY="false"
SYNC="false"

for arg in "$@"; do
  case "$arg" in
    --prefix=*) PREFIX="${arg#*=}" ;;
    --lang=*)   LANG_ARG="${arg#*=}" ;;
    --status=*) STATUS="${arg#*=}" ;;
    --concurrency=*) CONC="${arg#*=}" ;;
    --sync)     SYNC="true" ;;
    --dry-run)  DRY="true" ;;
    *) echo "未知参数: $arg"; exit 1 ;;
  esac
done

WRITE_STATIC="false"
[ "$SYNC" = "true" ] && WRITE_STATIC="true"

ssh production "set -e
B='http://localhost:8000/api/v1'
TOK=\$(curl -s -X POST \"\$B/auth/login\" -d 'username=admin&password=admin123' | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"access_token\"])')
MODE='DB-ONLY (staged, 检验后 --sync 再上静态)' 
[ \"$SYNC\" = \"true\" ] && MODE='SYNC-STATIC (live)'
echo \"=== publish-batch: prefix=${PREFIX} lang=${LANG_ARG} status=${STATUS} concurrency=${CONC} dry_run=${DRY} write_static=${WRITE_STATIC} — \${MODE} ===\"
curl -s -X POST -H \"Authorization: Bearer \$TOK\" \"\$B/pages/publish-batch?prefix=${PREFIX}&lang=${LANG_ARG}&status=${STATUS}&concurrency=${CONC}&dry_run=${DRY}&write_static=${WRITE_STATIC}\" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(\"total:\", d[\"total\"], \"| success:\", d[\"success\"], \"| failed:\", len(d[\"failed\"]))
if d.get(\"dry_run\"):
    print(\"(dry-run 模式，未实际发布)\")
elif d.get(\"write_static\") is False:
    print(\"(DB-ONLY: 已写入 publish 数据库；请先到 prod.webfilebot.com/en.. 检验，通过后运行 --sync 同步静态文件)\")
elif d.get(\"write_static\") is True:
    print(\"(SYNC-STATIC: 静态文件已更新 — live)\")
from collections import Counter
c = Counter()
for f in d[\"failed\"]:
    err = f[\"error\"]
    sc = err.split(\"[\")[1].split(\"]\")[0] if \"[\" in err else \"?\"
    c[sc] += 1
if c: print(\"failure status codes:\", dict(c))
for f in d[\"failed\"][:10]: print(\" FAIL:\", f[\"path\"], \"->\", f[\"error\"][:120])
'
"
