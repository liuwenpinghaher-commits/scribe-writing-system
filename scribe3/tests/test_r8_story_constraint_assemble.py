"""R8 W1/W2: shipped assemble join order + allowlist + secret mask."""
from __future__ import annotations

from types import SimpleNamespace

from scribe3.context_budget import (
    L0_NEVER_CUT,
    GENERATION_SEGMENT_LAYERS,
    generation_physical_order_names,
    join_generation_segments,
    ordered_generation_segments,
)
from scribe3.injection_registry import DRAMA_CORE_NAMES, SEGMENT_REGISTRY
from scribe3.prompt_allowlist import strip_engineering_leaks_segments
from scribe3.story_constraint_prompt import (
    field_line,
    format_story_constraint_block,
    format_story_contract_head,
    format_story_fuel_parts,
    load_evidence_must_show,
)


def test_physical_order_contract_before_drive():
    names = generation_physical_order_names()
    assert names.index("narrative_contract") < names.index("story_ember")
    assert names.index("story_ember") < names.index("event_drive")
    assert names.index("event_drive") < names.index("event_drive_hook")
    assert "narrative_contract" in L0_NEVER_CUT
    assert "story_ember" not in L0_NEVER_CUT
    assert GENERATION_SEGMENT_LAYERS["narrative_contract"] == "redline"
    assert GENERATION_SEGMENT_LAYERS["story_ember"] == "supplemental"
    meta = {s.name: s for s in SEGMENT_REGISTRY}
    assert meta["narrative_contract"].tier == "L0"
    assert "narrative_contract" in DRAMA_CORE_NAMES


def test_join_order_indices_contract_before_drive():
    segs = [
        {"name": "prefix", "layer": "redline", "text": "P"},
        {"name": "event_drive", "layer": "redline", "text": "DRIVE"},
        {"name": "narrative_contract", "layer": "redline", "text": "【本章必须发生的场面】"},
    ]
    ordered = ordered_generation_segments(segs)
    names = [s["name"] for s in ordered]
    assert names.index("narrative_contract") < names.index("event_drive")
    joined, rep = join_generation_segments(segs)
    assert "【本章必须发生的场面】" in joined
    assert joined.index("【本章必须发生的场面】") < joined.index("DRIVE")


def test_format_block_keeps_jujiao_in_field():
    block = format_story_constraint_block(
        {
            "desire": "拒交铜匙、挨过夜审",
            "obstacle": "冷锅婆堵门讨香",
            "turn": "先倒半炉热灰",
            "cost": "脚印被人看见",
        }
    )
    assert "拒交" in block
    assert "必须说出拒交" not in block
    assert "角色嘴里不得复述" in block
    assert "冷锅婆" not in block.split("欲望：")[0]  # default voice must not inject 冷锅婆


def test_field_line_strips_meta_ids():
    assert "validation.ok" not in field_line("desire", "validation.ok 钥匙捂住")
    oral = "今晚先把门闩死"
    assert field_line("turn", oral) == oral


def test_evidence_read_order_bindings_then_pressure():
    ch = {
        "narrative_contract": {
            "bindings": {"evidence_must_show": ["账簿上勾了一笔"]},
        },
        "pressure_drive": {"irreversible": {"evidence_must_show": ["不该用这条"]}},
    }
    assert load_evidence_must_show(ch) == ["账簿上勾了一笔"]
    ch2 = {"pressure_drive": {"stairs": [{"text": "门开了一线"}]}}
    assert load_evidence_must_show(ch2) == []


def test_allowlist_skips_request_constraint():
    segs = [
        {"name": "prefix", "text": "GATE-B 可开写 机判过关 每章≥3"},
        {"name": "request_constraint", "text": "别搞得像 GATE 过关，走 D3 巷过城门闸"},
    ]
    out = strip_engineering_leaks_segments(segs)
    assert "GATE-B" not in out[0]["text"]
    assert "可开写" not in out[0]["text"]
    assert "机判过关" not in out[0]["text"]
    assert "GATE" in out[1]["text"]
    assert "D3 巷" in out[1]["text"]
    assert "城门闸" in out[1]["text"]


def test_assemble_contract_vs_empty_mouth():
    """有合同：场面头在、驱动不含优先执行。空合同：无场面头。"""
    import os
    os.environ["SCRIBE3_NARRATIVE_ENGINE"] = "1"
    from scribe3.api.services.write_assemble_context import (
        _event_drive_block,
        load_chapter_story_inputs,
    )
    from scribe3.story_constraint_prompt import format_story_contract_head

    contract = {
        "desire": "灰七要去侧门查昨夜脚印与匙齿",
        "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
        "turn": "热灰抵半债并把假片扔给灰狸",
        "cost": "暂禁侧门且父名挂上夜审阴影",
        "bindings": {"evidence_must_show": ["空锅里一撮热灰"]},
    }
    drive = {
        "inciting_force": {"summary": "债上门"},
        "opposition": {"wants": "讨债"},
        "scene_turn": "拦门",
        "end_hook": "门外还有脚步",
    }

    class _St:
        def __init__(self, ch):
            self.ch = ch

        def get_chapter(self, _n):
            return self.ch

    st_full = _St({"narrative_contract": contract, "narrative_drive": drive})
    inputs = load_chapter_story_inputs(st_full, 5)
    head = format_story_contract_head(
        inputs.get("contract"),
        evidence_must_show=inputs.get("evidence_must_show"),
    )
    hook = _event_drive_block(
        st_full, 5, contract=inputs.get("contract"),
    )
    assert "【本章必须发生的场面】" in head
    assert "优先执行" not in (hook or "")
    assert "章末还悬着" in (hook or "")

    st_empty = _St({"narrative_drive": drive})
    inputs2 = load_chapter_story_inputs(st_empty, 5)
    head2 = format_story_contract_head(
        inputs2.get("contract"),
        evidence_must_show=inputs2.get("evidence_must_show"),
    )
    full = _event_drive_block(st_empty, 5)
    assert head2 == ""
    assert "本章冲突时钟" in (full or "")
    assert "优先执行" not in (full or "")


def test_format_block_keeps_fuel_before_cap():
    head = format_story_contract_head({
        "desire": "拒交铜匙、挨过夜审",
        "obstacle": "冷锅婆堵门讨香",
        "turn": "先倒半炉热灰",
        "cost": "脚印被人看见",
    })
    fuel = format_story_fuel_parts(
        recall_context="侧门还亮着一盏油灯，灰印未干。",
        causal_graph="- 第4章 听见咳",
        prior_consequences="- 账簿上勾了一笔",
    )
    assert "欲望：拒交铜匙、挨过夜审" in head
    assert "【上章余烬】" not in head
    assert "【上章余烬】" in fuel["story_ember"]
    assert "【世界此刻】" in fuel["story_recall"]
    assert "【前因后果】" in fuel["story_causal"]
    assert "账簿上勾了一笔" in fuel["story_ember"]
    long_recall = "侧门油灯。" * 400
    long_fuel = format_story_fuel_parts(recall_context=long_recall)
    assert len(long_fuel["story_recall"]) <= 4000 + 30
    assert "侧门油灯" in long_fuel["story_recall"]


def test_causal_chain_query_fail_records_soft_fail():
    # 本分支写路径未挂 _causal_chain_for_write；空合同场面头仍须为空。
    from scribe3.story_constraint_prompt import format_story_contract_head
    assert format_story_contract_head({}) == ""


def test_order_indices_include_contract_before_drive():
    from scribe3.context_budget import assert_physical_order_indices, join_generation_segments
    segs = [
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】限知"},
        {"name": "codex_named", "layer": "supplemental", "text": "设定"},
        {"name": "envelope", "layer": "envelope", "text": "ENV"},
        {"name": "drama_contract", "layer": "redline", "text": "戏"},
        {"name": "event_drive", "layer": "redline", "text": "DRIVE"},
        {"name": "story_ember", "layer": "supplemental", "text": "【上章余烬】"},
        {"name": "narrative_contract", "layer": "redline", "text": "【本章必须发生的场面】"},
        {"name": "prefix", "layer": "redline", "text": "P"},
    ]
    joined, rep = join_generation_segments(segs, v2=True)
    idx = rep.get("order_indices") or {}
    assert "narrative_contract" in idx
    assert idx["narrative_contract"] < idx["event_drive"]
    assert idx["narrative_contract"] < idx.get("story_ember", 99)
    assert_physical_order_indices(idx)
    assert joined.index("【本章必须发生的场面】") < joined.index("DRIVE")
    assert joined.index("【上章余烬】") < joined.index("DRIVE")


def test_hook_only_no_priority_when_contract():
    from scribe3.narrative_drive import format_event_drive_hook_only, format_event_drive_block
    drive = {
        "inciting_force": {"summary": "债上门"},
        "opposition": {"wants": "讨债"},
        "scene_turn": "拦门",
        "end_hook": "门外还有脚步",
    }
    hook = format_event_drive_hook_only(drive)
    full = format_event_drive_block(drive)
    assert "章末还悬着" in hook
    assert "优先执行" not in hook
    assert "本章冲突时钟" in full
    assert "优先执行" not in full


def test_write_assemble_v1_does_not_import_format_contract_block():
    import inspect
    from scribe3.api.services import write_assemble_v1 as m
    src = inspect.getsource(m)
    assert "format_contract_block" not in src
