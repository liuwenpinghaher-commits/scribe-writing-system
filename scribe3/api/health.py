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
    store_for = request.app.state.store_for
    try:
        store_for("main")._query("RETURN 1")
        return {"ok": True, "ns": "scribe3", "db": "ok"}
    except Exception as e:
        return {"ok": False, "ns": "scribe3", "db": f"down: {str(e)[:80]}"}


@router.get("/ready")
def ready(request: Request):
    """就绪探针:DB 可达 200,否则 503(部署/看门狗用)。"""
    store_for = request.app.state.store_for
    try:
        store_for("main")._query("RETURN 1")
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db not ready: {str(e)[:80]}")
