"""S-3: DB 级 inflight 幂等锁（替代/增强进程内 set）。

默认 flag SCRIBE3_DB_INFLIGHT_LOCK 关 → MemoryInflightLock（进程内，兼容现状）。
开 → TableInflightLock 走 inflight 表 UNIQUE(work,seq,op)。
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol

_log = logging.getLogger("scribe3.inflight_lock")

_TRUE = {"1", "true", "yes", "on"}


def db_inflight_lock_enabled() -> bool:
    try:
        from scribe3.surreal_flags import db_inflight_lock
        return db_inflight_lock()
    except Exception:
        pass
    return (os.environ.get("SCRIBE3_DB_INFLIGHT_LOCK") or "").strip().lower() in _TRUE


@dataclass
class LockResult:
    ok: bool
    reason: str = ""


class InflightBackend(Protocol):
    def acquire(self, work: str, seq: int, op: str, *, ttl_seconds: int = 300) -> LockResult: ...
    def release(self, work: str, seq: int, op: str) -> bool: ...
    def cleanup_stale(self) -> int: ...


class MemoryInflightLock:
    """进程内锁（单测 / flag 关）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[tuple[str, int, str], float] = {}

    def acquire(self, work: str, seq: int, op: str, *, ttl_seconds: int = 300) -> LockResult:
        key = (work or "main", int(seq), str(op or "loop"))
        now = time.time()
        with self._lock:
            exp = self._rows.get(key)
            if exp is not None and exp > now:
                return LockResult(ok=False, reason="held")
            self._rows[key] = now + max(1, int(ttl_seconds))
            return LockResult(ok=True)

    def release(self, work: str, seq: int, op: str) -> bool:
        key = (work or "main", int(seq), str(op or "loop"))
        with self._lock:
            self._rows.pop(key, None)
            return True

    def cleanup_stale(self) -> int:
        now = time.time()
        with self._lock:
            dead = [k for k, exp in self._rows.items() if exp <= now]
            for k in dead:
                self._rows.pop(k, None)
            return len(dead)


class TableInflightLock:
    """Surreal inflight 表 UNIQUE 锁。store 需提供 _query / _execute_write。"""

    def __init__(self, store: Any) -> None:
        self._st = store

    def acquire(self, work: str, seq: int, op: str, *, ttl_seconds: int = 300) -> LockResult:
        w, s, o = (work or "main"), int(seq), str(op or "loop")
        rid = f"{w}_{s}_{o}".replace(":", "_")
        try:
            self._st.create_inflight_lock(
                rid, work=w, seq=s, op=o, ttl=int(ttl_seconds),
            )
            return LockResult(ok=True)
        except Exception as e:
            msg = str(e).lower()
            if "unique" in msg or "already" in msg or "exists" in msg or "conflict" in msg:
                return LockResult(ok=False, reason="held")
            _log.warning("TableInflightLock.acquire fail-soft→held: %s", e)
            return LockResult(ok=False, reason=str(e)[:120])

    def release(self, work: str, seq: int, op: str) -> bool:
        w, s, o = (work or "main"), int(seq), str(op or "loop")
        rid = f"{w}_{s}_{o}".replace(":", "_")
        try:
            self._st.delete_inflight_lock(rid)
            return True
        except Exception as e:
            _log.warning("TableInflightLock.release: %s", e)
            return False

    def cleanup_stale(self) -> int:
        try:
            rows = self._st.cleanup_stale_inflight_locks() or []
            return len(rows) if isinstance(rows, list) else 0
        except Exception as e:
            _log.debug("cleanup_stale: %s", e)
            return 0


_MEMORY = MemoryInflightLock()


def get_inflight_lock(store: Any | None = None) -> InflightBackend:
    if db_inflight_lock_enabled() and store is not None:
        return TableInflightLock(store)
    return _MEMORY


def acquire_chapter_op(store: Any | None, work: str, seq: int, op: str) -> LockResult:
    return get_inflight_lock(store).acquire(work, seq, op)


def release_chapter_op(store: Any | None, work: str, seq: int, op: str) -> bool:
    return get_inflight_lock(store).release(work, seq, op)
