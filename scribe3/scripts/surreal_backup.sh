#!/usr/bin/env bash
# S-2 SurrealDB 逐书备份(v3.1 docs 优化批):生产库 ~/.scribe2-surreal/data.db
# 此前零备份——书稿是不可再生资产,file 目录热拷贝在 surrealkv 写入中不保证一致,
# 官方一致性备份通道是 `surreal export`(逐 db 导出 SurrealQL 脚本,可 import 恢复)。
#
# 用法:
#   scribe3/scripts/surreal_backup.sh              # 备份 ns=scribe3 全部书(db)
#   SCRIBE3_BACKUP_KEEP=30 …/surreal_backup.sh     # 保留最近 30 份(默认 14)
#
# 恢复(单书):
#   surreal import --endpoint http://127.0.0.1:8001 -u root -p root \
#     --ns scribe3 --db <书slug> ~/.scribe3-backups/<时间戳>/<书slug>.surql
set -euo pipefail

ENDPOINT="${SCRIBE3_SURREAL_HTTP:-http://127.0.0.1:8001}"
NS="${SCRIBE3_SURREAL_NS:-scribe3}"
USER="${SCRIBE3_SURREAL_USER:-root}"
PASS="${SCRIBE3_SURREAL_PASS:-root}"
OUT_ROOT="${SCRIBE3_BACKUP_DIR:-$HOME/.scribe3-backups}"
KEEP="${SCRIBE3_BACKUP_KEEP:-14}"
SURREAL_BIN="${SURREAL_BIN:-$HOME/.surrealdb/surreal}"
command -v "$SURREAL_BIN" >/dev/null 2>&1 || SURREAL_BIN="$(command -v surreal)"

STAMP="$(date '+%Y%m%d-%H%M%S')"
OUT="$OUT_ROOT/$STAMP"
mkdir -p "$OUT"

# 枚举 ns 下全部 db(书):INFO FOR NS 的 databases 键
DBS="$("$SURREAL_BIN" sql --endpoint "$ENDPOINT" -u "$USER" -p "$PASS" \
        --ns "$NS" --json --hide-welcome <<< 'INFO FOR NS;' \
      | python3 -c 'import json,sys
data = json.load(sys.stdin)
row = data[0] if isinstance(data, list) else data
result = row.get("result", row) if isinstance(row, dict) else row
print("\n".join((result or {}).get("databases", {}).keys()))')"

if [ -z "$DBS" ]; then
  echo "❌ ns=$NS 下没有发现任何 db(书),中止" >&2
  exit 1
fi

n=0
while IFS= read -r db; do
  [ -z "$db" ] && continue
  "$SURREAL_BIN" export --endpoint "$ENDPOINT" -u "$USER" -p "$PASS" \
    --ns "$NS" --db "$db" "$OUT/$db.surql"
  size=$(wc -c < "$OUT/$db.surql" | tr -d ' ')
  echo "  ✅ $db → $OUT/$db.surql (${size}B)"
  n=$((n+1))
done <<< "$DBS"

echo "备份完成:$n 本书 → $OUT"

# 轮转:只保留最近 KEEP 份(按目录名时间戳倒序,跳过最新 KEEP 份删其余;
# 不用 head -n -N——BSD/macOS head 不支持负数)
cd "$OUT_ROOT"
ls -1d 20* 2>/dev/null | sort -r | tail -n "+$((KEEP + 1))" | while IFS= read -r old; do
  rm -rf "$OUT_ROOT/${old:?}"
  echo "  ♻ 轮转删除旧备份:$old"
done
echo "当前保留 $(ls -1d 20* 2>/dev/null | wc -l | tr -d ' ') 份(上限 $KEEP)"
