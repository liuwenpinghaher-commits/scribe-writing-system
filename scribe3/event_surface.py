"""事件表面投影：时间线 label 等人话化（不改 event schema / 写路径）。

见 docs/plans/2026-08-09-proposition-author-ux-v2-optimization.md · PR-UX0 / KD-15。
"""
from __future__ import annotations

from typing import Any


def _clip(text: str, n: int = 36) -> str:
    s = (text or "").strip()
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)] + "…"


def _first_subj_local(ev: Any) -> str | None:
    """从 participants 取 SUBJ oid 的本地段，不查 character 表（禁止 N+1）。

    例 role:焦三 → 焦三；与前端 stripRole 一致。无 SUBJ 则 None。
    """
    parts = getattr(ev, "participants", None)
    if parts is None and isinstance(ev, dict):
        parts = ev.get("participants")
    parts = parts or {}
    raw = parts.get("SUBJ") if isinstance(parts, dict) else None
    if raw is None:
        return None
    oid = raw[0] if isinstance(raw, (list, tuple)) else raw
    s = str(oid or "").strip()
    if not s:
        return None
    return s.split(":", 1)[-1] or None


def format_event_timeline_label(ev: Any) -> tuple[str, str]:
    """返回 (label, label_source)；label_source ∈ goal|composed|type。

    优先级（KD-15）：motivated_by_goal 截断 > SUBJ 本地 id · type > type。
    """
    goal = getattr(ev, "motivated_by_goal", None)
    if goal is None and isinstance(ev, dict):
        goal = ev.get("motivated_by_goal") or ev.get("goal")
    goal_s = (str(goal).strip() if goal is not None else "")
    if goal_s:
        return _clip(goal_s, 36), "goal"

    et = getattr(ev, "type", None)
    if et is None and isinstance(ev, dict):
        et = ev.get("type") or ev.get("event_type")
    et_s = (str(et).strip() if et is not None else "") or "事件"

    subj = _first_subj_local(ev)
    if subj:
        return f"{subj} · {et_s}", "composed"
    return et_s, "type"
