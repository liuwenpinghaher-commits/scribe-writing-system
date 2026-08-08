#!/usr/bin/env bash
# =============================================================================
# Hermes 三网关冒烟：确认「三个网关在跑、能 models、速答能 completion」
#
# 硬失败条件（与「系统是否在跑」相关）：
#   - systemd unit 非 active（若本机有 unit）
#   - 8642/8643/8644 /v1/models 非 200
#   - 8642 短 completion 非 200
#
# 安全建议（8642 零工具）：默认 FAIL；可用 STRICT_TOOLS=0 降为 NOTE（不推荐生产）
#
# 不做：
#   - 不钉死 Hermes 版本号
#   - 不要求 timeout/compression 精确数值（那是 check_hermes_tiers，可选）
#
# 用法（demo 机）:
#   ./scripts/smoke_hermes_gateways.sh
#   HERMES_BASE=http://172.18.0.1 ./scripts/smoke_hermes_gateways.sh
# =============================================================================
set -euo pipefail

BASE="${HERMES_BASE:-http://172.18.0.1}"
ENV_FILE="${HERMES_ENV:-$HOME/.hermes/.env}"
STRICT_TOOLS="${STRICT_TOOLS:-1}"
PASS=0
FAIL=0

log() { printf '%s\n' "$*"; }
ok() { PASS=$((PASS + 1)); log "  OK  $*"; }
bad() { FAIL=$((FAIL + 1)); log "  FAIL $*"; }
note() { log "  NOTE $*"; }

KEY=""
if [[ -f "$ENV_FILE" ]]; then
  KEY="$(grep -E '^API_SERVER_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
fi
AUTH=()
if [[ -n "$KEY" ]]; then
  AUTH=(-H "Authorization: Bearer $KEY")
fi

log "==> smoke_hermes_gateways BASE=$BASE $(date -Iseconds 2>/dev/null || date)"
log "==> 目标：三网关存活 + 能应答（非版本钉死）"

if command -v systemctl >/dev/null 2>&1; then
  for u in hermes-gateway hermes-gateway-scribe3 hermes-gateway-scribe3-write; do
    st="$(systemctl is-active "$u.service" 2>/dev/null || echo missing)"
    if [[ "$st" == "active" ]]; then ok "systemctl $u=$st"; else bad "systemctl $u=$st"; fi
  done
fi

# 8642 工具面：默认仍当安全门禁；可 STRICT_TOOLS=0 放宽
if command -v python3 >/dev/null 2>&1 && [[ -f "$HOME/.hermes/config.yaml" ]]; then
  if python3 - <<'PY'
import yaml
from pathlib import Path
d = yaml.safe_load((Path.home() / ".hermes" / "config.yaml").read_text())
pt = (d.get("platform_toolsets") or {}).get("api_server")
print(pt if pt is not None else [])
raise SystemExit(0 if (pt == [] or pt is None) else 1)
PY
  then
    ok "8642 platform_toolsets.api_server empty (safety)"
  else
    if [[ "$STRICT_TOOLS" == "1" ]]; then
      bad "8642 platform_toolsets.api_server not empty (set STRICT_TOOLS=0 to warn-only)"
    else
      note "8642 tools not empty (STRICT_TOOLS=0, not failing)"
      ok "8642 tools check skipped"
    fi
  fi
  # Hermes 版本只打印
  if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/hermes" ]]; then
    note "hermes CLI: $($HOME/.hermes/hermes-agent/venv/bin/hermes --version 2>/dev/null | head -1 || true)"
  fi
fi

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

t0="$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')"
code="$(curl -sS -o /tmp/hermes_chat_8642.json -w '%{http_code}' \
  --connect-timeout 5 --max-time 120 \
  "${AUTH[@]}" -H "Content-Type: application/json" \
  -d '{"model":"default","messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":16}' \
  "${BASE}:8642/v1/chat/completions" 2>/dev/null || echo fail)"
t1="$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')"
ms=$((t1 - t0))
if [[ "$code" == "200" ]]; then
  ok "POST :8642/chat/completions http=$code ms=$ms (LLM path alive)"
else
  bad "POST :8642/chat/completions http=$code ms=$ms body=$(head -c 100 /tmp/hermes_chat_8642.json 2>/dev/null)"
fi

if command -v ss >/dev/null 2>&1; then
  extra="$(ss -lntp 2>/dev/null | grep -E ':864[56]\b' || true)"
  if [[ -n "$extra" ]]; then
    note "extra listeners (optional deduce etc.):"
    log "$extra"
  fi
fi

log "==> summary pass=$PASS fail=$FAIL"
log "==> proves: three gateways up + models + one completion. Does NOT prove: write MCP, full app chat/write SSE."
if [[ -n "${HERMES_SMOKE_REPORT:-}" ]]; then
  {
    echo "# hermes gateway smoke $(date -Iseconds 2>/dev/null || date)"
    echo "pass=$PASS fail=$FAIL"
  } >>"$HERMES_SMOKE_REPORT"
fi
if [[ "$FAIL" -eq 0 ]]; then exit 0; fi
exit 1
