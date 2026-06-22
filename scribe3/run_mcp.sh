#!/bin/sh
# scribe3 MCP server launcher(供 Hermes 挂载)。
# cd 到仓库根(让 scribe3 包可导入)+ 用 scribe3 独立 venv 跑 stdio MCP。
# 注:此处只 cd + 跑 Python(连已运行的 :8001),不 spawn surreal,故中文路径 panic 坑无关。
cd "/Users/miaoma/Downloads/写作 3.0" || exit 1
exec scribe3/.venv/bin/python -m scribe3.mcp
