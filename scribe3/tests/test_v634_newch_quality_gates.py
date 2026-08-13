"""第 6–10 章质量闸：驱动 shipped 函数，夹具来自现网全文。禁止写死合计字。"""
from __future__ import annotations

from pathlib import Path

from scribe3.anti_meta_narration import is_meta_span, scan_anti_meta
from scribe3.craft_leak_scan import scan_craft_leaks
from scribe3.prose_sanitize import (
    find_restaged_scene,
    sanitize_for_persist,
    strip_replacement_chars,
    visible_length,
)
from scribe3.reader_ready import beat_scene_keywords, scene_cover
from scribe3.pipeline_trace import headline_from_spans
from scribe3.run_card import ExpectedFacts, expected_for, row_verdict

EV = Path(__file__).resolve().parents[2] / "docs" / "evidence" / "v634-newch-20260814"
CH6 = (EV / "04-serialize" / "ch06.md").read_text(encoding="utf-8")
CH7 = (EV / "04-serialize" / "ch07.md").read_text(encoding="utf-8")

# demo GET /chapter 的 GATE-B 节拍（与现网一致）
CH6_BEATS = [
    {"text": "清册官在炉前摊开灯册要封炉。"},
    {"text": "阿绣把三户假账麻纸藏进木匣夹层。"},
    {"text": "霍三刀巷口按鞘观望不肯进场。"},
]


def test_n1_is_meta_span_does_not_kill_comma_prose():
    line = (
        "青黑长衫的人到了跟前，袖子里抖出一卷册子，也不铺垫，"
        "平着摊在炉门前的青砖上，正是《镇口铜炉灯册总登》。"
    )
    i = line.find("灯册")
    assert i >= 0
    assert is_meta_span(line, i, i + 2, []) is False
    seo = "伏笔触碰：灯册、封炉、刀鞘、夜税"
    j = seo.find("灯册")
    assert is_meta_span(seo, j, j + 2, []) is True


def test_n1_scene_cover_ch6_hits_landed_beats():
    assert "清册" in CH6 and "木匣" in CH6 and "灯册" in CH6
    keys0 = beat_scene_keywords(CH6_BEATS[0]["text"])
    assert "清册" in keys0 or "灯册" in keys0 or "封炉" in keys0
    keys1 = beat_scene_keywords(CH6_BEATS[1]["text"])
    assert "木匣" in keys1 or "麻纸" in keys1
    assert "木匣" in CH6 and "麻纸" in CH6
    sc = scene_cover(CH6, CH6_BEATS, [])
    assert sc["total"] == 3
    assert sc["valid"] >= 2
    assert sc["ok"] is True


def test_n2_furnace_and_sheath_markers_from_newch():
    assert "契就清" in CH6
    leaks6 = scan_craft_leaks(CH6, "role:沈拾灯")
    assert any(x["kind"] == "furnace_covenant" for x in leaks6)
    assert "从尸身上解" in CH7
    leaks7 = scan_craft_leaks(CH7, "role:霍三刀")
    assert any(x["kind"] == "sheath_contradiction" for x in leaks7)
    hinge_only = scan_craft_leaks("门轴声重，像有许久不曾开过。", "role:霍三刀")
    assert not any(x["kind"] == "side_door" for x in hinge_only)
    pick = scan_craft_leaks("他把铜签伸进锁眼，门轴没响。", "role:阿绣")
    assert any(x["kind"] == "side_door" for x in pick)


def test_n3_expected_for_matches_default_injectors():
    facts = ExpectedFacts(
        has_synopsis=True,
        has_beats=True,
        has_deduction=True,
        normalized_phase="final",
        phase="final",
    )
    assert expected_for("craft", facts) == (True, "always_engines")
    assert expected_for("purpose", facts)[0] is True
    assert expected_for("deduction_final", facts)[0] is True
    empty = ExpectedFacts()
    assert expected_for("craft", empty)[0] is True


def test_n4_skip_finalize_is_not_green():
    assert row_verdict(True, "empty") == "red"
    assert row_verdict(True, "present") == "green"
    h = headline_from_spans([{
        "step_key": "save.finalize_gate",
        "step_title": "定稿门",
        "verdict": "red",
        "actual": "empty",
        "actual_reason": "skipped_by_flag",
    }])
    assert "跳过" in h
    assert "对照齐全" not in h


def test_n5_replacement_char_and_restage_from_ch6():
    dirty = "炉火舔着膛。\ufffd沈拾灯没动。"
    assert "\ufffd" not in strip_replacement_chars(dirty)
    san = sanitize_for_persist(dirty)
    assert "replacement_char" in san["reasons"]
    assert "\ufffd" not in san["prose"]
    rest = find_restaged_scene(CH6)
    assert rest is not None
    assert len(rest["shared"]) >= 3
    san6 = sanitize_for_persist(CH6)
    assert "restaged_scene" in san6["reasons"]
    assert visible_length(CH6) > 80


def test_n0_anti_meta_still_clear_on_ch6_body():
    am = scan_anti_meta(CH6)
    assert am.get("ok_for_claim") is True


if __name__ == "__main__":
    test_n1_is_meta_span_does_not_kill_comma_prose()
    test_n1_scene_cover_ch6_hits_landed_beats()
    test_n2_furnace_and_sheath_markers_from_newch()
    test_n3_expected_for_matches_default_injectors()
    test_n4_skip_finalize_is_not_green()
    test_n5_replacement_char_and_restage_from_ch6()
    test_n0_anti_meta_still_clear_on_ch6_body()
    print("PASS test_v634_newch_quality_gates")
