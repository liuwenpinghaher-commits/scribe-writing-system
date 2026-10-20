#!/usr/bin/env bash
# Thicken 主路径冒烟（已部署 demo only · 默认零持久化变更）
# 用法:
#   BASE=https://tonglu.example.com \
#   SMOKE_USER=... SMOKE_PASS=... \
#   ./scribe3/scripts/smoke_scribe3_thicken.sh
#
# 凭证（任一）: SMOKE_USER/SMOKE_PASS 或 USER/PASS 或 SCRIBE3_SMOKE_USER/PASS
# REQUIRE_AUTH=1 — 登录失败或鉴权路由非 200 则 FAIL（默认 0：未登录时 401 算存活）
#
# 可选:
#   MUTATE_STAGE=1     — 允许 POST stage/advance（默认关）
#   EXECUTE_PARALLEL=1 — 允许 execute=true（默认仅 plan dry-run）
#   WORK=main SEQ=1
set -euo pipefail

BASE="${BASE:-https://tonglu.example.com}"
COOKIE_JAR="${COOKIE_JAR:-/tmp/scribe3_thicken_smoke.ck}"
WORK="${WORK:-main}"
SEQ="${SEQ:-1}"
MUTATE_STAGE="${MUTATE_STAGE:-0}"
EXECUTE_PARALLEL="${EXECUTE_PARALLEL:-0}"
REQUIRE_AUTH="${REQUIRE_AUTH:-0}"

SMOKE_U="${SMOKE_USER:-${SCRIBE3_SMOKE_USER:-${USER:-}}}"
SMOKE_P="${SMOKE_PASS:-${SCRIBE3_SMOKE_PASS:-${PASS:-}}}"
# 避免把系统 USER 当登录名：仅当 PASS 也设时才用 USER
if [[ -n "${PASS:-}" && -z "${SMOKE_USER:-}" && -z "${SCRIBE3_SMOKE_USER:-}" ]]; then
  SMOKE_U="${USER:-}"
  SMOKE_P="${PASS}"
fi
# 若只有系统 USER 无 PASS，清空以免误登
if [[ -z "${SMOKE_P}" ]]; then
  SMOKE_U=""
fi

AUTHED=0

log() { echo "[smoke] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }
# 已登录时期望 200；未登录允许 401（存活）
expect_auth() {
  local label="$1" code="$2"
  if [[ "$AUTHED" == "1" || "$REQUIRE_AUTH" == "1" ]]; then
    [[ "$code" == "200" ]] || fail "$label expected 200 got $code (AUTHED=$AUTHED REQUIRE_AUTH=$REQUIRE_AUTH)"
  else
    [[ "$code" == "200" || "$code" == "401" ]] || fail "$label $code"
  fi
  [[ "$code" != "403" ]] || fail "$label 403 unexpected"
}

curl_json() {
  local method="$1" path="$2" data="${3:-}"
  if [[ -n "$data" ]]; then
    curl -sS -L -X "$method" "${BASE}${path}" \
      -H "Content-Type: application/json" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      --max-time 40 \
      -d "$data" -w "\n%{http_code}"
  else
    curl -sS -L -X "$method" "${BASE}${path}" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      --max-time 40 \
      -w "\n%{http_code}"
  fi
}

split_body_code() {
  BODY=$(echo "$1" | sed '$d')
  CODE=$(echo "$1" | tail -n1)
}

# 1 health
log "health"
RAW=$(curl -sS -L -w "\n%{http_code}" --max-time 20 "${BASE}/api/health" || true)
split_body_code "$RAW"
[[ "$CODE" == "200" ]] || fail "health $CODE $BODY"
echo "$BODY" | grep -q '"ok"' || fail "health body"

# 2 login
if [[ -n "$SMOKE_U" && -n "$SMOKE_P" ]]; then
  log "login as ${SMOKE_U}"
  # JSON 转义简易：去掉引号
  local_user=${SMOKE_U//\"/}
  local_pass=${SMOKE_P//\"/}
  RAW=$(curl -sS -L -X POST "${BASE}/api/auth/login" \
    -H "Content-Type: application/json" \
    -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
    -d "{\"username\":\"${local_user}\",\"password\":\"${local_pass}\"}" \
    -w "\n%{http_code}" --max-time 30 || true)
  split_body_code "$RAW"
  if [[ "$CODE" == "200" || "$CODE" == "204" ]]; then
    AUTHED=1
    log "login ok"
  else
    if [[ "$REQUIRE_AUTH" == "1" ]]; then
      fail "login $CODE $BODY"
    fi
    log "login code=$CODE (continue unauthenticated)"
  fi
elif [[ "$REQUIRE_AUTH" == "1" ]]; then
  fail "REQUIRE_AUTH=1 but no SMOKE_USER/SMOKE_PASS"
else
  log "no credentials (SMOKE_USER/PASS) — auth routes may 401"
fi

# 3 storyline gantt
log "storyline/gantt"
RAW=$(curl_json GET "/api/storyline/gantt?work=${WORK}" || true)
split_body_code "$RAW"
expect_auth "gantt" "$CODE"

# 4 GET stage
log "GET stage seq=$SEQ"
RAW=$(curl_json GET "/api/chapters/${SEQ}/stage?work=${WORK}" || true)
split_body_code "$RAW"
expect_auth "stage GET" "$CODE"
[[ "$CODE" != "403" ]] || fail "stage GET 403 — emergency bypass missing?"

# 5 optional advance
if [[ "$MUTATE_STAGE" == "1" ]]; then
  log "POST stage/advance (MUTATE_STAGE=1)"
  RAW=$(curl_json POST "/api/chapters/${SEQ}/stage/advance?work=${WORK}" '{"action":"advance"}' || true)
  split_body_code "$RAW"
  expect_auth "stage advance" "$CODE"
else
  log "skip stage advance (MUTATE_STAGE=0 default)"
fi

# 6 soft-precheck
log "soft-precheck"
RAW=$(curl_json POST "/api/soft-precheck" '{"synopsis":"smoke","beats":["a"]}' || true)
split_body_code "$RAW"
expect_auth "soft-precheck" "$CODE"

# 7 parallel plan dry-run
log "parallel plan dry-run"
RAW=$(curl_json POST "/api/chapters/${SEQ}/deduce/parallel?work=${WORK}" \
  '{"focalizers":["甲","乙"],"mode":"preview","execute":false}' || true)
split_body_code "$RAW"
expect_auth "parallel plan" "$CODE"
if [[ "$CODE" == "200" ]]; then
  echo "$BODY" | grep -q 'scribe3_deduce_preview\|dry_run\|preview' || log "plan body check soft-fail"
fi

# 8 optional execute
if [[ "$EXECUTE_PARALLEL" == "1" ]]; then
  log "parallel execute (EXECUTE_PARALLEL=1)"
  RAW=$(curl_json POST "/api/chapters/${SEQ}/deduce/parallel?work=${WORK}" \
    '{"focalizers":["甲"],"mode":"preview","execute":true,"max_parallel":1,"timeout_s":60}' || true)
  split_body_code "$RAW"
  expect_auth "parallel execute" "$CODE"
  if [[ "$CODE" == "200" ]]; then
    if echo "$BODY" | grep -q '"all_stub"[[:space:]]*:[[:space:]]*true'; then
      log "WARN all_stub=true (Hermes path may be stub)"
    fi
  fi
else
  log "skip parallel execute (EXECUTE_PARALLEL=0 default)"
fi

# 9 agent-crons
log "agent-crons"
RAW=$(curl_json GET "/api/agent-crons" || true)
split_body_code "$RAW"
expect_auth "agent-crons" "$CODE"
if [[ "$CODE" == "200" ]]; then
  echo "$BODY" | grep -q 'note_zh\|mutates_hermes_timer\|hermes_cron\|jobs' || log "crons body soft"
  echo "$BODY" | grep -q 'hermes' || log "crons hermes field soft"
fi

# 10 benchmarks
log "benchmarks"
RAW=$(curl_json GET "/api/benchmarks" || true)
split_body_code "$RAW"
expect_auth "benchmarks" "$CODE"

# 11 budget-probe config
log "budget-probe config"
RAW=$(curl_json POST "/api/debug/budget-probe" '{"mode":"config"}' || true)
split_body_code "$RAW"
expect_auth "budget-probe" "$CODE"

# 12 debug locks
log "debug/locks"
RAW=$(curl_json GET "/api/debug/locks" || true)
split_body_code "$RAW"
if [[ "$AUTHED" == "1" || "$REQUIRE_AUTH" == "1" ]]; then
  [[ "$CODE" == "200" ]] || fail "locks expected 200 got $CODE"
else
  [[ "$CODE" == "200" || "$CODE" == "401" || "$CODE" == "404" ]] || fail "locks $CODE"
fi

# 13 soft/event-led L0
log "soft/event-led"
RAW=$(curl_json POST "/api/soft/event-led" '{"prose":"债主堵门「还清」","include_llm":false}' || true)
split_body_code "$RAW"
expect_auth "event-led" "$CODE"

log "OK thicken smoke (AUTHED=$AUTHED zero-mutate defaults)"
exit 0
