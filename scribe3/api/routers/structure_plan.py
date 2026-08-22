"""只读：长篇结构预算建议。不落库。"""
from __future__ import annotations

from fastapi import APIRouter, Query

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
