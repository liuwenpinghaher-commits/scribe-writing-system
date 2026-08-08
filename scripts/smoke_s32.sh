#!/usr/bin/env bash
# =============================================================================
# SurrealDB 3.2.4 + scribe3 demo 冒烟（打已部署栈，不启第二套库）
#
# 用法：
#   ./scripts/smoke_s32.sh                  # 默认公网 https://www.qing.blue
#   BASE_URL=http://127.0.0.1 ./scripts/smoke_s32.sh
#   在 demo 机上（可走本机反代）:
#   BASE_URL=http://127.0.0.1 SSH 内执行也可只测 API
#
# 登录：
#   优先环境变量 SMOKE_USER / SMOKE_PASS
#   否则从 DEMO_ENV_FILE（默认尝试 deploy/prod 路径）读 SCRIBE3_BOOTSTRAP_USERS
#
# 退出码：0 全绿；非 0 失败步骤
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-https://www.qing.blue}"
API="${BASE_URL%/}/api"
WORK="${SMOKE_WORK:-main}"
COOKIE_JAR="${SMOKE_COOKIE_JAR:-$(mktemp -t smoke_s32_XXXXXX.cookies)}"
REPORT="${SMOKE_REPORT:-}"
TMP_BODY="$(mktemp -t smoke_s32_XXXXXX.body)"
trap 'rm -f "$COOKIE_JAR" "$TMP_BODY"' EXIT

pass=0
fail=0
notes=()

log() { printf '%s\n' "$*"; }
ok() { pass=$((pass + 1)); log "  OK  $*"; }
bad() { fail=$((fail + 1)); log "  FAIL $*"; notes+=("$*"); }

# --- credentials ---
USER_NAME="${SMOKE_USER:-}"
PASS_WORD="${SMOKE_PASS:-}"
if [[ -z "$USER_NAME" || -z "$PASS_WORD" ]]; then
  for f in \
    "${DEMO_ENV_FILE:-}" \
    "${HOME}/.scribe3-smoke.env" \
    "/opt/scribe3/app/deploy/prod/.env" \
    "$(cd "$(dirname "$0")/.." && pwd)/deploy/prod/.env"
  do
    [[ -n "$f" && -f "$f" ]] || continue
    boot="$(grep -E '^SCRIBE3_BOOTSTRAP_USERS=' "$f" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
    if [[ -n "$boot" && "$boot" == *:* ]]; then
      USER_NAME="${boot%%,*}"
      USER_NAME="${USER_NAME%%:*}"
      PASS_WORD="${boot#*:}"
      PASS_WORD="${PASS_WORD%%,*}"
      break
    fi
  done
fi

if [[ -z "$USER_NAME" || -z "$PASS_WORD" ]]; then
  log "缺少登录凭证：设置 SMOKE_USER/SMOKE_PASS 或 DEMO_ENV_FILE 中的 SCRIBE3_BOOTSTRAP_USERS"
  exit 2
fi

curl_json() {
  # usage: curl_json METHOD PATH [json_body] [extra curl args...]
  local method="$1" path="$2"
  shift 2
  local body=""
  if [[ $# -gt 0 && "$1" != -* ]]; then
    body="$1"
    shift
  fi
  local code
  if [[ -n "$body" ]]; then
    code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' \
      -X "$method" "${API}${path}" \
      -H 'Content-Type: application/json' \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      --connect-timeout 10 --max-time 60 \
      -d "$body" "$@" || true)"
  else
    code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' \
      -X "$method" "${API}${path}" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      -H "X-Work: ${WORK}" \
      --connect-timeout 10 --max-time 60 \
      "$@" || true)"
  fi
  printf '%s' "$code"
}

log "==> smoke_s32 BASE_URL=$BASE_URL WORK=$WORK user=$USER_NAME"
log "==> $(date -Iseconds 2>/dev/null || date)"

# 1 health / ready (public)
code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' --connect-timeout 10 --max-time 20 "${API}/ready" || true)"
if [[ "$code" == "200" ]] && grep -q 'ready' "$TMP_BODY" 2>/dev/null; then
  ok "GET /ready -> $code $(head -c 80 "$TMP_BODY")"
else
  bad "GET /ready -> $code $(head -c 120 "$TMP_BODY")"
fi

code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' --connect-timeout 10 --max-time 20 "${API}/health" || true)"
if [[ "$code" == "200" ]]; then
  ok "GET /health -> $code $(head -c 80 "$TMP_BODY")"
else
  bad "GET /health -> $code $(head -c 120 "$TMP_BODY")"
fi

# 2 login
code="$(curl_json POST /auth/login "{\"username\":\"${USER_NAME}\",\"password\":\"${PASS_WORD}\"}")"
if [[ "$code" == "200" ]]; then
  ok "POST /auth/login -> $code"
else
  bad "POST /auth/login -> $code $(head -c 160 "$TMP_BODY")"
fi

# 3 capabilities
code="$(curl_json GET /capabilities)"
if [[ "$code" == "200" ]] && grep -q 'memory_fabric_v1' "$TMP_BODY"; then
  # fabric should be true by product default
  if grep -q '"memory_fabric_v1"[[:space:]]*:[[:space:]]*true' "$TMP_BODY"; then
    ok "GET /capabilities memory_fabric_v1=true"
  else
    bad "GET /capabilities memory_fabric not true: $(head -c 200 "$TMP_BODY")"
  fi
else
  bad "GET /capabilities -> $code $(head -c 160 "$TMP_BODY")"
fi

# 4 works
code="$(curl_json GET /works)"
if [[ "$code" == "200" ]]; then
  ok "GET /works -> $code $(head -c 120 "$TMP_BODY")"
else
  bad "GET /works -> $code $(head -c 160 "$TMP_BODY")"
fi

# 5 chapters + codex health (need work header)
code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -H "X-Work: ${WORK}" \
  --connect-timeout 10 --max-time 60 \
  "${API}/chapters" || true)"
if [[ "$code" == "200" ]]; then
  ok "GET /chapters X-Work=$WORK -> $code"
else
  bad "GET /chapters -> $code $(head -c 160 "$TMP_BODY")"
fi

code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -H "X-Work: ${WORK}" \
  --connect-timeout 10 --max-time 60 \
  "${API}/codex/health" || true)"
if [[ "$code" == "200" ]]; then
  ok "GET /codex/health -> $code $(head -c 120 "$TMP_BODY")"
else
  bad "GET /codex/health -> $code $(head -c 160 "$TMP_BODY")"
fi

# 6 memory pending-claims
code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -H "X-Work: ${WORK}" \
  --connect-timeout 10 --max-time 60 \
  "${API}/memory/pending-claims" || true)"
if [[ "$code" == "200" ]]; then
  ok "GET /memory/pending-claims -> $code $(head -c 120 "$TMP_BODY")"
elif [[ "$code" == "403" ]]; then
  bad "GET /memory/pending-claims -> 403 (MEMORY_FABRIC disabled?)"
else
  bad "GET /memory/pending-claims -> $code $(head -c 160 "$TMP_BODY")"
fi

# 7 optional: surreal version via docker on remote-friendly path
if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^prod-surreal-1$'; then
  ver="$(docker exec prod-surreal-1 /surreal version 2>/dev/null | head -1 || true)"
  if echo "$ver" | grep -q '3.2'; then
    ok "prod-surreal-1 version: $ver"
  else
    bad "prod-surreal-1 version unexpected: $ver"
  fi
  img="$(docker inspect prod-surreal-1 --format '{{.Config.Image}}' 2>/dev/null || true)"
  if echo "$img" | grep -q 'v3.2'; then
    ok "prod-surreal-1 image: $img"
  else
    bad "prod-surreal-1 image not 3.2.x: $img"
  fi
else
  log "  SKIP docker surreal version (not on demo host or no docker)"
fi

log "==> summary pass=$pass fail=$fail"
if [[ -n "$REPORT" ]]; then
  {
    echo "# smoke_s32 $(date -Iseconds 2>/dev/null || date)"
    echo "BASE_URL=$BASE_URL WORK=$WORK pass=$pass fail=$fail"
    printf '%s\n' "${notes[@]:-}"
  } >>"$REPORT"
  log "appended report: $REPORT"
fi

if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
exit 0
