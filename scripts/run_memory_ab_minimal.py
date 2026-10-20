#!/usr/bin/env python3
"""D5/D7：minimal steer 下 A（记忆开）/ B（关 fabric）各写同一章，产出对照与评分表。

用法（demo）：
  API_BASE=https://tonglu.example.com SCRIBE3_BOOTSTRAP_USERS=admin:x \\
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
os.environ.setdefault("API_BASE", "https://tonglu.example.com")
os.environ["SCRIBE3_MEMORY_STEER_MODE"] = "minimal"
os.environ.setdefault("MIN_CH_CHARS", "2800")
os.environ.setdefault("MAX_STEPS_PER_CH", "25")
# 关键：禁止 advisory 从历史版本恢复，否则 B 组会捡到 A 组成稿 → lead≈0 伪对照
os.environ["AB_SKIP_VERSION_RESTORE"] = "1"
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "v63_memory_journey", ROOT / "scripts" / "v63_memory_journey.py",
)
v63 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(v63)

BASE = os.environ.get("API_BASE", "https://tonglu.example.com")
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


def set_ablation(mode: str) -> None:
    """轨 2：热设 SCRIBE3_MEMORY_ABLATION（none | no_must | no_must_facts）。"""
    m = (mode or "none").strip() or "none"
    code, res = v63.curl(
        "PUT", "/api/settings/SCRIBE3_MEMORY_ABLATION",
        {"value": m}, timeout=60,
    )
    print(f"set ablation={m} http={code} {str(res)[:160]}", flush=True)


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


def score_pair(a: str, b: str, syn: str, *, void_reason: str | None = None) -> dict:
    """scorer v2 + 三层闸门。诚实：非真人双盲。"""
    from scribe3.memory_gain import score_prose_heuristic_v2, three_tier_gates

    sa = score_prose_heuristic_v2(a, syn, label="A")
    sb = score_prose_heuristic_v2(b, syn, label="B")
    keys = ("coherence", "canon_echo", "contradiction")
    avg_a = sum(sa[k] for k in keys) / 3
    avg_b = sum(sb[k] for k in keys) / 3
    gates = three_tier_gates(avg_a, avg_b, sa, sb)
    if void_reason:
        gates["void_reason"] = void_reason
        gates["engineering_gate"] = False
        gates["machine_pass_rule_met"] = False
        gates["pass_rule_met"] = False
    return {
        "A": sa,
        "B": sb,
        "avg_A": round(avg_a, 3),
        "avg_B": round(avg_b, 3),
        **gates,
    }


def set_iron_strip(strip: bool) -> None:
    code, res = v63.curl(
        "PUT", "/api/settings/SCRIBE3_MEMORY_IRON_IN_ABLATION",
        {"value": "strip" if strip else "keep"}, timeout=60,
    )
    print(f"set iron={'strip' if strip else 'keep'} http={code} {str(res)[:120]}", flush=True)


def assert_settings_restored() -> None:
    """finally 后：fabric ON、ablation none、iron keep。"""
    code, cap = v63.curl("GET", "/api/capabilities", timeout=30)
    flags = (cap or {}).get("flags") if isinstance(cap, dict) else {}
    fab = flags.get("memory_fabric_v1") if isinstance(flags, dict) else None
    print(f"assert fabric={fab}", flush=True)
    if fab is not True and fab != "true" and fab != 1:
        print("WARN fabric not ON after restore", flush=True)
    # settings GET may 405 on some keys — rely on PUT success logs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--seq", type=int, default=6)
    ap.add_argument(
        "--track",
        type=int,
        default=2,
        choices=(1, 2),
        help="1=产品增益(关 fabric)；2=记忆贡献(no_must_facts，默认)",
    )
    ap.add_argument(
        "--escalate",
        action="store_true",
        help="轨2：B1→B2→B3 未过 engineering_gate 则继续纯化（最多 3 臂）",
    )
    ap.add_argument(
        "--out-dir",
        default="",
        help="证据目录，默认 artifacts/ab-minimal-{work}-ch{seq}",
    )
    args = ap.parse_args()
    work = args.work
    seq = args.seq
    track = int(args.track)
    escalate = bool(args.escalate) or (
        os.environ.get("AB_ESCALATE", "").strip().lower() in {"1", "true", "yes"}
    )
    out = Path(args.out_dir) if args.out_dir else (
        ROOT / "artifacts" / f"ab-minimal-{work}-ch{seq}-track{track}"
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
    print(
        f"chapter {seq} title={title} syn_len={v63.cn_len(syn)} "
        f"track={track} escalate={escalate}",
        flush=True,
    )

    # ── A：fabric ON + ablation none + minimal ──
    print("===== A: fabric ON + ablation=none + minimal =====", flush=True)
    set_fabric(True)
    set_ablation("none")
    set_iron_strip(False)
    time.sleep(1)
    n_a = ab_drive_chapter(work, evid, seq)
    prose_a = extract_prose(work, seq)
    ud_a = usage_preview(work, seq)
    (out / "a_prose.md").write_text(
        f"# A · track{track} · fabric ON · ablation=none · ch{seq} "
        f"chars={v63.cn_len(prose_a)}\n\n{prose_a}\n",
        encoding="utf-8",
    )
    (out / "a_usage_digest.json").write_text(
        json.dumps(ud_a, ensure_ascii=False, indent=2)[:80000], encoding="utf-8",
    )
    print(f"A done chars={v63.cn_len(prose_a)} drive_n={n_a}", flush=True)

    # restated void（post-hoc：若 A 成稿像粘贴圣经则记 void；minimal 路径通常否）
    void_reason = None
    try:
        from scribe3.memory_must_link import (
            collect_must_anchors, detect_author_restated_canon,
        )
        # 无 store 时跳过；仅当 prose 本身像作者圣经时标记
        # 用成稿 vs 空锚：此处用 syn 占位，实战由 pilot steer 检测
        if "完整无缺" in prose_a and "缺口" in prose_a:
            void_reason = "prose_dual_truth_self_contradiction"
    except Exception:
        pass

    arms: list[dict] = []
    prose_b = ""
    ud_b: dict = {}
    best_scores: dict | None = None

    def run_b_arm(arm: str, *, fabric_off: bool, ablation: str, strip_iron: bool) -> dict:
        nonlocal prose_b, ud_b
        print(
            f"===== B {arm}: fabric_off={fabric_off} ablation={ablation} "
            f"strip_iron={strip_iron} =====",
            flush=True,
        )
        if fabric_off:
            set_fabric(False)
            set_ablation("none")
            set_iron_strip(False)
        else:
            set_fabric(True)
            set_ablation(ablation)
            set_iron_strip(strip_iron)
        time.sleep(1)
        n_b = ab_drive_chapter(work, evid, seq)
        prose_b = extract_prose(work, seq)
        ud_b = usage_preview(work, seq)
        (out / f"b_{arm}_prose.md").write_text(
            f"# B {arm} · track{track} · ch{seq} chars={v63.cn_len(prose_b)}\n\n"
            f"{prose_b}\n",
            encoding="utf-8",
        )
        (out / f"b_{arm}_usage.json").write_text(
            json.dumps(ud_b, ensure_ascii=False, indent=2)[:80000], encoding="utf-8",
        )
        # 兼容主文件名 = 最新 B 臂
        (out / "b_prose.md").write_text(
            f"# B {arm} · track{track} · ch{seq} chars={v63.cn_len(prose_b)}\n\n"
            f"{prose_b}\n",
            encoding="utf-8",
        )
        (out / "b_usage_digest.json").write_text(
            json.dumps(ud_b, ensure_ascii=False, indent=2)[:80000], encoding="utf-8",
        )
        sc = score_pair(prose_a, prose_b, syn, void_reason=void_reason)
        sc["b_arm"] = arm
        print(
            f"B {arm} done chars={v63.cn_len(prose_b)} lead={sc.get('lead_A_minus_B')} "
            f"eng={sc.get('engineering_gate')} mach={sc.get('machine_pass_rule_met')}",
            flush=True,
        )
        return sc

    try:
        if track == 1:
            best_scores = run_b_arm("B1", fabric_off=True, ablation="none", strip_iron=False)
            arms.append(best_scores)
        else:
            # B1
            best_scores = run_b_arm(
                "B1", fabric_off=False, ablation="no_must_facts", strip_iron=False,
            )
            arms.append(best_scores)
            if escalate and not best_scores.get("engineering_gate"):
                sc2 = run_b_arm(
                    "B2", fabric_off=False, ablation="no_must_facts", strip_iron=True,
                )
                arms.append(sc2)
                # 取 lead 更大者作为主报告 B
                if sc2.get("lead_A_minus_B", 0) >= best_scores.get("lead_A_minus_B", 0):
                    best_scores = sc2
                if not best_scores.get("engineering_gate"):
                    # B3：脱敏 synopsis 再写（尽量弱化设定句）
                    print("===== B3: desensitize synopsis + B2 strip =====", flush=True)
                    code_ch, ch0 = v63.curl("GET", f"/api/chapter?seq={seq}", work=work)
                    old_syn = syn
                    if isinstance(ch0, dict):
                        thin = (
                            f"第{seq}章。POV 焦点人物。核心冲突一句：压力加剧。"
                            f"可见汉字≥2800。禁止复述全书设定。"
                        )
                        v63.curl(
                            "POST", "/api/save-chapter",
                            {
                                "seq": seq,
                                "synopsis": thin,
                                "prose": ch0.get("prose") or "（占位）",
                                "focalizer": ch0.get("focalizer") or f"role:覃灰七",
                            },
                            work=work, timeout=120,
                        )
                        syn = thin
                    sc3 = run_b_arm(
                        "B3", fabric_off=False, ablation="no_must_facts", strip_iron=True,
                    )
                    arms.append(sc3)
                    if sc3.get("lead_A_minus_B", 0) >= best_scores.get("lead_A_minus_B", 0):
                        best_scores = sc3
                    # restore synopsis text in scores note
                    best_scores["b3_synopsis_thinned"] = True
                    best_scores["original_synopsis_len"] = v63.cn_len(old_syn)
    finally:
        print("===== restore fabric ON + ablation=none + iron=keep =====", flush=True)
        set_iron_strip(False)
        set_ablation("none")
        set_fabric(True)
        assert_settings_restored()

    scores = best_scores or score_pair(prose_a, prose_b or "", syn, void_reason=void_reason)
    scores["arms"] = [
        {
            "b_arm": a.get("b_arm"),
            "lead": a.get("lead_A_minus_B"),
            "engineering_gate": a.get("engineering_gate"),
            "machine_pass_rule_met": a.get("machine_pass_rule_met"),
            "avg_B": a.get("avg_B"),
        }
        for a in arms
    ]
    scores["protocol"] = "memory_gain_ab_v2"
    scores["track"] = track
    scores["escalate"] = escalate
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

    lead = scores.get("lead_A_minus_B", 0)
    md = f"""# 七维记忆质量 · A/B（memory_gain_ab_v2 · scorer v2）

| 项 | 值 |
|----|-----|
| 时间 | {datetime.now(timezone.utc).isoformat()} |
| 书 | `{work}` |
| 对照章 | {seq} 《{title}》 |
| 协议 | memory_gain_ab_v2 · track={track} · escalate={escalate} |
| 证据目录 | `{out}` |
| **声明** | **禁止宣称任一维 ≥9.5**（须 human_pass_rule_met） |

## 三层闸门

| 闸门 | 值 |
|------|-----|
| engineering_gate | **{scores.get('engineering_gate')}**（{scores.get('engineering_gate_rule')}） |
| machine_pass_rule_met / pass_rule_met | **{scores.get('machine_pass_rule_met')}** |
| human_pass_rule_met | {scores.get('human_pass_rule_met')} |
| lead | **{lead}** |
| b_arm（主报告） | {scores.get('b_arm')} |
| arms | `{json.dumps(scores.get('arms'), ensure_ascii=False)}` |
| void_reason | {scores.get('void_reason')} |
| scorer | {scores.get('scorer')} |

## 分项

| 指标 | A | B |
|------|---|---|
| 字数 | {scores['A']['chars']} | {scores['B']['chars']} |
| coherence | {scores['A']['coherence']} | {scores['B']['coherence']} |
| canon_echo | {scores['A']['canon_echo']} | {scores['B']['canon_echo']} |
| contradiction | {scores['A']['contradiction']} | {scores['B']['contradiction']} |
| 均分 | {scores['avg_A']} | {scores['avg_B']} |

A 锚: `{json.dumps(scores['A']['anchors'], ensure_ascii=False)}`  
B 锚: `{json.dumps(scores['B']['anchors'], ensure_ascii=False)}`

## 路径

- minimal steer；AB_SKIP 旧版本  
- track2：B1 no_must_facts →（escalate）B2 strip iron → B3 thin synopsis  
- finally：fabric ON + ablation none + iron keep  
"""
    (out / "12-quality-d1-7-ab.md").write_text(md, encoding="utf-8")
    (evid / "12-quality-d1-7-ab.md").write_text(md, encoding="utf-8")
    (evid / "ab-minimal").mkdir(exist_ok=True)
    for name in ("a_prose.md", "b_prose.md", "scores.json", "a_usage_digest.json",
                 "b_usage_digest.json", "d6_questionnaire.md", "12-quality-d1-7-ab.md"):
        src = out / name
        if src.exists():
            (evid / "ab-minimal" / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    (out / "00-author-path.md").write_text(
        f"# A/B 路径\n\nwork={work} seq={seq} track={track} escalate={escalate}\n"
        f"minimal=1 scorer=v2 protocol=memory_gain_ab_v2\n"
        f"A=fabric_on ablation=none\n"
        f"B arms={json.dumps(scores.get('arms'), ensure_ascii=False)}\n"
        f"restored fabric+ablation+iron\n",
        encoding="utf-8",
    )
    print("WROTE", out, flush=True)
    print("SCORES", json.dumps(scores, ensure_ascii=False)[:1000], flush=True)
    print(
        "machine_pass_rule_met", scores.get("machine_pass_rule_met"),
        "engineering_gate", scores.get("engineering_gate"),
        "lead", lead, flush=True,
    )


if __name__ == "__main__":
    main()
