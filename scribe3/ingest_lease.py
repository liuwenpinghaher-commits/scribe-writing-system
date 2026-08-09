"""共享 ingest 租约（设计 C-P4 · PR-1 · CAS 修订）。

纯逻辑 + 可选 store 适配。单元测试用 MemoryLeaseBackend，无需 Surreal。
生产：TableLeaseBackend 经独立 ingest_lease 表 CREATE ONLY / UPDATE WHERE 做 CAS；
ChapterLeaseBackend 同步 CAS 写 chapter 冗余字段；purge 前 assert_lease_owner。
"""
from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

_log = logging.getLogger("scribe3.ingest_lease")


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


def lease_record_id(work: str, seq: int) -> str:
    """确定性 record key：work_seq（仅 [A-Za-z0-9_]）。"""
    w = re.sub(r"[^A-Za-z0-9_]", "_", (work or "main").strip() or "main")
    return f"{w}_{int(seq)}"


class MemoryLeaseBackend:
    """进程内 + 可共享的 dict（单测 / 同进程）。CAS 经 atomic_try_acquire。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[tuple[str, int], tuple[str, float]] = {}

    def get(self, work: str, seq: int) -> tuple[str, float] | None:
        with self._lock:
            return self._get_unlocked(work, seq)

    def _get_unlocked(
        self, work: str, seq: int, now: float | None = None,
    ) -> tuple[str, float] | None:
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
                return AcquireResult(
                    ok=True, owner=owner, until=until, reason="renewed",
                )
            return AcquireResult(
                ok=False, owner=cur_owner, until=cur_until, reason="held_by_other",
            )

    def assert_owner(self, work: str, seq: int, owner: str, *, now: float | None = None) -> bool:
        with self._lock:
            cur = self._get_unlocked(work, seq, now=now)
            return bool(cur and cur[0] == owner)


# 进程内全局后端（HTTP 后台任务共用）；MCP 进程另有自己的实例+DB 表
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
    """原子语义：无有效租约则占用；同 owner 可续期；他主有效则失败。

    生产后端必须实现 atomic_try_acquire（CAS）；无此方法时走 get+set（仅单测 stub）。
    """
    t = time.time() if now is None else now
    until = t + float(ttl)
    atomic = getattr(backend, "atomic_try_acquire", None)
    if callable(atomic):
        return atomic(work, int(seq), owner, until, now=t)
    # 非生产路径：无 CAS 能力时仍尝试 get/set（测试 stub）
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


def assert_lease_owner(
    backend: LeaseBackend,
    work: str,
    seq: int,
    owner: str,
    *,
    now: float | None = None,
) -> bool:
    """purge 前二次校验：当前有效租约 owner 必须匹配。"""
    if not owner:
        return False
    fn = getattr(backend, "assert_owner", None)
    if callable(fn):
        return bool(fn(work, int(seq), owner, now=now))
    cur = backend.get(work, int(seq))
    if not cur:
        return False
    return cur[0] == owner


class TableLeaseBackend:
    """独立 ingest_lease 表 · CREATE ONLY + UPDATE WHERE CAS（跨进程）。"""

    def __init__(self, store) -> None:
        self.st = store
        self._ensured = False

    def _ensure(self) -> None:
        if self._ensured:
            return
        try:
            self.st._raw_query(
                "DEFINE TABLE IF NOT EXISTS ingest_lease SCHEMALESS;"
            )
            for field, typ in (
                ("work", "option<string>"),
                ("seq", "option<int>"),
                ("owner", "option<string>"),
                ("until", "option<float>"),
                ("state", "option<string>"),
                ("heartbeat_at", "option<float>"),
            ):
                try:
                    self.st._raw_query(
                        f"DEFINE FIELD IF NOT EXISTS {field} ON ingest_lease TYPE {typ};"
                    )
                except Exception:
                    pass
        except Exception as e:
            _log.warning("ingest_lease table ensure failed: %s", e)
        self._ensured = True

    def _rid(self, work: str, seq: int) -> str:
        return lease_record_id(work, seq)

    def get(self, work: str, seq: int) -> tuple[str, float] | None:
        self._ensure()
        try:
            rows = self.st._query(
                "SELECT owner AS o, until AS u FROM type::record('ingest_lease', $id)",
                {"id": self._rid(work, seq)},
            ) or []
            if not rows:
                return None
            o = (rows[0].get("o") or "").strip()
            u = float(rows[0].get("u") or 0)
            if not o or u <= time.time():
                return None
            return str(o), u
        except Exception:
            return None

    def set(self, work: str, seq: int, owner: str, until: float) -> None:
        """非 CAS 写入（仅内部/续期兜底）；生产 acquire 走 atomic_try_acquire。"""
        self._ensure()
        rid = self._rid(work, seq)
        try:
            self.st._execute_write(
                "UPSERT type::record('ingest_lease', $id) SET "
                "work=$w, seq=$s, owner=$o, until=$u, state='leased', heartbeat_at=$u",
                {
                    "id": rid, "w": work, "s": int(seq),
                    "o": owner, "u": float(until),
                },
            )
        except Exception as e:
            _log.warning("ingest_lease set failed: %s", e)

    def clear(self, work: str, seq: int, owner: str) -> bool:
        self._ensure()
        rid = self._rid(work, seq)
        try:
            # 仅 owner 匹配才清
            self.st._execute_write(
                "UPDATE type::record('ingest_lease', $id) SET "
                "owner=NONE, until=0, state='idle' "
                "WHERE owner = $o",
                {"id": rid, "o": owner},
            )
            cur = self.get(work, seq)
            return cur is None or cur[0] != owner
        except Exception:
            return False

    def atomic_try_acquire(
        self, work: str, seq: int, owner: str, until: float, *, now: float,
    ) -> AcquireResult:
        """CAS：CREATE ONLY 抢占；已存在则 UPDATE WHERE 过期或同 owner。"""
        self._ensure()
        rid = self._rid(work, seq)
        binds = {
            "id": rid, "w": work, "s": int(seq),
            "o": owner, "u": float(until), "now": float(now),
        }
        # 1) 尝试 CREATE ONLY（首占）
        try:
            self.st._execute_write(
                "CREATE ONLY type::record('ingest_lease', $id) SET "
                "work=$w, seq=$s, owner=$o, until=$u, state='leased', heartbeat_at=$u",
                binds,
            )
            # 创建 成功 → 确认我们是 owner
            if self.assert_owner(work, seq, owner, now=now):
                return AcquireResult(ok=True, owner=owner, until=until)
        except Exception:
            # 已存在或其它错误 → 走条件 UPDATE
            pass

        # 2) UPDATE WHERE 过期 / 空 owner / 同 owner
        try:
            self.st._execute_write(
                "UPDATE type::record('ingest_lease', $id) SET "
                "owner=$o, until=$u, state='leased', heartbeat_at=$u, work=$w, seq=$s "
                "WHERE owner = NONE OR owner = NONE OR until = NONE "
                "OR until < $now OR until <= $now OR owner = $o OR owner = ''",
                binds,
            )
        except Exception as e:
            _log.warning("ingest_lease CAS update failed: %s", e)

        if self.assert_owner(work, seq, owner, now=now):
            # 区分 renew vs 抢过期
            return AcquireResult(ok=True, owner=owner, until=until)

        cur = self.get(work, seq)
        if cur:
            return AcquireResult(
                ok=False, owner=cur[0], until=cur[1], reason="held_by_other",
            )
        return AcquireResult(ok=False, reason="cas_failed")

    def assert_owner(
        self, work: str, seq: int, owner: str, *, now: float | None = None,
    ) -> bool:
        t = time.time() if now is None else now
        self._ensure()
        try:
            rows = self.st._query(
                "SELECT owner AS o, until AS u FROM type::record('ingest_lease', $id)",
                {"id": self._rid(work, seq)},
            ) or []
            if not rows:
                return False
            o = (rows[0].get("o") or "").strip()
            u = float(rows[0].get("u") or 0)
            return bool(o == owner and u > t)
        except Exception:
            return False


class ChapterLeaseBackend:
    """chapter 行冗余字段 · UPDATE WHERE CAS（跨进程备份通道）。"""

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
            o = (rows[0].get("o") or "").strip()
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
        try:
            self.st._execute_write(
                "UPDATE type::record('chapter',$seq) SET "
                "ingest_lease_owner=NONE, ingest_lease_until=NONE "
                "WHERE ingest_lease_owner = $o",
                {"seq": int(seq), "o": owner},
            )
            cur = self.get(work, seq)
            return cur is None or cur[0] != owner
        except Exception:
            return False

    def atomic_try_acquire(
        self, work: str, seq: int, owner: str, until: float, *, now: float,
    ) -> AcquireResult:
        """CAS：UPDATE WHERE 空/过期/同 owner 后 re-read 校验。"""
        self._ensure()
        binds = {
            "seq": int(seq), "o": owner, "u": float(until), "now": float(now),
        }
        try:
            self.st._execute_write(
                "UPDATE type::record('chapter',$seq) SET "
                "ingest_lease_owner=$o, ingest_lease_until=$u "
                "WHERE ingest_lease_owner = NONE OR ingest_lease_owner = NONE "
                "OR ingest_lease_until = NONE OR ingest_lease_until < $now "
                "OR ingest_lease_until <= $now OR ingest_lease_owner = $o "
                "OR ingest_lease_owner = ''",
                binds,
            )
        except Exception as e:
            _log.warning("chapter lease CAS failed: %s", e)

        if self.assert_owner(work, seq, owner, now=now):
            return AcquireResult(ok=True, owner=owner, until=until)
        cur = self.get(work, seq)
        if cur:
            return AcquireResult(
                ok=False, owner=cur[0], until=cur[1], reason="held_by_other",
            )
        return AcquireResult(ok=False, reason="cas_failed")

    def assert_owner(
        self, work: str, seq: int, owner: str, *, now: float | None = None,
    ) -> bool:
        t = time.time() if now is None else now
        self._ensure()
        try:
            rows = self.st._query(
                "SELECT ingest_lease_owner AS o, ingest_lease_until AS u "
                "FROM type::record('chapter',$seq)",
                {"seq": int(seq)},
            ) or []
            if not rows:
                return False
            o = (rows[0].get("o") or "").strip()
            u = float(rows[0].get("u") or 0)
            return bool(o == owner and u > t)
        except Exception:
            return False


def combined_backend(store=None) -> LeaseBackend:
    """生产：Table CAS + Chapter CAS + 进程内存；均实现 atomic_try_acquire。"""
    if store is None:
        return _GLOBAL_MEM
    table = TableLeaseBackend(store)
    ch = ChapterLeaseBackend(store)

    class _Combo:
        def get(self, work, seq):
            r = table.get(work, seq)
            if r:
                return r
            r = ch.get(work, seq)
            if r:
                return r
            return _GLOBAL_MEM.get(work, seq)

        def set(self, work, seq, owner, until):
            table.set(work, seq, owner, until)
            ch.set(work, seq, owner, until)
            _GLOBAL_MEM.set(work, seq, owner, until)

        def clear(self, work, seq, owner):
            a = table.clear(work, seq, owner)
            b = ch.clear(work, seq, owner)
            c = _GLOBAL_MEM.clear(work, seq, owner)
            return a or b or c

        def atomic_try_acquire(self, work, seq, owner, until, *, now):
            # 1) 表 CAS（跨进程主通道）
            r = table.atomic_try_acquire(work, seq, owner, until, now=now)
            if not r.ok:
                return r
            # 2) 冗余 chapter 字段 + 进程内存（失败不撤表锁——assert 会挡住 purge）
            try:
                ch.atomic_try_acquire(work, seq, owner, until, now=now)
            except Exception:
                pass
            try:
                _GLOBAL_MEM.atomic_try_acquire(work, seq, owner, until, now=now)
            except Exception:
                pass
            # 3) 最终以表 assert 为准
            if table.assert_owner(work, seq, owner, now=now):
                return AcquireResult(ok=True, owner=owner, until=until, reason=r.reason)
            return AcquireResult(ok=False, reason="cas_failed_after_table")

        def assert_owner(self, work, seq, owner, *, now=None):
            if table.assert_owner(work, seq, owner, now=now):
                return True
            if ch.assert_owner(work, seq, owner, now=now):
                return True
            return _GLOBAL_MEM.assert_owner(work, seq, owner, now=now)

    return _Combo()


def assert_lease_or_raise(
    backend: LeaseBackend,
    work: str,
    seq: int,
    owner: str,
) -> None:
    """purge 前硬校验；失败抛 RuntimeError 阻止 apply_delta。"""
    if not assert_lease_owner(backend, work, seq, owner):
        raise RuntimeError(
            f"ingest lease lost work={work} seq={seq} owner={owner}: "
            "refusing purge/apply"
        )
