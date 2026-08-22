"""记忆打分纯函数（O8 · access_count / pin_forever · 无 pydantic）。"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


def memory_access_decay_enabled() -> bool:
    from scribe3.feature_flags import get_flag
    raw = (get_flag("SCRIBE3_MEMORY_ACCESS_DECAY") or "1").strip().lower()
    return raw not in ("0", "false", "off", "no")


def access_boost(access_count: int | None) -> float:
    """访问频率加成，上限 1.5。"""
    if not memory_access_decay_enabled():
        return 1.0
    n = max(0, int(access_count or 0))
    return min(1.5, 1.0 + n * 0.1)


def time_decay(
    *,
    age_days: float,
    half_life: float,
    pinned: bool = False,
    pin_forever: bool = False,
) -> float:
    """时间衰减；pin_forever / pinned → 1.0。"""
    if pin_forever or pinned:
        return 1.0
    hl = max(0.01, float(half_life))
    return 0.5 ** (max(0.0, float(age_days)) / hl)


def score_with_access(
    *,
    rrf_score: float,
    importance: int = 2,
    confidence: float = 1.0,
    age_days: float = 0.0,
    half_life: float = 30.0,
    pinned: bool = False,
    pin_forever: bool = False,
    access_count: int = 0,
    focus_bonus: float = 0.0,
    pin_bonus: float = 0.0,
    source_kind: str = "episodic",
) -> float:
    """与 final_score 同构的可单测打分（canonical 置顶单独处理）。"""
    if source_kind == "canonical":
        return float(rrf_score) + 1.0
    decay = time_decay(
        age_days=age_days,
        half_life=half_life,
        pinned=pinned,
        pin_forever=pin_forever,
    )
    boost = access_boost(access_count)
    importance_f = 0.65 + 0.07 * int(importance)
    confidence_f = 0.75 + 0.25 * float(confidence)
    return (
        float(rrf_score) * importance_f * confidence_f * decay * boost
        + float(focus_bonus)
        + float(pin_bonus)
    )


def age_days_from_observed(observed_at: datetime | None, now: datetime | None = None) -> float:
    if observed_at is None:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    return max(0.0, (now - observed_at).total_seconds() / 86400)


def attrs_from_candidate(cand: Any) -> dict[str, Any]:
    """从鸭子类型候选取 access_count / pin_forever。"""
    return {
        "access_count": int(getattr(cand, "access_count", 0) or 0),
        "pin_forever": bool(getattr(cand, "pin_forever", False)),
        "pinned": bool(getattr(cand, "pinned", False)),
    }
