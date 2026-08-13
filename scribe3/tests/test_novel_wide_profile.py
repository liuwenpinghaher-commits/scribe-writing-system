"""分档 96k：默认 48k；wide+窗+work 时 L2 与 O1 同为 96000。禁止本机 Surreal。"""
from __future__ import annotations

import os
from pathlib import Path

from scribe3.context_budget import (
    L0_NEVER_CUT,
    NOVEL_ENVELOPE_TOKEN_BUDGET,
    NOVEL_PROMPT_HARD,
    NOVEL_PROMPT_HARD_WIDE,
    WIDE_FUEL_CAP_CAUSAL,
    WIDE_FUEL_CAP_EMBER,
    WIDE_FUEL_CAP_RECALL,
    WIDE_MIN_MODEL_WINDOW,
    WIDE_SUPPLEMENTAL_HARD,
    WIDE_SUPPLEMENTAL_SOFT,
    DEFAULT_SUPPLEMENTAL_HARD,
    DEFAULT_SUPPLEMENTAL_SOFT,
    get_prompt_hard,
    get_supplemental_hard,
    get_supplemental_soft,
    get_total_prompt_budget,
    join_generation_segments,
    novel_wide_enabled,
    novel_wide_for_work,
    resolve_write_caps,
)
from scribe3.story_constraint_prompt import (
    FUEL_CAP_RECALL,
    format_story_fuel_parts,
    get_fuel_caps,
)


WIDE_ENV = (
    "SCRIBE3_NOVEL_WIDE",
    "SCRIBE3_NOVEL_PROMPT_HARD",
    "SCRIBE3_MODEL_CONTEXT_WINDOW",
    "SCRIBE3_NOVEL_WIDE_WORKS",
    "SCRIBE3_SUPPLEMENTAL_HARD",
    "SCRIBE3_SUPPLEMENTAL_SOFT",
    "SCRIBE3_TOTAL_BUDGET",
)


def _clear_wide():
    for k in WIDE_ENV:
        os.environ.pop(k, None)


def _segs():
    return [
        {"name": "prefix", "layer": "redline", "text": "P" * 20},
        {"name": "event_drive", "layer": "redline", "text": "【事件驱动】钉"},
        {"name": "drama_contract", "layer": "redline", "text": "【戏剧合同】钉"},
        {"name": "envelope", "layer": "envelope", "text": "E" * 100},
        {"name": "codex", "layer": "supplemental", "text": "设定" * 10},
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】限知"},
    ]


def test_hard_budget_constant_and_fuel_not_l0():
    assert NOVEL_PROMPT_HARD == 48000
    assert NOVEL_PROMPT_HARD_WIDE == 96000
    assert NOVEL_ENVELOPE_TOKEN_BUDGET == 22000
    for n in ("story_ember", "story_recall", "story_causal"):
        assert n not in L0_NEVER_CUT


def test_default_join_is_48k_without_wide_flag():
    _clear_wide()
    assert get_prompt_hard() == 48000
    assert get_prompt_hard(work="soak") == 48000
    assert get_supplemental_hard() == DEFAULT_SUPPLEMENTAL_HARD
    assert get_supplemental_soft() == DEFAULT_SUPPLEMENTAL_SOFT
    assert get_total_prompt_budget() == 48000
    _, rep = join_generation_segments(_segs(), v2=True)
    assert rep["prompt_hard"] == 48000
    assert (rep.get("l2") or {}).get("prompt_hard") == 48000
    assert (rep.get("total_enforce") or {}).get("total_budget") == 48000
    assert rep.get("novel_wide") is False


def test_wide_same_caps_on_l2_and_o1_for_listed_work():
    _clear_wide()
    os.environ["SCRIBE3_NOVEL_WIDE"] = "1"
    os.environ["SCRIBE3_MODEL_CONTEXT_WINDOW"] = "256000"
    os.environ["SCRIBE3_NOVEL_WIDE_WORKS"] = "soak"
    try:
        assert novel_wide_enabled() is True
        assert novel_wide_for_work("soak") is True
        assert novel_wide_for_work("other") is False
        assert novel_wide_for_work(None) is False
        assert get_prompt_hard(work="soak") == 96000
        assert get_prompt_hard(work="other") == 48000
        assert get_prompt_hard() == 48000
        assert get_supplemental_hard(work="soak") == WIDE_SUPPLEMENTAL_HARD
        assert get_supplemental_soft(work="soak") == WIDE_SUPPLEMENTAL_SOFT
        assert get_supplemental_hard(work="other") == DEFAULT_SUPPLEMENTAL_HARD
        caps = resolve_write_caps("soak")
        assert caps["prompt_hard"] == caps["total_budget"] == 96000
        _, rep = join_generation_segments(_segs(), v2=True, work="soak")
        assert rep["prompt_hard"] == 96000
        assert (rep.get("l2") or {}).get("prompt_hard") == 96000
        assert (rep.get("total_enforce") or {}).get("total_budget") == 96000
        assert (rep.get("l2") or {}).get("supplemental_hard") == 36000
        assert rep.get("novel_wide") is True
        _, narrow = join_generation_segments(_segs(), v2=True, work="other")
        assert narrow["prompt_hard"] == 48000
        assert (narrow.get("total_enforce") or {}).get("total_budget") == 48000
        _, bare = join_generation_segments(_segs(), v2=True)
        assert bare["prompt_hard"] == 48000
        assert bare.get("work_unspecified_narrow") is True
    finally:
        _clear_wide()


def test_wide_missing_window_raises_not_42k():
    _clear_wide()
    os.environ["SCRIBE3_NOVEL_WIDE"] = "1"
    os.environ.pop("SCRIBE3_MODEL_CONTEXT_WINDOW", None)
    try:
        raised = False
        try:
            get_prompt_hard(work="soak")
        except RuntimeError as e:
            raised = True
            assert "MODEL_CONTEXT_WINDOW" in str(e)
        assert raised
        try:
            get_total_prompt_budget(work="soak")
            total_swallowed = True
        except RuntimeError:
            total_swallowed = False
        assert total_swallowed is False
        try:
            join_generation_segments(_segs(), v2=True, work="soak")
            join_swallowed = True
        except RuntimeError:
            join_swallowed = False
        assert join_swallowed is False
    finally:
        _clear_wide()


def test_illegal_numeric_flag_raises():
    _clear_wide()
    os.environ["SCRIBE3_NOVEL_PROMPT_HARD"] = "72000"
    try:
        try:
            novel_wide_enabled()
            bad = False
        except RuntimeError as e:
            bad = True
            assert "72000" in str(e)
        assert bad
    finally:
        _clear_wide()


def test_window_too_small_raises():
    _clear_wide()
    os.environ["SCRIBE3_NOVEL_WIDE"] = "1"
    os.environ["SCRIBE3_MODEL_CONTEXT_WINDOW"] = "128000"
    try:
        try:
            novel_wide_enabled()
            ok = False
        except RuntimeError as e:
            ok = True
            assert str(WIDE_MIN_MODEL_WINDOW) in str(e)
        assert ok
    finally:
        _clear_wide()


def test_v1_join_passes_work():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "join_generation_segments(segs, v2=_v2, work=work)" in src
    assert "collect_story_fuel_segments(_inputs, work=work)" in src


def test_auto_96k_when_model_window_large_without_flag():
    """产品默认：窗够大就 96k，不必再翻 WIDE=1。"""
    _clear_wide()
    os.environ.pop("SCRIBE3_NOVEL_WIDE", None)
    os.environ["SCRIBE3_MODEL_CONTEXT_WINDOW"] = "256000"
    try:
        assert novel_wide_enabled() is True
        assert get_prompt_hard(work="main") == 96000
        assert get_supplemental_hard(work="main") == WIDE_SUPPLEMENTAL_HARD
        assert get_fuel_caps(work="main")["recall"] == WIDE_FUEL_CAP_RECALL
        _, rep = join_generation_segments(_segs(), v2=True, work="main")
        assert rep["prompt_hard"] == 96000
        assert (rep.get("total_enforce") or {}).get("total_budget") == 96000
    finally:
        _clear_wide()


def test_explicit_wide_off_stays_48k_even_with_large_window():
    _clear_wide()
    os.environ["SCRIBE3_NOVEL_WIDE"] = "0"
    os.environ["SCRIBE3_MODEL_CONTEXT_WINDOW"] = "1000000"
    try:
        assert novel_wide_enabled() is False
        assert get_prompt_hard(work="main") == 48000
        assert get_fuel_caps(work="main")["recall"] == FUEL_CAP_RECALL
    finally:
        _clear_wide()


def test_wide_fuel_caps_keep_more_story_memory():
    _clear_wide()
    long_recall = "侧门油灯。" * 1500
    narrow = format_story_fuel_parts(recall_context=long_recall)
    os.environ["SCRIBE3_NOVEL_WIDE"] = "1"
    os.environ["SCRIBE3_MODEL_CONTEXT_WINDOW"] = "256000"
    try:
        wide = format_story_fuel_parts(recall_context=long_recall, work="main")
        assert len(narrow["story_recall"]) <= FUEL_CAP_RECALL + 30
        assert len(wide["story_recall"]) > len(narrow["story_recall"])
        assert len(wide["story_recall"]) <= WIDE_FUEL_CAP_RECALL + 30
        caps = get_fuel_caps(work="main")
        assert caps == {
            "ember": WIDE_FUEL_CAP_EMBER,
            "recall": WIDE_FUEL_CAP_RECALL,
            "causal": WIDE_FUEL_CAP_CAUSAL,
        }
    finally:
        _clear_wide()
