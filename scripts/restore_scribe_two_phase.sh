#!/usr/bin/env bash
# =============================================================================
# 两阶段恢复（推荐）：apply_schema → data-only import
#
# 在 demo 机执行，依赖 prod-backend-1 + prod-surreal-1。
#
# 用法：
#   ./scripts/restore_scribe_two_phase.sh /path/to/scribe3__main.surql
#   TARGET_DB=restore_tp_main KEEP=1 ./scripts/restore_scribe_two_phase.sh export.surql
#
# 步骤：
#   1) create_work / SurrealStore(db=TARGET).apply_schema()
#   2) 从 export 抽出 TABLE DATA（跳过 _migration）
#   3) surreal import 到 TARGET_DB
#   4) 计数冒烟；默认 KEEP=0 时 REMOVE DATABASE
# =============================================================================
set -euo pipefail

FILE="${1:-}"
CONTAINER_S="${SURREAL_CONTAINER:-prod-surreal-1}"
CONTAINER_B="${BACKEND_CONTAINER:-prod-backend-1}"
NS="${NS:-scribe3}"
TARGET_DB="${TARGET_DB:-restore_tp_$(date +%Y%m%d%H%M%S)}"
KEEP="${KEEP:-0}"
ENV_FILE="${SURREAL_ENV_FILE:-/opt/scribe3/app/deploy/prod/.env}"
WORKDIR="${WORKDIR:-/tmp/restore_tp_$$}"

if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "usage: $0 <full-export.surql>" >&2
  exit 2
fi

USER_NAME="${SURREAL_USER:-}"
PASS_WORD="${SURREAL_PASS:-}"
if [[ -z "$USER_NAME" || -z "$PASS_WORD" ]]; then
  USER_NAME="$(grep -E '^SURREAL_USER=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
  PASS_WORD="$(grep -E '^SURREAL_PASS=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
fi
USER_NAME="${USER_NAME:-root}"

mkdir -p "$WORKDIR"
DATA_ONLY="$WORKDIR/data_only.surql"

# strip script may live next to this script or in /tmp
STRIP="${STRIP_PY:-}"
if [[ -z "$STRIP" ]]; then
  for c in \
    "$(dirname "$0")/surreal_export_data_only.py" \
    /opt/scribe3/app/scripts/surreal_export_data_only.py \
    /tmp/surreal_export_data_only.py \
    /opt/scribe3-host/surreal_export_data_only.py
  do
    [[ -f "$c" ]] && STRIP="$c" && break
  done
fi
if [[ -z "$STRIP" ]]; then
  echo "missing surreal_export_data_only.py" >&2
  exit 1
fi

echo "==> [1/4] data-only extract"
python3 "$STRIP" "$FILE" -o "$DATA_ONLY" --skip-tables _migration
head -5 "$DATA_ONLY"
wc -c "$DATA_ONLY"

echo "==> [2/4] apply_schema on db=$TARGET_DB via backend"
SCHEMA_PY="$WORKDIR/apply_schema.py"
cat >"$SCHEMA_PY" <<PY
from scribe3.store import create_work, SurrealStore
slug = "$TARGET_DB"
try:
    create_work(title="restore two-phase drill", slug=slug)
    print("create_work_ok")
except Exception as e:
    print("create_work:", type(e).__name__, e)
st = SurrealStore(db=slug)
st.apply_schema()
n = len(st._query("SELECT * FROM _migration") or [])
print("migrations", n)
assert n >= 100, n
print("SCHEMA_OK")
PY
docker cp "$SCHEMA_PY" "$CONTAINER_B:/tmp/apply_schema_restore.py"
docker exec -e PYTHONPATH=/app "$CONTAINER_B" python3 -u /tmp/apply_schema_restore.py

echo "==> [3/4] import data-only"
remote="/data/import_data_only_$$.surql"
docker cp "$DATA_ONLY" "$CONTAINER_S:$remote"
if docker exec "$CONTAINER_S" /surreal import \
  --endpoint http://127.0.0.1:8000 \
  -u "$USER_NAME" -p "$PASS_WORD" \
  --namespace "$NS" --database "$TARGET_DB" \
  "$remote" 2>"$WORKDIR/import.err"; then
  echo "IMPORT_OK"
else
  echo "IMPORT_FAIL" >&2
  cat "$WORKDIR/import.err" >&2 || true
  exit 1
fi

echo "==> [4/4] counts"
COUNT_PY="$WORKDIR/count.py"
cat >"$COUNT_PY" <<PY
from scribe3.store import SurrealStore
st = SurrealStore(db="$TARGET_DB")
for t in ("character", "proposition", "chapter", "memory_item", "_migration"):
    try:
        rows = st._query(f"SELECT count() AS c FROM {t} GROUP ALL")
        print(t, (rows or [{}])[0].get("c"))
    except Exception as e:
        print(t, "ERR", e)
print("COUNT_OK")
PY
docker cp "$COUNT_PY" "$CONTAINER_B:/tmp/count_restore.py"
docker exec -e PYTHONPATH=/app "$CONTAINER_B" python3 -u /tmp/count_restore.py

if [[ "$KEEP" != "1" ]]; then
  echo "==> cleanup REMOVE DATABASE $TARGET_DB (KEEP=1 to retain)"
  CLEAN_PY="$WORKDIR/clean.py"
  cat >"$CLEAN_PY" <<PY
from scribe3.store.core_preamble import _reg_conn
db = _reg_conn()
slug = "$TARGET_DB"
try:
    db.query(f"REMOVE DATABASE IF EXISTS {slug}")
    print("removed db")
except Exception as e:
    print("remove db", e)
try:
    db.query("DELETE type::record('work', \$s)", {"s": slug})
    print("removed work row")
except Exception as e:
    print("remove work row", e)
PY
  docker cp "$CLEAN_PY" "$CONTAINER_B:/tmp/clean_restore.py"
  docker exec -e PYTHONPATH=/app "$CONTAINER_B" python3 -u /tmp/clean_restore.py
fi

echo "TARGET_DB=$TARGET_DB two-phase restore DONE"
rm -rf "$WORKDIR"
