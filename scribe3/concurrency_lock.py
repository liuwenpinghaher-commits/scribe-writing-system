"""并发锁（O28 · 旗控；默认进程内，可注入 store）。"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import os
import threading
import time
from typing import Any, Protocol


def distributed_lock_enabled() -> bool:
    raw = (get_flag("SCRIBE3_DISTRIBUTED_LOCK") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


class LockStore(Protocol):
    def try_create_inflight(self, kind: str, target: str, worker: str, ttl_sec: int) -> bool: ...
    def delete_inflight(self, kind: str, target: str) -> None: ...


_lock = threading.Lock()
# kind -> target -> {worker, expires}
_MEM: dict[str, dict[str, dict[str, Any]]] = {}


def acquire_lock(
    kind: str,
    target: str,
    *,
    ttl_seconds: int = 60,
    worker: str | None = None,
    store: LockStore | None = None,
) -> bool:
    """获取锁。distributed 旗开且提供 store 时走 store；否则进程内。"""
    k = str(kind or "run")
    t = str(target or "")
    if not t:
        return True
    w = worker or f"pid:{os.getpid()}"
    ttl = max(1, int(ttl_seconds))
    if distributed_lock_enabled() and store is not None:
        try:
            return bool(store.try_create_inflight(k, t, w, ttl))
        except Exception:
            # store 失败降级进程内
            pass
    now = time.time()
    with _lock:
        bucket = _MEM.setdefault(k, {})
        row = bucket.get(t)
        if row and float(row.get("expires") or 0) > now:
            return False
        bucket[t] = {"worker": w, "expires": now + ttl}
        return True


def release_lock(
    kind: str,
    target: str,
    *,
    store: LockStore | None = None,
) -> None:
    k = str(kind or "run")
    t = str(target or "")
    if distributed_lock_enabled() and store is not None:
        try:
            store.delete_inflight(k, t)
        except Exception:
            pass
    with _lock:
        bucket = _MEM.get(k) or {}
        bucket.pop(t, None)


def lock_snapshot() -> dict[str, Any]:
    now = time.time()
    with _lock:
        return {
            kind: {
                tgt: row
                for tgt, row in bucket.items()
                if float(row.get("expires") or 0) > now
            }
            for kind, bucket in _MEM.items()
        }


class InMemoryLockStore:
    """测试用 store：模拟 UNIQUE 冲突。"""

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str], dict[str, Any]] = {}
        self._lk = threading.Lock()

    def try_create_inflight(self, kind: str, target: str, worker: str, ttl_sec: int) -> bool:
        now = time.time()
        key = (kind, target)
        with self._lk:
            row = self._rows.get(key)
            if row and float(row["expires"]) > now:
                return False
            self._rows[key] = {"worker": worker, "expires": now + ttl_sec}
            return True

    def delete_inflight(self, kind: str, target: str) -> None:
        with self._lk:
            self._rows.pop((kind, target), None)
