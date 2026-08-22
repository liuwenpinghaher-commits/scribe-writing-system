#!/usr/bin/env bash
# 每日定时执行质量判定观测，输出 JSON 持久化到 /var/log/scribe3/observability/
set -euo pipefail
LOG_DIR="${OBSERVABILITY_LOG_DIR:-/var/log/scribe3/observability}"
mkdir -p "$LOG_DIR"
DATE=$(date +%Y-%m-%d)
cd "${SCRIBE3_ROOT:-/app}"
PYTHON="${PYTHON:-python3}"
"$PYTHON" scripts/observability_quality_stats.py --book main --days 1 \
  > "$LOG_DIR/quality_stats_${DATE}.json" 2>&1 || true
