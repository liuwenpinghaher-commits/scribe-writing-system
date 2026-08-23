"""LLM-P4-2：抽取失败后排队再试（最多 3 次）。"""
from __future__ import annotations

from typing import Any, Callable

_PENDING: list[dict[str, Any]] = []
_MAX = 3
_QUEUE_CAP = 200


def queue_extract_retry(text: str, reason: str = "") -> dict[str, Any]:
    rec = {"text": (text or "")[:2000], "reason": reason or "", "n": 0}
    if len(_PENDING) >= _QUEUE_CAP:
        _PENDING.pop(0)
    _PENDING.append(rec)
    return rec


def pending_extracts() -> list[dict[str, Any]]:
    return list(_PENDING)


def retry_pending_extracts(complete_fn: Callable[[str], str] | None = None) -> dict[str, Any]:
    done: list[dict[str, Any]] = []
    keep: list[dict[str, Any]] = []
    for rec in list(_PENDING):
        n = int(rec.get("n") or 0)
        if n >= _MAX:
            keep.append(rec)
            continue
        rec["n"] = n + 1
        if complete_fn is None:
            keep.append(rec)
            continue
        try:
            from scribe3.canon_extract import extract_claims_from_prose
            extract_claims_from_prose(rec.get("text") or "", complete_fn=complete_fn)
            done.append(rec)
        except Exception:
            keep.append(rec)
    _PENDING[:] = keep
    return {"retried": len(done) + len(keep), "ok": len(done), "left": len(_PENDING)}
