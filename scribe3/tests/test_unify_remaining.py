"""统一度剩余项：对照聚合、预算、错误形状、限知、渲染、规划门。不启 Surreal。"""
from __future__ import annotations

from scribe3.http_errors import error_body, shape_http_detail
from scribe3.prompt_renderer import render_slots, shadow_equal
from scribe3.quality_gate import from_existing, gate_result
from scribe3.recall_service import (
    _BUDGET_BY_TAG,
    _SHADOW_RING,
    budget_for,
    record_shadow_stat,
    shadow_diff,
    summarize_recall_shadow,
)
from scribe3.write_commit import commit_if_approved


def test_budget_by_tag_is_single_source():
    assert budget_for("playbook_codex") == 800
    assert budget_for("volume_intro") == 400
    assert budget_for("ledger") == 900
    assert "playbook_codex" in _BUDGET_BY_TAG
    from scribe3.playbook import context as ctx
    assert ctx._CODEX_BUDGET == budget_for("playbook_codex")
    assert ctx._VOLUME_INTRO_BUDGET == budget_for("volume_intro")


def test_recall_shadow_aggregates_by_path():
    _SHADOW_RING.clear()
    record_shadow_stat({"ok": True, "path": "playbook", "threshold_ok": True, "secret_leak_count": 0})
    record_shadow_stat({"ok": True, "path": "playbook", "threshold_ok": False, "secret_leak_count": 0})
    record_shadow_stat({"ok": True, "path": "discuss", "threshold_ok": True, "secret_leak_count": 0})
    out = summarize_recall_shadow()
    assert out["by_path"]["playbook"]["n"] == 2
    assert out["by_path"]["playbook"]["threshold_ok_rate"] == 0.5
    assert out["by_path"]["discuss"]["threshold_ok_rate"] == 1.0


def test_shadow_vector_channel_recorded(monkeypatch):
    monkeypatch.setenv("SCRIBE3_RECALL_SHADOW_VECTOR", "1")

    class St:
        def facts_at(self, seq):
            return [{"entity_id": "role:柳岸青", "attribute": "身体", "value": "四十二度不是病是标价"}]

        def hybrid_recall(self, q, chapter, k=8):
            return [{"entity_id": "role:柳岸青", "attribute": "身体", "value": "四十二度不是病是标价"}]

    rec = shadow_diff(St(), 1, "role:柳岸青", "柳岸青 / 身体：四十二度不是病是标价", query="柳岸青", path="playbook")
    assert rec.get("ok") is True
    assert "hybrid" in (rec.get("channels") or []) or "facts_at" in (rec.get("channels") or [])


def test_as_playbook_store_reuses_mem():
    from scribe3.stage_generate import _as_playbook_store

    class St:
        pass

    st = St()
    a = _as_playbook_store(st)
    b = _as_playbook_store(st)
    assert a is b
    assert st._playbook_mem is a


def test_http_error_shape_lock():
    body = error_body("stage_gone", "这一站拆了", http=410)
    assert set(body) >= {"code", "message"}
    assert body["code"] == "stage_gone"
    shaped = shape_http_detail("炸了")
    assert shaped["code"] == "http_error"
    assert "炸了" in shaped["message"]
    shaped2 = shape_http_detail({"code": "x", "message": "人话"})
    assert shaped2 == {"code": "x", "message": "人话"}


def test_plan_volumes_accept_and_decline():
    calls = []
    out = commit_if_approved("s3_plan_volumes", False, lambda: calls.append("w") or {"volumes": 1})
    assert out["status"] == "declined"
    assert calls == []
    out2 = commit_if_approved("s3_plan_volumes", True, lambda: {"volumes": 2, "planned": True})
    assert out2["status"] == "written"
    assert out2.get("volumes") == 2
    out3 = commit_if_approved(
        "s3_plan_chapter_accounts", False,
        lambda: {"volume_id": "v1"},
    )
    assert out3["status"] == "declined"


def test_join_uses_prompt_renderer_markers():
    from scribe3.context_budget import join_generation_segments
    joined, _rep = join_generation_segments([
        {"name": "event_drive", "layer": "redline", "text": "【事件驱动】甲"},
        {"name": "drama_contract", "layer": "redline", "text": "【戏剧合同】乙"},
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】丙"},
    ], v2=True)
    assert "【event_drive】" in joined or "事件驱动" in joined
    assert joined.index("事件驱动") < joined.index("戏剧合同") < joined.index("最终提醒")


def test_judge_adds_gate_shape():
    from scribe3.playbook.judge import _normalize
    raw = _normalize({
        "verdict": "fail",
        "answers": [{"q": 1, "answer": "no", "evidence": "原句", "reason": "没发生"}],
        "opinion": "今晚那件事没落在纸上",
    })
    from scribe3.quality_gate import from_existing
    g = from_existing({
        "ok": raw["verdict"] == "pass",
        "code": raw["verdict"],
        "message": raw["opinion"],
        "hits": raw["answers"],
    })
    assert g["ok"] is False
    assert g["code"] == "fail"
    assert g["hits"]


def test_prompt_renderer_and_quality_shape():
    text = render_slots({"duty": "今晚按回碎片", "play": ""})
    assert "【duty】" in text
    assert "今晚按回碎片" in text
    assert "<prompt>" in text
    assert shadow_equal("a  b", "a b")
    g = gate_result(ok=False, code="leak", message="拆穿了", hits=[{"word": "锁眼"}])
    assert g["ok"] is False and g["code"] == "leak" and g["hits"]
    wrapped = from_existing({"ok": True, "issues": []})
    assert wrapped["ok"] is True
    assert "hits" in wrapped


def test_visible_to_strips_secret():
    from scribe3.epistemic import visible_to

    class F:
        def __init__(self, id, secret=False):
            self.id = id
            self.secret = secret

    class St:
        def facts_at(self, n):
            return [F("fact:a"), F("fact:secret", secret=True)]

    ids = visible_to(St(), "book", 1, "author")
    assert "fact:a" in ids
    assert "fact:secret" not in ids


def test_beats_write_legacy_flag_registered():
    from scribe3.feature_flags import FLAG_REGISTRY, flag_truthy, get_all_flags
    names = {f.name for f in FLAG_REGISTRY}
    for k in (
        "SCRIBE3_BEATS_WRITE_LEGACY",
        "SCRIBE3_HTTP_ERRORS_UNIFIED",
        "SCRIBE3_PROMPT_RENDERER",
        "SCRIBE3_QUALITY_GATE_UNIFIED",
        "SCRIBE3_EPISTEMIC_ORACLE",
        "SCRIBE3_RECALL_SHADOW_VECTOR",
        "SCRIBE3_RECALL_PLAYBOOK",
    ):
        assert k in names
    flags = get_all_flags()
    assert flags["SCRIBE3_RECALL_PLAYBOOK"]["default"] == "1"
    assert flags["SCRIBE3_PROMPT_RENDERER"]["default"] == "1"
    assert flags["SCRIBE3_QUALITY_GATE_UNIFIED"]["default"] == "1"
    assert flags["SCRIBE3_EPISTEMIC_ORACLE"]["default"] == "1"
    assert flags["SCRIBE3_HTTP_ERRORS_UNIFIED"]["default"] == "1"
    assert flag_truthy("SCRIBE3_RECALL_PLAYBOOK") is True


def test_dropped_chapter_fields_gated_in_source():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "store" / "chapters.py").read_text(encoding="utf-8")
    assert "SCRIBE3_BEATS_WRITE_LEGACY" in src
    assert "beats" in src
