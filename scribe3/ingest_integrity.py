"""DED-03：ingest 中途失败可被完整性检查发现并标成需要重放。"""
from __future__ import annotations

import json
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


def checkpoint_ingest(
    store: Any,
    seq: int,
    *,
    ok: bool,
    needs_replay: bool,
    n: int = 0,
    delta: dict | None = None,
) -> dict[str, Any]:
    rec = {
        "seq": int(seq),
        "ok": bool(ok),
        "needs_replay": bool(needs_replay),
        "n": int(n or 0),
        "delta": delta,
    }
    if store is None:
        return rec
    bucket = getattr(store, "_ingest_checkpoints", None)
    if not isinstance(bucket, dict):
        try:
            store._ingest_checkpoints = {}
            bucket = store._ingest_checkpoints
        except Exception:
            bucket = None
    if isinstance(bucket, dict):
        bucket[int(seq)] = rec
    writer = getattr(store, "_execute_write", None)
    if callable(writer):
        payload = None
        if delta is not None:
            try:
                payload = json.dumps(delta, ensure_ascii=False)
            except Exception:
                payload = None
        writer(
            "UPSERT ingest_checkpoint SET seq=$s, ok=$ok, needs_replay=$nr, n=$n, "
            "delta=$d, updated_at=time::now()",
            {"s": int(seq), "ok": bool(ok), "nr": bool(needs_replay), "n": int(n or 0), "d": payload},
        )
    return rec


def load_ingest_checkpoint(store: Any, seq: int) -> dict[str, Any] | None:
    if store is None:
        return None
    bucket = getattr(store, "_ingest_checkpoints", None)
    if isinstance(bucket, dict) and int(seq) in bucket:
        return dict(bucket[int(seq)])
    query = getattr(store, "_query", None)
    if not callable(query):
        return None
    rows = query(
        "SELECT seq, ok, needs_replay, n, delta FROM ingest_checkpoint WHERE seq=$s LIMIT 1",
        {"s": int(seq)},
    ) or []
    if not rows:
        return None
    rec = dict(rows[0])
    raw = rec.get("delta")
    if isinstance(raw, str):
        try:
            rec["delta"] = json.loads(raw)
        except Exception:
            pass
    return rec


def heal_ingest_if_needed(store: Any, seq: int, delta: dict | None = None) -> int:
    """checkpoint 标了需要重放时，用留下的 delta 再跑一遍 apply。"""
    cp = load_ingest_checkpoint(store, seq)
    if not ingest_needs_replay(cp):
        return 0
    body = delta
    if body is None and isinstance(cp, dict):
        body = cp.get("delta")
    if not isinstance(body, dict):
        return 0
    from scribe3.ingest import apply_delta
    return int(apply_delta(store, body, seq) or 0)
