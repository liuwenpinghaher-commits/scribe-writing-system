#!/usr/bin/env bash
# 写网关 MCP 冒烟。默认不接入 deploy_demo.sh hot。
# MCP_GATE=1 时失败 exit 1；否则仍打印结果但默认 exit 0（便于手工看）。
set -euo pipefail
KEY_FILE="${HERMES_WRITE_ENV:-/opt/scribe3-host/.hermes/profiles/scribe3_write/.env}"
BASE="${HERMES_RUNS_API:-http://172.18.0.1:8644/v1}"
GATE="${MCP_GATE:-0}"

key=""
if [[ -f "$KEY_FILE" ]]; then
  key=$(grep -E '^API_SERVER_KEY=' "$KEY_FILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
url="${BASE%/}/toolsets"
code="000"
body=""
if [[ -n "$key" ]]; then
  code=$(curl -sS -o /tmp/smoke_write_mcp.json -w '%{http_code}' -m 8 \
    -H "Authorization: Bearer $key" "$url" || echo fail)
  body=$(head -c 2000 /tmp/smoke_write_mcp.json 2>/dev/null || true)
else
  echo "no API_SERVER_KEY in $KEY_FILE" >&2
  [[ "$GATE" = "1" ]] && exit 1
  exit 0
fi
echo "toolsets http=$code"
n=$(python3 -c "import json,sys
try:
 d=json.load(open('/tmp/smoke_write_mcp.json'))
 rows=d.get('data') or d.get('toolsets') or d if isinstance(d,list) else []
 n=0
 if isinstance(rows,list):
  for r in rows:
   if isinstance(r,dict):
    n+=len(r.get('tools') or [])
 print(n)
except Exception:
 print(0)
")
echo "runtime_tool_count=$n"
if [[ "$code" != "200" || "$n" -lt 1 ]]; then
  echo "WRITE_GATEWAY_EMPTY" >&2
  [[ "$GATE" = "1" ]] && exit 1
  exit 0
fi
echo "SMOKE_OK"
