#!/bin/sh
# scribe3 体检 cron 入口 launcher(供 Hermes cron --script 调用)。
# cd 仓库根 + scribe3 独立 venv 跑体检;stdout(健康报告/[SILENT])注入 agent prompt。
cd "/Users/miaoma/Downloads/写作 3.0" || exit 1
exec scribe3/.venv/bin/python -m scribe3.qc_scan
