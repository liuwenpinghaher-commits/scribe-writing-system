"""Mechanical negative samples for R2. No hand-picking. No LLM rewrite."""
from __future__ import annotations

import re

from scribe3.eval.extract_card import load_source_slice, parse_card
from scribe3.eval.score_r1 import load_label_card

_CITE = re.compile(r"^\s*[-*]\s*.*?[：:](.+)$")
LECTURE = "他终于释怀了。"


def citation_quotes(section: str) -> list[str]:
    out = []
    for line in (section or "").splitlines():
        m = _CITE.match(line)
        if m:
            q = m.group(1).strip().strip("「」""\"'")
            if q:
                out.append(q)
    return out


def _drop(text: str, quotes: list[str]) -> str:
    out = text
    for q in quotes:
        if q and q in out:
            out = out.replace(q, "")
    return out


def _replace(text: str, quotes: list[str], new: str) -> str:
    out = text
    for q in quotes:
        if q and q in out:
            out = out.replace(q, new)
    return out


def turn_quotes(seq: int) -> list[str]:
    gold = parse_card(load_label_card(seq))
    return citation_quotes(gold.get("这场戏有没有翻", ""))


def stay_quotes(seq: int) -> list[str]:
    """账/回不去：处境翻的那一截。灌样本要抹掉它，留下热闹。"""
    gold = parse_card(load_label_card(seq))
    stay = citation_quotes(gold.get("这一节回不去的事", ""))
    turns = turn_quotes(seq)
    # Prefer quotes that the 翻段也点过；没有交集就用回不去的全部。
    hit = [s for s in stay if any(s in t or t in s for t in turns)]
    return hit or stay or (turns[-1:] if turns else [])


def make_cut(seq: int) -> str:
    return _drop(load_source_slice(seq), turn_quotes(seq))


def make_pump(seq: int) -> str:
    return _drop(load_source_slice(seq), stay_quotes(seq))


def make_lecture(seq: int) -> str:
    return _replace(load_source_slice(seq), turn_quotes(seq), LECTURE)


def make_all(seq: int) -> dict[str, str]:
    return {"cut": make_cut(seq), "pump": make_pump(seq), "lecture": make_lecture(seq)}
