"""Health / readiness probes (Phase 1 first extraction).

URLs unchanged: GET /health, GET /ready.
Behaviour identical to the previous in-app handlers.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request):
    # 审计 #80:真探测——ping 默认书连接(此前纯桩,DB 挂了照样报 ok 假绿)。
    # A6: 追加 changefeed / locks 观测字段（向后兼容 ok/ns/db）。
    store_for = request.app.state.store_for
    out: dict = {"ok": True, "ns": "scribe3", "db": "ok"}
    try:
        store_for("main")._query("RETURN 1")
    except Exception as e:
        out["ok"] = False
        out["db"] = f"down: {str(e)[:80]}"
    # changefeed worker
    try:
        from scribe3.changefeed_consumer import changefeed_cache_enabled
        w = getattr(request.app.state, "changefeed_worker", None)
        if w is not None and hasattr(w, "status"):
            out["changefeed"] = w.status()
        else:
            out["changefeed"] = {
                "enabled": changefeed_cache_enabled(),
                "alive": False,
                "note": "worker_not_started",
            }
    except Exception as e:
        out["changefeed"] = {"enabled": False, "alive": False, "error": str(e)[:80]}
    # lock flags
    try:
        from scribe3.concurrency_lock import distributed_lock_enabled
        from scribe3.surreal_flags import db_inflight_lock
        out["locks"] = {
            "distributed": bool(distributed_lock_enabled()),
            "db_inflight": bool(db_inflight_lock()),
        }
    except Exception:
        out["locks"] = {}
    return out


@router.get("/ready")
def ready(request: Request):
    """就绪探针:DB 可达 200,否则 503(部署/看门狗用)。"""
    store_for = request.app.state.store_for
    try:
        store_for("main")._query("RETURN 1")
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db not ready: {str(e)[:80]}")
