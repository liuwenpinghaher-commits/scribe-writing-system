"""共享 ingest 租约（设计 C-P4 · PR-1）。

纯逻辑 + 可选 store 适配。单元测试用 MemoryLeaseBackend，无需 Surreal。
生产：ChapterLeaseBackend 写 chapter 行字段（DEFINE IF NOT EXISTS fail-soft）。
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass
class AcquireResult:
    ok: bool
    owner: str = ""
    reason: str = ""
    until: float = 0.0


class LeaseBackend(Protocol):
    def get(self, work: str, seq: int) -> tuple[str, float] | None:
        """返回 (owner, until_unix) 或 None。"""
        ...

    def set(self, work: str, seq: int, owner: str, until: float) -> None:
        ...

    def clear(self, work: str, seq: int, owner: str) -> bool:
        """仅 owner 匹配时清除；返回是否清除。"""
        ...


class MemoryLeaseBackend:
    """进程内 + 可共享的 dict（单测 / 同进程）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[tuple[str, int], tuple[str, float]] = {}

    def get(self, work: str, seq: int) -> tuple[str, float] | None:
        with self._lock:
            return self._get_unlocked(work, seq)

    def _get_unlocked(self, work: str, seq: int, now: float | None = None) -> tuple[str, float] | None:
        t = time.time() if now is None else now
        row = self._rows.get((work, int(seq)))
        if not row:
            return None
        owner, until = row
        if until <= t:
            self._rows.pop((work, int(seq)), None)
            return None
        return owner, until

    def set(self, work: str, seq: int, owner: str, until: float) -> None:
        with self._lock:
            self._rows[(work, int(seq))] = (owner, until)

    def clear(self, work: str, seq: int, owner: str) -> bool:
        with self._lock:
            row = self._rows.get((work, int(seq)))
            if not row:
                return True
            if row[0] != owner:
                return False
            self._rows.pop((work, int(seq)), None)
            return True

    def atomic_try_acquire(
        self, work: str, seq: int, owner: str, until: float, *, now: float,
    ) -> AcquireResult:
        """同锁内 get+set，防并发双赢。"""
        with self._lock:
            cur = self._get_unlocked(work, seq, now=now)
            if cur is None:
                self._rows[(work, int(seq))] = (owner, until)
                return AcquireResult(ok=True, owner=owner, until=until)
            cur_owner, cur_until = cur
            if cur_owner == owner:
                self._rows[(work, int(seq))] = (owner, until)
                return AcquireResult(ok=True, owner=owner, until=until, reason="renewed")
            return AcquireResult(
                ok=False, owner=cur_owner, until=cur_until, reason="held_by_other",
            )


# 进程内全局后端（HTTP 后台任务共用）；MCP 进程另有自己的实例+DB 字段
_GLOBAL_MEM = MemoryLeaseBackend()


def global_memory_backend() -> MemoryLeaseBackend:
    return _GLOBAL_MEM


def new_owner() -> str:
    return uuid.uuid4().hex[:16]


def try_acquire_ingest_lease(
    backend: LeaseBackend,
    work: str,
    seq: int,
    owner: str,
    ttl: float = 600.0,
    *,
    now: float | None = None,
) -> AcquireResult:
    """原子语义：无有效租约则占用；同 owner 可续期；他主有效则失败。"""
    t = time.time() if now is None else now
    until = t + float(ttl)
    atomic = getattr(backend, "atomic_try_acquire", None)
    if callable(atomic):
        return atomic(work, int(seq), owner, until, now=t)
    cur = backend.get(work, int(seq))
    if cur is None:
        backend.set(work, int(seq), owner, until)
        return AcquireResult(ok=True, owner=owner, until=until)
    cur_owner, cur_until = cur
    if cur_until <= t:
        backend.set(work, int(seq), owner, until)
        return AcquireResult(ok=True, owner=owner, until=until)
    if cur_owner == owner:
        backend.set(work, int(seq), owner, until)
        return AcquireResult(ok=True, owner=owner, until=until, reason="renewed")
    return AcquireResult(
        ok=False, owner=cur_owner, until=cur_until, reason="held_by_other",
    )


def release_ingest_lease(
    backend: LeaseBackend, work: str, seq: int, owner: str,
) -> bool:
    return backend.clear(work, int(seq), owner)


class ChapterLeaseBackend:
    """把租约落在 chapter 行（跨进程，经 Surreal）。"""

    def __init__(self, store) -> None:
        self.st = store
        self._ensured = False

    def _ensure(self) -> None:
        if self._ensured:
            return
        try:
            self.st._raw_query(
                "DEFINE FIELD IF NOT EXISTS ingest_lease_owner ON chapter TYPE option<string>;"
            )
            self.st._raw_query(
                "DEFINE FIELD IF NOT EXISTS ingest_lease_until ON chapter TYPE option<float>;"
            )
        except Exception:
            pass
        self._ensured = True

    def get(self, work: str, seq: int) -> tuple[str, float] | None:
        self._ensure()
        try:
            rows = self.st._query(
                "SELECT ingest_lease_owner AS o, ingest_lease_until AS u "
                "FROM type::record('chapter',$seq)",
                {"seq": int(seq)},
            ) or []
            if not rows:
                return None
            o = rows[0].get("o") or ""
            u = float(rows[0].get("u") or 0)
            if not o or u <= time.time():
                return None
            return str(o), u
        except Exception:
            return None

    def set(self, work: str, seq: int, owner: str, until: float) -> None:
        self._ensure()
        try:
            self.st._execute_write(
                "UPDATE type::record('chapter',$seq) SET "
                "ingest_lease_owner=$o, ingest_lease_until=$u",
                {"seq": int(seq), "o": owner, "u": float(until)},
            )
        except Exception:
            pass

    def clear(self, work: str, seq: int, owner: str) -> bool:
        self._ensure()
        cur = self.get(work, seq)
        if cur is None:
            return True
        if cur[0] != owner:
            return False
        try:
            self.st._execute_write(
                "UPDATE type::record('chapter',$seq) SET "
                "ingest_lease_owner=NONE, ingest_lease_until=NONE",
                {"seq": int(seq)},
            )
            return True
        except Exception:
            return False


def combined_backend(store=None) -> LeaseBackend:
    """优先 chapter 字段；失败时回落全局内存（同进程仍有效）。"""
    if store is None:
        return _GLOBAL_MEM
    ch = ChapterLeaseBackend(store)

    class _Combo:
        def get(self, work, seq):
            r = ch.get(work, seq)
            if r:
                return r
            return _GLOBAL_MEM.get(work, seq)

        def set(self, work, seq, owner, until):
            ch.set(work, seq, owner, until)
            _GLOBAL_MEM.set(work, seq, owner, until)

        def clear(self, work, seq, owner):
            a = ch.clear(work, seq, owner)
            b = _GLOBAL_MEM.clear(work, seq, owner)
            return a or b

    return _Combo()
