#!/usr/bin/env bash
# =============================================================================
# Hermes 三网关冒烟 + 轻量基线（不动三网关架构）
#
# 用法（demo 机推荐）:
#   ./scripts/smoke_hermes_gateways.sh
#   HERMES_BASE=http://172.18.0.1 ./scripts/smoke_hermes_gateways.sh
#
# 鉴权: 读 ~/.hermes/.env 的 API_SERVER_KEY（不打印）
# =============================================================================
set -euo pipefail

BASE="${HERMES_BASE:-http://172.18.0.1}"
ENV_FILE="${HERMES_ENV:-$HOME/.hermes/.env}"
REPORT="${HERMES_SMOKE_REPORT:-}"
PASS=0
FAIL=0

log() { printf '%s\n' "$*"; }
ok() { PASS=$((PASS + 1)); log "  OK  $*"; }
bad() { FAIL=$((FAIL + 1)); log "  FAIL $*"; }

KEY=""
if [[ -f "$ENV_FILE" ]]; then
  KEY="$(grep -E '^API_SERVER_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
fi
AUTH=()
if [[ -n "$KEY" ]]; then
  AUTH=(-H "Authorization: Bearer $KEY")
fi

log "==> smoke_hermes_gateways BASE=$BASE $(date -Iseconds 2>/dev/null || date)"

# units if present
if command -v systemctl >/dev/null 2>&1; then
  for u in hermes-gateway hermes-gateway-scribe3 hermes-gateway-scribe3-write; do
    st="$(systemctl is-active "$u.service" 2>/dev/null || echo missing)"
    if [[ "$st" == "active" ]]; then ok "systemctl $u=$st"; else bad "systemctl $u=$st"; fi
  done
fi

# toolset invariant from yaml if present
if command -v python3 >/dev/null 2>&1 && [[ -f "$HOME/.hermes/config.yaml" ]]; then
  python3 - <<'PY' && ok "8642 platform_toolsets.api_server empty" || bad "8642 toolsets not empty"
import yaml
from pathlib import Path
d = yaml.safe_load((Path.home() / ".hermes" / "config.yaml").read_text())
pt = (d.get("platform_toolsets") or {}).get("api_server")
assert pt == [] or pt is None, pt
print("tools", pt)
PY
fi

declare -A EXPECT_PORT=([8642]=1 [8643]=1 [8644]=1)
for port in 8642 8643 8644; do
  t0="$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')"
  code="$(curl -sS -o "/tmp/hermes_models_${port}.json" -w '%{http_code}' \
    --connect-timeout 5 --max-time 20 \
    "${AUTH[@]}" "${BASE}:${port}/v1/models" 2>/dev/null || echo fail)"
  t1="$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')"
  ms=$((t1 - t0))
  if [[ "$code" == "200" ]]; then
    ok "GET :${port}/v1/models http=$code ms=$ms"
  else
    bad "GET :${port}/v1/models http=$code ms=$ms"
  fi
done

# short completion on 8642 only (zero-tool; cheapest)
t0="$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')"
code="$(curl -sS -o /tmp/hermes_chat_8642.json -w '%{http_code}' \
  --connect-timeout 5 --max-time 120 \
  "${AUTH[@]}" -H "Content-Type: application/json" \
  -d '{"model":"default","messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":16}' \
  "${BASE}:8642/v1/chat/completions" 2>/dev/null || echo fail)"
t1="$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')"
ms=$((t1 - t0))
if [[ "$code" == "200" ]] && grep -q 'OK\|ok\|content' /tmp/hermes_chat_8642.json 2>/dev/null; then
  ok "POST :8642/chat/completions http=$code ms=$ms"
else
  bad "POST :8642/chat/completions http=$code ms=$ms body=$(head -c 100 /tmp/hermes_chat_8642.json 2>/dev/null)"
fi

# optional extra listeners note
if command -v ss >/dev/null 2>&1; then
  extra="$(ss -lntp 2>/dev/null | grep -E ':864[56]\b' || true)"
  if [[ -n "$extra" ]]; then
    log "  NOTE extra listeners (deduce?):"
    log "$extra"
  fi
fi

log "==> summary pass=$PASS fail=$FAIL"
if [[ -n "${HERMES_SMOKE_REPORT:-}" ]]; then
  {
    echo "# hermes gateway smoke $(date -Iseconds 2>/dev/null || date)"
    echo "pass=$PASS fail=$FAIL"
  } >>"$HERMES_SMOKE_REPORT"
fi
if [[ "$FAIL" -eq 0 ]]; then exit 0; fi
exit 1
