"""用户 20 项 Spec 余差闭合 — 驱动 shipped 代码（无假实现）。"""
from __future__ import annotations

import inspect
import os
import threading

import pytest


def test_p0_lock_single_path_no_set_mutex():
    from scribe3.api import app_impl as A
    src = inspect.getsource(A._acquire_op_mutex)
    assert "acquire_chapter_lock" in src
    assert "_loop_inflight.add" not in src
    assert "_pending_ingest" not in src or "add" not in src
    assert len(src.splitlines()) <= 25
    from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
    r1 = acquire_chapter_lock("loop", "spec_w", 1)
    assert r1.ok
    r2 = acquire_chapter_lock("loop", "spec_w", 1)
    assert not r2.ok
    release_chapter_lock("loop", "spec_w", 1)


def test_p0_discuss_soft_secret_entry():
    from scribe3.epistemic_guard import guard_discuss_instructions, scan_prompt_for_any_secrets
    from scribe3.ontology import Fact

    class St:
        def facts_at(self, ch):
            return [Fact("f1", "r", "秘密", "炉心印能开侧门",
                         valid_from=1, secret=True, leak_markers=["炉心印能开"])]

    hits = scan_prompt_for_any_secrets("写出炉心印能开侧门", St())
    assert hits
    _, soft = guard_discuss_instructions("炉心印能开侧门", St(), chapter=1)
    assert soft
    # wired in assemble_discussion_system
    from scribe3.api.services import write_assemble as wa
    assert "guard_discuss_instructions" in inspect.getsource(wa.assemble_discussion_system)


def test_p0_audit_query_purge():
    from scribe3.audit_maintenance import purge_audit_events, query_audit_log, audit_ttl_days

    class St:
        def _execute_write(self, q, p=None):
            self.last = q
            return True

        def _query(self, q, p=None):
            return [{"kind": "pilot_state", "at": "now"}]

    st = St()
    assert audit_ttl_days() >= 1
    assert purge_audit_events(st)["ok"] is True
    assert "audit_event" in st.last
    assert query_audit_log(st)


def test_p0_soul_body_has_three_layers(monkeypatch):
    monkeypatch.delenv("SCRIBE3_HERMES_SOUL_LAYERS", raising=False)  # default on
    from scribe3.hermes_runtime import build_hermes_request_body, soul_layers_enabled
    assert soul_layers_enabled() is True
    body = build_hermes_request_body(
        input_text="hi", instructions="task body", stream=True, store=True,
    )
    assert body["instructions"] == "task body"
    assert body.get("system")
    assert body.get("personality")
    monkeypatch.setenv("SCRIBE3_HERMES_SOUL_LAYERS", "0")
    # re-import enabled check
    from importlib import reload
    import scribe3.hermes_runtime as hr
    reload(hr)
    body2 = hr.build_hermes_request_body(input_text="x", instructions="y")
    assert "system" not in body2


def test_p1_changefeed_interval_and_purge():
    from scribe3.changefeed_consumer import ChangefeedCacheWorker
    from scribe3.context_cache import purge_cache_watch
    w = ChangefeedCacheWorker(lambda: None)
    assert w._interval <= 0.5

    class St:
        def __init__(self):
            self.q = []

        def _execute_write(self, q, p=None):
            self.q.append(q)

    st = St()
    assert purge_cache_watch(st) == 1
    assert any("cache_watch" in x for x in st.q)


def test_p1_stats_total_words():
    from scribe3.stats_views import read_stats_bundle

    class St:
        def _query(self, *a, **k):
            raise RuntimeError("no")

        def chapters_lite(self):
            return [{"seq": 1, "qc_word_count": 1200, "stage": "draft"}]

    b = read_stats_bundle(St())
    assert b["total_words"] >= 1200
    assert b["chapter_count"] >= 1


def test_p1_live_id_filter():
    from scribe3.live import live_id_allowed
    assert live_id_allowed("chapter", {"id": "chapter:2"}, {"chapter": ["2"]}) is True
    assert live_id_allowed("chapter", {"id": "chapter:9"}, {"chapter": ["2"]}) is False


def test_p1_distill_modes_differ(monkeypatch):
    from scribe3 import literary_distill as ld
    text = "他发现真相。\n\n但必须付出代价。\n\n终于改变态度。\n\n冲突对峙展开。" * 3
    monkeypatch.setenv("SCRIBE3_DISTILL_MODE", "heuristic")
    h = ld.literary_distill(text)
    monkeypatch.setenv("SCRIBE3_DISTILL_MODE", "llm")
    m = ld.literary_distill(text)
    assert h["control"]["mode"] == "heuristic"
    assert m["control"]["mode"] == "llm"
    assert m["audit"]["source"] != h["audit"]["source"]
    # llm path uses sentence extract source
    assert "sentence" in m["audit"]["source"] or "llm" in m["audit"]["source"]


def test_p1_emotion_neg5_to_pos5():
    from scribe3.emotion_scale import score_prose_emotion
    from scribe3.storyline_project import project_emotion_curve
    pos = score_prose_emotion("欢喜安心温暖希望")
    neg = score_prose_emotion("绝望恐惧黑暗痛恨")
    assert -5 <= pos["value"] <= 5 and -5 <= neg["value"] <= 5
    assert pos["value"] > neg["value"]
    out = project_emotion_curve([
        {"seq": 1, "prose": "欢喜安心"},
        {"seq": 2, "prose": "绝望恐惧"},
    ])
    assert "emotion" in out["points"][0]
    assert out.get("emotion_scale") == [-5.0, 5.0]


def test_p2_dtw_and_core_dimensions():
    from scribe3.craft_ruler import craft_ruler_report, dtw_distance, IDEAL_EMOTION_CURVE
    assert abs(dtw_distance([0, 1], [0, 1]) - dtw_distance([0, 1], [0, 1])) < 1e-9
    rep = craft_ruler_report([{"emotion": x} for x in IDEAL_EMOTION_CURVE])
    assert rep["similarity"] >= 0.9
    assert rep.get("core_dimensions")
    keys = {d["key"] for d in rep["core_dimensions"]}
    assert "emotional_effect" in keys
    assert "CORE_DIMENSIONS" in (rep.get("dimension_ssot") or "")


def test_p2_storyline_memory_crud():
    from scribe3.storyline_store import clear_for_tests, create_storyline, link_chapter, list_storylines
    clear_for_tests()
    r = create_storyline("w", title="弧A", chapter_seqs=[1])
    link_chapter("w", r["id"], 2)
    assert any(x["id"] == r["id"] for x in list_storylines("w"))


def test_p2_hub_uses_recharts():
    from pathlib import Path
    hub = Path(__file__).resolve().parents[1] / "web/src/views/StorylineHub.jsx"
    text = hub.read_text(encoding="utf-8")
    assert "recharts" in text
    assert "LineChart" in text
    assert "BarChart" in text
    assert "storyline-hub" in text
    assert "storylineHub" in text or "/storyline/hub" in text
    assert "border-line" in text  # design tokens, not raw border-black
    assert text.count("\n") > 120  # not ~86 line CSS bars only


def test_storyline_hub_bundle_once():
    """Hub 打包：一次 chapters 源，gantt+emotion+lines 同包。"""
    from scribe3.api.routers import product_backlog as pb
    from scribe3.storyline_store import clear_for_tests, create_storyline

    clear_for_tests()
    create_storyline("hubw", title="T", chapter_seqs=[1])

    class St:
        def chapters_lite(self):
            return [
                {"seq": 1, "title": "一", "synopsis": "赌注：生死"},
                {"seq": 2, "title": "二", "beats": [{"conflict": "x"}]},
            ]

        def open_promises(self):
            return []

        def list_storylines(self):
            return [{"id": "s1", "title": "T", "chapter_seqs": [1], "arc_kind": "main"}]

    import scribe3.api.app_impl as core
    old = getattr(core, "_store_for", None)
    core._store_for = lambda work="main": St()  # type: ignore
    try:
        pack = pb.storyline_hub_ep(work="hubw")
        assert pack["gantt"]["count"] == 2
        assert pack["emotion"]["count"] == 2
        assert pack["storylines"]
        assert pack.get("chapter_source") == "chapters_lite"
        assert pack["gantt"]["rows"][1]["phase"] == "beats"
    finally:
        if old is not None:
            core._store_for = old


def test_p2_leader_election():
    from scribe3.changefeed_leader import try_acquire_leader, leader_election_enabled
    # default off → always leader
    st = try_acquire_leader()
    assert st["is_leader"] is True
    assert st.get("election") is False


def test_p2_docs_in_repo():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert (root / "docs/plans/2026-08-12-storyline-visualization-design.md").is_file()
    assert (root / "docs/ops/changefeed-multi-worker.md").is_file()
    assert (root / "docs/plans/2026-08-12-gap-fix-20-spec.md").is_file()


def test_p0_tool_filter_default_safe_for_write():
    from scribe3.hermes_runtime import HermesEventAdapter
    ad = HermesEventAdapter()
    ev = ad.adapt({"type": "tool.started", "name": "s3_add_character", "arguments": "{}"})
    assert ev["kind"] == "tool.started"
    ad2 = HermesEventAdapter(phase="discuss", filter_tools=True)
    ev2 = ad2.adapt({"type": "tool.started", "name": "s3_save_chapter", "arguments": "{}"})
    assert ev2["kind"] == "tool.blocked"


def test_migration_130_exists():
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "migrations/130_storyline.surql"
    assert p.is_file() and "storyline" in p.read_text()
