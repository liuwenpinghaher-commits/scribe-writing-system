#!/usr/bin/env bash
# 旁路 restore 演练：把 backup 的 .surql import 到 **新 database 名**（不覆盖正式库）
#
# 用法（demo 机）:
#   ./scripts/restore_surreal_side_db.sh /opt/scribe3/backups/surreal/20260808-185520/scribe3__main.surql
#   TARGET_DB=restore_drill_main ./scripts/restore_surreal_side_db.sh path/to.surql
#
# 成功标准：import 后 SELECT count 可查；演练完可 REMOVE DATABASE。
set -euo pipefail

FILE="${1:-}"
CONTAINER="${SURREAL_CONTAINER:-prod-surreal-1}"
NS="${NS:-scribe3}"
TARGET_DB="${TARGET_DB:-restore_drill_$(date +%Y%m%d%H%M%S)}"
ENV_FILE="${SURREAL_ENV_FILE:-/opt/scribe3/app/deploy/prod/.env}"

if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "usage: $0 <export.surql>" >&2
  exit 2
fi
if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "container missing: $CONTAINER" >&2
  exit 1
fi

USER_NAME="${SURREAL_USER:-}"
PASS_WORD="${SURREAL_PASS:-}"
if [[ -z "$USER_NAME" || -z "$PASS_WORD" ]]; then
  USER_NAME="$(grep -E '^SURREAL_USER=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
  PASS_WORD="$(grep -E '^SURREAL_PASS=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
fi
USER_NAME="${USER_NAME:-root}"

# 将文件拷入容器
remote="/tmp/restore_in_$$.surql"
docker cp "$FILE" "$CONTAINER:$remote"

echo "==> import ns=$NS db=$TARGET_DB from $FILE"
# 3.x: 先用 sql 建库再 import（若 import 自带 define 也可）
docker exec "$CONTAINER" /surreal sql --endpoint http://127.0.0.1:8000 \
  -u "$USER_NAME" -p "$PASS_WORD" --ns "$NS" --db "$TARGET_DB" \
  -q "INFO FOR DB;" >/tmp/restore_pre.log 2>&1 || true

if docker exec "$CONTAINER" /surreal import \
  --endpoint http://127.0.0.1:8000 \
  -u "$USER_NAME" -p "$PASS_WORD" \
  --namespace "$NS" --database "$TARGET_DB" \
  "$remote" 2>/tmp/restore_import.err; then
  echo "IMPORT_OK"
else
  echo "IMPORT_FAIL" >&2
  cat /tmp/restore_import.err >&2 || true
  exit 1
fi

echo "==> smoke count on $TARGET_DB"
docker exec "$CONTAINER" /surreal sql --endpoint http://127.0.0.1:8000 \
  -u "$USER_NAME" -p "$PASS_WORD" --ns "$NS" --db "$TARGET_DB" \
  -q "SELECT count() AS c FROM character GROUP ALL; SELECT count() AS c FROM memory_item GROUP ALL;" \
  2>&1 | tee /tmp/restore_count.out || true

if [[ "${KEEP_RESTORE_DB:-0}" != "1" ]]; then
  echo "==> cleanup REMOVE DATABASE $TARGET_DB (set KEEP_RESTORE_DB=1 to keep)"
  docker exec "$CONTAINER" /surreal sql --endpoint http://127.0.0.1:8000 \
    -u "$USER_NAME" -p "$PASS_WORD" --ns "$NS" --db "$TARGET_DB" \
    -q "REMOVE DATABASE IF EXISTS $TARGET_DB;" 2>&1 || true
fi

echo "TARGET_DB=$TARGET_DB DONE"
