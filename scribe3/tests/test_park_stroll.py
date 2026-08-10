"""PR-6a · park_stroll severity 矩阵与 triage buckets（无 Surreal / 无 LLM）。"""
from __future__ import annotations

from pathlib import Path

import pytest

from scribe3.loop import build_regen_constraints, triage
from scribe3.pressure_metrics import (
    _is_high_chapter,
    _sev_spatial,
    measure_pressure,
    pressure_should_block,
)
from scribe3.review.blocking import is_blocking_issue

FIX = Path(__file__).resolve().parent / "fixtures" / "pressure_gold"

# 金样病文：巷志 run≥3 + 时间匀速（可无 progress 触发 park_stroll）
_STROLL_PROSE = (FIX / "bad_walkthrough.md").read_text(encoding="utf-8")
_STROLL_SYN = "炉巷旧库侧门扎纸铺磨刀摊"
_STROLL_BEATS = "出巷 侧门 记门 回铺 等待"


def _kinds(findings: list) -> set[str]:
    return {(f.get("meta") or {}).get("kind") for f in findings}


def _sev_of(findings: list, kind: str) -> str | None:
    for f in findings:
        if (f.get("meta") or {}).get("kind") == kind:
            return (f.get("meta") or {}).get("severity")
    return None


# ── severity helpers ──────────────────────────────────────────────


def test_is_high_chapter_pressure_and_role():
    assert _is_high_chapter(4, "") is True
    assert _is_high_chapter(5, "低压") is True
    assert _is_high_chapter(3, "") is False
    assert _is_high_chapter(2, "高压") is True
    assert _is_high_chapter(1, "推进") is True
    assert _is_high_chapter(3, "关系回收") is False


def test_sev_spatial_matrix_default_advisory(monkeypatch):
    """代码默认 PARK_STROLL_BLOCKING=0 → 一律 advisory。"""
    monkeypatch.delenv("SCRIBE3_PARK_STROLL_BLOCKING", raising=False)
    assert _sev_spatial(5, "高压", kind="spatial_inventory") == "advisory"
    assert _sev_spatial(5, "高压", kind="park_stroll") == "advisory"
    assert _sev_spatial(5, "高压", kind="time_linear_flag") == "advisory"


def test_sev_spatial_matrix_flag_on(monkeypatch):
    """PARK_STROLL_BLOCKING=1 + 高压 → spatial/park blocking；time_linear 仍 advisory。"""
    monkeypatch.setenv("SCRIBE3_PARK_STROLL_BLOCKING", "1")
    assert _sev_spatial(5, "", kind="spatial_inventory") == "blocking"
    assert _sev_spatial(2, "推进", kind="spatial_inventory") == "blocking"
    assert _sev_spatial(5, "高压", kind="park_stroll") == "blocking"
    # 单独 time_linear 恒 advisory（组合靠 park_stroll）
    assert _sev_spatial(5, "高压", kind="time_linear_flag") == "advisory"
    # 低压 + 无高压 role → 仍 advisory
    assert _sev_spatial(2, "低压", kind="spatial_inventory") == "advisory"
    assert _sev_spatial(3, "", kind="park_stroll") == "advisory"


# ── measure_pressure emit ─────────────────────────────────────────


def test_park_stroll_fires_without_progress_contract(monkeypatch):
    """KD-NQ-14：无 progress / 无合同，仅 spatial∧time_linear + 高压 → park_stroll。"""
    monkeypatch.delenv("SCRIBE3_PARK_STROLL_BLOCKING", raising=False)
    monkeypatch.delenv("SCRIBE3_PDC_BLOCKING", raising=False)
    m = measure_pressure(
        _STROLL_PROSE,
        None,
        synopsis=_STROLL_SYN,
        beats_text=_STROLL_BEATS,
        chapter_pressure=5,
    )
    kinds = _kinds(m["findings"])
    assert "spatial_inventory" in kinds, m["findings"]
    assert "time_linear_flag" in kinds, m["findings"]
    assert "park_stroll" in kinds, m["findings"]
    # 默认旗关 → advisory
    assert _sev_of(m["findings"], "park_stroll") == "advisory"
    assert _sev_of(m["findings"], "spatial_inventory") == "advisory"
    assert pressure_should_block(m["findings"], chapter_pressure=5) is False
    # progress 指标 n/a
    assert m["metrics"]["progress_zero_advance"]["tier"] == "n/a"
    assert m["contract_present"] is False


def test_park_stroll_blocking_when_flag_on(monkeypatch):
    monkeypatch.setenv("SCRIBE3_PARK_STROLL_BLOCKING", "1")
    monkeypatch.delenv("SCRIBE3_PDC_BLOCKING", raising=False)
    m = measure_pressure(
        _STROLL_PROSE,
        None,
        synopsis=_STROLL_SYN,
        beats_text=_STROLL_BEATS,
        chapter_pressure=5,
    )
    assert _sev_of(m["findings"], "park_stroll") == "blocking"
    assert _sev_of(m["findings"], "spatial_inventory") == "blocking"
    assert _sev_of(m["findings"], "time_linear_flag") == "advisory"
    assert pressure_should_block(m["findings"], chapter_pressure=5) is True


def test_park_stroll_low_pressure_no_emit(monkeypatch):
    monkeypatch.setenv("SCRIBE3_PARK_STROLL_BLOCKING", "1")
    m = measure_pressure(
        _STROLL_PROSE,
        None,
        synopsis=_STROLL_SYN,
        beats_text=_STROLL_BEATS,
        chapter_pressure=2,
        role="低压",
    )
    kinds = _kinds(m["findings"])
    # 低压可不 emit park_stroll；spatial/time 仍可有 finding
    assert "park_stroll" not in kinds
    assert m["metrics"]["park_stroll"]["value"] is False


def test_park_stroll_role_high_even_low_cp(monkeypatch):
    """role∈{推进} 即高压，cp 可 <4。"""
    monkeypatch.setenv("SCRIBE3_PARK_STROLL_BLOCKING", "1")
    m = measure_pressure(
        _STROLL_PROSE,
        None,
        synopsis=_STROLL_SYN,
        beats_text=_STROLL_BEATS,
        chapter_pressure=2,
        role="推进",
    )
    assert "park_stroll" in _kinds(m["findings"])
    assert _sev_of(m["findings"], "park_stroll") == "blocking"


def test_park_stroll_with_gold_bad_walkthrough(monkeypatch):
    """病样金样：有合同也可检出 park_stroll（默认 advisory）。"""
    monkeypatch.delenv("SCRIBE3_PARK_STROLL_BLOCKING", raising=False)
    import json
    contract = json.loads((FIX / "contract_good.json").read_text(encoding="utf-8"))
    m = measure_pressure(
        _STROLL_PROSE, contract,
        synopsis=_STROLL_SYN,
        beats_text=_STROLL_BEATS,
        chapter_pressure=5,
    )
    assert "park_stroll" in _kinds(m["findings"])
    assert _sev_of(m["findings"], "park_stroll") == "advisory"
    # 有 progress 时也可因 zero / spatial 组合触发
    assert m["contract_present"] is True


# ── triage ────────────────────────────────────────────────────────


def test_triage_park_stroll_blocking_recognized():
    """meta.severity=blocking + type=pressure + kind=park_stroll → blocking 桶 / story。"""
    post = {
        "leaks": [],
        "issues": [{
            "type": "pressure",
            "message": "公园散步：高压章疑似无主推进",
            "text": "",
            "meta": {"kind": "park_stroll", "severity": "blocking"},
        }],
        "ai_grade": {},
        "degraded_stages": [],
    }
    assert is_blocking_issue(post["issues"][0]) is True
    out = triage(post)
    assert out["verdict"] == "blocking"
    assert any(b.get("kind") == "park_stroll" for b in out["blocking"])
    assert any(b.get("detector") == "pressure_metrics" for b in out["blocking"])
    assert "buckets" in out
    assert any(b.get("kind") == "park_stroll" for b in out["buckets"]["story"])


def test_triage_park_stroll_advisory_default():
    post = {
        "leaks": [],
        "issues": [{
            "type": "pressure",
            "message": "公园散步",
            "text": "",
            "meta": {"kind": "park_stroll", "severity": "advisory"},
        }],
        "ai_grade": {},
        "degraded_stages": [],
    }
    out = triage(post)
    assert out["verdict"] != "blocking"
    assert out["advisory_count"] >= 1
    assert "buckets" in out
    assert out["buckets"]["story"] or out["buckets"]["style"]


def test_build_regen_constraints_park_stroll():
    text = build_regen_constraints(
        [{"detector": "pressure_metrics", "kind": "park_stroll",
          "quote": "", "note": "公园散步"}],
        next_attempt=1,
    )
    assert "公园散步" in text or "巷志" in text
    assert "pressure_metrics" in text


def test_triage_buckets_skeleton_always_present():
    out = triage({"leaks": [], "issues": [], "ai_grade": {}, "degraded_stages": []})
    assert set(out["buckets"].keys()) == {"redline", "story", "style"}
    assert out["verdict"] == "pass"
