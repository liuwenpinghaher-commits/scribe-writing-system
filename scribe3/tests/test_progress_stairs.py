"""情节台阶（progress）· 真模块单测。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scribe3.pressure_drive import (
    MAX_PDC_BLOCK,
    bootstrap_pdc_from_texts,
    evidence_ok,
    render_pressure_drive_block,
    validate_pdc,
)
from scribe3.pressure_metrics import measure_pressure

FIX = Path(__file__).resolve().parent / "fixtures" / "pressure_gold"


def _base_contract(**kw) -> dict:
    c = bootstrap_pdc_from_texts(
        synopsis="旧库侧门 高压 压力级:5",
        beat_texts=["侧门", "权衡", "抉择", "余波"],
        chapter_pressure=5,
        role="高压",
        fork_choice="半寸插匙进门接名或退回空过三日",
        evidence="半寸匙痕",
        cost_steps=["退则空过三日", "选错则收不回"],
        **kw,
    )
    assert c is not None
    return c


def test_progress_fail_soft_does_not_ok_false():
    c = _base_contract()
    c["progress"] = {
        "version": "psc.v1",
        "min_stairs": 1,
        "stairs": [],  # illegal
        "location_grind": {"primary_locus": "侧门", "max_contiguous_chars": 900, "max_contiguous_paras": 6},
        "retreat_policy": {"allow_retreat": True, "require_world_change": True,
                           "change_kinds": ["cost", "decision", "irreversible"]},
    }
    v = validate_pdc(c)
    assert v["ok"] is True, v  # core still ok
    assert v["progress_ok"] is False
    assert any("progress_invalid" in w for w in v["warnings"])
    block = render_pressure_drive_block(c)
    assert "压力驱动合同" in block
    assert "岔路" in block or "不可逆" in block
    assert "结构待修" not in block
    assert len(block) <= MAX_PDC_BLOCK


def test_render_includes_progress_and_under_400():
    c = _base_contract()
    assert c.get("progress")
    block = render_pressure_drive_block(c)
    assert len(block) <= MAX_PDC_BLOCK
    assert "半寸匙痕" in block
    assert any(k in block for k in ("台阶", "退", "同地"))


def test_bootstrap_dual_short_stairs():
    c = _base_contract()
    prog = c["progress"]
    stairs = prog["stairs"]
    assert len(stairs) >= 2
    kinds = {s["kind"] for s in stairs}
    assert "irreversible" in kinds or any(s["kind"] in ("cost", "decision") for s in stairs)
    # cost/decision short
    for s in stairs:
        if s["kind"] in ("cost", "decision"):
            assert len(s["evidence_must_show"]) <= 12
            assert evidence_ok(s["evidence_must_show"])
            # not whole cost_steps sentence
            assert s["evidence_must_show"] != "退则空过三日" or len(s["evidence_must_show"]) <= 12


def test_stairs_hit_min_stairs_gating():
    c = _base_contract()
    # force two stairs, min 1, one hit
    c["progress"]["min_stairs"] = 1
    c["progress"]["stairs"] = [
        {"id": "s1", "kind": "cost", "label": "a", "evidence_must_show": "空过三日", "is_retreat_cost": True},
        {"id": "s2", "kind": "irreversible", "label": "b", "evidence_must_show": "半寸匙痕", "is_retreat_cost": False},
    ]
    prose_one = "他终于空过三日，门仍关着。"  # 仅 cost 锚，无 半寸匙痕
    m = measure_pressure(prose_one, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    assert m["metrics"]["progress_stairs_anchored"]["value"] == 1
    assert m["metrics"]["progress_stairs_anchored"]["tier"] == "light"  # hit 1 >= need 1

    c["progress"]["min_stairs"] = 2
    m2 = measure_pressure(prose_one, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    assert m2["metrics"]["progress_stairs_anchored"]["value"] == 1
    assert m2["metrics"]["progress_stairs_anchored"]["tier"] == "heavy"  # hit 1 < 2


def test_grind_g1_quiet_land_clears():
    """安静落地：无 force 词但首次 cost evidence → 打断，不超顶则无 grind finding。"""
    c = _base_contract()
    c["progress"]["location_grind"] = {
        "primary_locus": "侧门",
        "max_contiguous_chars": 200,
        "max_contiguous_paras": 10,
    }
    c["progress"]["stairs"] = [
        {"id": "s1", "kind": "cost", "label": "咬合", "evidence_must_show": "匙齿咬合", "is_retreat_cost": False},
    ]
    # few short paras then quiet land
    prose = (
        "侧门前他停住了。\n\n"
        "侧门缝里渗着灰。\n\n"
        "侧门边他再看一眼。\n\n"
        "匙齿咬合，锁芯轻响。\n\n"
    )
    m = measure_pressure(prose, c, synopsis="旧库侧门", beats_text="侧门", chapter_pressure=5)
    # landing should prevent long run; may or may not exceed 200
    kinds = [(f.get("meta") or {}).get("kind") for f in m["findings"]]
    # if grind fires, fail G1 - with short paras before land should be ok
    assert "location_grind_run" not in kinds or m["metrics"]["location_grind_run"]["tier"] == "light"


def test_grind_g2_bare_force_does_not_clear():
    c = _base_contract()
    c["progress"]["location_grind"] = {
        "primary_locus": "侧门",
        "max_contiguous_chars": 80,
        "max_contiguous_paras": 3,
    }
    c["progress"]["stairs"] = [
        {"id": "s1", "kind": "cost", "label": "x", "evidence_must_show": "空过三日", "is_retreat_cost": True},
    ]
    # many locus paras with only 决定/推开 - no stair evidence
    paras = ["侧门前他决定了，又推开念头。"] * 8
    prose = "\n\n".join(paras)
    m = measure_pressure(prose, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    kinds = [(f.get("meta") or {}).get("kind") for f in m["findings"]]
    assert "location_grind_run" in kinds
    assert m["metrics"]["location_grind_run"]["value"] > 80


def test_grind_g3_force_and_evidence_clears():
    c = _base_contract()
    c["progress"]["location_grind"] = {
        "primary_locus": "侧门",
        "max_contiguous_chars": 500,
        "max_contiguous_paras": 20,
    }
    c["progress"]["stairs"] = [
        {"id": "s1", "kind": "decision", "label": "d", "evidence_must_show": "拧开", "is_retreat_cost": False},
    ]
    prose = (
        "侧门前他犹豫。\n\n"
        "侧门边再停。\n\n"
        "他决定拧开，门缝一动。\n\n"
        "侧门又静。\n\n"
    )
    m = measure_pressure(prose, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    # after clear, later single para shouldn't accumulate past cap easily
    assert m["metrics"]["location_grind_run"]["tier"] in ("light", "n/a", "mid")


def test_grind_g4_repaste_same_evidence_does_not_clear():
    """G4 抗锚刷：同 evidence 连贴 ≥10 段 → run 不断；须出 grind finding。

    旧 bug：settle() 每次证据打断清空 seen，再贴同一串又算 fresh → max_run=0。
    """
    c = _base_contract()
    c["progress"]["location_grind"] = {
        "primary_locus": "侧门",
        "max_contiguous_chars": 80,
        "max_contiguous_paras": 4,
    }
    c["progress"]["stairs"] = [
        {
            "id": "s1",
            "kind": "cost",
            "label": "空过",
            "evidence_must_show": "空过三日",
            "is_retreat_cost": True,
        },
    ]
    # 15 段同地 + 同一 cost evidence（无离场）
    paras = ["侧门前他空过三日，又站着。"] * 15
    prose = "\n\n".join(paras)
    m = measure_pressure(prose, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    kinds = [(f.get("meta") or {}).get("kind") for f in m["findings"]]
    assert "location_grind_run" in kinds, m["metrics"]["location_grind_run"]
    # 首段可作 fresh 落地打断；其后 14 段须累计 → max_run 远大于 0
    assert m["metrics"]["location_grind_run"]["value"] > 80, m["metrics"]["location_grind_run"]
    assert m["metrics"]["location_grind_run"]["tier"] in ("mid", "heavy")


def test_retreat_no_cost():
    c = _base_contract()
    c["progress"]["stairs"] = [
        {"id": "s1", "kind": "info", "label": "i", "evidence_must_show": "灰被拨过", "is_retreat_cost": False},
    ]
    prose = "他退回了巷口，头也不回，灰被拨过。"
    m = measure_pressure(prose, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    assert m["metrics"]["retreat_no_cost"]["value"] is True
    kinds = [(f.get("meta") or {}).get("kind") for f in m["findings"]]
    assert "retreat_no_cost" in kinds

    prose2 = "他退回了巷口，却已空过三日。"
    c["progress"]["stairs"] = [
        {"id": "s1", "kind": "cost", "label": "c", "evidence_must_show": "空过三日", "is_retreat_cost": True},
    ]
    m2 = measure_pressure(prose2, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    assert m2["metrics"]["retreat_no_cost"]["value"] is False


def test_separation_grind_vs_good():
    """痕迹已绿但长磨 → dirtier on grind；好稿 stairs light 且无 grind。"""
    c = _base_contract()
    c["progress"]["location_grind"] = {
        "primary_locus": "侧门",
        "max_contiguous_chars": 100,
        "max_contiguous_paras": 3,
    }
    irrev = "半寸匙痕"
    c["irreversible"]["evidence_must_show"] = irrev
    c["progress"]["stairs"] = [
        {"id": "s1", "kind": "cost", "label": "空过", "evidence_must_show": "空过三日", "is_retreat_cost": True},
        {"id": "s2", "kind": "irreversible", "label": "痕", "evidence_must_show": irrev, "is_retreat_cost": False},
    ]
    # drag: irrev once, then long grind WITHOUT repeating irrev (else each para clears run)
    drag = "侧门边有半寸匙痕。\n\n" + "\n\n".join(
        ["侧门前他停了又停，只是站着。"] * 12
    )
    good = (
        "侧门前一息。\n\n"
        "要么进要么退。他拧开半寸，半寸匙痕落下。\n\n"
        "他没退，空过三日的念头掐灭了。"
    )
    md = measure_pressure(drag, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    mg = measure_pressure(good, c, synopsis="侧门", beats_text="侧门", chapter_pressure=5)
    assert md["metrics"]["irreversible_anchored"]["tier"] == "light"
    assert md["metrics"]["location_grind_run"]["tier"] in ("mid", "heavy")
    assert mg["metrics"]["progress_stairs_anchored"]["tier"] == "light"
    # primary: drag not cleaner than good on stairs+grind
    drag_bad = (
        md["metrics"]["location_grind_run"]["tier"] in ("mid", "heavy")
        or md["metrics"]["progress_stairs_anchored"]["tier"] == "heavy"
    )
    good_ok = mg["metrics"]["progress_stairs_anchored"]["tier"] == "light"
    assert drag_bad and good_ok


def test_section_12_5_retreat_cost_failsoft():
    """§1.2 ⑤：高压可退岔路 + 仅 info 阶 → progress_ok False，core ok 仍 True。"""
    c = _base_contract()
    c["fork"] = {
        "choice": "拧开侧门接名或退回空过三日",
        "cost_steps": ["退则空过三日"],
    }
    c["chapter_pressure"] = 5
    c["role"] = "高压"
    c["progress"]["stairs"] = [
        {
            "id": "s1",
            "kind": "info",
            "label": "巷志",
            "evidence_must_show": "灰被拨过",
            "is_retreat_cost": False,
        },
    ]
    c["progress"]["min_stairs"] = 1
    v = validate_pdc(c)
    assert v["ok"] is True
    assert v["progress_ok"] is False
    assert any("progress_invalid_retreat_cost" in w for w in v["warnings"])
    block = render_pressure_drive_block(c)
    assert "岔路" in block or "不可逆" in block
    assert "结构待修" not in block


def test_gold_separation_with_progress_cap250():
    """gold 合同 progress cap=250：bad 出 grind/stairs heavy；good stairs light。"""
    contract = json.loads((FIX / "contract_good.json").read_text())
    assert "progress" in contract
    assert int(contract["progress"]["location_grind"]["max_contiguous_chars"]) == 250
    bad = (FIX / "bad_walkthrough.md").read_text()
    good = (FIX / "good_pressure.md").read_text()
    mb = measure_pressure(bad, contract, synopsis="侧门", beats_text="侧门 抉择", chapter_pressure=5)
    mg = measure_pressure(good, contract, synopsis="侧门", beats_text="侧门 抉择", chapter_pressure=5)
    # bad: stairs miss or zero advance; grind finding expected under cap=250
    assert mb["metrics"]["progress_stairs_anchored"]["tier"] in ("heavy", "n/a") or (
        mb["metrics"]["progress_zero_advance"]["value"] is True
    )
    kinds_b = [(f.get("meta") or {}).get("kind") for f in mb["findings"]]
    assert "location_grind_run" in kinds_b or mb["metrics"]["location_grind_run"]["tier"] in (
        "mid", "heavy",
    )
    # good: stairs light (半寸匙痕)
    assert mg["metrics"]["progress_stairs_anchored"]["tier"] == "light"
    # no invert
    assert not (
        mg["metrics"]["location_grind_run"]["tier"] in ("mid", "heavy")
        and mb["metrics"]["progress_stairs_anchored"]["tier"] == "light"
        and mg["metrics"]["progress_stairs_anchored"]["tier"] != "light"
    )


def test_chapter_meta_req_accepts_pressure_drive():
    """HTTP ChapterMetaReq 须含 pressure_drive，否则 PATCH 静默丢键。"""
    from scribe3.api.models import ChapterMetaReq

    req = ChapterMetaReq.model_validate({
        "pressure_drive": {
            "version": "pdc.v1",
            "fork": {"choice": "a"},
            "irreversible": {"evidence_must_show": "半寸匙痕"},
            "progress": {"version": "psc.v1", "min_stairs": 1, "stairs": [
                {"id": "s1", "kind": "cost", "label": "c",
                 "evidence_must_show": "空过", "is_retreat_cost": True},
            ]},
        }
    })
    dumped = req.model_dump(exclude_unset=True)
    assert "pressure_drive" in dumped
    assert isinstance(dumped["pressure_drive"], dict)
    assert dumped["pressure_drive"].get("progress")


def test_regen_imper_by_kind_progress():
    """pressure_metrics + kind → 换阶/换场，非默认「消除该硬伤」。"""
    from scribe3.loop import build_regen_constraints

    out = build_regen_constraints(
        [{
            "detector": "pressure_metrics",
            "kind": "progress_stairs_anchored",
            "note": "台阶未落地",
            "quote": "侧门前",
        }],
        next_attempt=1,
    )
    assert "换场" in out or "换阶" in out
    assert "消除该硬伤" not in out
    leaks = build_regen_constraints(
        [{"detector": "find_leaks", "kind": "leak", "note": "泄露", "quote": "x"}],
        next_attempt=1,
    )
    assert "私密" in leaks or "疑惧" in leaks
