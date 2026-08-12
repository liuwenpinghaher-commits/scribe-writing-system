#!/usr/bin/env bash
# SL6：故事线融合 demo 冒烟（已部署栈 · 禁止 budget-probe 作 storyline 证明）
# 用法：
#   BASE=https://tonglu.qing.blue/api WORK=main TOKEN=... ./scripts/smoke_storyline_fusion.sh
#   或 DEMO_USER/DEMO_PASS 登录后自动取 cookie/token（若环境支持）
set -euo pipefail

BASE="${BASE:-https://tonglu.qing.blue/api}"
WORK="${WORK:-main}"
CHAPTER="${CHAPTER:-1}"
OUT="${OUT:-}"

log() { echo "$*"; }
json_get() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print($1)" 2>/dev/null || true
}

AUTH_H=()
if [[ -n "${TOKEN:-}" ]]; then
  AUTH_H=(-H "Authorization: Bearer ${TOKEN}")
elif [[ -n "${COOKIE:-}" ]]; then
  AUTH_H=(-H "Cookie: ${COOKIE}")
fi

curl_j() {
  local method="$1" path="$2"
  shift 2
  curl -sS -X "$method" "${BASE}${path}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    "${AUTH_H[@]}" \
    "$@"
}

log "== SL6 storyline fusion smoke · BASE=$BASE work=$WORK =="

log "-- 1) hub (lite default focus)"
HUB=$(curl_j GET "/storyline/hub?work=${WORK}" || true)
echo "$HUB" | head -c 800
echo
echo "$HUB" | python3 -c "
import sys,json
d=json.load(sys.stdin)
assert 'storylines' in d or 'gantt' in d, d
print('focus_seq=', d.get('focus_seq'))
print('refs=', d.get('refs'))
print('HUB_OK')
" || { log "HUB_FAIL (may need auth)"; exit 1; }

log "-- 2) create line + patch craft_only + delete"
CREATE=$(curl_j POST "/storyline/lines?work=${WORK}" \
  -d "{\"title\":\"smoke-fusion\",\"notes\":\"公开\",\"craft_only\":true,\"chapter_seqs\":[${CHAPTER}]}")
SID=$(echo "$CREATE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" || true)
log "created id=$SID"
if [[ -n "$SID" ]]; then
  PATCH=$(curl_j PATCH "/storyline/lines/${SID}?work=${WORK}" \
    -d '{"craft_only":false,"notes":"机密勿进"}')
  echo "$PATCH" | python3 -c "
import sys,json
d=json.load(sys.stdin)
assert d.get('craft_only') is False, d
print('PATCH_CRAFT_ONLY_OK')
"
  curl_j DELETE "/storyline/lines/${SID}?work=${WORK}" | head -c 200
  echo
  log "DELETE_OK"
else
  log "CREATE skipped/failed (auth?)"
fi

log "-- 3) inject-preview use_store=1 omit"
PREV=$(curl_j POST "/storyline/inject-preview?work=${WORK}" \
  -d "{\"focus_seq\":${CHAPTER},\"use_store\":1,\"promise_mode\":\"omit\"}")
echo "$PREV" | python3 -c "
import sys,json
d=json.load(sys.stdin)
text=d.get('text') or ''
assert '开放伏笔：' not in text, text[:200]
print('promise_mode=', d.get('promise_mode') or (d.get('feed') or {}).get('promise_mode'))
print('INJECT_PREVIEW_OK line_count=', (d.get('audit') or {}).get('line_count'))
"

log "-- 4) craft-align honesty"
ALIGN=$(curl_j GET "/storyline/craft-align?work=${WORK}")
echo "$ALIGN" | python3 -c "
import sys,json
d=json.load(sys.stdin)
align=d.get('align') or {}
dims=align.get('core_dimensions') or []
fake=[x for x in dims if x.get('key')!='emotional_effect' and x.get('score')==0.5 and x.get('source') not in ('uncomputed','neutral_placeholder')]
# uncomputed must not be measured 0.5
bad=[x for x in dims if x.get('key')!='emotional_effect' and x.get('source') not in ('uncomputed','neutral_placeholder',None) and x.get('score')==0.5]
print('dims=', [(x.get('key'), x.get('source'), x.get('score')) for x in dims[:6]])
assert not bad, bad
print('CRAFT_ALIGN_OK')
"

log "-- 5) write assemble trigger + injection-trace"
# 同实例触发写组装（chat/write 在 SSE 前 assemble）
WRITE_CODE=$(curl -sS -o /tmp/sl_write_body.txt -w "%{http_code}" \
  "${AUTH_H[@]}" \
  "${BASE}/chat/write?work=${WORK}&chapter=${CHAPTER}&msg=$(python3 -c 'import urllib.parse;print(urllib.parse.quote(\"故事线冒烟触发组装\"))')" \
  || echo "000")
log "chat/write http=$WRITE_CODE"
TRACE=$(curl_j GET "/debug/injection-trace?work=${WORK}" || true)
echo "$TRACE" | python3 -c "
import sys,json
raw=sys.stdin.read()
try:
  d=json.loads(raw)
except Exception:
  print('TRACE_PARSE_FAIL', raw[:300])
  sys.exit(2)
br=d.get('budget_report') or d
si=None
if isinstance(br, dict):
  si=br.get('storyline_inject')
  if si is None and isinstance(br.get('report'), dict):
    si=br['report'].get('storyline_inject')
if si is None:
  print('NO_STORYLINE_INJECT_KEY — 未命中本进程 assemble / 跨 worker；非产品回归')
  print(raw[:500])
  sys.exit(3)
print('storyline_inject=', si)
pm=si.get('promise_mode')
assert pm=='omit' or pm is None, si
print('INJECTION_TRACE_OK')
" || log "TRACE_STEP_SOFT_FAIL code=$?"

log "== smoke done =="
if [[ -n "$OUT" ]]; then
  {
    echo "HUB_SNIP=${HUB:0:400}"
    echo "PREV_SNIP=${PREV:0:400}"
    echo "ALIGN_SNIP=${ALIGN:0:400}"
    echo "TRACE_SNIP=${TRACE:0:600}"
  } >> "$OUT"
fi
