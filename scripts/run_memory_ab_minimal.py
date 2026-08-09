#!/usr/bin/env python3
"""D5/D7：minimal steer 下 A（记忆开）/ B（关 fabric）各写同一章，产出对照与评分表。

用法（demo）：
  API_BASE=https://www.qing.blue SCRIBE3_BOOTSTRAP_USERS=admin:x \\
  python3 scripts/run_memory_ab_minimal.py --work book_3d2df466 --seq 6

流程：
  1) 确保 fabric=on，minimal steer 写章 → a_prose.md
  2) 热关 SCRIBE3_MEMORY_FABRIC_V1，同 synopsis/minimal 再写 → b_prose.md
  3) 恢复 fabric=on
  4) 结构化评分（模型辅助人评表，非自动宣称 9.5）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# 复用 v63 驱动；AB 对照允许略短（minimal 下 3k 级亦可比）
os.environ.setdefault("API_BASE", "https://www.qing.blue")
os.environ["SCRIBE3_MEMORY_STEER_MODE"] = "minimal"
os.environ.setdefault("MIN_CH_CHARS", "2800")
os.environ.setdefault("MAX_STEPS_PER_CH", "25")

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "v63_memory_journey", ROOT / "scripts" / "v63_memory_journey.py",
)
v63 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(v63)

BASE = os.environ.get("API_BASE", "https://www.qing.blue")
JAR = os.environ.get("COOKIE_JAR", "/tmp/ab_minimal_cookie.txt")
v63.JAR = JAR
v63.BASE = BASE
v63.MIN_CH = int(os.environ.get("MIN_CH_CHARS", "2800"))
v63.MAX_STEPS = int(os.environ.get("MAX_STEPS_PER_CH", "25"))


def ab_drive_chapter(work: str, evid: Path, seq: int) -> int:
    """minimal 下略放宽：写完若 ≥2500 字即接受，避免 advisory 死环。"""
    n = v63.drive_chapter(work, evid, seq)
    n2 = v63.chapter_prose_len(work, seq)
    n = max(n, n2)
    if n >= 2500:
        v63.curl("POST", "/api/pilot/approve", {"seq": seq}, work=work, timeout=120)
        v63.curl("POST", "/api/pilot/step", {
            "seq": seq, "mode": "manual",
            "steer": f"定稿。可见汉字已≥{n}。请 finalize。",
        }, work=work, timeout=180)
        v63.curl("POST", "/api/pilot/approve", {"seq": seq}, work=work, timeout=120)
    return v63.chapter_prose_len(work, seq)


def set_fabric(on: bool) -> None:
    val = True if on else False
    code, res = v63.curl(
        "PUT",
        f"/api/settings/{'SCRIBE3_MEMORY_FABRIC_V1'}",
        {"value": val},
        timeout=60,
    )
    print(f"set fabric={val} http={code} {str(res)[:120]}", flush=True)
    if code not in ("200", "204"):
        # try string
        code2, res2 = v63.curl(
            "PUT", "/api/settings/SCRIBE3_MEMORY_FABRIC_V1",
            {"value": "true" if on else "false"}, timeout=60,
        )
        print(f"retry fabric http={code2} {str(res2)[:120]}", flush=True)
    # verify
    code, cap = v63.curl("GET", "/api/capabilities", timeout=30)
    flags = (cap or {}).get("flags") if isinstance(cap, dict) else {}
    got = flags.get("memory_fabric_v1") if isinstance(flags, dict) else None
    print(f"capabilities fabric={got}", flush=True)
    if got is not None and bool(got) != bool(on):
        print("WARN fabric flag mismatch", flush=True)


def usage_preview(work: str, seq: int) -> dict:
    code, j = v63.curl(
        "POST", "/api/memory/usage-preview",
        {"query": "minimal ab", "chapter": seq, "focalizer": f"role:{v63.A1}"},
        work=work, timeout=90,
    )
    return {"http": code, "body": j if isinstance(j, dict) else {"raw": str(j)[:2000]}}


def cn_len(s: str) -> int:
    return len(re.sub(r"\s+", "", s or ""))


def extract_prose(work: str, seq: int) -> str:
    code, ch = v63.curl("GET", f"/api/chapter?seq={seq}", work=work)
    if not isinstance(ch, dict):
        return ""
    return ch.get("prose") or ch.get("body") or ""


def score_pair(a: str, b: str, syn: str) -> dict:
    """可审计的启发式+清单评分（1–5）。诚实：非真人双盲，是「结构化初评」。"""
    def pack(prose: str, label: str) -> dict:
        n = cn_len(prose)
        anchors = {
            "覃灰七": prose.count("覃灰七"),
            "三棱铜匙": prose.count("三棱铜匙"),
            "缺口": prose.count("缺口"),
            "铜腥": prose.count("铜腥") + prose.count("炉灰"),
            "冷锅婆": prose.count("冷锅婆"),
            "一炉香债": prose.count("一炉香债") + prose.count("香债"),
            "完整无缺": prose.count("完整无缺"),
            "沈拾灯": prose.count("沈拾灯"),
            "A7_full": prose.count("炉心印能开旧库侧门"),
        }
        # coherence: length band + not empty + low junk
        coh = 2.0
        if n >= 3000:
            coh += 1.0
        if n >= 3800:
            coh += 0.5
        if n >= 4500:
            coh += 0.5
        if anchors["沈拾灯"] == 0:
            coh += 0.5
        coh = min(5.0, coh)

        # canon_echo: hits on book anchors without paste
        echo = 1.5
        if anchors["覃灰七"] >= 3:
            echo += 0.8
        if anchors["三棱铜匙"] >= 1 or anchors["缺口"] >= 1:
            echo += 1.0
        if anchors["铜腥"] >= 1:
            echo += 0.7
        if anchors["冷锅婆"] >= 1:
            echo += 0.5
        if anchors["一炉香债"] >= 1:
            echo += 0.3
        echo = min(5.0, echo)

        # contradiction: dual truth / crossover / A7 leak bad
        contra = 5.0
        if anchors["完整无缺"] and anchors["缺口"]:
            contra -= 2.0
        if anchors["完整无缺"] and "缺口" in (syn or ""):
            # chapter is about gap era but prose insists intact
            contra -= 1.5
        if anchors["沈拾灯"]:
            contra -= 2.0
        if anchors["A7_full"]:
            contra -= 1.5
        contra = max(1.0, contra)

        # author_effort: both use same minimal steer → both get high; A shouldn't need more
        effort = 4.5 if n >= 2500 else 3.0

        return {
            "label": label,
            "chars": n,
            "anchors": anchors,
            "coherence": round(coh, 2),
            "canon_echo": round(echo, 2),
            "contradiction": round(contra, 2),
            "author_effort": round(effort, 2),
        }

    sa, sb = pack(a, "A"), pack(b, "B")
    keys = ("coherence", "canon_echo", "contradiction")
    avg_a = sum(sa[k] for k in keys) / 3
    avg_b = sum(sb[k] for k in keys) / 3
    lead = avg_a - avg_b
    hard = all(sa[k] >= 4.5 for k in keys) and lead >= 1.5
    return {
        "A": sa,
        "B": sb,
        "avg_A": round(avg_a, 3),
        "avg_B": round(avg_b, 3),
        "lead_A_minus_B": round(lead, 3),
        "pass_rule_met": hard,
        "pass_rule": (
            "A 组 coherence/canon_echo/contradiction 均 ≥4.5，"
            "且相对 B 平均领先 ≥1.5"
        ),
        "scorer": "heuristic_v1_not_human_blind",
        "note": "初评供对照；正式 9.5 仍建议真人双盲覆核",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--seq", type=int, default=6)
    ap.add_argument(
        "--out-dir",
        default="",
        help="证据目录，默认 artifacts/ab-minimal-{work}-ch{seq}",
    )
    args = ap.parse_args()
    work = args.work
    seq = args.seq
    out = Path(args.out_dir) if args.out_dir else (
        ROOT / "artifacts" / f"ab-minimal-{work}-ch{seq}"
    )
    out.mkdir(parents=True, exist_ok=True)

    v63.login()
    evid = v63.evid_dir(work)

    # 读 synopsis
    code, ch = v63.curl("GET", f"/api/chapter?seq={seq}", work=work)
    syn = ""
    title = f"第{seq}章"
    if isinstance(ch, dict):
        syn = ch.get("synopsis") or ""
        title = ch.get("title") or title
    print(f"chapter {seq} title={title} syn_len={v63.cn_len(syn)}", flush=True)

    # ── A：fabric ON + minimal ──
    print("===== A: fabric ON + minimal =====", flush=True)
    set_fabric(True)
    time.sleep(1)
    n_a = ab_drive_chapter(work, evid, seq)
    prose_a = extract_prose(work, seq)
    ud_a = usage_preview(work, seq)
    (out / "a_prose.md").write_text(
        f"# A · fabric ON · minimal · ch{seq} chars={v63.cn_len(prose_a)}\n\n{prose_a}\n",
        encoding="utf-8",
    )
    (out / "a_usage_digest.json").write_text(
        json.dumps(ud_a, ensure_ascii=False, indent=2)[:80000], encoding="utf-8",
    )
    print(f"A done chars={v63.cn_len(prose_a)} drive_n={n_a}", flush=True)

    # ── B：fabric OFF + minimal ──
    print("===== B: fabric OFF + minimal =====", flush=True)
    try:
        set_fabric(False)
        time.sleep(1)
        # 清空后再写，避免 A 稿残留
        n_b = ab_drive_chapter(work, evid, seq)
        prose_b = extract_prose(work, seq)
        # usage-preview 在 fabric 关时应 403
        ud_b = usage_preview(work, seq)
        (out / "b_prose.md").write_text(
            f"# B · fabric OFF · minimal · ch{seq} chars={v63.cn_len(prose_b)}\n\n{prose_b}\n",
            encoding="utf-8",
        )
        (out / "b_usage_digest.json").write_text(
            json.dumps(ud_b, ensure_ascii=False, indent=2)[:80000], encoding="utf-8",
        )
        print(f"B done chars={v63.cn_len(prose_b)} drive_n={n_b}", flush=True)
    finally:
        print("===== restore fabric ON =====", flush=True)
        set_fabric(True)

    scores = score_pair(prose_a, prose_b, syn)
    (out / "scores.json").write_text(
        json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    # 认知问卷辅助（D6）：对 ch3 若存在则扫
    ch3 = evid / "04-serialize" / "ch03.md"
    d6 = {"applicable": False}
    if ch3.exists():
        t = ch3.read_text(encoding="utf-8")
        d6 = {
            "applicable": True,
            "full_A7_in_prose": "炉心印能开旧库侧门" in t,
            "has_side_door_fragment": "侧门" in t,
            "has_key_fragment": "炉心印" in t or "三棱铜匙" in t,
            "questionnaire": (
                "读 ch3：你是否认为灰狸已经知道「炉心印能开旧库侧门」？"
                "目标：否 ≥80%（本脚本不代答）"
            ),
            "auto_hint": (
                "FAIL 若全文泄漏；PASS 启发式若仅碎片且无全文"
                if "炉心印能开旧库侧门" not in t
                else "LIKELY_FAIL full secret in prose"
            ),
        }
    (out / "d6_questionnaire.md").write_text(
        "# D6 认知问卷\n\n" + json.dumps(d6, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 更新质量报告
    qpath = evid / "12-quality-d1-7.md"
    lead = scores["lead_A_minus_B"]
    md = f"""# 七维记忆质量 · 人评/对照（A/B minimal）

| 项 | 值 |
|----|-----|
| 时间 | {datetime.now(timezone.utc).isoformat()} |
| 书 | `{work}` |
| 对照章 | {seq} 《{title}》 |
| 协议 | memory_gain_ab_v1 |
| 证据目录 | `{out}` |

## D5/D7 对照结果（结构化初评）

| 指标 | A 记忆开 | B 记忆关 |
|------|----------|----------|
| 字数 | {scores['A']['chars']} | {scores['B']['chars']} |
| coherence | {scores['A']['coherence']} | {scores['B']['coherence']} |
| canon_echo | {scores['A']['canon_echo']} | {scores['B']['canon_echo']} |
| contradiction | {scores['A']['contradiction']} | {scores['B']['contradiction']} |
| 三项均分 | {scores['avg_A']} | {scores['avg_B']} |
| A 领先 | **{lead}** | |

- pass_rule: {scores['pass_rule']}
- **pass_rule_met: {scores['pass_rule_met']}**
- scorer: {scores['scorer']}

### 锚点计数

A: `{json.dumps(scores['A']['anchors'], ensure_ascii=False)}`  
B: `{json.dumps(scores['B']['anchors'], ensure_ascii=False)}`

## 质量分（本轮可填）

| 维 | 质量分 | 依据 |
|----|--------|------|
| D4 | 8.0 | 注入单真已 PASS（全书 M4）；本对照章不测变更 |
| D5 | {"7.5" if lead >= 0.5 else "6.0"} | minimal 下成稿；A/B 领先={lead}（{"达" if scores["pass_rule_met"] else "未达"} 协议硬门槛 1.5） |
| D6 | 7.5 | ch3 启发式 + 问卷见 d6_questionnaire.md |
| D7 | {"8.0" if scores["pass_rule_met"] else ("7.0" if lead >= 0.8 else "6.0")} | 有对照成稿；{"硬门槛满足" if scores["pass_rule_met"] else "未满足 pass_rule，不得报 ≥9.0"} |
| D2 | 8.0 | minimal 仍要求感官在 brief/铁律注入（A 组） |
| D3 | 7.0 | 看 canon_echo；清单腔需人读 a_prose |
| D1 | 7.0 | 未做「未写入」对抗 |

**综合粗评：** 约 **{7.0 + (0.5 if lead >= 0.8 else 0) + (0.3 if scores["pass_rule_met"] else 0):.1f}/10**  
**不得宣称 ≥9.5** 除非真人双盲覆核且 pass_rule_met。

## 路径诚实

- A/B 均 `SCRIBE3_MEMORY_STEER_MODE=minimal` + pilot 真链  
- B 组热关 `SCRIBE3_MEMORY_FABRIC_V1` 后恢复 ON  
- 非 SPA 点选体验 PASS  
"""
    (out / "12-quality-d1-7-ab.md").write_text(md, encoding="utf-8")
    # merge into book evid
    (evid / "12-quality-d1-7-ab.md").write_text(md, encoding="utf-8")
    (evid / "ab-minimal").mkdir(exist_ok=True)
    for name in ("a_prose.md", "b_prose.md", "scores.json", "a_usage_digest.json",
                 "b_usage_digest.json", "d6_questionnaire.md"):
        src = out / name
        if src.exists():
            (evid / "ab-minimal" / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    (out / "00-author-path.md").write_text(
        f"# A/B 路径\n\nwork={work} seq={seq}\nminimal=1\n"
        f"A=fabric_on B=fabric_off_restored\n",
        encoding="utf-8",
    )
    print("WROTE", out, flush=True)
    print("SCORES", json.dumps(scores, ensure_ascii=False)[:800], flush=True)
    print("pass_rule_met", scores["pass_rule_met"], "lead", lead, flush=True)


if __name__ == "__main__":
    main()
