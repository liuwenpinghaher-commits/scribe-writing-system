#!/usr/bin/env bash
# =============================================================================
# 已部署栈冒烟：确认「系统在跑、主路径通」
#
# 做什么：
#   ready/health、登录、作品列表、章节、codex、记忆 API 可达性
# 不做什么：
#   - 不钉死 Surreal/Hermes 小版本号（有容器时只打印版本作参考）
#   - 不把「产品默认开关」写成永久失败条件（如 fabric 关了只 NOTE，不 fail）
#   - 不替代完整回归 / 真人 UI 验收
#
# 用法：
#   ./scripts/smoke_s32.sh
#   BASE_URL=https://tonglu.qing.blue SMOKE_WORK=main ./scripts/smoke_s32.sh
#
# 凭证：SMOKE_USER/SMOKE_PASS，或 DEMO_ENV_FILE / deploy/prod/.env 的
#       SCRIBE3_BOOTSTRAP_USERS
# 退出码：0 主路径绿；非 0 有硬失败
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-https://tonglu.qing.blue}"
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
note() { log "  NOTE $*"; }

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

log "==> smoke_s32 (liveness) BASE_URL=$BASE_URL WORK=$WORK user=$USER_NAME"
log "==> $(date -Iseconds 2>/dev/null || date)"
log "==> 目标：确认已部署栈主路径在跑（非版本钉死、非全量回归）"

# 1) 进程级可达
code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' --connect-timeout 10 --max-time 20 "${API}/ready" || true)"
if [[ "$code" == "200" ]] && grep -q 'ready' "$TMP_BODY" 2>/dev/null; then
  ok "GET /ready -> $code $(head -c 80 "$TMP_BODY")"
else
  bad "GET /ready -> $code $(head -c 120 "$TMP_BODY")"
fi

code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' --connect-timeout 10 --max-time 20 "${API}/health" || true)"
if [[ "$code" == "200" ]]; then
  ok "GET /health -> $code $(head -c 120 "$TMP_BODY")"
  # health 里若有 db/ns 字样，说明后端认为库可达
  if grep -qiE 'db|surreal|ns|ok' "$TMP_BODY" 2>/dev/null; then
    note "health payload suggests backend↔DB path present"
  fi
else
  bad "GET /health -> $code $(head -c 120 "$TMP_BODY")"
fi

# 2) 鉴权
code="$(curl_json POST /auth/login "{\"username\":\"${USER_NAME}\",\"password\":\"${PASS_WORD}\"}")"
if [[ "$code" == "200" ]]; then
  ok "POST /auth/login -> $code"
else
  bad "POST /auth/login -> $code $(head -c 160 "$TMP_BODY")"
fi

# 3) capabilities：只要 200 即主配置 API 活着；开关值只 NOTE
code="$(curl_json GET /capabilities)"
if [[ "$code" == "200" ]]; then
  ok "GET /capabilities -> $code"
  if grep -q '"memory_fabric_v1"[[:space:]]*:[[:space:]]*true' "$TMP_BODY" 2>/dev/null; then
    note "memory_fabric_v1=true (product default; not a hard smoke fail if false)"
  elif grep -q 'memory_fabric' "$TMP_BODY" 2>/dev/null; then
    note "memory_fabric flag present but not true — feature may be off by env"
  fi
else
  bad "GET /capabilities -> $code $(head -c 160 "$TMP_BODY")"
fi

# 4) 作品域
code="$(curl_json GET /works)"
if [[ "$code" == "200" ]]; then
  ok "GET /works -> $code $(head -c 100 "$TMP_BODY")"
else
  bad "GET /works -> $code $(head -c 160 "$TMP_BODY")"
fi

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
  ok "GET /codex/health -> $code $(head -c 100 "$TMP_BODY")"
else
  bad "GET /codex/health -> $code $(head -c 160 "$TMP_BODY")"
fi

# 5) 记忆 API：200=通；403=功能关（NOTE）；其它 fail
code="$(curl -sS -o "$TMP_BODY" -w '%{http_code}' \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -H "X-Work: ${WORK}" \
  --connect-timeout 10 --max-time 60 \
  "${API}/memory/pending-claims" || true)"
if [[ "$code" == "200" ]]; then
  ok "GET /memory/pending-claims -> $code"
elif [[ "$code" == "403" ]]; then
  note "GET /memory/pending-claims -> 403 (fabric/feature off — path reachable, feature gated)"
  ok "memory API gated-but-alive (403)"
else
  bad "GET /memory/pending-claims -> $code $(head -c 160 "$TMP_BODY")"
fi

# 6) 可选：容器存活与版本——只打印，永不因版本号 fail
if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^prod-surreal-1$'; then
  st="$(docker inspect -f '{{.State.Status}}' prod-surreal-1 2>/dev/null || echo unknown)"
  if [[ "$st" == "running" ]]; then
    ok "prod-surreal-1 container running"
  else
    bad "prod-surreal-1 container status=$st"
  fi
  ver="$(docker exec prod-surreal-1 /surreal version 2>/dev/null | head -1 || true)"
  img="$(docker inspect prod-surreal-1 --format '{{.Config.Image}}' 2>/dev/null || true)"
  note "surreal version (info only): ${ver:-?}"
  note "surreal image (info only): ${img:-?}"
else
  note "skip surreal container inspect (no docker / not on host)"
fi

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^prod-backend-1$'; then
  st="$(docker inspect -f '{{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' prod-backend-1 2>/dev/null || echo unknown)"
  if echo "$st" | grep -q running; then
    ok "prod-backend-1 $st"
  else
    bad "prod-backend-1 $st"
  fi
fi

log "==> summary pass=$pass fail=$fail"
log "==> smoke proves: edge+API+auth+work APIs alive. Does NOT prove: full write SSE, quality, or fixed versions."
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
