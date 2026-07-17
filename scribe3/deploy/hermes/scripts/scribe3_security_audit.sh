#!/bin/bash
# P4(hermes 能力审查):周检供应链——hermes venv / 插件依赖 / 固定 npx/uvx MCP 的
# OSV.dev 漏洞扫描(hermes security audit)。
# --no-agent 哨兵:干净=静默;发现漏洞或扫描失败才输出(送达提醒)。
set -u
export PATH="$HOME/.local/bin:$PATH"
out=$(hermes security audit 2>&1); rc=$?
if [ $rc -ne 0 ] && [ -z "$out" ]; then
  echo "hermes security audit 运行失败(rc=$rc,无输出)"
  exit 0
fi
hits=$(echo "$out" | grep -cE "PYSEC-|GHSA-|CVE-") || hits=0
if [ "$hits" -gt 0 ]; then
  echo "scribe3 供应链周检:发现 $hits 条漏洞记录(hermes venv/插件/MCP 固定包):"
  echo "$out" | grep -E "PYSEC-|GHSA-|CVE-|fixed in" | head -20
  echo "(处置:通常随 hermes update 升级修复;升级前跑 scribe3/HERMES_UPGRADE_EVAL.md 演练)"
fi
exit 0
