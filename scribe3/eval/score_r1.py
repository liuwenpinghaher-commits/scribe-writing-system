"""R1：系统卡 vs 人工金卡，五个硬字段一致率。

评分器可以读留出章 gold（那是答案）。extract_card 仍然不许读。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scribe3.eval.card_schema import R1_HARD_FIELDS
from scribe3.eval.extract_card import empty_shell_card, parse_card

ROOT = Path(__file__).resolve().parents[2]
EVAL = Path(__file__).resolve().parent
GOLD_DIR = ROOT / "docs/worlds/乱世铜炉-拆文/章卡"
_CITE = re.compile(r"^\s*[-*]\s*")
_ZH = re.compile(r"[\u4e00-\u9fff]+")


def load_label_card(seq: int) -> str:
    """Eval-only. Holdout gold is the answer key."""
    return (GOLD_DIR / f"{seq}.md").read_text(encoding="utf-8")


def scored_seqs() -> list[int]:
    ch = json.loads((EVAL / "chapters.json").read_text(encoding="utf-8"))
    holdout = set(json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))["holdout"])
    out = []
    for row in ch["chapters"]:
        if row["seq"] not in holdout:
            continue
        if row.get("r1_skip_reason"):
            continue
        out.append(row["seq"])
    return out


def turned(text: str) -> bool | None:
    head = (text or "").strip().split("。")[0][:40]
    if "没翻" in head or "没有翻" in head:
        return False
    if head.startswith("翻") or "翻了" in head:
        return True
    return None


def _chars(text: str) -> set[str]:
    body = []
    for line in (text or "").splitlines():
        if _CITE.match(line):
            continue
        body.append(line)
    blob = "".join(_ZH.findall("\n".join(body)))
    return set(blob)


def jaccard(a: str, b: str) -> float:
    sa, sb = _chars(a), _chars(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def score_pair(pred_md: str, gold_md: str) -> dict:
    pred, gold = parse_card(pred_md), parse_card(gold_md)
    fields = {}
    hits = 0
    for name in R1_HARD_FIELDS:
        p, g = pred.get(name, ""), gold.get(name, "")
        if name == "这场戏有没有翻":
            ok = turned(p) is not None and turned(p) == turned(g)
            fields[name] = {"ok": ok, "pred": turned(p), "gold": turned(g)}
        else:
            sim = jaccard(p, g)
            ok = sim >= 0.25
            fields[name] = {"ok": ok, "sim": round(sim, 4)}
        hits += int(fields[name]["ok"])
    n = len(R1_HARD_FIELDS)
    return {"hits": hits, "n": n, "score": hits / n if n else 0.0, "fields": fields}


def ceiling_on_dev(limit: int = 20) -> dict:
    """Gold vs gold. Must be ~1. Uses dev only so the test never depends on holdout files."""
    holdout = set(json.loads((EVAL / "holdout.json").read_text(encoding="utf-8"))["holdout"])
    ch = json.loads((EVAL / "chapters.json").read_text(encoding="utf-8"))
    scores = []
    for row in ch["chapters"]:
        seq = row["seq"]
        if seq in holdout or row.get("r1_skip_reason"):
            continue
        gold = load_label_card(seq)
        scores.append(score_pair(gold, gold)["score"])
        if len(scores) >= limit:
            break
    return {"n": len(scores), "mean": sum(scores) / len(scores) if scores else 0.0}


def floor_on_dev() -> dict:
    gold = load_label_card(1)
    pred = empty_shell_card(1, "空")
    return score_pair(pred, gold)
