#!/usr/bin/env bash
# 在 demo 机执行 M1/M2：seed → hotpath probe → memory e2e（打已部署 backend）
set -euo pipefail
CONTAINER="${BACKEND_CONTAINER:-prod-backend-1}"
ROOT_APP="${REMOTE_APP_DIR:-/opt/scribe3/app}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "need $CONTAINER on this host" >&2
  exit 1
fi

# 热更 tools 到容器（若本机已 scp 到 /tmp）
if [[ -d /tmp/scribe3_tools_m1 ]]; then
  docker cp /tmp/scribe3_tools_m1/. "$CONTAINER:/app/scribe3/tools/"
fi
# 或从 app 树
if [[ -d "$ROOT_APP/scribe3/tools" ]]; then
  docker cp "$ROOT_APP/scribe3/tools/seed_perf_fixture.py" "$CONTAINER:/app/scribe3/tools/" 2>/dev/null || true
  docker cp "$ROOT_APP/scribe3/tools/probe_s32_hotpath.py" "$CONTAINER:/app/scribe3/tools/" 2>/dev/null || true
  docker cp "$ROOT_APP/scribe3/tools/memory_e2e_s32.py" "$CONTAINER:/app/scribe3/tools/" 2>/dev/null || true
fi

echo "==> seed perf_s32"
docker exec -e PYTHONPATH=/app "$CONTAINER" python3 -u -m scribe3.tools.seed_perf_fixture \
  --n-char 12 --n-prop 20 --n-ch 10 --n-mem 10

echo "==> hotpath probe"
docker exec -e PYTHONPATH=/app "$CONTAINER" python3 -u -m scribe3.tools.probe_s32_hotpath --work perf_s32

echo "==> memory e2e on main"
docker exec -e PYTHONPATH=/app "$CONTAINER" python3 -u -m scribe3.tools.memory_e2e_s32 --work main

echo "M1_M2_DONE"
