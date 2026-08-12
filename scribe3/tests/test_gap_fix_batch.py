"""GAP-1…20 核心可测单元（驱动真实 shipped 模块，无假实现）。"""
from __future__ import annotations

import os
import threading

import pytest


# ── GAP-1 锁 ──────────────────────────────────────────────
def test_gap1_chapter_lock_busy_on_reentry():
    from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
    r1 = acquire_chapter_lock("loop", "wt_gap", 1)
    assert r1.ok
    r2 = acquire_chapter_lock("loop", "wt_gap", 1)
    assert not r2.ok and r2.status == "busy"
    release_chapter_lock("loop", "wt_gap", 1)
    r3 = acquire_chapter_lock("loop", "wt_gap", 1)
    assert r3.ok
    release_chapter_lock("loop", "wt_gap", 1)


def test_gap1_enqueue_then_bg_ingest_runs_body(monkeypatch):
    """enqueue 不得持锁导致 _bg_ingest 永远 busy（skeptic 硬伤）。"""
    from scribe3.api.services import ingest_bg as ib
    from scribe3.novel_first_surface import is_chapter_op_busy
    from scribe3.chapter_lock import release_chapter_lock

    ran: list[tuple] = []

    class FakeStore:
        def __init__(self, *a, **k):
            pass

        def close(self):
            pass

        def _execute_write(self, *a, **k):
            return True

        def refresh_chapter_cache(self, *a, **k):
            pass

        def get_chapter(self, *a, **k):
            return {}

    def fake_ingest(st, seq, complete, **kw):
        ran.append(("ingest", int(seq)))
        return {"ok": True, "prose_fp": "fp1"}

    class Acq:
        ok = True
        owner = "o1"

    monkeypatch.setattr(ib, "SurrealStore", FakeStore, raising=False)
    # free name in _bg_ingest 解析自模块全局
    import scribe3.api.services.ingest_bg as ibmod
    ibmod.SurrealStore = FakeStore  # type: ignore

    import scribe3.ingest as ing
    monkeypatch.setattr(ing, "ingest_chapter", fake_ingest)

    import scribe3.ingest_lease as il
    monkeypatch.setattr(il, "try_acquire_ingest_lease", lambda *a, **k: Acq())
    monkeypatch.setattr(il, "release_ingest_lease", lambda *a, **k: None)
    monkeypatch.setattr(il, "combined_backend", lambda st: object())
    monkeypatch.setattr(il, "new_owner", lambda: "owner1")

    monkeypatch.setattr(ib, "mark_chapter_ingest_status", lambda *a, **k: None)
    monkeypatch.setattr(ib, "_refresh_scorecard_after_ingest", lambda *a, **k: None)

    # 确保无残留锁
    try:
        release_chapter_lock("ingest", "wt_enq", 42)
    except Exception:
        pass

    tasks: list = []

    class BG:
        def add_task(self, fn, *a, **k):
            tasks.append((fn, a))

    ok = ib._enqueue_ingest_raw(BG(), "wt_enq", 42)
    assert ok is True
    assert tasks, "应调度 _bg_ingest"
    # enqueue 后不得仍持有 ingest 锁
    assert not is_chapter_op_busy("ingest", "wt_enq", 42)

    fn, args = tasks[0]
    fn(*args)
    assert ran == [("ingest", 42)], f"后台 ingest 体未执行: {ran}"
    assert not is_chapter_op_busy("ingest", "wt_enq", 42)


def test_gap1_acquire_op_mutex_uses_chapter_lock_only():
    """_acquire_op_mutex 不再维护 _loop_inflight 集合。"""
    from scribe3.api import app_impl as A
    import inspect
    src = inspect.getsource(A._acquire_op_mutex)
    assert "acquire_chapter_lock" in src
    assert "_loop_inflight.add" not in src
    assert "_chapter_repair_inflight" not in src
    assert len(src.splitlines()) <= 30
    # 遗留集合不得再被互斥路径读写
    assert not hasattr(A, "_loop_inflight_lock")
    assert not hasattr(A, "_chapter_repair_inflight")


def test_gap1_concurrent_mutex_one_winner():
    from scribe3.api import app_impl as A
    from fastapi import HTTPException

    results = []

    def worker():
        try:
            A._acquire_op_mutex("w_conc", 9, "loop", detail="busy")
            results.append("ok")
        except HTTPException as e:
            results.append(e.status_code)
        except Exception as e:
            results.append(type(e).__name__)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start(); t2.start()
    t1.join(); t2.join()
    assert results.count("ok") == 1
    assert 409 in results
    A._release_op_mutex("w_conc", 9, "loop")


# ── GAP-6 cache_watch ─────────────────────────────────────
def test_gap6_purge_cache_watch_calls_store():
    from scribe3.context_cache import purge_cache_watch

    class St:
        def __init__(self):
            self.writes = []

        def _execute_write(self, q, p=None):
            self.writes.append(q)
            return True

    st = St()
    n = purge_cache_watch(st, max_age_seconds=3600)
    assert n == 1
    assert any("cache_watch" in w for w in st.writes)


# ── GAP-3 audit ───────────────────────────────────────────
def test_gap3_purge_and_query_audit():
    from scribe3.audit_maintenance import purge_audit_events, query_audit_log, audit_ttl_days

    class St:
        def __init__(self):
            self.qs = []

        def _execute_write(self, q, p=None):
            self.qs.append(("w", q))
            return True

        def _query(self, q, p=None):
            self.qs.append(("q", q))
            return [{"kind": "pilot_state", "source_table": "pilot_state"}]

    st = St()
    assert audit_ttl_days() >= 1
    out = purge_audit_events(st, days=30)
    assert out["ok"] is True
    rows = query_audit_log(st, limit=10)
    assert rows and rows[0]["kind"] == "pilot_state"


# ── GAP-5 stats ───────────────────────────────────────────
def test_gap5_stats_bundle_fallback():
    from scribe3.stats_views import read_stats_bundle

    class St:
        def _query(self, q, p=None):
            raise RuntimeError("no view")

        def chapters_lite(self):
            return [
                {"seq": 1, "stage": "draft", "prose": "字" * 100},
                {"seq": 2, "stage": "outline", "qc_word_count": 50},
            ]

    b = read_stats_bundle(St())
    assert b["chapter_count"] >= 2
    assert b["total_words"] >= 50
    assert any(x.get("stage") for x in b["phase_distribution"])


# ── GAP-9 epistemic soft ──────────────────────────────────
def test_gap9_scan_any_secrets_no_focalizer(monkeypatch):
    from scribe3.epistemic_guard import (
        scan_prompt_for_any_secrets,
        scan_prompt_for_off_frame_secrets,
        guard_discuss_instructions,
    )
    from scribe3.ontology import Fact

    class St:
        def facts_at(self, ch):
            return [
                Fact("fact:sec", "role:x", "秘密", "炉心印能开侧门",
                     valid_from=1, secret=True, leak_markers=["炉心印能开"]),
            ]

    st = St()
    # hard path: no focalizer → empty
    assert scan_prompt_for_off_frame_secrets("炉心印能开侧门", st, focalizer="") == []
    # soft any path
    hits = scan_prompt_for_any_secrets("正文含炉心印能开侧门", st, chapter=1)
    assert hits and hits[0].get("soft")
    _, soft = guard_discuss_instructions("炉心印能开侧门出现", st, chapter=1)
    assert soft


# ── GAP-2 interval ────────────────────────────────────────
def test_gap2_changefeed_default_interval_le_1s():
    from scribe3.changefeed_consumer import ChangefeedCacheWorker
    w = ChangefeedCacheWorker(lambda: None, work="main")
    assert w._interval <= 1.0
    assert w._interval == 0.2 or w._interval > 0


# ── GAP-10 distill modes ──────────────────────────────────
def test_gap10_distill_modes(monkeypatch):
    from scribe3 import literary_distill as ld
    text = "第一段代价很大。\n\n第二段终于改变态度。\n\n第三段冲突对峙。"
    monkeypatch.setenv("SCRIBE3_DISTILL_MODE", "heuristic")
    h = ld.literary_distill(text)
    assert h["mode"] == "heuristic" or h["control"]["mode"] == "heuristic"
    assert h["bullets"]
    monkeypatch.setenv("SCRIBE3_DISTILL_MODE", "llm")
    m = ld.literary_distill(text)
    assert m.get("mode") == "llm" or m["control"]["mode"] == "llm"
    monkeypatch.setenv("SCRIBE3_DISTILL_MODE", "token")
    t = ld.literary_distill(text * 5)
    assert t.get("mode") == "token" or t["control"]["mode"] == "token"
    assert "compressed_preview" in t or t["bullets"]


# ── GAP-14/18 emotion ─────────────────────────────────────
def test_gap14_emotion_scale_range():
    from scribe3.emotion_scale import score_prose_emotion, tension_01_to_signed
    pos = score_prose_emotion("他终于安心欢喜地笑了，温暖希望")
    neg = score_prose_emotion("绝望恐惧黑暗与恨，痛彻心扉")
    assert -5 <= pos["value"] <= 5
    assert -5 <= neg["value"] <= 5
    assert pos["value"] > neg["value"]
    assert tension_01_to_signed(0.5) == 0.0
    assert tension_01_to_signed(1.0) == 5.0


# ── GAP-15 craft ruler ────────────────────────────────────
def test_gap15_dtw_symmetric_and_ideal():
    from scribe3.craft_ruler import dtw_distance, align_to_ideal, IDEAL_EMOTION_CURVE, craft_ruler_report
    a = [0.0, 1.0, 2.0, 1.0]
    b = [0.0, 1.1, 1.9, 1.0]
    d1 = dtw_distance(a, b)
    d2 = dtw_distance(b, a)
    assert abs(d1 - d2) < 1e-6
    al = align_to_ideal(list(IDEAL_EMOTION_CURVE))
    assert al["similarity"] >= 0.9
    rep = craft_ruler_report([{"emotion": x} for x in IDEAL_EMOTION_CURVE])
    assert "dtw_distance" in rep


# ── GAP-16 storyline store ────────────────────────────────
def test_gap16_storyline_crud_and_link():
    from scribe3.storyline_store import (
        clear_for_tests, create_storyline, list_storylines, link_chapter, update_storyline,
    )
    clear_for_tests()
    row = create_storyline("w1", title="主弧", chapter_seqs=[1])
    assert row["id"].startswith("sl_")
    assert list_storylines("w1")
    link_chapter("w1", row["id"], 3)
    u = update_storyline("w1", row["id"], notes="x")
    assert 3 in u["chapter_seqs"] and u["notes"] == "x"


# ── GAP-11 tool filter ────────────────────────────────────
def test_gap11_filter_blocks_disallowed():
    from scribe3.run_tool_filter import filter_tool_calls
    calls = [
        {"name": "s3_list_chapters"},
        {"name": "s3_save_chapter"},
        {"name": "mcp__scribe3__s3_get_chapter"},
    ]
    out = filter_tool_calls(calls, allow=frozenset({"s3_list_chapters", "s3_get_chapter"}))
    assert out["enforced"]
    assert len(out["blocked"]) >= 1
    names = [c.get("name") for c in out["kept"]]
    assert "s3_list_chapters" in names


# ── GAP-13 approval audit ─────────────────────────────────
def test_gap13_commit_records_audit():
    from scribe3.approval_audit import clear_for_tests, list_approval_events
    from scribe3.write_commit import commit_if_approved
    clear_for_tests()
    r = commit_if_approved("s3_add_character", False, lambda: {"ok": True})
    assert r["status"] == "declined"
    ev = list_approval_events(limit=5)
    assert any(e.get("status") == "declined" for e in ev)


# ── GAP-7 soul layers body ────────────────────────────────
def test_gap7_soul_layers_in_body(monkeypatch):
    monkeypatch.setenv("SCRIBE3_HERMES_SOUL_LAYERS", "1")
    from importlib import reload
    import scribe3.hermes_runtime as hr
    reload(hr)
    body = hr.build_hermes_request_body(
        input_text="hi", instructions="task", stream=True, store=True,
    )
    assert body.get("system") and body.get("personality")
    assert body.get("instructions") == "task"


# ── GAP-19 emotion curve craft ────────────────────────────
def test_gap19_emotion_curve_includes_align():
    from scribe3.storyline_project import project_emotion_curve
    chapters = [
        {"seq": 1, "prose": "安心欢喜温暖"},
        {"seq": 2, "prose": "绝望恐惧黑暗"},
        {"seq": 3, "prose": "终于改变希望"},
    ]
    out = project_emotion_curve(chapters)
    assert out["points"]
    assert "emotion" in out["points"][0]
    assert -5 <= out["points"][0]["emotion"] <= 5
    ca = out.get("craft_align")
    assert isinstance(ca, dict), "craft_align must be present"
    assert "dtw_distance" in ca and "similarity" in ca
    assert 0.0 <= float(ca["similarity"]) <= 1.0


# ── GAP-4 live id filter behavior ─────────────────────────
def test_gap4_live_id_allowed_filters():
    from scribe3.live import live_id_allowed
    # no filter → all allowed
    assert live_id_allowed("chapter", {"id": "chapter:1"}, None) is True
    # filter match
    ids = {"chapter": ["chapter:3", "3"]}
    assert live_id_allowed("chapter", {"id": "chapter:3"}, ids) is True
    assert live_id_allowed("chapter", {"id": "chapter:9"}, ids) is False
    # other table unfiltered
    assert live_id_allowed("promise", {"id": "promise:x"}, ids) is True


def test_gap11_adapter_blocks_write_tool_on_discuss():
    """生产路径：HermesEventAdapter 对 discuss 阶段拦截写工具。"""
    from scribe3.hermes_runtime import HermesEventAdapter
    ad = HermesEventAdapter(phase="discuss", filter_tools=True)
    ev = ad.adapt({
        "type": "tool.started",
        "name": "s3_save_chapter",
        "arguments": "{}",
        "run_id": "r1",
    })
    assert ev["kind"] == "tool.blocked"
    assert ev["name"] == "s3_save_chapter" or "save" in str(ev.get("name"))
    ok = ad.adapt({
        "type": "tool.started",
        "name": "s3_list_chapters",
        "arguments": "{}",
    })
    assert ok["kind"] == "tool.started"


def test_gap11_default_adapter_allows_write_tools():
    """默认 adapter（write_stream/ai_run）不得把 s3_add_character 标成 tool.blocked。"""
    from scribe3.hermes_runtime import HermesEventAdapter
    ad = HermesEventAdapter()  # 默认 filter_tools=False
    for name in ("s3_add_character", "s3_save_chapter", "s3_add_fact"):
        ev = ad.adapt({
            "type": "tool.started",
            "name": name,
            "arguments": "{}",
            "run_id": "write1",
        })
        assert ev["kind"] == "tool.started", f"{name} blocked by default adapter: {ev}"
        assert "blocked" not in ev.get("kind", "")


def test_gap11_filter_tools_true_without_phase_does_not_enforce():
    """filter_tools=True 但 phase 空 → 不 enforce（防误配）。"""
    from scribe3.hermes_runtime import HermesEventAdapter
    ad = HermesEventAdapter(phase=None, filter_tools=True)
    ev = ad.adapt({
        "type": "tool.started",
        "name": "s3_add_character",
        "arguments": "{}",
    })
    assert ev["kind"] == "tool.started"


def test_gap11_write_stream_constructs_safe_adapter():
    """write_stream 源码须显式 filter_tools=False。"""
    import inspect
    from scribe3.api.services import write_stream as ws
    src = inspect.getsource(ws)
    assert "filter_tools=False" in src
    assert "HermesEventAdapter" in src


def test_gap12_chat_stream_guards_hermes(monkeypatch):
    """chat_stream 对非 Hermes complete 可观测阻断。"""
    from scribe3.llm_path_guard import assert_llm_path_ok

    def openai_like(p, **kw):
        return p

    openai_like.__module__ = "openai.api"
    r = assert_llm_path_ok(openai_like, path="discuss")
    assert r["bypass"] is True
    # hermes path ok
    from scribe3.llm import hermes_complete_stream
    r2 = assert_llm_path_ok(hermes_complete_stream, path="discuss")
    assert r2["bypass"] is False


def test_gap13_canon_apply_records_audit():
    from scribe3.approval_audit import clear_for_tests, list_approval_events
    from scribe3.canon_loop import apply_change_pack, ChangePack, ChangeItem
    clear_for_tests()
    # empty pack still records started/finished
    pack = {
        "id": "cp_test",
        "work": "main",
        "source": "discussion",
        "items": [],
        "status": "proposed",
    }
    apply_change_pack(pack, approved_item_ids=[], store=None)
    ev = list_approval_events(limit=10)
    assert any(e.get("chain") == "canon" for e in ev)


# ── migrations exist ──────────────────────────────────────
def test_gap_migrations_exist():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "migrations"
    assert (root / "128_audit_ttl_index.surql").is_file()
    assert (root / "129_extended_stats_views.surql").is_file()


def test_gap20_docs_exist():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert (root / "docs/plans/2026-08-12-gap-fix-20-spec.md").is_file()
    assert (root / "docs/plans/2026-08-12-storyline-and-hermes-decisions.md").is_file()


def test_gap12_hermes_path_guard():
    from scribe3.llm_path_guard import assert_llm_path_ok, is_hermes_complete_fn

    def hermes_complete(p):
        return p

    hermes_complete.__module__ = "scribe3.hermes_client"
    assert is_hermes_complete_fn(hermes_complete)
    r = assert_llm_path_ok(hermes_complete, path="discuss")
    assert r["ok"] and not r["bypass"]

    def openai_direct(p):
        return p

    openai_direct.__module__ = "openai"
    r2 = assert_llm_path_ok(openai_direct, path="discuss")
    assert r2["bypass"] is True


def test_gap8_prefetch_injects_prefs(monkeypatch):
    monkeypatch.setenv("SCRIBE3_API_BASE", "http://example.invalid")
    monkeypatch.setenv("SCRIBE3_PREFETCH_PREFS_TEXT", "喜欢短句")
    import importlib.util
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "hermes_plugins" / "scribe3-memory" / "__init__.py"
    spec = importlib.util.spec_from_file_location("scribe3_mem_plug", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prov = mod.Scribe3MemoryProvider()
    prov.initialize("scribe3|work:main|thread:t1")

    class Api:
        def prefetch(self, **kw):
            return {"context": "base-ctx"}

    prov.api = Api()
    out = prov.prefetch("q", session_id="scribe3|work:main|thread:t1")
    assert "author_preferences" in out and "喜欢短句" in out and "base-ctx" in out
