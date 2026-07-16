#!/usr/bin/env bash
# 真调档编排:临时 surreal + 后端(真 Hermes 网关)+ 前端 dev → full_journey → 拆。
# 需本机 Hermes 网关已起(:8643/:8644)。surreal 用【独立临时库】绝不碰生产《纸命》/《印迹》。
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
PIDS=()
cleanup() { for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT

# 安全前置(fail-loud):3311/3321 必须空闲。若被占用,本脚本的临时后端起不来,而 curl 探活会
# 误命中【已在跑的服务】——本机开发后端连的是生产 surreal(:8001),会把测试书写进生产库
# 《纸命》/《印迹》。宁可拒绝运行也绝不碰生产。
for _port in 3311 3321; do
  if lsof -iTCP:"$_port" -sTCP:LISTEN -n >/dev/null 2>&1; then
    echo "❌ 端口 $_port 已被占用——拒绝运行以防误连生产服务/污染生产库。" >&2
    echo "   请先停掉占用者(如本机开发前后端),或在干净环境(CI)运行。" >&2
    exit 1
  fi
done

# 1) 临时内存 surreal(随机端口;净化环境防非 ASCII 路径 SIGABRT,同 conftest)
SPORT=$(python3 -c "import socket;s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()")
SURREAL_BIN="${SURREAL_BIN:-$(command -v surreal || echo "$HOME/.surrealdb/surreal")}"
( cd /tmp && exec env -i PATH=/usr/bin:/bin:/usr/local/bin HOME="$HOME" \
    "$SURREAL_BIN" start --no-banner --bind "127.0.0.1:$SPORT" --user root --pass root memory ) &
PIDS+=($!)

# 2) 后端 :3321 连【临时】surreal(真网关不 mock,沿用本机 Hermes 配置 :8643/:8644)
export SCRIBE3_SURREAL_URL="ws://127.0.0.1:$SPORT/rpc"
export SCRIBE3_SETTINGS_DB="$(mktemp -d)/settings.sqlite3"
export SCRIBE3_LLM_LEDGER="$(mktemp -d)/ledger.sqlite3"
"$ROOT/scribe3/.venv/bin/python" -m uvicorn scribe3.app:app --host 127.0.0.1 --port 3321 &
PIDS+=($!)

# 3) 前端 dev :3311(proxy /api → :3321)
( cd scribe3/web && exec npm run dev ) &
PIDS+=($!)

# 4) 等就绪 → 跑真调完整旅程
for i in $(seq 1 40); do
  curl -sf http://127.0.0.1:3321/health >/dev/null 2>&1 \
    && curl -sf http://127.0.0.1:3311/ >/dev/null 2>&1 && break
  sleep 1
done
cd scribe3/web && E2E_BASE=http://127.0.0.1:3311 node e2e/full_journey.mjs
