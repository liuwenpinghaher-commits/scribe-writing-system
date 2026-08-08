#!/usr/bin/env bash
# 检查 Hermes 三 profile 分档（超时/压缩/工具面）
#
# 默认：工具面不对才 FAIL；timeout/compression 仅与「期望表」比较并打印，
#       不一致时 NOTE/WARN，不 fail（分档可调，不是版本钉死）。
# 严格模式：STRICT_TIERS=1 时 timeout/comp 也必须与期望一致。
#
# 期望值可用环境变量覆盖，避免写死唯一合法配置：
#   EXPECT_8642_TIMEOUT=300 EXPECT_8643_TIMEOUT=900 EXPECT_8644_TIMEOUT=1800
#   EXPECT_8642_COMP=0.4 ...
set -euo pipefail

python3 <<'PY'
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FAIL need PyYAML")
    sys.exit(2)

strict = os.environ.get("STRICT_TIERS", "0").strip() in {"1", "true", "yes", "on"}
home = Path.home() / ".hermes"
paths = {
    "8642": home / "config.yaml",
    "8643": home / "profiles" / "scribe3" / "config.yaml",
    "8644": home / "profiles" / "scribe3_write" / "config.yaml",
}
# 期望：工具面是安全不变量；数值是当前推荐分档（可 env 覆盖）
expect = {
    "8642": {
        "timeout": int(os.environ.get("EXPECT_8642_TIMEOUT", "300")),
        "comp": float(os.environ.get("EXPECT_8642_COMP", "0.40")),
        "tools": [],
    },
    "8643": {
        "timeout": int(os.environ.get("EXPECT_8643_TIMEOUT", "900")),
        "comp": float(os.environ.get("EXPECT_8643_COMP", "0.50")),
        "tools": ["scribe3_read"],
    },
    "8644": {
        "timeout": int(os.environ.get("EXPECT_8644_TIMEOUT", "1800")),
        "comp": float(os.environ.get("EXPECT_8644_COMP", "0.55")),
        "tools": ["scribe3_read", "scribe3_write"],
    },
}
fail = 0
warn = 0
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
    tools = list(tools)
    comp = (d.get("compression") or {}).get("threshold")
    to = ag.get("gateway_timeout")
    exp = expect[label]

    # tools: always hard for 8642 empty; write must include write
    if label == "8642" and tools not in ([],):
        print(f"FAIL {label} tools={tools} want [] (safety)")
        fail += 1
    elif label == "8643" and "scribe3_write" in tools:
        print(f"FAIL {label} must not expose write tools: {tools}")
        fail += 1
    elif label == "8644" and "scribe3_write" not in tools:
        print(f"FAIL {label} missing scribe3_write: {tools}")
        fail += 1
    else:
        print(f"OK  {label} tools={tools}")

    # numeric tiers: soft unless STRICT
    num_ok = True
    if to != exp["timeout"]:
        num_ok = False
        msg = f"{label} gateway_timeout={to} (recommended {exp['timeout']})"
        if strict:
            print(f"FAIL {msg}")
            fail += 1
        else:
            print(f"NOTE {msg}")
            warn += 1
    if comp is None or abs(float(comp) - float(exp["comp"])) > 0.001:
        num_ok = False
        msg = f"{label} compression.threshold={comp} (recommended {exp['comp']})"
        if strict:
            print(f"FAIL {msg}")
            fail += 1
        else:
            print(f"NOTE {msg}")
            warn += 1
    if num_ok:
        print(f"OK  {label} timeout={to} comp={comp}")

print("NOTE app _maybe_summarize_thread default threshold=40 (separate from Hermes compression)")
print(f"summary fail={fail} warn={warn} strict={strict}")
sys.exit(1 if fail else 0)
PY
