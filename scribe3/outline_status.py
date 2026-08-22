"""改纲之后：没核对的章标待核对。缺字段 = 旧书，不拦。核对完可冻回去。"""
from __future__ import annotations

from typing import Any

_FROZEN = "frozen"
_STALE = "stale"
_REVIEW = "review"


def is_high_confidence(row: dict[str, Any] | None) -> bool:
    c = str((row or {}).get("confidence") or "").strip().lower()
    return c == "high"


def should_block_stage(stage: str, outline_status: str | None) -> bool:
    """缺字段不拦。只有明确 stale 才拦演绎/草稿。review 要人看，不自动锁死。"""
    stg = str(stage or "").strip().lower()
    status = str(outline_status or "").strip().lower()
    if not status:
        return False
    return stg in ("deduce", "draft") and status == _STALE


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


def _outline_rev(row: dict[str, Any] | None) -> int:
    try:
        return max(0, int((row or {}).get("outline_rev") or 0))
    except (TypeError, ValueError):
        return 0


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
                updater(int(seq), {"outline_status": _STALE})
            except Exception:
                continue
        for seq in split["pending_human"]:
            try:
                updater(int(seq), {"outline_status": _REVIEW})
            except Exception:
                continue
    return split


def refreeze_chapter(store: Any, seq: int) -> dict[str, Any]:
    """stale/review → frozen，outline_rev+1。已冻结再调一次不改版本。"""
    try:
        n = int(seq)
    except (TypeError, ValueError):
        return {"ok": False, "code": "seq_invalid"}
    getter = getattr(store, "get_chapter", None)
    if not callable(getter):
        return {"ok": False, "code": "store_unusable", "seq": n}
    try:
        ch = getter(n) or None
    except Exception:
        ch = None
    if not isinstance(ch, dict):
        return {"ok": False, "code": "chapter_missing", "seq": n}
    status = str(ch.get("outline_status") or "").strip().lower()
    rev = _outline_rev(ch)
    if status == _FROZEN:
        return {
            "ok": True,
            "seq": n,
            "outline_status": _FROZEN,
            "outline_rev": rev,
            "idempotent": True,
        }
    new_rev = rev + 1
    updater = getattr(store, "update_chapter_meta", None)
    if not callable(updater):
        return {"ok": False, "code": "store_unusable", "seq": n}
    try:
        wrote = updater(n, {"outline_status": _FROZEN, "outline_rev": new_rev})
    except Exception:
        wrote = False
    if not wrote:
        return {"ok": False, "code": "update_failed", "seq": n}
    return {
        "ok": True,
        "seq": n,
        "outline_status": _FROZEN,
        "outline_rev": new_rev,
        "idempotent": False,
    }
