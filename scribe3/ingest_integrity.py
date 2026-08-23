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
    retry_count: int | None = None,
) -> dict[str, Any]:
    rec = {
        "seq": int(seq),
        "ok": bool(ok),
        "needs_replay": bool(needs_replay),
        "n": int(n or 0),
        "delta": delta,
        "retry_count": int(retry_count or 0),
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
            "delta=$d, retry_count=$rc, updated_at=time::now()",
            {"s": int(seq), "ok": bool(ok), "nr": bool(needs_replay),
             "n": int(n or 0), "d": payload, "rc": int(rec.get("retry_count") or 0)},
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
        "SELECT seq, ok, needs_replay, n, delta, retry_count FROM ingest_checkpoint WHERE seq=$s LIMIT 1",
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


def list_ingest_needing_replay(store: Any) -> list[dict[str, Any]]:
    """扫所有标了要重放的 ingest 检查点。"""
    out: list[dict[str, Any]] = []
    if store is None:
        return out
    bucket = getattr(store, "_ingest_checkpoints", None)
    if isinstance(bucket, dict):
        for seq, rec in bucket.items():
            if not isinstance(rec, dict):
                continue
            row = dict(rec)
            row.setdefault("seq", int(seq))
            if ingest_needs_replay(row):
                out.append(row)
        return out
    query = getattr(store, "_query", None)
    if not callable(query):
        return out
    try:
        rows = query(
            "SELECT seq, ok, needs_replay, n, delta, retry_count FROM ingest_checkpoint "
            "WHERE needs_replay = true OR ok = false",
        ) or []
    except Exception:
        return out
    for r in rows:
        rec = dict(r)
        raw = rec.get("delta")
        if isinstance(raw, str):
            try:
                rec["delta"] = json.loads(raw)
            except Exception:
                pass
        if ingest_needs_replay(rec):
            out.append(rec)
    return out


def heal_pending_ingests(store: Any) -> dict[str, Any]:
    """连库/开机：扫 needs_replay 并用留下的 delta 重放。失败不阻断启动。"""
    healed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for rec in list_ingest_needing_replay(store):
        seq = int(rec.get("seq") or 0)
        if seq <= 0:
            continue
        try:
            n = heal_ingest_if_needed(store, seq)
            healed.append({"seq": seq, "n": n})
        except Exception as e:
            errors.append({
                "seq": seq,
                "error": type(e).__name__,
                "detail": str(e)[:200],
            })
    return {"healed": healed, "errors": errors}


def retry_failed_ingests(store: Any, *, max_retries: int = 3) -> dict[str, Any]:
    """定时：failed/needs_replay 且 retry_count < 3 的检查点自动重放。"""
    attempted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for rec in list_ingest_needing_replay(store):
        seq = int(rec.get("seq") or 0)
        if seq <= 0:
            continue
        ntry = int(rec.get("retry_count") or 0)
        if ntry >= int(max_retries):
            skipped.append({"seq": seq, "retry_count": ntry})
            continue
        ok = True
        err = ""
        applied = 0
        try:
            applied = heal_ingest_if_needed(store, seq, rec.get("delta") if isinstance(rec.get("delta"), dict) else None)
        except Exception as e:
            ok = False
            err = type(e).__name__
        checkpoint_ingest(
            store, seq,
            ok=ok, needs_replay=not ok,
            n=applied, delta=rec.get("delta") if isinstance(rec.get("delta"), dict) else None,
            retry_count=ntry + 1,
        )
        attempted.append({"seq": seq, "ok": ok, "retry_count": ntry + 1, "error": err})
    return {"attempted": attempted, "skipped": skipped}


def maybe_heal_ingest_on_connect(store: Any) -> dict[str, Any] | None:
    """连库后调用：表不存在或查询失败时静默跳过。"""
    if store is None:
        return None
    try:
        return heal_pending_ingests(store)
    except Exception:
        return None
