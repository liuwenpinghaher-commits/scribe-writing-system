"""PR-3 · DRAMA_GATE advisory + 缺口清单（纯函数；无 Surreal / 无网络）。"""
from __future__ import annotations

import json

from scribe3.drama_beats import (
    extract_drama_gaps,
    format_drama_gate_park_reason,
    should_drama_gate_park,
    validate_drama_beats,
)
from scribe3.api.services.pilot_runtime import (
    _compose_beats_meta,
    _drama_gate_park_if_needed,
)


def _weak_high_beats():
    """高压场景下缺 GCD 的 v1 仅 text 节拍。"""
    return [
        {"id": "b1", "kind": "scene", "text": "他走进长巷闻见潮气"},
        {"id": "b2", "kind": "scene", "text": "又拐进侧门听见水声"},
    ]


def test_extract_drama_gaps_missing_fields():
    beats = _weak_high_beats()
    dv = validate_drama_beats(
        beats, chapter_pressure=5, role="高压",
        synopsis="他走进长巷闻见潮气。又拐进侧门听见水声。",
        hard_pressure=4, compat_v1=False,
    )
    gaps = extract_drama_gaps(beats, validation=dv)
    assert "b1" in gaps["missing_goal"]
    assert "b1" in gaps["missing_conflict"]
    assert "b1" in gaps["missing_turn"]
    assert gaps["lines"]
    assert any("goal" in ln or "缺" in ln for ln in gaps["lines"])


def test_format_park_reason_advisory_and_json():
    gaps = {
        "missing_goal": ["b1"],
        "missing_conflict": ["b1", "b2"],
        "missing_turn": ["b2"],
        "missing_cost": ["b1"],
        "lines": ["b1缺goal/conflict/cost", "b2缺conflict/turn"],
        "errors": ["scene_gcd_incomplete:need>=4"],
    }
    msg = format_drama_gate_park_reason(gaps, advisory=True)
    assert msg.startswith("drama_incomplete:")
    assert "可补字段继续" in msg
    assert "缺口" in msg
    assert "清单:" in msg
    assert "missing_goal" in msg
    assert "PATCH" in msg or "s3_patch_chapter_plan" in msg
    # 紧凑 JSON 可解析
    jpart = msg.split("清单:", 1)[1].split("。", 1)[0]
    parsed = json.loads(jpart)
    assert parsed["missing_goal"] == ["b1"]
    assert "b2" in parsed["missing_conflict"]


def test_should_drama_gate_park_only_high_and_flag():
    weak = {
        "ok": False,
        "metrics": {"is_high": True},
        "errors": ["scene_gcd_incomplete:need>=4"],
    }
    assert should_drama_gate_park(weak, gate_enabled=True) is True
    assert should_drama_gate_park(weak, gate_enabled=False) is False
    low = {"ok": False, "metrics": {"is_high": False}, "errors": ["rel_tension_missing"]}
    assert should_drama_gate_park(low, gate_enabled=True) is False
    ok = {"ok": True, "metrics": {"is_high": True}, "errors": []}
    assert should_drama_gate_park(ok, gate_enabled=True) is False


def test_compose_meta_embeds_gaps():
    beats = _weak_high_beats()
    meta = _compose_beats_meta(
        beats,
        schema="v1",
        beats_source="llm_v1",
        synopsis="他走进长巷。又拐进侧门。",
        chapter_pressure=5,
        role="高压",
    )
    dv = meta["drama_validation"]
    assert "gaps" in dv
    assert isinstance(dv["gaps"].get("lines"), list)
    assert "missing_goal" in dv["gaps"]


def test_drama_gate_park_if_needed_monkeypatch(monkeypatch):
    beats = _weak_high_beats()
    # compat off so high-pressure v1 → ok=False
    monkeypatch.setenv("SCRIBE3_DRAMA_GATE_COMPAT", "0")
    meta = _compose_beats_meta(
        beats,
        schema="v1",
        beats_source="synopsis_segments",
        synopsis="他走进长巷闻见潮气。又拐进侧门听见水声。",
        chapter_pressure=5,
        role="高压",
    )
    assert meta["drama_validation"]["ok"] is False
    assert meta["drama_validation"]["metrics"].get("is_high") is True

    # 默认门关 → 不 park
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.drama_gate_enabled", lambda: False,
    )
    assert _drama_gate_park_if_needed(meta) is None

    # 门开 → park 且不要求调用方擦 beats
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.drama_gate_enabled", lambda: True,
    )
    park = _drama_gate_park_if_needed(meta)
    assert park is not None
    assert "pilot_park" in park
    assert "可补字段继续" in park["pilot_park"]
    assert park["drama_gate"]["mode"] == "advisory"
    assert park["drama_gate"]["gaps"]
    assert park["drama_gate"]["ok"] is False
