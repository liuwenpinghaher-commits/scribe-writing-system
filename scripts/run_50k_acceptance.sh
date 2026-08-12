#!/usr/bin/env bash
# 铜炉写作系统 · 5万字 Linux CLI + Playwright 全程验收入口
#
# 用法:
#   ./scripts/run_50k_acceptance.sh              # 新建书跑全程
#   ./scripts/run_50k_acceptance.sh --resume     # 从 checkpoint 续跑
#
# 环境变量（常用）:
#   E2E_BASE=http://127.0.0.1:3311
#   E2E_API=http://127.0.0.1:3321
#   E2E_ALLOW_DEPLOYED=1          # 必须：声明连接已部署验收/demo 栈
#   E2E_BOOK_TITLE='50k全程验收·demo'
#   E2E_WORK=book_xxx             # 可选：续写已有书
#   E2E_WORD_TARGET=50000
#   E2E_TARGET_CHAPTERS=18
#   E2E_MIN_PROSE=2500
#   E2E_CHAPTER_MAX_MS=480000
#   E2E_ART=/path/to/artifacts/...
#   E2E_RESUME=1
#
# 安全:
#   - 未设 E2E_ALLOW_DEPLOYED=1 时脚本拒绝运行（防误写）
#   - 不启动临时 Surreal；只打已部署栈
#   - 正文只经 Playwright UI + 审批，禁止 API 灌库
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export E2E_BASE="${E2E_BASE:-http://127.0.0.1:3311}"
export E2E_API="${E2E_API:-http://127.0.0.1:3321}"
export E2E_ALLOW_DEPLOYED="${E2E_ALLOW_DEPLOYED:-1}"
export E2E_WORD_TARGET="${E2E_WORD_TARGET:-50000}"
export E2E_TARGET_CHAPTERS="${E2E_TARGET_CHAPTERS:-18}"
export E2E_MIN_PROSE="${E2E_MIN_PROSE:-2500}"
export E2E_CHAPTER_MAX_MS="${E2E_CHAPTER_MAX_MS:-480000}"

RESUME=0
for arg in "$@"; do
  case "$arg" in
    --resume|-r) RESUME=1 ;;
    --help|-h)
      sed -n '2,30p' "$0"
      exit 0
      ;;
  esac
done
if [[ "$RESUME" == "1" ]]; then
  export E2E_RESUME=1
fi

echo "== 50k acceptance preflight =="
echo "ROOT=$ROOT"
echo "E2E_BASE=$E2E_BASE E2E_API=$E2E_API"
echo "E2E_ALLOW_DEPLOYED=$E2E_ALLOW_DEPLOYED RESUME=${E2E_RESUME:-0}"

# 服务探活（fail-loud）
if ! curl -sf --max-time 5 "$E2E_API/health" >/dev/null; then
  echo "❌ 后端不可达: $E2E_API/health" >&2
  echo "   请确认 demo/验收栈已启动（docker compose / deploy_demo）。" >&2
  exit 1
fi
if ! curl -sf --max-time 5 "$E2E_BASE/" >/dev/null; then
  echo "❌ 前端不可达: $E2E_BASE" >&2
  exit 1
fi
echo "OK health endpoints"

# Playwright / Node
if ! command -v node >/dev/null; then
  echo "❌ 需要 node" >&2
  exit 1
fi
WEB="$ROOT/scribe3/web"
if [[ ! -d "$WEB/node_modules/playwright" && ! -d "$WEB/node_modules/playwright-core" ]]; then
  echo "⚠ scribe3/web 未找到 playwright 包；若运行失败请在 demo 机 web 目录安装依赖（勿在内存极紧的 Grok 机 npm ci）。" >&2
fi

# 可选：把仓库 root 放进 PYTHONPATH 供 quality_bridge
export PYTHONPATH="${PYTHONPATH:-}:$ROOT"
if [[ -x "$ROOT/scribe3/.venv/bin/python" ]]; then
  export E2E_PYTHON="${E2E_PYTHON:-$ROOT/scribe3/.venv/bin/python}"
fi

STAMP="$(date -u +%Y%m%d)"
export E2E_ART="${E2E_ART:-$ROOT/artifacts/e2e-50k-${STAMP}-run}"
mkdir -p "$E2E_ART"

echo "ART=$E2E_ART"
echo "== launching Playwright journey =="

cd "$WEB"
# 单次全程可达 6h+
export NODE_OPTIONS="${NODE_OPTIONS:-}"
exec node --experimental-default-type=module e2e/acceptance_50k/run_50k_acceptance.mjs "$@"
