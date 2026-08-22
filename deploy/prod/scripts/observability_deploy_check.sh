#!/usr/bin/env bash
# 观测部署就绪检查（第十三轮 T21）
set -euo pipefail
PASS=0
FAIL=0
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

check() {
  if eval "$2" >/dev/null 2>&1; then
    echo "✓ $1"
    PASS=$((PASS + 1))
  else
    echo "✗ $1"
    FAIL=$((FAIL + 1))
  fi
}

check "/etc/scribe3/env 存在" "[ -f /etc/scribe3/env ]"
check "SCRIBE3_ROOT 已设置" "grep -q SCRIBE3_ROOT /etc/scribe3/env"
check "日志目录可写" "[ -w ${OBSERVABILITY_LOG_DIR:-/var/log/scribe3/observability} ]"
check "cron 脚本可执行" "[ -x deploy/prod/scripts/observability_cron.sh ]"
check "Grafana JSON 语法合法" "python3 -c \"import json; json.load(open('deploy/prod/grafana/quality-stats-panel.json'))\""
if command -v systemd-analyze >/dev/null 2>&1; then
  check "systemd timer 语法" "systemd-analyze verify deploy/prod/systemd/scribe3-observability.timer 2>&1 | grep -v 'Cannot'"
else
  echo "⊘ systemd timer 语法（本机无 systemd-analyze，仅 Linux 部署机检查）"
fi

echo "---"
echo "通过: $PASS / 失败: $FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "观测部署就绪"
  exit 0
fi
echo "观测部署未就绪（请修复上述失败项）"
exit "$FAIL"
