"""DED-08：章末态抽失败时给下一章一份能接戏的降级状态。"""
from __future__ import annotations

from typing import Any


def degrade_chapter_state(seq: int, prev: dict | None = None, reason: str = "") -> dict[str, Any]:
    base = dict(prev) if isinstance(prev, dict) else {}
    return {
        "ok": True,
        "degraded": True,
        "seq": int(seq or 0),
        "reason": reason or "chapter_state_extract_failed",
        "prev_state": base or None,
        "note": "上一章状态没抽出，这一章按降级状态接戏，不要当空白开场。",
    }
