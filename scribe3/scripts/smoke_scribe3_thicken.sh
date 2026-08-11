#!/usr/bin/env bash
# Thicken 主路径冒烟（已部署 demo only · 默认零持久化变更）
# 用法:
#   BASE=https://tonglu.qing.blue COOKIE_JAR=/tmp/s3.ck \
#   USER=... PASS=... ./scribe3/scripts/smoke_scribe3_thicken.sh
#
# 可选:
#   MUTATE_STAGE=1     — 允许 POST stage/advance（默认关）
#   EXECUTE_PARALLEL=1 — 允许 execute=true（默认仅 plan dry-run）
#   WORK=main SEQ=1
set -euo pipefail

BASE="${BASE:-https://tonglu.qing.blue}"
COOKIE_JAR="${COOKIE_JAR:-/tmp/scribe3_thicken_smoke.ck}"
WORK="${WORK:-main}"
SEQ="${SEQ:-1}"
MUTATE_STAGE="${MUTATE_STAGE:-0}"
EXECUTE_PARALLEL="${EXECUTE_PARALLEL:-0}"

log() { echo "[smoke] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

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

# 2 login if credentials
if [[ -n "${USER:-}" && -n "${PASS:-}" ]]; then
  log "login"
  RAW=$(curl -sS -L -X POST "${BASE}/api/auth/login" \
    -H "Content-Type: application/json" \
    -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
    -d "{\"username\":\"${USER}\",\"password\":\"${PASS}\"}" \
    -w "\n%{http_code}" --max-time 30 || true)
  split_body_code "$RAW"
  [[ "$CODE" == "200" || "$CODE" == "204" ]] || log "login code=$CODE (continue if session already valid)"
fi

# 3 storyline gantt (auth may 401 without login — still count as alive if 401/200)
log "storyline/gantt"
RAW=$(curl_json GET "/api/storyline/gantt?work=${WORK}" || true)
split_body_code "$RAW"
[[ "$CODE" == "200" || "$CODE" == "401" ]] || fail "gantt $CODE"
[[ "$CODE" != "403" ]] || fail "gantt 403 unexpected"

# 4 GET stage (hard step · no mutate)
log "GET stage seq=$SEQ"
RAW=$(curl_json GET "/api/chapters/${SEQ}/stage?work=${WORK}" || true)
split_body_code "$RAW"
[[ "$CODE" != "403" ]] || fail "stage GET 403 — emergency bypass missing?"
[[ "$CODE" == "200" || "$CODE" == "401" ]] || fail "stage GET $CODE"

# 5 optional advance
if [[ "$MUTATE_STAGE" == "1" ]]; then
  log "POST stage/advance (MUTATE_STAGE=1)"
  RAW=$(curl_json POST "/api/chapters/${SEQ}/stage/advance?work=${WORK}" '{"action":"advance"}' || true)
  split_body_code "$RAW"
  [[ "$CODE" != "403" ]] || fail "stage advance 403"
else
  log "skip stage advance (MUTATE_STAGE=0 default)"
fi

# 6 soft-precheck
log "soft-precheck"
RAW=$(curl_json POST "/api/soft-precheck" '{"synopsis":"smoke","beats":["a"]}' || true)
split_body_code "$RAW"
[[ "$CODE" == "200" || "$CODE" == "401" ]] || log "soft-precheck $CODE (soft)"

# 7 parallel plan dry-run
log "parallel plan dry-run"
RAW=$(curl_json POST "/api/chapters/${SEQ}/deduce/parallel?work=${WORK}" \
  '{"focalizers":["甲","乙"],"mode":"preview","execute":false}' || true)
split_body_code "$RAW"
[[ "$CODE" != "403" ]] || fail "parallel plan 403 — emergency bypass missing?"
[[ "$CODE" == "200" || "$CODE" == "401" ]] || fail "parallel plan $CODE"
if [[ "$CODE" == "200" ]]; then
  echo "$BODY" | grep -q 'scribe3_deduce_preview\|dry_run\|preview' || log "plan body check soft-fail"
fi

# 8 optional execute
if [[ "$EXECUTE_PARALLEL" == "1" ]]; then
  log "parallel execute (EXECUTE_PARALLEL=1)"
  RAW=$(curl_json POST "/api/chapters/${SEQ}/deduce/parallel?work=${WORK}" \
    '{"focalizers":["甲"],"mode":"preview","execute":true,"max_parallel":1,"timeout_s":60}' || true)
  split_body_code "$RAW"
  [[ "$CODE" != "403" ]] || fail "parallel execute 403"
else
  log "skip parallel execute (EXECUTE_PARALLEL=0 default)"
fi

log "OK thicken smoke (zero-mutate defaults)"
exit 0
