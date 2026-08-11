#!/bin/sh
# scribe3 MCP server launcher (for Hermes stdio mount).
#
# Prefer the dockerized backend when present: host Hermes has no Surreal DNS and
# often no host-side scribe3 venv. Fall back to repo-local venv for pure host dev.
set -eu

CTR="${SCRIBE3_MCP_CONTAINER:-}"
if [ -z "$CTR" ] && command -v docker >/dev/null 2>&1; then
  for c in prod-backend-1 scribe3-backend-1 backend; do
    if docker inspect "$c" >/dev/null 2>&1; then
      CTR=$c
      break
    fi
  done
fi
if [ -n "${CTR:-}" ]; then
  exec docker exec -i "$CTR" python -m scribe3.mcp
fi

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
if [ -x "$ROOT/scribe3/.venv/bin/python" ]; then
  exec "$ROOT/scribe3/.venv/bin/python" -m scribe3.mcp
fi
if [ -x "$ROOT/.venv/bin/python" ]; then
  exec "$ROOT/.venv/bin/python" -m scribe3.mcp
fi
exec python3 -m scribe3.mcp
