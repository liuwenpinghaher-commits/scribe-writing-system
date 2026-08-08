#!/usr/bin/env bash
# 校验 Hermes 三 profile 分档不变量（H1 落地后）
# 在 demo 机或能读 ~/.hermes 的环境执行。
set -euo pipefail

python3 <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FAIL need PyYAML")
    sys.exit(2)

home = Path.home() / ".hermes"
paths = {
    "8642": home / "config.yaml",
    "8643": home / "profiles" / "scribe3" / "config.yaml",
    "8644": home / "profiles" / "scribe3_write" / "config.yaml",
}
expect = {
    "8642": {"timeout": 300, "comp": 0.40, "tools": []},
    "8643": {"timeout": 900, "comp": 0.50, "tools": ["scribe3_read"]},
    "8644": {"timeout": 1800, "comp": 0.55, "tools": ["scribe3_read", "scribe3_write"]},
}
fail = 0
for label, path in paths.items():
    if not path.is_file():
        print(f"FAIL missing {path}")
        fail += 1
        continue
    d = yaml.safe_load(path.read_text())
    ag = d.get("agent") or {}
    tools = (d.get("platform_toolsets") or {}).get("api_server")
    if tools is None:
        tools = []
    comp = (d.get("compression") or {}).get("threshold")
    to = ag.get("gateway_timeout")
    exp = expect[label]
    ok = True
    if to != exp["timeout"]:
        print(f"FAIL {label} gateway_timeout={to} want {exp['timeout']}")
        ok = False
    if abs(float(comp) - float(exp["comp"])) > 0.001:
        print(f"FAIL {label} compression.threshold={comp} want {exp['comp']}")
        ok = False
    if list(tools) != list(exp["tools"]):
        print(f"FAIL {label} tools={tools} want {exp['tools']}")
        ok = False
    if ok:
        print(f"OK  {label} timeout={to} comp={comp} tools={tools}")
    else:
        fail += 1

# dual-compression note: app summarize threshold fixed at 40 msgs
print("NOTE app _maybe_summarize_thread default threshold=40 (Hermes compression is separate)")
print("NOTE do not lower both aggressively without measuring long-thread quality")
sys.exit(1 if fail else 0)
PY
