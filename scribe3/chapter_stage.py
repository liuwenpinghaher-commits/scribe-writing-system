"""章节阶段机（O19 · 默认 soft · 不合并五阶段正文字段）。"""
from __future__ import annotations

import os
from typing import Any

PHASES: tuple[str, ...] = ("outline", "beats", "deduce", "draft", "final")
_DESIGN_PHASES: tuple[str, ...] = ("design", "deduce", "draft", "final")

# action -> 期望 next（从任意当前；非法则 advisory）
_ACTIONS: dict[str, str] = {
    "start_outline": "outline",
    "start_design": "design",
    "to_beats": "beats",
    "to_design": "design",
    "to_deduce": "deduce",
    "to_draft": "draft",
    "to_final": "final",
    "advance": "",  # 顺序 +1
}


def _design_on() -> bool:
    return True


def active_phases() -> tuple[str, ...]:
    return _DESIGN_PHASES


def stage_machine_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_STAGE_MACHINE") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def stage_machine_hard() -> bool:
    raw = (os.environ.get("SCRIBE3_STAGE_MACHINE_HARD") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def normalize_phase(phase: str | None) -> str | None:
    p = (phase or "").strip().lower()
    aliases = {
        "plan": "outline",
        "meta": "beats",
        "write": "draft",
        "polish": "final",
        "chapter_design": "design",
    }
    p = aliases.get(p, p)
    if _design_on() and p in ("outline", "plan", "beats"):
        p = "design"
    if p in active_phases() or p in PHASES or p == "design":
        return p
    return None


def next_phase(current: str | None) -> str | None:
    phases = active_phases()
    cur = normalize_phase(current)
    if cur is None:
        return phases[0]
    try:
        i = phases.index(cur)
    except ValueError:
        return phases[0]
    if i + 1 < len(phases):
        return phases[i + 1]
    return cur


def allowed_forward(current: str | None, target: str | None) -> bool:
    """是否允许从 current 到 target（可同阶段；可前进；默认允许回退 soft）。"""
    phases = active_phases()
    c, t = normalize_phase(current), normalize_phase(target)
    if t is None:
        return False
    if c is None:
        return True
    if c not in phases or t not in phases:
        return not stage_machine_hard()
    return phases.index(t) >= phases.index(c) or not stage_machine_hard()


def transition(
    current: str | None,
    action: str,
    *,
    hard: bool | None = None,
) -> dict[str, Any]:
    """阶段转移。默认 soft：非法跳转仍给 next 建议 + advisories，ok=False。

    hard=True 或旗 SCRIBE3_STAGE_MACHINE_HARD：ok=False 且 blocked=True。
    """
    use_hard = stage_machine_hard() if hard is None else bool(hard)
    act = (action or "").strip().lower()
    cur = normalize_phase(current)
    advisories: list[str] = []
    # soft set：显式 phase 写（作者 localStorage 同步）；仍 advisory
    if act == "set":
        # phase 由调用方经 action 附带？用 current 的 next 目标：
        # 约定：transition(current, "set") 无效；需 action=set 且 payload phase 在上层注入
        # 本函数：若 current 已是合法 phase 且 action=set，则 next=current（上层传 target 作 current）
        tgt = cur
        if tgt is None:
            return {
                "ok": False,
                "blocked": use_hard,
                "current": cur,
                "next": cur,
                "action": act,
                "advisories": ["set_missing_phase"],
                "severity": "advisory",
                "hard_park": False,
            }
        advisories.append("soft_set")
        return {
            "ok": True,
            "soft_ok": True,
            "blocked": False,
            "current": cur,
            "next": tgt,
            "action": "set",
            "advisories": advisories,
            "severity": "advisory",
            "hard_park": False,
            "phases": list(active_phases()),
        }
    if act == "advance" or act == "":
        tgt = next_phase(cur)
    elif act in _ACTIONS and _ACTIONS[act]:
        tgt = normalize_phase(_ACTIONS[act]) or _ACTIONS[act]
    elif act in active_phases() or act in PHASES or act == "design":
        tgt = normalize_phase(act) or act
    else:
        return {
            "ok": False,
            "blocked": use_hard,
            "current": cur,
            "next": cur,
            "action": act,
            "advisories": [f"unknown_action:{act}"],
            "severity": "advisory",
            "hard_park": False,
        }
    ok = True
    phases = active_phases()
    if cur in phases and tgt in phases:
        if phases.index(tgt) < phases.index(cur):
            advisories.append("backward_transition")
            if use_hard:
                ok = False
        if phases.index(tgt) > phases.index(cur) + 1:
            advisories.append("skipped_phase")
            if use_hard:
                ok = False
    return {
        "ok": ok if use_hard else True,  # soft：业务上允许作者跳，但标 advisory
        "soft_ok": True,
        "blocked": (not ok) and use_hard,
        "current": cur,
        "next": tgt if not ((not ok) and use_hard) else cur,
        "action": act,
        "advisories": advisories,
        "severity": "hard" if use_hard and not ok else "advisory",
        "hard_park": False,  # 永不默认 hard park 正文
        "phases": list(phases),
    }


def stage_from_chapter_dict(ch: dict[str, Any] | None) -> str | None:
    """从章 dict 推断阶段（不读正文合并字段）。"""
    ch = ch or {}
    st = ch.get("stage_state") or ch.get("stage") or {}
    if isinstance(st, dict) and st.get("phase"):
        return normalize_phase(str(st.get("phase")))
    if isinstance(st, str):
        return normalize_phase(st)
    meta = ch.get("meta") or {}
    if isinstance(meta, dict) and meta.get("phase"):
        return normalize_phase(str(meta.get("phase")))
    # 启发式：有 prose 偏 draft/final
    if (ch.get("prose") or "").strip():
        return "draft"
    plan = ch.get("plan") or {}
    if isinstance(plan, dict) and (plan.get("beats") or plan.get("deductions")):
        if plan.get("beats"):
            return "design" if _design_on() else "beats"
        return "deduce"
    if ch.get("beats") or ch.get("chapter_spine"):
        if _design_on() and (ch.get("beats") or ch.get("chapter_spine")):
            return "design"
        if ch.get("beats"):
            return "beats"
    if (ch.get("synopsis") or ch.get("outline") or "").strip():
        return "design" if _design_on() else "outline"
    return None
