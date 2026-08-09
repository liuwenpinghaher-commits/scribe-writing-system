#!/usr/bin/env python3
"""生成七维质量报告骨架（通/绿 + 待人评槽）。禁止把地板绿写成 9.5。

用法：
  python3 scripts/quality_d17_report.py --work book_4c7815eb \\
    --out artifacts/e2e-.../12-quality-d1-7.md
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("API_BASE", "https://www.qing.blue")
JAR = os.environ.get("COOKIE_JAR", "/tmp/q17_cookie.txt")


def curl(method, path, data=None, timeout=90, work=""):
    out = Path("/tmp/q17_out.json")
    urlpath = path
    if work and "work=" not in path and not path.startswith("/api/auth"):
        urlpath += ("&" if "?" in path else "?") + "work=" + work
    cmd = [
        "curl", "-sS", "-o", str(out), "-w", "%{http_code}",
        "-b", JAR, "-c", JAR, "-X", method,
        "-H", f"Origin: {BASE}", "--max-time", str(timeout),
    ]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json",
                "-d", json.dumps(data, ensure_ascii=False)]
    cmd.append(BASE + urlpath)
    p = subprocess.run(cmd, capture_output=True, text=True)
    body = out.read_text() if out.exists() else ""
    try:
        j = json.loads(body) if body else None
    except Exception:
        j = body
    return p.stdout.strip(), j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--chapter", type=int, default=5)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    w = args.work
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    u, pw = bu.split(":", 1)
    subprocess.run(["rm", "-f", JAR], check=False)
    code, _ = curl("POST", "/api/auth/login", {"username": u, "password": pw})
    if code != "200":
        raise SystemExit(f"login {code}")

    code, pref = curl("POST", "/api/memory/prefetch", {
        "query": "三棱铜匙 状态 铁律",
        "chapter": args.chapter,
    }, work=w, timeout=120)
    ctx = (pref or {}).get("context") or "" if isinstance(pref, dict) else ""
    ud = (pref or {}).get("usage_digest") if isinstance(pref, dict) else {}

    dual = ("完整无缺" in ctx) and ("缺口" in ctx)
    has_gap = "缺口" in ctx
    has_must = "戏剧必需" in ctx or "〔必需〕" in ctx
    has_law = "作者铁律" in ctx or "写作宪法" in ctx
    main_cast = ""
    for ln in ctx.splitlines():
        if "主要角色" in ln:
            main_cast = ln.strip()
            break
    noisy = any(x in main_cast for x in ("王二嫂", "覃有年", "群演"))

    # 地板分（≤6）与质量分（待人评）分离
    floors = {
        "D1_honest_floor": "PASS" if has_law else "PARTIAL",
        "D2_iron_floor": "PASS" if has_law else "FAIL",
        "D3_canon_floor": "PASS" if has_must else "PARTIAL",
        "D4_single_truth_floor": "FAIL" if dual else ("PASS" if has_gap else "PARTIAL"),
        "D5_minimal_floor": "ENV" if os.environ.get("SCRIBE3_MEMORY_STEER_MODE") else "UNTESTED",
        "D6_epistemic_floor": "SEE_PROBE",
        "D7_gain_floor": "PASS" if (ud or {}).get("summary") else "FAIL",
    }

    out_path = Path(args.out) if args.out else (
        ROOT / "artifacts" / f"12-quality-d1-7-{w}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md = f"""# 七维记忆质量报告 · {w}

| 项 | 值 |
|----|-----|
| 生成 | {datetime.now(timezone.utc).isoformat()} |
| 书 | `{w}` · chapter={args.chapter} |
| prefetch | http={code} len={len(ctx)} |
| **声明** | **下列「质量分」未填人评前不得写 ≥9.5；通/绿 alone 封顶 6.0** |

## 自动化地板（≤6.0 权重）

```json
{json.dumps(floors, ensure_ascii=False, indent=2)}
```

| 检查 | 结果 |
|------|------|
| 双真（完整无缺∧缺口） | {"是 FAIL" if dual else "否"} |
| 有缺口新态 | {has_gap} |
| must-link/戏剧必需 | {has_must} |
| 作者铁律 | {has_law} |
| usage_digest | {bool((ud or {}).get("summary"))} |
| 主角色行 | `{main_cast[:120]}` |
| 主角色噪声嫌疑 | {noisy} |

## 质量分（人评槽 · 默认空）

| 维 | 质量分 (0–10) | 证据 / 人评纪要 |
|----|---------------|-----------------|
| D1 诚实 |  | 对抗未写入设定时是否承认不知 |
| D2 铁律 |  | minimal 下铜腥/禁系统流是否进正文 |
| D3 正典叙事 |  | 极简指令下是否像记得世界（非清单） |
| D4 变更一致 |  | 改设定后注入面零互斥 + 正文跟新 |
| D5 少喂连贯 |  | A/B 消融：见 ablation_memory_d5d7 |
| D6 限知 |  | 认知问卷：灰狸是否「已知」开侧门 |
| D7 增益 |  | comparison_protocol 三项 + 领先 1.5 |

**综合质量：** _未人评，不得填 9.5_

## usage_digest

{(ud or {}).get("summary") or "—"}

## 上下文摘录

```
{ctx[:1500]}
```
"""
    out_path.write_text(md, encoding="utf-8")
    print("wrote", out_path)
    print("floors", floors)
    sys.exit(0 if not dual and code == "200" else 2)


if __name__ == "__main__":
    main()
