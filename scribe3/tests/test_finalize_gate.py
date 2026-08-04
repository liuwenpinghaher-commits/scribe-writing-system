"""写作方案强制闭环 · 定稿门闩 + ingest 可观测 + 检测器 TDD。

策略单测不启 Surreal;API 路径测通过 FakeStore + 真实 handler 函数
(scribe3.app 上 rebind 后的 save_chapter / ingest_status / ingest_retry)。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from scribe3.finalize_gate import (
    build_deterministic_post,
    build_ingest_status_row,
    check_finalize_for_save,
    collect_deterministic_post_for_prose,
    evaluate_finalize_gate,
    finalize_gate_env_enabled,
)
from scribe3.loop import triage
from scribe3.volume_signals import (
    motifs_without_echo,
    overdue_promises_in_range,
    volume_chapter_seqs,
    volume_review_signals,
)


# ===== FakeStore:驱动真实 handler 而无 Surreal =====

class FakeStore:
    def __init__(self):
        self.chapters: dict[int, dict] = {}
        self.saved: list[tuple] = []
        self.versions: list = []
        self.writes: list = []  # 捕获 mark_chapter_ingest_status 真实落库

    def save_chapter(self, seq, prose, title="", focalizer=None):
        prev = self.chapters.get(int(seq)) or {}
        self.chapters[int(seq)] = {
            "seq": int(seq), "prose": prose, "title": title,
            "focalizer": focalizer,
            "ingest_status": prev.get("ingest_status"),
            "ingest_error": prev.get("ingest_error"),
        }
        self.saved.append((int(seq), prose))

    def get_chapter(self, seq):
        return dict(self.chapters.get(int(seq)) or {})

    def latest_version_prose(self, seq, kind):
        return None

    def add_chapter_version(self, *a, **k):
        self.versions.append((a, k))

    def recent_proses(self, seq, k=8):
        return []

    def motif_terms(self):
        return None

    def list_chapters(self):
        return [{"seq": s} for s in sorted(self.chapters)]

    def chapters_lite(self):
        return self.list_chapters()

    def _execute_write(self, sql, params=None):
        """实现 mark_chapter_ingest_status 所用 Surreal UPDATE 语义(无剧院手写 status)。"""
        params = params or {}
        self.writes.append((sql, dict(params)))
        if "ingest_status" in (sql or "") and "seq" in params:
            ch = self.chapters.setdefault(int(params["seq"]), {"seq": int(params["seq"])})
            ch["ingest_status"] = params.get("st")
            ch["ingest_error"] = params.get("er", "")


# ===== 纯策略 =====

def test_finalize_gate_blocking_refuses(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post(
        "x", leaks=[{"marker": "治眼", "fact_id": "fact:治眼"}])
    d = evaluate_finalize_gate(post, danger_draft=False)
    assert d["allowed"] is False and d["verdict"] == "blocking"


def test_finalize_gate_danger_draft_bypasses_blocking(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post(
        "x", leaks=[{"marker": "治眼", "fact_id": "fact:治眼"}])
    d = evaluate_finalize_gate(post, danger_draft=True)
    assert d["allowed"] is True and d["code"] == "danger_bypass"
    assert d["blocking"]


def test_finalize_gate_advisory_allows_no_rewrite(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    post = build_deterministic_post(
        "干净正文。",
        issues=[{"type": "degeneration", "message": "疑似", "text": "",
                 "meta": {"severity": "advisory", "kind": "truncated"}}])
    d = evaluate_finalize_gate(post)
    assert d["allowed"] is True
    assert d["verdict"] in ("advisory", "pass")


def test_finalize_gate_pass_allows(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    d = evaluate_finalize_gate(
        build_deterministic_post("他把伞收了,雨还没停。院里只有一声犬吠。"))
    assert d["allowed"] is True and d["verdict"] == "pass"


def test_finalize_gate_skip_and_env_off(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "0")
    assert finalize_gate_env_enabled() is False
    assert evaluate_finalize_gate(None)["code"] == "skipped"


def test_finalize_gate_no_post_fail_closed(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    d = evaluate_finalize_gate(None, danger_draft=False)
    assert d["allowed"] is False and d["code"] == "no_post"


def test_check_finalize_for_save_is_shared_helper(monkeypatch):
    """共享 helper:门开 + blocking post → 不 allowed(真实生产接线函数)。"""
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    from scribe3 import finalize_gate as FG

    monkeypatch.setattr(
        FG, "collect_deterministic_post_for_prose",
        lambda prose, **kw: build_deterministic_post(
            prose, leaks=[{"marker": "治眼", "fact_id": "f1"}]))
    st = FakeStore()
    d = check_finalize_for_save(st, 1, "他知道治眼。", focalizer="role:x")
    assert d["allowed"] is False and d["verdict"] == "blocking"
    d2 = check_finalize_for_save(
        st, 1, "他知道治眼。", focalizer="role:x", danger_draft=True)
    assert d2["allowed"] is True and d2["code"] == "danger_bypass"


# ===== 真实 save_chapter handler(非剧院) =====

def _install_fake_store(monkeypatch, st: FakeStore, work: str = "test"):
    import scribe3.app as A
    # set_store 默认 work=main;handler 测例一律 work=test → 必须对齐
    A.set_store(st, work=work)
    # 绕过在途/pilot 护栏
    monkeypatch.setattr(A, "_loop_inflight", set(), raising=False)
    monkeypatch.setattr(A, "_loop_inflight_lock", __import__("threading").Lock(), raising=False)
    monkeypatch.setattr(A, "_guard_pilot_busy", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(A, "_enqueue_ingest", lambda *a, **k: True, raising=False)
    return A


def test_real_save_chapter_handler_blocks_on_finalize(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "0")
    st = FakeStore()
    A = _install_fake_store(monkeypatch, st)
    from scribe3 import finalize_gate as FG
    monkeypatch.setattr(
        FG, "collect_deterministic_post_for_prose",
        lambda prose, **kw: build_deterministic_post(
            prose, leaks=[{"marker": "治眼", "fact_id": "f1"}]))
    from scribe3.api.models import SaveChapterReq
    with pytest.raises(HTTPException) as ei:
        A.save_chapter(
            SaveChapterReq(seq=1, prose="他知道治眼的秘方。", title="一"),
            BackgroundTasks(), work="test")
    assert ei.value.status_code == 409
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "blocked" or detail.get("verdict") == "blocking"
    assert st.saved == [], "blocking 不得落库"


def test_real_save_chapter_handler_danger_draft_persists(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "0")
    st = FakeStore()
    A = _install_fake_store(monkeypatch, st)
    from scribe3 import finalize_gate as FG
    monkeypatch.setattr(
        FG, "collect_deterministic_post_for_prose",
        lambda prose, **kw: build_deterministic_post(
            prose, leaks=[{"marker": "治眼", "fact_id": "f1"}]))
    from scribe3.api.models import SaveChapterReq
    out = A.save_chapter(
        SaveChapterReq(seq=2, prose="危险草稿。", title="二", danger_draft=True),
        BackgroundTasks(), work="test")
    assert out["status"] == "saved"
    assert out.get("finalize_gate", {}).get("danger_draft") is True
    assert st.saved and st.saved[-1][1] == "危险草稿。"


def test_real_save_chapter_handler_pass_persists(monkeypatch):
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "0")
    st = FakeStore()
    A = _install_fake_store(monkeypatch, st)
    from scribe3 import finalize_gate as FG
    monkeypatch.setattr(
        FG, "collect_deterministic_post_for_prose",
        lambda prose, **kw: build_deterministic_post(prose))
    from scribe3.api.models import SaveChapterReq
    out = A.save_chapter(
        SaveChapterReq(seq=3, prose="他把伞收了。", title="三"),
        BackgroundTasks(), work="test")
    assert out["status"] == "saved"
    assert out.get("finalize_gate", {}).get("verdict") == "pass"
    assert st.saved[-1][0] == 3


def test_s3_save_chapter_shares_finalize_gate(monkeypatch):
    """MCP 路径与 REST 共用 check_finalize_for_save。"""
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    st = FakeStore()
    import scribe3.mcp.tools_write as TW
    monkeypatch.setattr(TW, "_store_for", lambda work=None: st)
    from scribe3 import finalize_gate as FG
    monkeypatch.setattr(
        FG, "collect_deterministic_post_for_prose",
        lambda prose, **kw: build_deterministic_post(
            prose, leaks=[{"marker": "治眼", "fact_id": "f1"}]))
    blocked = TW.s3_save_chapter(9, "他知道治眼。", work="test")
    assert blocked["status"] == "blocked"
    assert st.saved == []
    ok = TW.s3_save_chapter(9, "他知道治眼。", work="test", danger_draft=True)
    assert ok["status"] == "saved"
    assert st.saved


# ===== 真实 ingest_status / ingest_retry =====

def test_build_ingest_status_row_honesty():
    """纯函数契约:failed 永不 ok。"""
    r = build_ingest_status_row(1, {"ingest_status": "failed", "ingest_error": "LLM挂了"})
    assert r["failed"] is True and r["ok"] is False
    r2 = build_ingest_status_row(1, {"ingest_status": "ok"}, pending=True)
    assert r2["ok"] is False and r2["pending"] is True
    r3 = build_ingest_status_row(1, {"ingest_status": "ok"})
    assert r3["ok"] is True and r3["failed"] is False
    r4 = build_ingest_status_row(1, {"ingest_status": "parse_failed"})
    assert r4["failed"] is True and r4["ok"] is False


def test_real_ingest_status_handler_failed_not_ok(monkeypatch):
    st = FakeStore()
    st.chapters[7] = {
        "seq": 7, "prose": "正文。",
        "ingest_status": "failed", "ingest_error": "LLM挂了",
    }
    st.chapters[8] = {
        "seq": 8, "prose": "另一章。",
        "ingest_status": "ok", "ingest_error": "",
    }
    A = _install_fake_store(monkeypatch, st)
    monkeypatch.setattr(A, "_pending_ingest", set(), raising=False)
    row = A.ingest_status(seq=7, work="test")
    assert row["failed"] is True
    assert row["ok"] is False
    assert "LLM" in (row.get("ingest_error") or "")
    ok_row = A.ingest_status(seq=8, work="test")
    assert ok_row["ok"] is True and ok_row["failed"] is False
    listing = A.ingest_status(seq=None, work="test")
    assert listing["failed_count"] >= 1
    assert any(r["seq"] == 7 for r in listing["failed_backlog"])


def test_real_ingest_retry_forced_failure_then_success(monkeypatch):
    """强制失败 + 重试成功:状态必须由生产 mark_chapter_ingest_status 落库。

    禁剧院:fake_ingest_chapter 不得手写 status;测试不得在失败后手标 failed。
    断言 chapter 字段与 GET /ingest/status 同源。
    """
    st = FakeStore()
    st.chapters[5] = {"seq": 5, "prose": "需反哺的正文。", "title": "五",
                      "ingest_status": None, "ingest_error": ""}
    A = _install_fake_store(monkeypatch, st)
    monkeypatch.setattr(A, "_pending_ingest", set(), raising=False)
    import threading
    monkeypatch.setattr(A, "_pending_ingest_lock", threading.Lock(), raising=False)

    calls = {"n": 0}

    def fake_ingest_chapter(store, seq, llm):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("forced_fail")
        # 只返回业务结果——禁止在此写 ingest_status(那是 mark 单源职责)
        return {"ok": True, "parse_failed": False}

    import scribe3.ingest as I
    monkeypatch.setattr(I, "ingest_chapter", fake_ingest_chapter)

    # 首次同步 /ingest 失败 → raise 且 chapter 已 mark failed
    with pytest.raises(RuntimeError, match="forced_fail"):
        A.ingest(5, work="test")
    ch_after_fail = st.get_chapter(5)
    assert ch_after_fail.get("ingest_status") == "failed", (
        "生产 /ingest 异常必须经 mark_chapter_ingest_status 落 failed,不得靠测试手写")
    assert "forced_fail" in (ch_after_fail.get("ingest_error") or "")
    # 真有 _execute_write 调用
    assert any("ingest_status" in (sql or "") for sql, _ in st.writes)
    before = A.ingest_status(seq=5, work="test")
    assert before["failed"] is True and before["ok"] is False

    # 重试(ingest_retry → 同一 ingest)成功 → mark ok,角标可消
    r = A.ingest_retry(5, BackgroundTasks(), work="test")
    assert r.get("ok") is True or r.get("parse_failed") is False
    ch_after_ok = st.get_chapter(5)
    assert ch_after_ok.get("ingest_status") == "ok", (
        "retry 成功必须 mark ok,否则 UI 角标永不消")
    assert (ch_after_ok.get("ingest_error") or "") == ""
    after = A.ingest_status(seq=5, work="test")
    assert after["ok"] is True and after["failed"] is False
    assert calls["n"] == 2


def test_mark_chapter_ingest_status_shared_helper(monkeypatch):
    """单源 mark:直接调用生产函数,经 store._execute_write 落字段。"""
    import scribe3.app as A
    st = FakeStore()
    st.chapters[3] = {"seq": 3, "prose": "x"}
    A.mark_chapter_ingest_status(st, 3, "failed", "boom")
    assert st.get_chapter(3)["ingest_status"] == "failed"
    assert "boom" in st.get_chapter(3)["ingest_error"]
    A.mark_chapter_ingest_status(st, 3, "ok")
    assert st.get_chapter(3)["ingest_status"] == "ok"
    assert st.get_chapter(3)["ingest_error"] == ""


def test_two_chapter_frame_advance_witness_knows():
    """可构造两章样本:ch1 事件见证 → ch2 帧投影含 knows(与 ingest 语义同构)。"""
    from scribe3.knowledge import project_frame, see_event
    from scribe3.ontology import Entity, Event, Fact, World

    w = World()
    w.add_entity(Entity("role:沈砚", "character", "沈砚"))
    w.add_entity(Entity("role:路人", "character", "路人"))
    f = Fact(
        id="fact:炉心", entity_id="role:白姑", attribute="secret",
        value="炉心真名", valid_from=1, secret=True,
        leak_markers=["炉心真名"],
    )
    w.add_fact(f)
    # 第1章:沈砚在场见证 → 获知
    ev = Event(
        id="ev:1", type="reveal", story_time=1,
        participants={"WITNESS": "role:沈砚"},
        effects=["fact:炉心"],
    )
    see_event(w, ev, ingest_seq=1)
    fr1 = project_frame(w, "role:沈砚", 1)
    assert fr1.knows("fact:炉心"), "ch1 见证后焦点者应知道"
    # 第2章:帧延续(since_chapter<=2)——下一章限知投影已 advance
    fr2 = project_frame(w, "role:沈砚", 2)
    assert fr2.knows("fact:炉心"), "ch2 帧应继承 ch1 获知"
    # 未在场者仍不知
    fr_other = project_frame(w, "role:路人", 2)
    assert not fr_other.knows("fact:炉心"), "未见证者 ch2 仍不知"


# ===== ConStory +3 / 卷信号 / 注入 =====

def test_find_calendar_month_regression():
    from scribe3.critique import find_calendar_month_regression
    assert find_calendar_month_regression("正月开笔,到了三月才完。") == []
    bad = find_calendar_month_regression("腊月里封炉,二月又开春。")
    assert bad and bad[0]["kind"] == "calendar_month_regression"


def test_find_pressure_adjacent_jumps():
    from scribe3.critique import find_pressure_adjacent_jumps
    jumps = find_pressure_adjacent_jumps(
        [{"seq": 1, "pressure": 1}, {"seq": 2, "pressure": 5}], threshold=3)
    assert len(jumps) == 1


def test_find_memory_denial_hits():
    from scribe3.critique import find_memory_denial_hits
    assert find_memory_denial_hits("他不知道炉心真名。", ["炉心真名"])
    assert find_memory_denial_hits("他不知道炉心真名。", []) == []


def test_volume_review_signals_overdue_and_motif():
    chapters = [{"seq": 1, "volume": "v1"}, {"seq": 2, "volume": "v1"}]
    seqs = volume_chapter_seqs(chapters, volume_id="v1")
    assert seqs == [1, 2]
    overdue = overdue_promises_in_range(
        [{"text": "灰契", "setup_chapter": 1, "status": "open", "resolve_by": 1}],
        up_to=10, seqs=seqs, slack=0)
    assert len(overdue) == 1
    unused = motifs_without_echo(
        [{"id": "m:铜", "name": "铜"}], {"m:铜": []}, seqs=seqs)
    assert unused and unused[0]["signal"] == "no_echo"


def test_anti_slop_inject_floor_on_vs_off(monkeypatch):
    from scribe3.api.services import write_assemble as WA
    monkeypatch.setenv("SCRIBE3_INJECT_FLOOR", "1")
    on = WA._anti_slop_floor_block()
    monkeypatch.setenv("SCRIBE3_INJECT_FLOOR", "0")
    off = WA._anti_slop_floor_block()
    assert on and off == "" and on != off
