#!/usr/bin/env bash
# 在开发机打包待迁数据（Surreal 逐书 + settings sqlite + Hermes 密钥/配置）。
# 用法:
#   bash deploy/prod/scripts/export_local_data.sh
# 产出: /tmp/scribe3-cloud-migrate-<stamp>.tgz
set -euo pipefail

ENDPOINT="${SCRIBE3_SURREAL_HTTP:-http://127.0.0.1:8001}"
NS="${SCRIBE3_SURREAL_NS:-scribe3}"
USER="${SCRIBE3_SURREAL_USER:-root}"
PASS="${SCRIBE3_SURREAL_PASS:-root}"
SURREAL_BIN="${SURREAL_BIN:-$(command -v surreal || true)}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SETTINGS_SRC="${SCRIBE3_SETTINGS_DB:-$HOME/.scribe2-surreal/scribe3_settings.sqlite3}"
LEDGER_SRC="${SCRIBE3_LLM_LEDGER:-$HOME/.scribe2-surreal/scribe3_llm_ledger.sqlite3}"

STAMP="$(date '+%Y%m%d-%H%M%S')"
OUT_ROOT="${OUT_ROOT:-/tmp/scribe3-cloud-migrate-$STAMP}"
mkdir -p "$OUT_ROOT/surql" "$OUT_ROOT/settings" "$OUT_ROOT/hermes"

if [ -z "$SURREAL_BIN" ]; then
  echo "找不到 surreal CLI" >&2
  exit 1
fi

echo "==> 枚举 ns=$NS 全部 db"
DBS="$("$SURREAL_BIN" sql --endpoint "$ENDPOINT" -u "$USER" -p "$PASS" \
        --ns "$NS" --json --hide-welcome <<< 'INFO FOR NS;' \
      | python3 -c 'import json,sys
data=json.load(sys.stdin)
row=data[0] if isinstance(data,list) else data
result=row.get("result",row) if isinstance(row,dict) else row
dbs=(result or {}).get("databases",{}) or {}
# 跳过明显测试/探针库，仍导出真实书与 main
skip_prefixes=("e2e_","race_","watchdog_","hermes_mcp_","mcp_stability","cp_test","c2verify")
skip_exact={"ok","other","test","book_","book_b","book_x","book_schema_repair_e2e_1785131361240",
            "book_schema_runtime_e2e_1785131440190","book_collector_e2e_1785131107451",
            "book_collector_preview_e2e_1785131502992"}
for name in sorted(dbs):
    if name in skip_exact: continue
    if any(name.startswith(p) for p in skip_prefixes): continue
    print(name)
')"

if [ -z "$DBS" ]; then
  echo "没有可导出的 db" >&2
  exit 1
fi

n=0
while IFS= read -r db; do
  [ -z "$db" ] && continue
  echo "  export $db"
  "$SURREAL_BIN" export --endpoint "$ENDPOINT" -u "$USER" -p "$PASS" \
    --ns "$NS" --db "$db" "$OUT_ROOT/surql/${db}.surql"
  n=$((n+1))
done <<< "$DBS"
echo "导出 $n 本/库 → $OUT_ROOT/surql"

echo "==> settings / ledger"
[ -f "$SETTINGS_SRC" ] && cp -a "$SETTINGS_SRC" "$OUT_ROOT/settings/" || echo "  无 settings"
[ -f "$LEDGER_SRC" ] && cp -a "$LEDGER_SRC" "$OUT_ROOT/settings/" || echo "  无 ledger"

echo "==> Hermes 最小资产（含 .env 密钥，仅本地打包，勿进 git）"
if [ -d "$HERMES_HOME" ]; then
  # 配置与密钥；不打包 hermes-agent 源码/venv（服务器另装）
  tar -C "$HERMES_HOME" -czf "$OUT_ROOT/hermes/hermes_config.tgz" \
    --exclude='hermes-agent' \
    --exclude='backups' \
    --exclude='state-snapshots' \
    --exclude='*.bak.*' \
    --exclude='profiles/*/state.db*' \
    --exclude='profiles/*/response_store.db*' \
    --exclude='profiles/*/sessions' \
    --exclude='profiles/*/logs' \
    --exclude='profiles/*/cache' \
    --exclude='profiles/*/audio_cache' \
    --exclude='profiles/*/image_cache' \
    --exclude='profiles/*/sandboxes' \
    --exclude='logs' \
    --exclude='cache' \
    --exclude='sessions' \
    .env config.yaml USER.md SOUL.md cron scripts profiles 2>/dev/null \
    || tar -C "$HERMES_HOME" -czf "$OUT_ROOT/hermes/hermes_config.tgz" .env config.yaml 2>/dev/null \
    || echo "  hermes 打包部分失败"
  ls -lh "$OUT_ROOT/hermes/" || true
fi

MANIFEST="$OUT_ROOT/MANIFEST.txt"
{
  echo "stamp=$STAMP"
  echo "ns=$NS"
  echo "dbs:"
  echo "$DBS"
  echo "settings=$(ls -1 "$OUT_ROOT/settings" 2>/dev/null | tr '\n' ' ')"
} > "$MANIFEST"

TGZ="${OUT_ROOT}.tgz"
tar -czf "$TGZ" -C "$(dirname "$OUT_ROOT")" "$(basename "$OUT_ROOT")"
echo "完成: $TGZ"
ls -lh "$TGZ"

