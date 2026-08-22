"""DED-08：章末态抽失败时给下一章一份能接戏的降级状态。"""
from __future__ import annotations

from typing import Any


def degrade_chapter_state(
    seq: int,
    prev: dict | None = None,
    reason: str = "",
    extra: dict | None = None,
) -> dict[str, Any]:
    base = dict(prev) if isinstance(prev, dict) else {}
    extra = dict(extra) if isinstance(extra, dict) else {}
    payload = dict(base)
    payload.update(extra)
    payload.update({
        "ok": True,
        "degraded": True,
        "seq": int(seq or 0),
        "reason": reason or "chapter_state_extract_failed",
        "prev_state": base or None,
        "note": "上一章状态没抽出，这一章按降级状态接戏，不要当空白开场。",
    })
    return payload


def persist_degraded_chapter_state(
    store: Any,
    seq: int,
    prev: dict | None = None,
    reason: str = "",
    extra: dict | None = None,
) -> dict[str, Any]:
    """把降级章末态冻住，下一章 prev_chapter_state 能读到，不要空白开场。"""
    payload = degrade_chapter_state(seq, prev=prev, reason=reason, extra=extra)
    if store is None:
        return payload
    try:
        from scribe3.playbook.envelope import pass_review
        from scribe3.playbook.memory_store import freeze_artifact
        freeze_artifact(
            store, "chapter_state", int(seq), payload,
            schema="chapter_state.v1",
            review=pass_review(),
            rewrite=True,
        )
    except Exception:
        inserter = getattr(store, "insert", None)
        if callable(inserter):
            rec = dict(payload)
            rec["status"] = "needs_human"
            rec["seq"] = int(seq)
            try:
                rec["version"] = store.next_version("chapter_state", int(seq))
            except Exception:
                rec["version"] = 1
            inserter("chapter_state", rec)
    return payload
