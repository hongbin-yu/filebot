#!/bin/bash
# ai-approve.sh — AI 批量审批执行器（admin 全权限，无 403）
# 用法:
#   ./ai-approve.sh --prefix=/canadasite --dry-run              # 统计待审批页面
#   ./ai-approve.sh --prefix=/canadasite                        # 审批全站（标记 approved）
#   ./ai-approve.sh --prefix=/canadasite/en/services            # 审批指定路径
#   ./ai-approve.sh --prefix=/canadasite --lang=fr              # 只审批法语
# 参数:
#   --prefix=     路径前缀 (默认 /canadasite)
#   --lang=       en|fr|both (默认 both)
#   --approved-by= 审批人标识 (默认 ai-approve)
#   --dry-run     只统计不审批
set -euo pipefail

PREFIX="/canadasite"
LANG_ARG="both"
APPROVED_BY="ai-approve"
DRY="false"

for arg in "$@"; do
  case "$arg" in
    --prefix=*) PREFIX="${arg#*=}" ;;
    --lang=*)   LANG_ARG="${arg#*=}" ;;
    --approved-by=*) APPROVED_BY="${arg#*=}" ;;
    --dry-run)  DRY="true" ;;
    *) echo "未知参数: $arg"; exit 1 ;;
  esac
done

ssh production "set -e
B='http://localhost:8000/api/v1'
TOK=\$(curl -s -X POST \"\$B/auth/login\" -d 'username=admin&password=admin123' | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"access_token\"])')
MODE='APPROVE (标记 approved, 可发布)' 
[ \"$DRY\" = \"true\" ] && MODE='DRY-RUN (只统计)'
echo \"=== approve-batch: prefix=${PREFIX} lang=${LANG_ARG} approved_by=${APPROVED_BY} — \${MODE} ===\"
curl -s -X POST -H \"Authorization: Bearer \$TOK\" \"\$B/pages/approve-batch?prefix=${PREFIX}&lang=${LANG_ARG}&approved_by=${APPROVED_BY}&dry_run=${DRY}\" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(\"total:\", d[\"total\"], \"| approved:\", d[\"approved\"])
if d.get(\"dry_run\"):
    print(\"(dry-run 模式，未实际审批)\")
from collections import Counter
c = Counter()
for f in d[\"failed\"]:
    sc = f[\"error\"].split(\"[\")[1].split(\"]\")[0] if \"[\" in f[\"error\"] else \"?\"
    c[sc] += 1
if c: print(\"failure status codes:\", dict(c))
for f in d[\"failed\"][:10]: print(\" FAIL:\", f[\"path\"], \"->\", f[\"error\"][:120])
'
"
