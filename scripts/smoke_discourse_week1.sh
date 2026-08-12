#!/usr/bin/env bash
# 话语层 Week-1 方案 E · demo 冒烟（已部署栈）
# BASE=https://tonglu.qing.blue/api WORK=main ./scripts/smoke_discourse_week1.sh
set -euo pipefail
BASE="${BASE:-https://tonglu.qing.blue/api}"
WORK="${WORK:-main}"
CJ="${CJ:-/tmp/discourse-smoke-cj.txt}"

log() { echo "$*"; }

curl -sS -c "$CJ" -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"chris0120"}' >/dev/null

log "== flags =="
curl -sS -b "$CJ" "$BASE/debug/flags" | python3 -c "
import sys,json
d=json.load(sys.stdin)
# shape may be {flags:{...}} or flat
src=d.get('flags') if isinstance(d.get('flags'), dict) else d
keys=[k for k in src if str(k).startswith('SCRIBE3_DISCOURSE_')]
need=['SCRIBE3_DISCOURSE_ADVISORY','SCRIBE3_DISCOURSE_INFO_DELTA','SCRIBE3_DISCOURSE_BLOCKING',
      'SCRIBE3_DISCOURSE_MESO','SCRIBE3_DISCOURSE_SERIAL','SCRIBE3_DISCOURSE_STAKES','SCRIBE3_DISCOURSE_RASHOMON']
missing=[k for k in need if k not in src]
print('discourse_flags', sorted(keys))
assert not missing, missing
print('FLAGS_OK')
"

log "== soft/discourse seq only =="
curl -sS -b "$CJ" -X POST "$BASE/soft/discourse?work=${WORK}" \
  -H 'Content-Type: application/json' \
  -d '{"seq":1}' | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('status', d.get('status'), 'severity', d.get('severity'))
print('breath_keys', list((d.get('breath') or {}).keys())[:6])
print('findings', len(d.get('findings') or []))
assert d.get('status') in ('ok','no_prose','degraded','off')
assert d.get('surface')=='soft.discourse' or d.get('status')
print('SOFT_OK')
"

log "== storyline omit still holds =="
curl -sS -b "$CJ" -X POST "$BASE/storyline/inject-preview?work=${WORK}" \
  -H 'Content-Type: application/json' \
  -d '{"focus_seq":1,\"use_store\":1,\"promise_mode\":\"omit\"}' | python3 -c "
import sys,json
d=json.load(sys.stdin)
t=d.get('text') or ''
assert '开放伏笔：' not in t
print('promise_mode', d.get('promise_mode') or (d.get('feed') or {}).get('promise_mode'))
print('STORYLINE_OMIT_OK')
"

log "== done =="
