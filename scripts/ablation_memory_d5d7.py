#!/usr/bin/env python3
"""D5/D7 消融脚手架：对照「记忆开」vs「关掉 must-link/事实表面」的组装差。

不做 LLM 写章（省费用/时间）；产出可人评的上下文 diff + 协议清单。
质量 9.5 仍须人评成稿 A/B（见 memory_gain.comparison_protocol）。

用法：
  API_BASE=https://www.qing.blue SCRIBE3_BOOTSTRAP_USERS=admin:x \\
  python3 scripts/ablation_memory_d5d7.py --work book_4c7815eb --chapter 4 \\
    --out artifacts/ablation-d5d7-book_4c7815eb.md
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
JAR = os.environ.get("COOKIE_JAR", "/tmp/ablation_d5d7_cookie.txt")


def curl(method, path, data=None, timeout=90, work=""):
    out = Path("/tmp/ablation_d5d7_out.json")
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
    ap.add_argument("--chapter", type=int, default=4)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    w = args.work
    ch = args.chapter
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    u, pw = bu.split(":", 1)
    subprocess.run(["rm", "-f", JAR], check=False)
    code, _ = curl("POST", "/api/auth/login", {"username": u, "password": pw})
    if code != "200":
        raise SystemExit(f"login {code}")

    # A 组：正常记忆
    code_a, pref_a = curl("POST", "/api/memory/prefetch", {
        "query": "本章 冲突 铜匙 缺口",
        "chapter": ch,
        "thread_id": "",
    }, work=w, timeout=120)
    ctx_a = (pref_a or {}).get("context") or "" if isinstance(pref_a, dict) else ""
    ud_a = (pref_a or {}).get("usage_digest") if isinstance(pref_a, dict) else {}

    # B 组：usage-preview 只能看开；「关记忆」用本地模拟：去掉 must/事实块标记行
    # （服务端无 fabric 软关开关时，以上下文差分近似 B）
    lines = ctx_a.splitlines()
    drop_prefixes = (
        "- 〔必需〕", "- world:", "- role:", "- 【本章戏剧必需",
        "- 【作者铁律", "  1.", "  2.",
    )
    ctx_b_lines = []
    for ln in lines:
        if any(ln.startswith(p) or p in ln[:20] for p in (
            "〔必需〕", "戏剧必需", "world:", "role:", "作者铁律", "开放伏笔:",
        )):
            continue
        ctx_b_lines.append(ln)
    ctx_b = "\n".join(ctx_b_lines)

    sys.path.insert(0, str(ROOT))
    from scribe3.memory_must_link import (
        detect_author_restated_canon, is_minimal_steer, minimal_chapter_steer,
    )
    from scribe3.memory_gain import comparison_protocol

    paste = "覃灰七 三棱铜匙 完整无缺 缺口 冷锅婆 炉心印 全部设定粘贴"
    anchors = [
        {"text": "world:三棱铜匙·state=缺口"},
        {"text": "出场/相关角色:覃灰七"},
        {"text": "开放伏笔:三棱铜匙与炉心印鉴伪"},
        {"text": "出场/相关角色:冷锅婆"},
    ]
    restated = detect_author_restated_canon(paste, anchors, threshold=0.5)
    protocol = comparison_protocol()
    min_steer = minimal_chapter_steer(ch, f"第{ch}章", "覃灰七", "铜匙缺口与侧门压力")

    markers_a = {
        "must_link": "戏剧必需" in ctx_a or "〔必需〕" in ctx_a,
        "iron_law": "作者铁律" in ctx_a or "写作宪法" in ctx_a,
        "key_gap": "缺口" in ctx_a,
        "key_intact": "完整无缺" in ctx_a,
        "main_cast": "主要角色" in ctx_a,
        "usage_digest": bool((ud_a or {}).get("summary")),
    }
    markers_b = {
        "must_link": "戏剧必需" in ctx_b or "〔必需〕" in ctx_b,
        "key_gap": "缺口" in ctx_b,
        "iron_law": "作者铁律" in ctx_b,
    }

    out_path = Path(args.out) if args.out else (
        ROOT / "artifacts" / f"ablation-d5d7-{w}-ch{ch}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md = f"""# D5/D7 消融脚手架 · {w} · ch{ch}

| 项 | 值 |
|----|-----|
| 时间 | {datetime.now(timezone.utc).isoformat()} |
| API | {BASE} |
| prefetch A | http={code_a} len={len(ctx_a)} |
| B 近似 | 剥离 must/事实/铁律行后 len={len(ctx_b)} |
| SCRIBE3_MEMORY_STEER_MODE | {os.environ.get('SCRIBE3_MEMORY_STEER_MODE', '(unset→full)')} |
| is_minimal_steer() | {is_minimal_steer()} |

## A 组标记（记忆开）

```json
{json.dumps(markers_a, ensure_ascii=False, indent=2)}
```

usage_digest: {(ud_a or {}).get("summary") or "—"}

## B 组标记（剥离正典注入后）

```json
{json.dumps(markers_b, ensure_ascii=False, indent=2)}
```

**差分期望（质量）：** A 有 must/缺口/铁律；B 明显变「瘦」→ 记忆在扛设定。  
若 A 仍含「完整无缺」与「缺口」双真 → D4 未过关。

## 极简 steer 样例（D5 生产对齐）

```
{min_steer}
```

## 作者粘贴圣经检测

```json
{json.dumps(restated, ensure_ascii=False, indent=2)}
```

restated=True 时该维验收 **一票否决**（不得刷分）。

## 人评 A/B 协议（D7 · 须另写两稿）

```json
{json.dumps(protocol, ensure_ascii=False, indent=2)}
```

### 人评表（填后才可报 ≥9.0）

| 项 | A 开记忆+极简 | B 关记忆/剥注入+极简 |
|----|---------------|----------------------|
| coherence 1–5 |  |  |
| canon_echo 1–5 |  |  |
| contradiction 1–5（越高越好=矛盾少） |  |  |
| 均值 |  |  |
| A 是否领先 ≥1.5 |  |  |

pass_rule: {protocol.get("pass_rule") if isinstance(protocol, dict) else protocol}

## A 上下文摘录（前 1200 字）

```
{ctx_a[:1200]}
```

## B 上下文摘录（前 800 字）

```
{ctx_b[:800]}
```

## 诚实

- 本脚本 **不** 自动宣称 D5/D7 ≥9.5。  
- B 组为客户端剥离近似；完整对照须两轮生成 + 人评。  
"""
    out_path.write_text(md, encoding="utf-8")
    print("wrote", out_path)
    print("markers_a", markers_a)
    print("markers_b", markers_b)
    print("dual_truth_fail", markers_a.get("key_intact") and markers_a.get("key_gap"))
    # 地板：A 有记忆标记且无双真
    ok = code_a == "200" and markers_a.get("key_gap") and not markers_a.get("key_intact")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
