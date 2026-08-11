"""进程内并发观测（P2 · 非分布式锁）。

记录 loop/ingest/run 等关键路径的 inflight 集合，供 metrics / 日志；
多 worker 部署时各进程独立，不宣称跨进程互斥。
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

_log = logging.getLogger("scribe3")
_lock = threading.Lock()
_inflight: dict[str, dict[str, float]] = {
    "loop": {},
    "ingest": {},
    "repair": {},
    "run": {},
}


def inflight_enter(kind: str, key: str) -> bool:
    """登记 in-flight；若 key 已存在返回 False（同进程重入告警）。"""
    k = str(kind or "run")
    kid = str(key or "")
    if not kid:
        return True
    with _lock:
        bucket = _inflight.setdefault(k, {})
        if kid in bucket:
            _log.warning("concurrency_obs reenter kind=%s key=%s", k, kid)
            return False
        bucket[kid] = time.time()
        return True


def inflight_leave(kind: str, key: str) -> None:
    k = str(kind or "run")
    kid = str(key or "")
    with _lock:
        bucket = _inflight.get(k) or {}
        bucket.pop(kid, None)


def inflight_snapshot() -> dict[str, Any]:
    with _lock:
        return {
            kind: {"count": len(keys), "keys_sample": list(keys)[:20]}
            for kind, keys in _inflight.items()
        }
