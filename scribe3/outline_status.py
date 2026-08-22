"""改纲之后：没核对的章标待核对。缺字段 = 旧书，不拦。"""
from __future__ import annotations

from typing import Any


def is_high_confidence(row: dict[str, Any] | None) -> bool:
    c = str((row or {}).get("confidence") or "").strip().lower()
    return c == "high"


def should_block_stage(stage: str, outline_status: str | None) -> bool:
    """缺字段不拦。只有明确 stale 才拦演绎/草稿。"""
    stg = str(stage or "").strip().lower()
    status = str(outline_status or "").strip().lower()
    if not status:
        return False
    return stg in ("deduce", "draft") and status == "stale"


def classify_intro_change(chapters: list[dict[str, Any]]) -> dict[str, list[int]]:
    stale: list[int] = []
    pending_human: list[int] = []
    for row in chapters or []:
        try:
            n = int(row.get("seq") or 0)
        except (TypeError, ValueError):
            continue
        if n <= 0:
            continue
        if is_high_confidence(row):
            pending_human.append(n)
        else:
            stale.append(n)
    return {"stale": stale, "pending_human": pending_human}


def mark_volume_intro_changed(store: Any, volume_id: str) -> dict[str, Any]:
    vid = str(volume_id or "").strip()
    if not vid:
        return {"stale": [], "pending_human": []}
    rows: list[dict[str, Any]] = []
    q = getattr(store, "_query", None)
    if not callable(q):
        return {"stale": [], "pending_human": []}
    try:
        rows = q(
            "SELECT seq, confidence, outline_status, outline_rev FROM chapter:.. "
            "WHERE volume = type::record('volume', $vid) "
            "AND (archived = NONE OR archived != true)",
            {"vid": vid},
        ) or []
    except Exception:
        return {"skipped": True, "stale": [], "pending_human": []}
    split = classify_intro_change([r for r in rows if isinstance(r, dict)])
    updater = getattr(store, "update_chapter_meta", None)
    if callable(updater):
        for seq in split["stale"]:
            try:
                updater(int(seq), {"outline_status": "stale"})
            except Exception:
                continue
    return split
