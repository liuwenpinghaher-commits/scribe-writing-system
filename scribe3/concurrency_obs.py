"""并发观测 + 可选 store 锁（O28）。

默认进程内 inflight 集合，供 metrics / 日志。
``SCRIBE3_DISTRIBUTED_LOCK=1`` 时经 ``concurrency_lock.acquire_lock``（可注入 store）。
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


def inflight_enter(kind: str, key: str, *, store: Any = None) -> bool:
    """登记 in-flight；若 key 已占用返回 False。

    旗开时先走 concurrency_lock；否则仅进程内 set（与历史行为一致）。
    """
    k = str(kind or "run")
    kid = str(key or "")
    if not kid:
        return True
    try:
        from scribe3.concurrency_lock import acquire_lock, distributed_lock_enabled
        if distributed_lock_enabled():
            ok = acquire_lock(k, kid, store=store)
            if not ok:
                _log.warning("concurrency_lock busy kind=%s key=%s", k, kid)
                return False
    except Exception:
        pass
    with _lock:
        bucket = _inflight.setdefault(k, {})
        if kid in bucket:
            _log.warning("concurrency_obs reenter kind=%s key=%s", k, kid)
            return False
        bucket[kid] = time.time()
        return True


def inflight_leave(kind: str, key: str, *, store: Any = None) -> None:
    k = str(kind or "run")
    kid = str(key or "")
    try:
        from scribe3.concurrency_lock import release_lock, distributed_lock_enabled
        if distributed_lock_enabled():
            release_lock(k, kid, store=store)
    except Exception:
        pass
    with _lock:
        bucket = _inflight.get(k) or {}
        bucket.pop(kid, None)


def inflight_snapshot() -> dict[str, Any]:
    with _lock:
        return {
            kind: {"count": len(keys), "keys_sample": list(keys)[:20]}
            for kind, keys in _inflight.items()
        }
