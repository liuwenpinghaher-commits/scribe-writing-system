"""DED-03：ingest 中途失败可被完整性检查发现并标成需要重放。"""
from __future__ import annotations

from typing import Any, Callable


def run_ingest_apply(apply_fn: Callable[[], int], seq: int) -> dict[str, Any]:
    try:
        n = apply_fn()
        return {"ok": True, "seq": int(seq), "n": int(n or 0), "needs_replay": False}
    except Exception as e:
        return {
            "ok": False,
            "seq": int(seq),
            "n": 0,
            "needs_replay": True,
            "error": type(e).__name__,
            "detail": str(e)[:200],
        }


def ingest_needs_replay(checkpoint: dict | None) -> bool:
    if not checkpoint:
        return True
    if checkpoint.get("ok") is False:
        return True
    if checkpoint.get("needs_replay"):
        return True
    return False
