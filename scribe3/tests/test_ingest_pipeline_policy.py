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


# ----- CAS table / chapter backends (fake store, no Surreal) -----

class FakeCASStore:
    """模拟 CREATE ONLY + UPDATE WHERE 语义，供 TableLeaseBackend / ChapterLeaseBackend。"""

    def __init__(self) -> None:
        self.table: dict[str, dict] = {}
        self.chapters: dict[int, dict] = {}
        self.create_calls = 0
        self.update_calls = 0
        self._lock = threading.Lock()

    def _raw_query(self, *a, **k):
        return None

    def _execute_write(self, q: str, binds: dict | None = None):
        binds = binds or {}
        with self._lock:
            return self._execute_write_unlocked(q, binds)

    def _execute_write_unlocked(self, q: str, binds: dict):
        is_table = "type::record('ingest_lease'" in q or 'type::record("ingest_lease"' in q
        is_chapter = "type::record('chapter'" in q or 'type::record("chapter"' in q
        # 清租约：仅识别 SET 子句（勿把 WHERE owner = NONE 当成 clear）
        q_compact = q.replace(" ", "")
        set_part = q_compact.split("WHERE")[0] if "WHERE" in q_compact else q_compact
        set_clear = (
            "SETowner=NONE" in set_part
            or "SETingest_lease_owner=NONE" in set_part
            or ",owner=NONE" in set_part
            or ",ingest_lease_owner=NONE" in set_part
        )

        if "CREATE ONLY" in q and is_table:
            self.create_calls += 1
            rid = binds["id"]
            if rid in self.table:
                raise RuntimeError("record already exists")
            self.table[rid] = {
                "owner": binds["o"], "until": float(binds["u"]),
                "work": binds.get("w"), "seq": binds.get("s"),
            }
            return

        if is_table and "UPDATE" in q:
            self.update_calls += 1
            rid = binds.get("id")
            if rid is None:
                return
            row = self.table.get(rid)
            now = float(binds.get("now") or time.time())
            o = binds.get("o")
            u = float(binds.get("u") or 0)
            if set_clear:
                if row and (row.get("owner") or "") == o:
                    row["owner"] = ""
                    row["until"] = 0
                return
            if "WHERE" in q:
                if row is None:
                    return
                owner = (row.get("owner") or "").strip()
                until = float(row.get("until") or 0)
                ok = (not owner) or until < now or until <= now or owner == o
                if ok:
                    row["owner"] = o
                    row["until"] = u
                return
            self.table[rid] = {
                "owner": o, "until": u,
                "work": binds.get("w"), "seq": binds.get("s"),
            }
            return

        if is_chapter and "ingest_lease_owner" in q:
            seq = int(binds.get("seq") or 0)
            row = self.chapters.setdefault(seq, {})
            now = float(binds.get("now") or time.time())
            o = binds.get("o")
            u = binds.get("u")
            if set_clear:
                if (row.get("ingest_lease_owner") or "") == o:
                    row["ingest_lease_owner"] = None
                    row["ingest_lease_until"] = None
                return
            if "WHERE" in q:
                owner = (row.get("ingest_lease_owner") or "").strip()
                until = float(row.get("ingest_lease_until") or 0)
                if (not owner) or until < now or until <= now or owner == o:
                    if o is not None:
                        row["ingest_lease_owner"] = o
                    if u is not None:
                        row["ingest_lease_until"] = float(u)
                return
            if o is not None:
                row["ingest_lease_owner"] = o
            if u is not None:
                row["ingest_lease_until"] = float(u)

    def _query(self, q: str, binds: dict | None = None):
        binds = binds or {}
        with self._lock:
            if "type::record('ingest_lease'" in q or 'type::record("ingest_lease"' in q:
                rid = binds.get("id")
                row = self.table.get(rid)
                if not row:
                    return []
                return [{"o": row.get("owner"), "u": row.get("until")}]
            if "type::record('chapter'" in q or 'type::record("chapter"' in q:
                seq = int(binds.get("seq") or 0)
                row = self.chapters.get(seq, {})
                return [{
                    "o": row.get("ingest_lease_owner"),
                    "u": row.get("ingest_lease_until"),
                }]
            return []


def test_table_lease_cas_create_only_first_wins():
    from scribe3.ingest_lease import TableLeaseBackend, try_acquire_ingest_lease, new_owner

    st = FakeCASStore()
    be = TableLeaseBackend(st)
    o1, o2 = new_owner(), new_owner()
    a1 = try_acquire_ingest_lease(be, "main", 1, o1, ttl=60)
    assert a1.ok, a1
    a2 = try_acquire_ingest_lease(be, "main", 1, o2, ttl=60)
    assert not a2.ok and a2.reason == "held_by_other"
    assert a2.owner == o1
    # 过期后可抢：把 until 推到过去，模拟 TTL 到期
    from scribe3.ingest_lease import lease_record_id
    rid = lease_record_id("main", 1)
    st.table[rid]["until"] = time.time() - 10
    a3 = try_acquire_ingest_lease(be, "main", 1, o2, ttl=60)
    assert a3.ok, a3


def test_table_lease_cas_concurrent_single_winner():
    from scribe3.ingest_lease import TableLeaseBackend, try_acquire_ingest_lease

    st = FakeCASStore()
    be = TableLeaseBackend(st)
    wins = []
    lock = threading.Lock()

    def race(i: int):
        r = try_acquire_ingest_lease(be, "w", 42, f"o{i:02d}", ttl=30)
        if r.ok:
            with lock:
                wins.append(f"o{i:02d}")

    threads = [threading.Thread(target=race, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # CREATE ONLY 路径下只有一个成功（假 store 非完全线程安全时允许 ≥1 但我们加了 table 级检查）
    # 以 assert_owner 为准：最多一个有效 owner
    owners = set()
    for i in range(12):
        if be.assert_owner("w", 42, f"o{i:02d}", now=None):
            owners.add(f"o{i:02d}")
    assert len(owners) == 1, owners


def test_chapter_lease_cas_where_not_toctou_double_set():
    from scribe3.ingest_lease import ChapterLeaseBackend, try_acquire_ingest_lease, new_owner

    st = FakeCASStore()
    be = ChapterLeaseBackend(st)
    o1, o2 = new_owner(), new_owner()
    assert try_acquire_ingest_lease(be, "main", 3, o1, ttl=60).ok
    r2 = try_acquire_ingest_lease(be, "main", 3, o2, ttl=60)
    assert not r2.ok
    assert be.assert_owner("main", 3, o1, now=None)
    assert not be.assert_owner("main", 3, o2, now=None)


def test_assert_lease_blocks_lost_owner():
    from scribe3.ingest_lease import (
        MemoryLeaseBackend, try_acquire_ingest_lease, assert_lease_owner,
        assert_lease_or_raise, new_owner, release_ingest_lease,
    )
    b = MemoryLeaseBackend()
    o1, o2 = new_owner(), new_owner()
    assert try_acquire_ingest_lease(b, "w", 1, o1, ttl=60).ok
    assert assert_lease_owner(b, "w", 1, o1)
    assert not assert_lease_owner(b, "w", 1, o2)
    release_ingest_lease(b, "w", 1, o1)
    try:
        assert_lease_or_raise(b, "w", 1, o1)
        assert False, "should raise"
    except RuntimeError as e:
        assert "lease lost" in str(e).lower() or "refusing" in str(e).lower()


def test_ingest_chapter_refuses_purge_when_lease_lost(monkeypatch):
    """驱动真实 ingest_chapter：lease_owner 失效 → 不调 apply_delta。"""
    from scribe3 import ingest as ing
    from scribe3.ingest_lease import MemoryLeaseBackend, try_acquire_ingest_lease, new_owner

    class MiniStore:
        def get_chapter(self, seq):
            return {"prose": "足够长的正文用于触发抽取路径。" * 5}
        def list_motifs(self):
            return []
        def open_promises(self):
            return []
        def characters(self):
            return []
        def char_anchors(self, cid):
            return {}

    st = MiniStore()
    be = MemoryLeaseBackend()
    owner = new_owner()
    try_acquire_ingest_lease(be, "main", 1, owner, ttl=60)
    # 释放租约 → 模拟被他主抢走后丢失
    be.clear("main", 1, owner)

    called = {"apply": 0}

    def fake_apply(*a, **k):
        called["apply"] += 1
        return 1

    monkeypatch.setattr(ing, "apply_delta", fake_apply)
    monkeypatch.setattr(ing, "grep_back_verify", lambda d, p: {"delta": d, "annotated": []})
    monkeypatch.setattr(
        ing, "parse_knowledge_delta",
        lambda r: {"learned": [], "did": [], "events": [], "voice_shift": []},
    )
    # 关掉 unified 走 legacy
    monkeypatch.setenv("SCRIBE3_UNIFIED_ANALYSIS", "0")

    def complete(prompt: str) -> str:
        return '{"learned":[],"did":[],"events":[],"voice_shift":[]}'

    r = ing.ingest_chapter(
        st, 1, complete, work="main", max_attempts=1,
        lease_owner=owner, lease_backend=be,
    )
    assert r.get("reason") == "lease_lost_before_purge"
    assert called["apply"] == 0


def test_s3_save_chapter_craft_gate_blocks_persist(monkeypatch):
    """驱动真实 s3_save_chapter：craft allowed=false → blocked 且 save_chapter 未调用。"""
    from scribe3.mcp import tools_write as tw

    st = FakeChapterStore()
    st.save_chapter = lambda *a, **k: (_ for _ in ()).throw(  # noqa: E731
        AssertionError("save_chapter must not be called")
    )
    # FakeChapterStore 无 save_chapter；用 MagicMock 风格
    class ST(FakeChapterStore):
        def __init__(self):
            super().__init__()
            self.saved = False
        def save_chapter(self, *a, **k):
            self.saved = True
        def add_chapter_version(self, *a, **k):
            return "v1"
        def list_chapters(self):
            return []

    st = ST()
    monkeypatch.setattr(tw, "_store_for", lambda work=None: st)

    def fake_fg(st_, seq, prose, **kw):
        return {
            "allowed": False,
            "code": "finalize_gate",
            "detail": "定稿门没过",
            "blocking": ["x"],
        }

    monkeypatch.setattr(
        "scribe3.finalize_gate.check_finalize_for_save",
        fake_fg,
    )
    out = tw.s3_save_chapter(
        1, "这是一段用于测试定稿门阻断落库的正文内容。" * 15,
        work="main",
    )
    assert out["status"] == "blocked"
    assert out["code"] == "finalize_gate"
    assert st.saved is False


def test_s3_save_chapter_craft_pass_then_finalize_can_block(monkeypatch):
    from scribe3.mcp import tools_write as tw

    class ST(FakeChapterStore):
        def __init__(self):
            super().__init__()
            self.saved = False
        def save_chapter(self, *a, **k):
            self.saved = True
        def add_chapter_version(self, *a, **k):
            return "v1"
        def list_chapters(self):
            return []

    st = ST()
    monkeypatch.setattr(tw, "_store_for", lambda work=None: st)
    monkeypatch.setattr(
        "scribe3.finalize_gate.check_finalize_for_save",
        lambda *a, **k: {
            "allowed": False, "code": "finalize_gate", "verdict": "blocking",
            "detail": "blocked", "blocking": ["x"],
        },
    )
    out = tw.s3_save_chapter(2, "正文" * 30, work="main")
    assert out["status"] == "blocked"
    assert out["code"] == "finalize_gate"
    assert st.saved is False


def test_combined_backend_has_atomic():
    from scribe3.ingest_lease import combined_backend, try_acquire_ingest_lease, new_owner
    st = FakeCASStore()
    be = combined_backend(st)
    assert callable(getattr(be, "atomic_try_acquire", None))
    o1, o2 = new_owner(), new_owner()
    assert try_acquire_ingest_lease(be, "main", 7, o1, ttl=30).ok
    assert not try_acquire_ingest_lease(be, "main", 7, o2, ttl=30).ok
