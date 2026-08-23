"""Stages 2–5：持久化/锁/完整性/注入/收件箱/健康度等打真实入口。"""
from __future__ import annotations

import inspect
from pathlib import Path

from scribe3.alerts import emit_alert
from scribe3.chapter_health import aggregate_chapter_health
from scribe3.context_snapshot import snapshot_clear, snapshot_get_or_set
from scribe3.degrade_state import degrade_chapter_state
from scribe3.embed_health import embedding_health
from scribe3.inbox_dismiss import dismiss_inbox_item, filter_inbox, is_dismissed
from scribe3.ingest import grep_back_verify
from scribe3.ingest_integrity import ingest_needs_replay, run_ingest_apply
from scribe3.pending_proposals import get_pending_proposal, save_pending_proposal


ROOT = Path(__file__).resolve().parents[2]


def test_dir_01_pending_proposal_survives_get():
    class St:
        pass
    st = St()
    rec = save_pending_proposal(st, {"ops": [{"tool": "s3_add_item"}]})
    assert rec["id"]
    got = get_pending_proposal(st, rec["id"])
    assert got and got["id"] == rec["id"]
    assert got["ops"]


def test_ded_03_ingest_integrity_marks_replay():
    def boom():
        raise RuntimeError("midway")
    out = run_ingest_apply(boom, 4)
    assert out["ok"] is False
    assert out["needs_replay"] is True
    assert ingest_needs_replay(out) is True
    assert ingest_needs_replay({"ok": True}) is False


def test_ded_07_snapshot_same_key_same_object():
    snapshot_clear()
    n = {"calls": 0}

    def factory():
        n["calls"] += 1
        return {"x": n["calls"]}

    a = snapshot_get_or_set("k", factory)
    b = snapshot_get_or_set("k", factory)
    assert a is b
    assert n["calls"] == 1


def test_inbox_dismiss_filters_items():
    st = object()
    dismiss_inbox_item(st, "needs_human:3")
    assert is_dismissed(st, "needs_human:3")
    items = filter_inbox(st, [{"id": "needs_human:3"}, {"id": "lesson:1"}])
    assert [i["id"] for i in items] == ["lesson:1"]


def test_chapter_health_aggregates_three_systems():
    h = aggregate_chapter_health(
        playbook={"ok": True, "status": "pass"},
        post_check={"verdict": "advisory"},
        review={"coverage": 0.8},
    )
    assert h["playbook_status"]
    assert h["post_check_verdict"] == "advisory"
    assert h["review_coverage"] == 0.8
    assert h["overall_grade"] == "yellow"


def test_ded_08_degraded_state_for_next_chapter():
    d = degrade_chapter_state(3, prev={"place": "华山"}, reason="extract_fail")
    assert d["ok"] is True
    assert d["degraded"] is True
    assert d["prev_state"]["place"] == "华山"


def test_mat_02_motif_unverified_dropped():
    out = grep_back_verify(
        {"motif": [{"motif": "灯与债", "evidence": "炉火在夜里还亮着"}]},
        "正文里没有那几个字。",
    )
    assert out["delta"]["motif"] == []
    assert out["dropped"] or out["annotated"]
    ok = grep_back_verify(
        {"motif": [{"motif": "灯与债", "evidence": "灯还亮着"}]},
        "今夜灯还亮着，债没有散。",
    )
    assert ok["delta"]["motif"]


def test_sys_05_alert_without_webhook_does_not_crash():
    r = emit_alert("daily_cap", "日帽触顶")
    assert r["ok"] is True
    assert r["delivered"] is False


def test_sys_06_embedding_health_shape():
    h = embedding_health()
    assert "ok" in h


def test_frontend_stage2_5_wires():
    api = (ROOT / "scribe3/web/src/api.js").read_text(encoding="utf-8")
    assert "patchEventCausalRoot" in api
    assert "_reconnect" in api
    assert "30000" in api
    hub = (ROOT / "scribe3/web/src/system/SystemHub.jsx").read_text(encoding="utf-8")
    assert "暂无技法" in hub and "暂无招式" in hub
    tl = (ROOT / "scribe3/web/src/views/TimelineView.jsx").read_text(encoding="utf-8")
    assert "CausalRootEditor" in tl
    assert "patchEventCausalRoot" in tl
    write = inspect.getsource(__import__("scribe3.api.routers.director", fromlist=["orch_apply_proposal_ep"]).orch_apply_proposal_ep)
    assert "save_pending_proposal" in write
    inbox = inspect.getsource(__import__("scribe3.api.routers.pilot_inbox", fromlist=["dismiss_inbox_ep"]).dismiss_inbox_ep)
    assert "dismiss_inbox_item" in inbox
    step = inspect.getsource(__import__("scribe3.api.routers.pilot_inbox", fromlist=["pilot_step"]).pilot_step)
    assert "acquire_chapter_lock" in step
    assert "journey_precheck" in step


def test_man_02_save_chapter_conflict_signature():
    from scribe3.store.chapters import ChaptersMixin
    src = inspect.getsource(ChaptersMixin.save_chapter)
    assert "expected_version" in src
    assert "chapter_conflict" in src
    # 004_manuscript：chapter.updated，SCHEMAFULL 没有 updated_at
    assert "updated=time::now()" in src
    assert "updated_at=" not in src
    # 空标题不得覆盖已有章名
    assert "existing.get(\"title\")" in src or "existing.get('title')" in src


def test_ded_04_undo_helper_exists():
    from scribe3.canon_loop import _undo_applied, apply_change_pack
    src = inspect.getsource(apply_change_pack)
    assert "_undo_applied" in src
    class St:
        def delete_faction(self, name):
            self.gone = name
    st = St()
    assert _undo_applied(st, {"module": "faction", "name": "x", "op": "add"}) is True


def test_t13_04_shadow_equal_negative():
    from scribe3.prompt_renderer import shadow_equal
    a = "第一段。\n第二段。"
    assert shadow_equal(a, a) is True
    assert shadow_equal(a, "第一段。") is False
    assert shadow_equal(a, "第二段。\n第一段。") is False


def test_motif_overheat_advisory():
    from scribe3.motif_heat import motif_overheat_advisory
    hot = motif_overheat_advisory([{"motif": "灯"}] * 5)
    assert hot and hot[0]["kind"] == "motif_overheat"


def test_echo_terms_in_extract_prompt():
    from scribe3.critique.rules.prompts import build_knowledge_extract_prompt
    p = build_knowledge_extract_prompt(
        "正文", motif_names=["灯与债"], motif_echoes={"灯与债": ["炉火"]},
    )
    assert "炉火" in p
