"""Intent / north-star chapter endpoints (Phase 1 extraction).

URLs unchanged:
  GET  /intent
  PUT  /intent
  PUT  /intent-goals
  GET  /north-star/chapter/{seq}

Behaviour identical to the previous in-app handlers.
north_star_book remains in app_impl until a later slice.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["intent"])

# Engineering quota keys only (must stay aligned with app_impl._INTENT_ENGINEERING_KEYS).
# Narrative north-star fields still go through PUT /intent (world-write gate).
_INTENT_ENGINEERING_KEYS = frozenset({
    "total_word_goal", "daily_word_goal", "overdue_threshold",
    "arc_tracking",  # 作品级弧光追踪 on|off（工艺旋钮，非叙事正文）
})


def _store_for(request: Request):
    return request.app.state.store_for


class IntentIn(BaseModel):
    reader_feeling: str = ""
    emotional_arc: str = ""
    red_lines: str = ""
    imagery: str = ""
    north_star: str = ""
    overdue_threshold: int | None = None
    total_word_goal: int | None = None
    daily_word_goal: int | None = None
    arc_tracking: str | None = None  # on|off


class IntentGoalsIn(BaseModel):
    """Engineering quota-only: word goals / overdue / arc_tracking. No narrative fields."""
    total_word_goal: int | None = None
    daily_word_goal: int | None = None
    overdue_threshold: int | None = None
    arc_tracking: str | None = None


@router.get("/intent")
def get_intent(request: Request, work: str = "main"):
    return _store_for(request)(work).get_intent()


@router.put("/intent")
def put_intent(i: IntentIn, request: Request, work: str = "main"):
    # exclude_unset: only persist fields the client actually sent.
    # Narrative fields are under the emergency world-write gate on /intent.
    # Engineering quotas should use PUT /intent-goals (gate-exempt).
    _store_for(request)(work).set_intent(i.model_dump(exclude_unset=True))
    return {"ok": True}


@router.put("/intent-goals")
def put_intent_goals(i: IntentGoalsIn, request: Request, work: str = "main"):
    """Engineering quota write (not under emergency world-write gate)."""
    data = i.model_dump(exclude_unset=True)
    data = {k: v for k, v in data.items() if k in _INTENT_ENGINEERING_KEYS}
    if not data:
        raise HTTPException(status_code=422, detail="no engineering goal fields to update")
    _store_for(request)(work).set_intent(data)
    return {"ok": True, "updated": list(data.keys())}


@router.get("/north-star/chapter/{seq}")
def north_star_chapter(seq: int, request: Request, work: str = "main"):
    """Chapter-level north-star scorecard (constraints / advisory / fulfillment)."""
    sc = _store_for(request)(work).get_chapter_scorecard(seq)
    if sc is None:
        raise HTTPException(status_code=404, detail=f"chapter {seq} 不存在或无正文")
    return sc
