#!/usr/bin/env bash
# 兼容入口：等价于 ./scripts/deploy_demo.sh hot
# 主文档见 scripts/deploy_demo.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/scripts/deploy_demo.sh" hot "$@"
