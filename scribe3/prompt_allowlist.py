"""Strip engineering-gate leaks from write-path segments (join-before)."""
from __future__ import annotations

import re
from typing import Any

ENGINEERING_LEAK_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"\bGATE-[AB]\b", re.I),
    re.compile(r"gate_[ab]\.ok", re.I),
    re.compile(r"scene_cover"),
    re.compile(r"mvp_pass|journey_pass|PASS_FORMULA"),
    re.compile(r"craft-gates|\bcraft_gates\b"),
    re.compile(r"WORDCOUNT|prose_cn\s*>=?\s*\d+"),
    re.compile(r"D[1-7]\s*[–\-]\s*D[1-7]|anti_stuffing|CONF_LEX"),
    re.compile(r"可开写|机判过关|材料够了"),
    re.compile(r"anti_meta\.\w+|claim_blocking"),
    re.compile(r"每章\s*≥\s*\d+|每\s*\d+\s*字|95%\s*闭嘴"),
)
SKIP_SEGMENT_NAMES = frozenset({"request_constraint"})


def strip_engineering_leaks(text: str) -> str:
    out = text or ""
    for pat in ENGINEERING_LEAK_PATTERNS:
        out = pat.sub("", out)
    return out


def strip_engineering_leaks_segments(segs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for s in segs or []:
        name = str(s.get("name") or "")
        item = dict(s)
        if name not in SKIP_SEGMENT_NAMES:
            item["text"] = strip_engineering_leaks(str(s.get("text") or ""))
        cleaned.append(item)
    return cleaned
