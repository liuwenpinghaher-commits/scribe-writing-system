"""故事线注入 polish（O33 · 旗控 · 不挡 redline）。"""
from __future__ import annotations

import os
from typing import Any


def storyline_inject_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_STORYLINE_INJECT") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def build_storyline_inject_segment(
    *,
    focus_seq: int | None = None,
    gantt_rows: list[dict[str, Any]] | None = None,
    open_promise_texts: list[str] | None = None,
    emotion_point: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """短注入段 + raw/audit；不读 tokens_saved。"""
    lines: list[str] = []
    raw_bits: list[str] = []
    if focus_seq:
        lines.append(f"焦点章：第{int(focus_seq)}章")
        raw_bits.append(f"focus={focus_seq}")
    if gantt_rows:
        nearby = [r for r in gantt_rows if isinstance(r, dict)][:5]
        phases = ", ".join(f"#{r.get('seq')}:{r.get('phase')}" for r in nearby)
        if phases:
            lines.append(f"近程阶段：{phases}")
            raw_bits.append(phases)
    for t in (open_promise_texts or [])[:5]:
        s = str(t).strip()
        if s:
            lines.append(f"开放伏笔：{s[:80]}")
            raw_bits.append(s)
    if emotion_point and emotion_point.get("label"):
        lines.append(
            f"张力启发：{emotion_point.get('label')}"
            f"（启发式，非文学评分）"
        )
    text = ""
    if lines:
        text = "\n\n【故事线提示｜借鉴勿当设定点名】\n" + "\n".join(f"- {x}" for x in lines) + "\n"
    return {
        "name": "storyline_polish",
        "layer": "supplemental",
        "text": text,
        "raw": "\n".join(raw_bits),
        "enabled": storyline_inject_enabled(),
        "audit": {
            "line_count": len(lines),
            "not_a_kpi": "tokens_saved",
            "redline_safe": True,
            "source": "storyline_inject_polish.v0",
        },
        "control": {"uses_tokens_saved": False},
    }
