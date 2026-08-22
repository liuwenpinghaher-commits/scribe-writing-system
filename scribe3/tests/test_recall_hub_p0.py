"""召回中枢 P0 与预算建议：内存夹具，不启 Surreal。"""
from __future__ import annotations

from scribe3.codex_digest import digest_payloads
from scribe3.feature_flags import flag_truthy, get_all_flags
from scribe3.playbook.context import build_ctx
from scribe3.recall_service import RecallPack, pack_text, shadow_diff
from scribe3.stage_generate import thicken_stage
from scribe3.structure_budget import suggest_budget
from scribe3.tests.test_playbook_context_guides import _FrozenOnly, _World


def test_digest_payloads_multi_group():
    rows = digest_payloads("character", "role:柳岸青", {
        "name": "柳岸青",
        "appearance": "右腕内嵌断指",
        "surface_goal": "按回碎片",
        "alias": "岸青",
    })
    groups = {r["field_group"] for r in rows}
    assert "all" in groups
    assert "identity" in groups
    assert "alias" in groups
    assert all(r["attribute"] == "codex_digest" for r in rows)


def test_shadow_does_not_change_codex_text():
    st = _World()
    ctx1 = build_ctx(st, 1, focalizer="role:柳岸青", playbook=_FrozenOnly())
    ctx2 = build_ctx(st, 1, focalizer="role:柳岸青", playbook=_FrozenOnly())
    assert ctx1["codex_recall"] == ctx2["codex_recall"]
    rec = shadow_diff(st, 1, "role:柳岸青", ctx1["codex_recall"])
    assert rec["ok"] is True
    assert "entity_jaccard" in rec
    assert rec.get("secret_leak_count") == 0
    assert "threshold_ok" in rec


def test_outline_stale_missing_field_does_not_block():
    def llm(_prompt, **_k):
        return "{}"
    out = thicken_stage("deduce", {}, llm_fn=llm, persist_fn=None, seq=1, st=_FrozenOnly())
    assert out.get("code") != "outline_stale"


def test_outline_stale_blocks_only_when_flag_and_stale(monkeypatch):
    monkeypatch.setenv("SCRIBE3_OUTLINE_STATUS_GATE", "1")
    # default is on; keep explicit for this case
    def llm(_prompt, **_k):
        return "{}"
    out = thicken_stage(
        "deduce", {"outline_status": "stale"}, llm_fn=llm, persist_fn=None, seq=1, st=_FrozenOnly(),
    )
    assert out.get("ok") is False
    assert out.get("code") == "outline_stale"
    out2 = thicken_stage("duty", {"outline_status": "stale"}, llm_fn=llm, persist_fn=None, seq=1, st=_FrozenOnly())
    assert out2.get("code") != "outline_stale"


def test_suggest_budget_short_vs_million():
    short = suggest_budget(45000)
    assert short["advisory"] is True
    assert short["volumes"] == 3
    million = suggest_budget(1_000_000)
    assert million["chapters"] > short["chapters"]
    assert million["volumes"] >= 4


def test_recall_flags_registered():
    flags = get_all_flags()
    assert flags["SCRIBE3_RECALL_SHADOW"]["default"] == "1"
    assert flags["SCRIBE3_RECALL_PLAYBOOK"]["default"] == "0"
    assert flags["SCRIBE3_OUTLINE_STATUS_GATE"]["default"] == "1"
    assert flag_truthy("SCRIBE3_RECALL_PLAYBOOK") is False


def test_pack_text_empty():
    assert pack_text(RecallPack()) == ""
