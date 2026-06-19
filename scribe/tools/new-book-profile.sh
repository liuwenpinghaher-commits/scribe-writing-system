#!/usr/bin/env bash
# 为一本书创建物理隔离的 Hermes Profile(独立 配置/记忆/技能/会话)。
# 用法:  bash tools/new-book-profile.sh <profile-name>
# 多本书 §2.7:数据层已按 work_id 隔离(共享库,支持跨书品味);此脚本额外给"每本书的 AI 会话"物理隔离。
set -euo pipefail
NAME="${1:?用法: new-book-profile.sh <profile-name>}"
HERMES_DIR="$(cd "$(dirname "$0")/../vendor/hermes-agent" && pwd)"

cd "$HERMES_DIR"
uv run hermes profile create "$NAME" || true

# 把默认 profile 的 model(含火山 api_key/base_url)与 scribe MCP 配置复制进新 profile,
# 使该 profile 开箱即用、且与其它书隔离。
uv run python - "$NAME" <<'PY'
import sys, pathlib, ruamel.yaml as ry
name = sys.argv[1]
yaml = ry.YAML()
base = pathlib.Path.home()/".hermes"/"config.yaml"
dst  = pathlib.Path.home()/".hermes"/"profiles"/name/"config.yaml"
cfg  = yaml.load(base.read_text()) or {}
prof = (yaml.load(dst.read_text()) if dst.exists() else {}) or {}
for k in ("model", "mcp_servers"):
    if k in cfg:
        prof[k] = cfg[k]
dst.parent.mkdir(parents=True, exist_ok=True)
import io; buf = io.StringIO(); yaml.dump(prof, buf); dst.write_text(buf.getvalue())
print(f"已写入 {dst}(model + scribe MCP 已继承,与其它书隔离)")
PY

echo "完成。用法:在 scribe/vendor/hermes-agent 下 'uv run hermes --profile $NAME chat' 即以该书的隔离会话运行。"
