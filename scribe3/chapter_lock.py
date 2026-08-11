"""统一章节锁表面（P2 · PR-10 / O-10）。

loop / ingest / repair 共用同一 acquire/release API。
默认进程内（concurrency_lock）；``SCRIBE3_DISTRIBUTED_LOCK=1`` 且注入 store 时走 store。
同 kind+chapter 重入 → busy（非静默双入）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scribe3.concurrency_lock import (
    InMemoryLockStore,
    acquire_lock,
    distributed_lock_enabled,
    release_lock,
)
from scribe3.concurrency_obs import inflight_enter, inflight_leave

CHAPTER_OPS = frozenset({"loop", "ingest", "repair", "run"})


@dataclass(frozen=True)
class ChapterLockResult:
    ok: bool
    status: str  # acquired | busy | invalid
    kind: str
    chapter_key: str
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "kind": self.kind,
            "chapter_key": self.chapter_key,
            "detail": self.detail,
        }


def chapter_target(work: str | None, seq: int | str) -> str:
    """稳定章节键：work:seq。"""
    return f"{(work or 'main').strip() or 'main'}:{int(seq)}"


def acquire_chapter_lock(
    kind: str,
    work: str | None,
    seq: int | str,
    *,
    store: Any = None,
    ttl_seconds: int = 120,
    worker: str | None = None,
) -> ChapterLockResult:
    """获取章节级锁。busy 时 ok=False、status=busy。"""
    k = str(kind or "run").strip().lower() or "run"
    if k not in CHAPTER_OPS:
        k = "run"
    target = chapter_target(work, seq)
    # concurrency_lock：进程内恒拒绝同 kind+target 重入；
    # distributed 旗开且 store 有时优先 store。
    got = acquire_lock(
        k, target, ttl_seconds=ttl_seconds, worker=worker, store=store,
    )
    if not got:
        return ChapterLockResult(
            ok=False,
            status="busy",
            kind=k,
            chapter_key=target,
            detail=f"chapter lock busy kind={k} key={target}",
        )
    # 观测：distributed 已由 acquire_lock 占坑，勿再 inflight_enter（会二次 store 抢锁）。
    # 旗关时 inflight_enter 只写进程内 map，不重复抢 concurrency_lock。
    try:
        if distributed_lock_enabled():
            import time as _time
            from scribe3 import concurrency_obs as _co
            with _co._lock:
                _co._inflight.setdefault(k, {})[target] = _time.time()
        else:
            inflight_enter(k, target, store=store)
    except Exception:
        pass
    return ChapterLockResult(
        ok=True,
        status="acquired",
        kind=k,
        chapter_key=target,
        detail="",
    )


def release_chapter_lock(
    kind: str,
    work: str | None,
    seq: int | str,
    *,
    store: Any = None,
) -> None:
    k = str(kind or "run").strip().lower() or "run"
    if k not in CHAPTER_OPS:
        k = "run"
    target = chapter_target(work, seq)
    try:
        if distributed_lock_enabled():
            from scribe3 import concurrency_obs as _co
            with _co._lock:
                (_co._inflight.get(k) or {}).pop(target, None)
            release_lock(k, target, store=store)
        else:
            inflight_leave(k, target, store=store)
            release_lock(k, target, store=store)
    except Exception:
        try:
            release_lock(k, target, store=store)
        except Exception:
            pass


def chapter_lock_busy_http_detail(result: ChapterLockResult) -> str:
    """映射 409 文案。"""
    op = result.kind
    try:
        seq = result.chapter_key.rsplit(":", 1)[-1]
    except Exception:
        seq = "?"
    if op == "repair":
        return f"第 {seq} 章正在执行质量修复，完成后请重新检查再操作"
    if op == "ingest":
        return f"第 {seq} 章正在反哺中，请稍后再试"
    if op == "loop":
        return f"第 {seq} 章正在生成中，请勿重复提交"
    return result.detail or f"chapter busy: {result.chapter_key}"


__all__ = [
    "CHAPTER_OPS",
    "ChapterLockResult",
    "InMemoryLockStore",
    "acquire_chapter_lock",
    "chapter_key",
    "chapter_lock_busy_http_detail",
    "chapter_target",
    "distributed_lock_enabled",
    "release_chapter_lock",
]

# alias
chapter_key = chapter_target
