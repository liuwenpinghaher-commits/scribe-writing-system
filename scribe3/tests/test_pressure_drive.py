"""PDC 纯函数单测 · 驱动真实 pressure_drive 模块。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scribe3.pressure_drive import (
    MAX_PDC_BLOCK,
    bootstrap_pdc_from_texts,
    first_ok_bootstrap_evidence,
    load_pdc,
    parse_pressure_drive,
    pdc_flag_enabled,
    render_pressure_drive_block,
    template_bootstrap_evidence,
    validate_pdc,
)
from scribe3.pressure_metrics import measure_pressure

FIX = Path(__file__).resolve().parent / "fixtures" / "pressure_gold"


def _load_contract() -> dict:
    return json.loads((FIX / "contract_good.json").read_text(encoding="utf-8"))


def _prose(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_validate_pdc_three_state():
    assert validate_pdc(None)["ok"] is None
    assert validate_pdc({"status": "missing"})["ok"] is None
    good = _load_contract()
    # gold fixture may lack progress — still core ok
    r0 = validate_pdc(good)
    assert r0["ok"] is True
    assert "progress_ok" in r0
    bad = dict(good)
    bad["fork"] = {"choice": "", "cost_steps": []}
    # has version + empty choice → ok False
    r = validate_pdc(bad)
    assert r["ok"] is False
    assert any("choice" in e for e in r["errors"])


def test_validate_pdc_high_requires_peak_and_span():
    c = _load_contract()
    for b in c["beats"]:
        b["is_peak"] = False
    r = validate_pdc(c)
    assert r["ok"] is False
    assert any("is_peak" in e for e in r["errors"])


def test_render_respects_400_and_keeps_p0():
    c = _load_contract()
    block = render_pressure_drive_block(c)
    assert block
    assert len(block) <= MAX_PDC_BLOCK
    assert "压力驱动合同" in block
    assert "半寸匙痕" in block
    assert "岔路" in block
    # empty
    assert render_pressure_drive_block(None) == ""
    assert render_pressure_drive_block({"status": "missing"}) == ""


def test_render_p0_priority_when_bloated():
    c = _load_contract()
    c["fork"]["choice"] = "岔" * 200
    c["irreversible"]["evidence_must_show"] = "痕" * 200
    c["motif_intensity_caps"] = [{"term": f"词{i}", "max_mentions": 1} for i in range(20)]
    block = render_pressure_drive_block(c)
    assert len(block) <= MAX_PDC_BLOCK
    assert "压力驱动合同" in block


def test_load_pdc_merges_beat_text():
    c = _load_contract()
    ch = {
        "pressure_drive": json.dumps(c, ensure_ascii=False),
        "beats": [{"text": "作者改过的节拍A"}, {"text": "作者改过的节拍B"}, {"text": "C"}, {"text": "D"}],
    }
    loaded = load_pdc(ch)
    assert loaded is not None
    assert loaded["beats"][0]["text"] == "作者改过的节拍A"
    assert loaded["beats"][0].get("p_level") == 2


def test_flag_env(monkeypatch):
    monkeypatch.delenv("SCRIBE3_PDC", raising=False)
    assert pdc_flag_enabled() is False
    monkeypatch.setenv("SCRIBE3_PDC", "1")
    assert pdc_flag_enabled() is True


def test_bootstrap_requires_core():
    assert bootstrap_pdc_from_texts(fork_choice="", evidence="x") is None
    c = bootstrap_pdc_from_texts(
        fork_choice="进或不进",
        evidence="掌心嵌灰印",
        beat_texts=["a", "b", "c", "d"],
    )
    assert c is not None
    assert validate_pdc(c)["ok"] is True


def test_first_ok_bootstrap_evidence_prefers_cost_turn_hook():
    """PR-7：evidence 优先 cost → turn → hook → 模板，非仅灰印。"""
    # empty → template
    assert first_ok_bootstrap_evidence(None, synopsis="") == "收不回的一步痕迹"
    assert first_ok_bootstrap_evidence([], synopsis="覃灰七") == "掌心嵌下的灰印"
    assert template_bootstrap_evidence("灰") == "掌心嵌下的灰印"

    beats = [
        {"text": "a", "cost": "", "turn": "门闩已错半寸", "hook": "明日有人来问"},
        {"text": "b", "cost": "退则空过三日", "turn": "别的", "hook": "钩"},
    ]
    # cost 优先于 turn/hook
    assert first_ok_bootstrap_evidence(beats) == "退则空过三日"

    no_cost = [
        {"text": "a", "cost": "的", "turn": "门闩已错半寸", "hook": "明日有人来问"},
    ]
    # cost 虚词/过短跳过 → turn
    assert first_ok_bootstrap_evidence(no_cost) == "门闩已错半寸"

    only_hook = [{"goal": "x", "hook": "掌心留灰印"}]
    assert first_ok_bootstrap_evidence(only_hook) == "掌心留灰印"

    # explicit template_fallback when fields empty
    assert (
        first_ok_bootstrap_evidence(
            [{"text": "only"}], template_fallback="作者指定痕迹"
        )
        == "作者指定痕迹"
    )


def test_bootstrap_uses_chapter_beats_for_evidence():
    """evidence 空 + chapter_beats → first_ok 填入 irreversible.evidence_must_show。"""
    c = bootstrap_pdc_from_texts(
        fork_choice="进或不进",
        evidence="",
        chapter_beats=[
            {"text": "侧门", "cost": "半寸匙痕收不回", "turn": "他拧开了"},
            {"text": "余波", "hook": "有人看见"},
        ],
        beat_texts=["侧门", "权衡", "抉择", "余波"],
    )
    assert c is not None
    assert c["irreversible"]["evidence_must_show"] == "半寸匙痕收不回"
    assert validate_pdc(c)["ok"] is True

    # no drama fields → synopsis template
    c2 = bootstrap_pdc_from_texts(
        synopsis="灰雾旧巷",
        fork_choice="进或不进",
        evidence="",
        chapter_beats=[{"text": "走"}],
        beat_texts=["a", "b", "c", "d"],
    )
    assert c2 is not None
    assert c2["irreversible"]["evidence_must_show"] == "掌心嵌下的灰印"


def test_separation_bad_worse_than_good():
    """病样相对对照：不可逆未锚定 + 巷志/仪式/匀速时间信号更重。"""
    contract = _load_contract()
    good = _prose("good_pressure.md")
    bad = _prose("bad_walkthrough.md")
    # 病样用「合同要求痕迹但正文没有」
    m_good = measure_pressure(
        good, contract,
        synopsis="侧门抉择",
        beats_text="侧门 旧库 抉择",
        chapter_pressure=5,
    )
    m_bad = measure_pressure(
        bad, contract,
        synopsis="炉巷旧库侧门扎纸铺磨刀摊",
        beats_text="出巷 侧门 记门 回铺 等待",
        chapter_pressure=5,
    )
    assert m_good["metrics"]["irreversible_anchored"]["tier"] == "light"
    assert m_bad["metrics"]["irreversible_anchored"]["tier"] == "heavy"
    # 巷志：病样应有 spatial finding
    bad_spatial = any(
        f.get("meta", {}).get("kind") == "spatial_inventory" for f in m_bad["findings"]
    )
    good_spatial = any(
        f.get("meta", {}).get("kind") == "spatial_inventory" for f in m_good["findings"]
    )
    assert bad_spatial, m_bad["findings"]
    assert not good_spatial, m_good["findings"]
    # 仪式复读：病样记门多次
    assert m_bad["metrics"]["ritual_overuse"]["value"] >= 2
    assert m_good["metrics"]["ritual_overuse"]["value"] <= 1
    # 时间匀速
    assert m_bad["metrics"]["time_linear_flag"]["value"] is True
    assert m_good["metrics"]["time_linear_flag"]["value"] is False


def test_parse_pressure_drive_json_string():
    c = _load_contract()
    s = json.dumps(c, ensure_ascii=False)
    assert parse_pressure_drive(s)["version"] == "pdc.v1"
    assert parse_pressure_drive("not-json") is None
