#!/usr/bin/env python3
"""Deterministic D1–D7 narrative quality rubric (anti-stuffing).

Composite = mean of D1..D7 (0–10 each). Uses shipped beat_shape / anti_meta.
Scoring uses **set presence** and structural ratios — repeating the same
keyword 100× does **not** raise the score (anti keyword-spam).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scribe3.anti_meta_narration import scan_anti_meta
from scribe3.narrative_contract import (
    conflict_beats_ok,
    cn_len,
    validate_narrative_contract,
)

DIMS = ("D1", "D2", "D3", "D4", "D5", "D6", "D7")

CONF_LEX = (
    "拦", "讨", "逼", "拒", "抵", "债", "威胁", "对峙", "扯", "跟", "缠",
    "不肯", "被迫", "挡", "压", "踢", "撞", "抢", "夺", "骗", "骂", "撵",
)
TURN_COST = (
    "抵账", "勾账", "勾了", "答应", "交出", "倒进", "塞进", "撕", "毁",
    "半袋", "半炉", "不再", "暂不", "代价", "欠", "丢下", "点名",
    "写进", "按手印", "还清", "半笔", "记一笔", "加账", "减账", "拒交",
)
BODY = (
    "抓", "扯", "踢", "撞", "拧", "按", "推", "塞", "倒", "舀", "咬",
    "甩", "顶", "跪", "抽", "拦", "夺", "挡",
)
SENSE = (
    "铜腥", "炉灰", "热灰", "烫", "疼", "账", "锅", "灰溅", "红印",
    "焦糊", "血", "汗",
)
COOL = ("清醒", "先不推", "心口发紧", "像提醒", "雾还没散")
COST_LINK = (
    "抵账", "勾账", "香债", "欠", "代价", "勾了", "记一笔", "还清",
    "加账", "减账", "拒交",
)


def _clamp(x: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, x))


def _r1(x: float) -> float:
    return round(float(x) + 1e-9, 1)


def _r2(x: float) -> float:
    return round(float(x) + 1e-9, 2)


def _present(prose: str, keys: tuple[str, ...] | list[str]) -> int:
    """How many distinct keys appear (≥1). Spam of one key counts as 1."""
    return sum(1 for k in keys if k in prose)


def score_chapter(
    *,
    prose: str,
    title: str = "",
    synopsis: str = "",
    contract: dict | None = None,
    beats: list | None = None,
    prior_keywords: list[str] | None = None,
) -> dict:
    prose = prose or ""
    n = max(1, cn_len(prose))
    quotes: dict[str, str] = {}
    lines = [ln.strip() for ln in prose.splitlines() if ln.strip()]

    # --- D1: evidence_must_show coverage (R8 W7b); no lex-count KPI
    from scribe3.story_constraint_prompt import load_evidence_must_show
    traces = load_evidence_must_show({"narrative_contract": contract or {}})
    if not traces:
        d1 = 0.0
        quotes["D1"] = "evidence_missing"
    else:
        hit = sum(1 for t in traces if t and (t in prose or t[:8] in prose))
        d1 = _clamp(2.0 + 8.0 * (hit / max(1, len(traces))))
        quotes["D1"] = f"evidence_hit={hit}/{len(traces)}"

    # --- D2 turn/cost: distinct irreversible markers + contract fields
    tc_n = _present(prose, TURN_COST)
    contract_ok = False
    c = None
    if contract:
        c = validate_narrative_contract(contract)
        contract_ok = bool(c.get("validation", {}).get("ok"))
        if contract_ok:
            tc_n += 0  # already covered by field quality below
    field_bonus = 0.0
    if c and contract_ok:
        # longer specific turn/cost (not placeholders) — cap once
        field_bonus = min(
            1.5,
            0.4 * sum(
                1
                for k in ("turn", "cost")
                if cn_len(c.get(k) or "") >= 12
            )
            + 0.35 * sum(
                1
                for k in ("desire", "obstacle")
                if cn_len(c.get(k) or "") >= 12
            ),
        )
    d2 = _clamp(2.5 + min(5.5, tc_n * 0.52) + field_bonus + (0.5 if contract_ok else 0.0))
    quotes["D2"] = f"distinct_turn_cost={tc_n}, contract_ok={contract_ok}, field_bonus={field_bonus:.2f}"

    # --- D3 dialogue/body: ratio of unique dlg lines + distinct body verbs; penalize cool template
    dlg_lines = [ln for ln in lines if "「" in ln]
    # unique dialogue lines
    dlg_u = len(set(dlg_lines))
    body_n = _present(prose, BODY)
    cool_n = _present(prose, COOL)
    # structural: share of lines that are dialogue (capped; spam same line doesn't help after set)
    dlg_share = dlg_u / max(1, len(set(lines)))
    # strong multi-voice action scenes can approach 10 without keyword spam
    d3 = _clamp(
        2.5
        + min(5.0, dlg_share * 9.0)
        + min(2.5, body_n * 0.28)
        - min(2.0, cool_n * 0.7)
    )
    quotes["D3"] = f"unique_dlg_lines={dlg_u}, distinct_body={body_n}, cool={cool_n}, dlg_share={dlg_share:.2f}"

    # --- D4 shipped beat_shape
    items = beats
    if contract and isinstance(contract.get("conflict_beats"), list):
        items = contract["conflict_beats"]
    items = items or []
    cb = conflict_beats_ok(items)
    ratio = (cb["valid"] / cb["total"]) if cb["total"] else 0.0
    prop_n = len(cb.get("prop_like") or [])
    # more valid conflict beats (honest multi-turn) can push D4 to 10
    d4 = _clamp(2.0 + ratio * 5.5 + min(2.5, cb["valid"] * 0.55) - prop_n * 1.5)
    if not cb["ok"]:
        d4 = min(d4, 4.0)
    quotes["D4"] = f"conflict_beats valid={cb['valid']}/{cb['total']} prop_like={prop_n}"

    # --- D5 continuity: distinct prior stakes present (set)
    prior = prior_keywords or [
        "匙", "炉", "灰狸", "冷锅", "侧门", "香债", "铜", "炉册", "爹", "假片",
        "夜审", "缺口", "脚印",
    ]
    cont = _present(prose, prior)
    core = ("香债", "侧门", "炉册", "夜审", "爹", "匙")
    core_n = _present(prose, core)
    d5 = _clamp(2.5 + min(5.0, cont * 0.35) + min(2.5, core_n * 0.4))
    quotes["D5"] = f"prior_present={cont}/{len(prior)}, core_present={core_n}"

    # --- D6 anti_meta shipped; slight length floor but not reward for padding past 1200
    am = scan_anti_meta(prose)
    claim_n = len(am.get("claim_blocking_ids") or [])
    soft_n = sum(1 for h in (am.get("hits") or []) if h.get("severity") == "soft")
    if am.get("ok_for_claim") and claim_n == 0:
        # plateau by ~1200 cn for full multi-beat chapter; beyond that no D6 gain
        len_part = min(1.8, max(0.0, (min(n, 1200) - 400) / 444.0))
        d6 = _clamp(7.0 + len_part - soft_n * 0.4)
    else:
        d6 = max(1.0, 3.0 - claim_n * 1.5)
    quotes["D6"] = f"ok_for_claim={am.get('ok_for_claim')} claim_hits={claim_n} soft={soft_n} cn={n}"

    # --- D7 sensory as plot cost: distinct sense types + cost link (once)
    sense_n = _present(prose, SENSE)
    cost_link = any(k in prose for k in COST_LINK)
    # fuller sensory palette (up to 12 types) can edge above 9.3 without spam
    d7 = _clamp(2.5 + min(5.5, sense_n * 0.48) + (1.8 if cost_link else 0.0))
    quotes["D7"] = f"distinct_sense={sense_n}, cost_linked={cost_link}"

    dims = {k: _r1(v) for k, v in zip(DIMS, (d1, d2, d3, d4, d5, d6, d7))}
    composite = _r2(sum(dims.values()) / 7.0)
    return {
        "title": title,
        "prose_cn": n,
        "dims": dims,
        "composite": composite,
        "quotes": quotes,
        "conflict_beats": cb,
        "contract_ok": contract_ok,
        "anti_meta_ok": bool(am.get("ok_for_claim")),
        "rubric": "anti_stuffing_v2",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prose", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--contract-json", default="")
    ap.add_argument("--beats-json", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    prose = Path(args.prose).read_text(encoding="utf-8")
    if prose.startswith("#"):
        prose = "\n".join(prose.splitlines()[1:]).lstrip()
    contract = (
        json.loads(Path(args.contract_json).read_text(encoding="utf-8"))
        if args.contract_json
        else None
    )
    beats = (
        json.loads(Path(args.beats_json).read_text(encoding="utf-8"))
        if args.beats_json
        else None
    )
    r = score_chapter(prose=prose, title=args.title, contract=contract, beats=beats)
    text = json.dumps(r, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
