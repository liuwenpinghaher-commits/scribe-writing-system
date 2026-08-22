"""parked · R8 W9: unattended auto-draft may require contract + ≥1 trace — no char floors.

半成品：仅测试引用，未接入作者主路径。接线计划见 docs/plans/parked-modules.md。
"""
from __future__ import annotations

from scribe3.narrative_contract import validate_narrative_contract
from scribe3.story_constraint_prompt import load_evidence_must_show


def unattended_scene_ok(chapter: dict | None) -> dict:
    ch = chapter if isinstance(chapter, dict) else {}
    c = validate_narrative_contract(ch.get("narrative_contract"))
    traces = load_evidence_must_show(ch)
    missing = []
    if not c.get("validation", {}).get("ok"):
        missing.append("narrative_contract")
    if not traces:
        missing.append("evidence_must_show")
    return {
        "ok": not missing,
        "missing": missing,
        "char_floor": None,
    }


UNATTENDED_PARK_REASON = "无人值守起草需要场面合同与至少一条痕迹"


def unattended_park_artifact(uo: dict | None) -> dict:
    """pilot_park 必须是人话字符串（pilot 用 str(artifact['pilot_park']) 当 reason）。"""
    u = uo if isinstance(uo, dict) else {}
    return {
        "pilot_park": UNATTENDED_PARK_REASON,
        "missing": list(u.get("missing") or []),
        "detail": UNATTENDED_PARK_REASON,
    }
