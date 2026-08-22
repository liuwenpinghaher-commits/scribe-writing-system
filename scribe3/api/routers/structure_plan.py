"""只读：长篇结构预算建议与设定缺口。不落库。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from scribe3.http_errors import error_body
from scribe3.structure_budget import suggest_budget

router = APIRouter(tags=["structure"])


@router.get("/structure/suggest-budget")
def suggest_structure_budget(
    work: str = "main",
    total_word_goal: int | None = Query(default=None),
    words_per_chapter: int = Query(default=3000),
):
    goal = total_word_goal
    if goal is None:
        try:
            from scribe3.api.app_impl import _store_for
            st = _store_for(work)
            intent = st.get_intent() if hasattr(st, "get_intent") else {}
            raw = (intent or {}).get("total_word_goal")
            if raw is not None:
                goal = int(raw)
        except Exception:
            goal = None
    return suggest_budget(goal, words_per_chapter)


@router.get("/codex/completeness")
def codex_completeness(work: str = "main"):
    """设定缺口只读报告，不挡写。"""
    try:
        from scribe3.api.app_impl import _store_for
        st = _store_for(work)
        if hasattr(st, "setting_completeness"):
            report = st.setting_completeness() or {}
        else:
            report = {}
    except Exception:
        return {
            "advisory": True,
            "blocks_write": False,
            "report": {},
            "note": "缺什么只告诉你，不挡开写。",
            "error": error_body("completeness_read", "设定缺口暂时读不到"),
        }
    return {
        "advisory": True,
        "blocks_write": False,
        "report": report,
        "note": "缺什么只告诉你，不挡开写。",
    }


@router.get("/volumes/{vid}/arc-units")
def list_arc_units(vid: str, work: str = "main"):
    try:
        from scribe3.api.app_impl import _store_for
        st = _store_for(work)
        intent = st.get_intent() if hasattr(st, "get_intent") else {}
        if not (intent or {}).get("structure_mode"):
            return {"units": [], "structure_mode": False}
        fn = getattr(st, "list_arc_units", None)
        units = fn(vid) if callable(fn) else []
        return {"units": units, "structure_mode": True}
    except Exception:
        return {"units": [], "structure_mode": False, "error": error_body("arc_units_read", "情节单元暂时读不到")}
