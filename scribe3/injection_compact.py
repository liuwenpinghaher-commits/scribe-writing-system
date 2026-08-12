"""重叠注入段折叠纯函数（rev.1.2 WS-1 C · 可单测、可 flag 关）。"""
from __future__ import annotations

import os
import re
from typing import Any


def _flag(name: str, default: str = "1") -> bool:
    v = (os.environ.get(name) if name in os.environ else default)
    v = (v or default).strip().lower()
    return v not in ("0", "false", "no", "off", "")


def volume_intro_compact_enabled() -> bool:
    try:
        from scribe3.quality_enablement_flags import volume_intro_compact_enabled as _f
        return bool(_f())
    except Exception:
        return _flag("SCRIBE3_VOLUME_INTRO_COMPACT", "1")


def phase_role_dedup_enabled() -> bool:
    try:
        from scribe3.quality_enablement_flags import phase_role_dedup_enabled as _f
        return bool(_f())
    except Exception:
        return _flag("SCRIBE3_PHASE_ROLE_DEDUP", "1")


def avoid_merge_antislop_enabled() -> bool:
    try:
        from scribe3.quality_enablement_flags import avoid_merge_antislop_enabled as _f
        return bool(_f())
    except Exception:
        return _flag("SCRIBE3_AVOID_MERGE_ANTISLOP", "1")


def pressure_diff_only_enabled() -> bool:
    try:
        from scribe3.quality_enablement_flags import pressure_diff_only_enabled as _f
        return bool(_f())
    except Exception:
        return _flag("SCRIBE3_PRESSURE_DIFF_ONLY", "1")


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def compact_volume_intro(
    volume_intro: str,
    *,
    synopsis: str = "",
    outline_text: str = "",
    volume_title: str = "",
    volume_goal: str = "",
) -> str:
    """已含 title/goal → ≤120 字钩子；否则保留但硬顶 400。关旗 → 原文硬顶 400。"""
    raw = (volume_intro or "").strip()
    if not volume_intro_compact_enabled():
        return raw[:400]
    title = (volume_title or "").strip()
    goal = (volume_goal or "").strip()
    syn_n = _norm(synopsis)
    ol_n = _norm(outline_text)
    title_n = _norm(title)
    already = False
    if title_n and (title_n in syn_n or title_n in ol_n):
        already = True
    if goal:
        g12 = _norm(goal[:12])
        if g12 and (g12 in syn_n or g12 in ol_n):
            already = True
    if already:
        hook = f"卷钩：{title or '本卷'} · {(goal or '')[:40]}".strip()
        return hook[:120]
    return raw[:400]


def _bigrams(s: str) -> set[str]:
    t = _norm(s)
    if len(t) < 2:
        return {t} if t else set()
    return {t[i : i + 2] for i in range(len(t) - 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter / union


def _containment(a: set[str], b: set[str]) -> float:
    """|a∩b|/|a|：短句是否已被 ref 覆盖（比 Jaccard 更稳）。"""
    if not a:
        return 1.0
    if not b:
        return 0.0
    return len(a & b) / len(a)


def dedup_phase_role(
    phase_role_text: str,
    *,
    craft_text: str = "",
    anti_slop_text: str = "",
) -> str:
    """句级与 craft/anti_slop 重叠则丢：Jaccard≥0.5 或 句 bigram 包含度≥0.5。"""
    raw = (phase_role_text or "").strip()
    if not phase_role_dedup_enabled():
        return raw
    if not raw:
        return ""
    ref = craft_text + "\n" + anti_slop_text
    ref_bg = _bigrams(ref)
    sentences = re.split(r"[。！？\n]+", raw)
    kept: list[str] = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        sb = _bigrams(s)
        if _jaccard(sb, ref_bg) >= 0.5 or _containment(sb, ref_bg) >= 0.5:
            continue
        kept.append(s)
    if not kept:
        return ""
    # 最多 1 句
    out = kept[0]
    if not out.endswith(("。", "！", "？")):
        out += "。"
    return out


PRESSURE_DIFF_KEYS: frozenset[str] = frozenset({
    "fork", "irreversible", "progress", "role", "chapter_pressure",
    "time_budget", "ritual_quota", "witness_policy", "stroke_plan",
    "motif_intensity_caps",
})

# drama 结构化键 → pressure 同义
_DRAMA_TO_PRESSURE: dict[str, str] = {
    "conflict": "fork",
    "fork": "fork",
    "irreversible": "irreversible",
    "progress": "progress",
    "role": "role",
    "chapter_pressure": "chapter_pressure",
    "time_budget": "time_budget",
    "ritual_quota": "ritual_quota",
    "witness_policy": "witness_policy",
    "stroke_plan": "stroke_plan",
    "motif_intensity_caps": "motif_intensity_caps",
}


def _nonempty(v: Any) -> bool:
    if v is None:
        return False
    if v == "" or v == {} or v == []:
        return False
    return True


def pressure_diff_keys(
    pressure_contract: dict | None,
    drama_contract: dict | None,
) -> frozenset[str] | None:
    """返回应 emit 的 pressure 键；None = 不做差集（整块保留）。

    drama 非 dict → None（整块保留）。
    """
    if not pressure_diff_only_enabled():
        return None
    if not isinstance(pressure_contract, dict):
        return None
    if not isinstance(drama_contract, dict):
        return None  # 仅渲染串 → 整块保留
    needed = {
        k for k in PRESSURE_DIFF_KEYS
        if _nonempty(pressure_contract.get(k))
    }
    in_drama: set[str] = set()
    for dk, pk in _DRAMA_TO_PRESSURE.items():
        if _nonempty(drama_contract.get(dk)):
            in_drama.add(pk)
    return frozenset(needed - in_drama)


def should_omit_avoid_domain() -> bool:
    """开旗时独立 avoid 域不推入 segments。"""
    return avoid_merge_antislop_enabled()
