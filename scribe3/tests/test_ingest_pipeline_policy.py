"""章节流水线闭环 · lease + IngestPolicy 纯逻辑单测（PR-1/2）。

不连 Surreal；用 MemoryLeaseBackend 与假 store hold 状态。
"""
from __future__ import annotations

import threading
import time

from scribe3.ingest_lease import (
    MemoryLeaseBackend,
    new_owner,
    release_ingest_lease,
    try_acquire_ingest_lease,
)
from scribe3.ingest_policy import (
    GateSnapshot,
    DecideResult,
    allow_distill,
    decide_ingest,
    prose_fingerprint,
    write_hold,
    clear_hold,
    run_or_enqueue,
)


class FakeChapterStore:
    """最小 hold/lease 字段模拟。"""

    def __init__(self) -> None:
        self._ch: dict[int, dict] = {}

    def get_chapter(self, seq: int) -> dict:
        return dict(self._ch.get(int(seq), {}))

    def _raw_query(self, *a, **k):
        return None

    def _execute_write(self, q: str, binds: dict | None = None):
        binds = binds or {}
        seq = int(binds.get("seq") or 0)
        row = self._ch.setdefault(seq, {})
        if "ingest_hold_reason" in q or "ingest_hold_reason=$r" in q:
            if binds.get("r") is not None:
                row["ingest_hold_reason"] = binds.get("r")
            if binds.get("t") is not None:
                row["ingest_confirm_token"] = binds.get("t")
            if binds.get("fp") is not None:
                row["ingest_hold_prose_fp"] = binds.get("fp")
            if binds.get("u") is not None:
                row["ingest_hold_until"] = binds.get("u")
            if binds.get("st") is not None:
                row["ingest_status"] = binds.get("st")
        if "ingest_hold_reason=NONE" in q:
            row.pop("ingest_hold_reason", None)
            row.pop("ingest_confirm_token", None)
            row.pop("ingest_hold_until", None)
        if "ingest_lease_owner" in q and "NONE" not in q:
            if binds.get("o") is not None:
                row["ingest_lease_owner"] = binds.get("o")
            if binds.get("u") is not None:
                row["ingest_lease_until"] = binds.get("u")
        if "ingest_lease_owner=NONE" in q:
            row.pop("ingest_lease_owner", None)
            row.pop("ingest_lease_until", None)

    def _query(self, q: str, binds: dict | None = None):
        binds = binds or {}
        seq = int(binds.get("seq") or 0)
        row = self._ch.get(seq, {})
        if "ingest_lease_owner" in q:
            return [{"o": row.get("ingest_lease_owner"), "u": row.get("ingest_lease_until")}]
        return [dict(row)]


def test_lease_acquire_release_and_other_blocked():
    b = MemoryLeaseBackend()
    o1, o2 = new_owner(), new_owner()
    a1 = try_acquire_ingest_lease(b, "w", 1, o1, ttl=60)
    assert a1.ok and a1.owner == o1
    a2 = try_acquire_ingest_lease(b, "w", 1, o2, ttl=60)
    assert not a2.ok and a2.reason == "held_by_other"
    assert release_ingest_lease(b, "w", 1, o1)
    a3 = try_acquire_ingest_lease(b, "w", 1, o2, ttl=60)
    assert a3.ok


def test_lease_same_owner_renew_and_expiry():
    b = MemoryLeaseBackend()
    o = new_owner()
    t0 = 1_000_000.0
    a = try_acquire_ingest_lease(b, "w", 2, o, ttl=10, now=t0)
    assert a.ok
    a2 = try_acquire_ingest_lease(b, "w", 2, o, ttl=10, now=t0 + 1)
    assert a2.ok and a2.reason == "renewed"
    # 过期后他主可抢
    o2 = new_owner()
    a3 = try_acquire_ingest_lease(b, "w", 2, o2, ttl=10, now=t0 + 100)
    assert a3.ok


def test_lease_concurrent_single_winner():
    b = MemoryLeaseBackend()
    wins = []
    lock = threading.Lock()

    def race(i: int):
        o = f"o{i}"
        r = try_acquire_ingest_lease(b, "w", 9, o, ttl=30)
        if r.ok:
            with lock:
                wins.append(o)

    threads = [threading.Thread(target=race, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(wins) == 1


def test_prose_fingerprint_stable():
    assert prose_fingerprint("甲乙丙") == prose_fingerprint("甲乙丙")
    assert prose_fingerprint("甲") != prose_fingerprint("乙")


def test_decide_advisory_hold():
    st = FakeChapterStore()
    prose = "advisory 正文" * 20
    d = decide_ingest(
        st, "main", 1,
        gate=GateSnapshot(path="save", finalize_verdict="advisory"),
        prose=prose, source="save",
    )
    assert d.action == "hold"
    assert d.hold_reason == "advisory_gate"
    assert d.confirm_token
    assert d.prose_fp == prose_fingerprint(prose)


def test_decide_pass_auto():
    st = FakeChapterStore()
    d = decide_ingest(
        st, "main", 1,
        gate=GateSnapshot(path="save", finalize_verdict="pass"),
        prose="pass 正文", source="save",
    )
    assert d.action == "auto"
    assert d.allow_distill


def test_decide_blocking_skip():
    st = FakeChapterStore()
    d = decide_ingest(
        st, "main", 1,
        gate=GateSnapshot(path="save", finalize_verdict="blocking"),
        prose="block", source="save",
    )
    assert d.action == "skip"
    assert d.skip_reason == "blocking_verdict"


def test_active_hold_supersedes_checkpoint():
    """KD18: save advisory hold 后 checkpoint 同 prose_fp 不得 auto。"""
    st = FakeChapterStore()
    prose = "hold me please " * 10
    d1 = decide_ingest(
        st, "main", 12,
        gate=GateSnapshot(path="save", finalize_verdict="advisory"),
        prose=prose, source="save",
    )
    assert d1.action == "hold"
    write_hold(
        st, 12, reason=d1.hold_reason, token=d1.confirm_token, prose_fp=d1.prose_fp,
    )
    # W2 checkpoint 无 snapshot
    d2 = decide_ingest(
        st, "main", 12,
        gate=GateSnapshot(path="checkpoint", finalize_verdict=None),
        prose=prose, source="checkpoint",
    )
    assert d2.action == "hold"
    assert d2.reason == "active_hold_supersedes"
    assert d2.confirm_token == d1.confirm_token


def test_checkpoint_missing_snapshot_hold_when_no_prior():
    st = FakeChapterStore()
    d = decide_ingest(
        st, "main", 3,
        gate=GateSnapshot(path="checkpoint", finalize_verdict=None),
        prose="solo checkpoint", source="checkpoint",
    )
    assert d.action == "hold"
    assert d.hold_reason == "missing_gate_snapshot"


def test_confirm_token_ok_and_bad():
    st = FakeChapterStore()
    prose = "confirm body"
    tok = "abc123token"
    write_hold(st, 5, reason="advisory_gate", token=tok, prose_fp=prose_fingerprint(prose))
    ok = decide_ingest(
        st, "main", 5,
        gate=GateSnapshot(path="confirm", finalize_verdict="pass"),
        prose=prose, source="confirm", confirm_token=tok,
    )
    assert ok.action == "auto"
    bad = decide_ingest(
        st, "main", 5,
        gate=GateSnapshot(path="confirm", finalize_verdict="pass"),
        prose=prose, source="confirm", confirm_token="wrong",
    )
    assert bad.action == "hold"


def test_force_overrides_hold():
    st = FakeChapterStore()
    prose = "forced"
    write_hold(
        st, 7, reason="advisory_gate", token="t",
        prose_fp=prose_fingerprint(prose),
    )
    d = decide_ingest(
        st, "main", 7,
        gate=GateSnapshot(path="http_ingest", finalize_verdict="pass"),
        prose=prose, source="http_ingest", force=True,
    )
    assert d.action == "auto"


def test_allow_distill_matrix():
    hold = DecideResult(action="hold", allow_distill=False)
    auto = DecideResult(action="auto", allow_distill=True)
    skip = DecideResult(action="skip")
    assert allow_distill(hold, apply_ok=True) is False
    assert allow_distill(auto, apply_ok=False) is False
    assert allow_distill(auto, apply_ok=True) is True
    assert allow_distill(skip, apply_ok=True) is False


def test_run_or_enqueue_bg_hold_no_enqueue():
    st = FakeChapterStore()
    prose = "x" * 40

    class BG:
        def __init__(self):
            self.tasks = []

        def add_task(self, fn, *a):
            self.tasks.append((fn, a))

    bg = BG()
    # 先 hold
    out = run_or_enqueue(
        st, "main", 8, mode="bg", background=bg,
        gate=GateSnapshot(path="save", finalize_verdict="advisory"),
        prose=prose, source="save",
    )
    assert out["held"] is True
    assert out["enqueued"] is False
    assert len(bg.tasks) == 0
    # checkpoint 第二跳
    out2 = run_or_enqueue(
        st, "main", 8, mode="bg", background=bg,
        gate=GateSnapshot(path="checkpoint", finalize_verdict=None),
        prose=prose, source="checkpoint",
    )
    assert out2["held"] is True
    assert out2["enqueued"] is False
    assert out2["reason"] == "active_hold_supersedes"
    assert len(bg.tasks) == 0


def test_run_or_enqueue_bg_pass_enqueues():
    st = FakeChapterStore()
    prose = "clean pass prose"

    class BG:
        def __init__(self):
            self.n = 0

        def add_task(self, fn, *a):
            self.n += 1

    # monkey: pending set 可能已存在；用真 _enqueue_ingest_raw
    bg = BG()
    out = run_or_enqueue(
        st, "main", 11, mode="bg", background=bg,
        gate=GateSnapshot(path="save", finalize_verdict="pass"),
        prose=prose, source="save",
    )
    assert out["action"] == "auto"
    assert out["enqueued"] is True
    assert bg.n == 1


def test_build_ingest_status_row_held():
    from scribe3.finalize_gate import build_ingest_status_row
    row = build_ingest_status_row(
        1,
        {
            "ingest_status": "held",
            "ingest_hold_reason": "advisory_gate",
            "ingest_hold_until": time.time() + 3600,
        },
    )
    assert row["held"] is True
    assert row["ingest_status"] == "held"
    assert row["ok"] is False
    assert row["hold_reason"] == "advisory_gate"
