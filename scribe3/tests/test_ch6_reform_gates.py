"""第6章改造门：headline / causal 人话 / drama 残片 / persist 扫词。零 Surreal。"""
from __future__ import annotations

from scribe3.drama_beats import format_drama_block
from scribe3.iceberg_leak import (
    PersistIcebergLeak,
    find_iceberg_leak_words,
    reject_persist_leaks,
    scan_persist_fields_for_leaks,
)
from scribe3.pipeline_trace import headline_from_spans
from scribe3.story_causal_text import humanize_causal_body, is_internal_event_id


def test_headline_thicken_skip_is_not_finalize_gate():
    h = headline_from_spans(
        [{
            "step_key": "assemble.seg.drama_vacuum",
            "step_title": "戏剧真空",
            "verdict": "red",
            "actual_reason": "skip_vacuum_has_contract_or_planning",
        }, {
            "step_key": "assemble.seg.codex_named",
            "step_title": "点名设定",
            "actual_reason": "injected",
            "verdict": "red",
        }, {
            "step_key": "llm.generate",
            "status": "succeeded",
        }],
        phase="outline",
    )
    assert "定稿门跳过" not in h
    assert "对照齐全" not in h


def test_headline_finalize_skip_still_says_gate():
    h = headline_from_spans([{
        "step_key": "save.finalize_gate",
        "step_title": "定稿门",
        "verdict": "green",
        "actual_reason": "skipped_by_flag",
    }])
    assert "定稿门跳过" in h


def test_causal_humanize_drops_event_ids():
    raw = (
        "【前因后果】\n"
        "- event:i5-0\n"
        "- event:⟨i5-1⟩\n"
        "- 第三章 · 炉册点名 → 第四章 · 注入对照（门槛迈不过去）\n"
    )
    got = humanize_causal_body(raw)
    assert "event:" not in got
    assert "i5-0" not in got
    assert "炉册点名" in got
    assert is_internal_event_id("event:i5-0")
    assert is_internal_event_id("⟨i5-0⟩")
    assert not is_internal_event_id("第四章 · 注入对照")


def test_drama_text_slots_no_double_colon():
    beats = [{
        "text": (
            "**进场：** 日头偏西。\n"
            "**事件：**：这不是说好的数。先前说好的是三斤半炉灰。\n"
            "**翻转：** 灰狸走到跟前挡住视线。\n"
            "**出场：** 灰狸举着铜片。\n"
            "**水下：** 他不能接那片铜。\n"
        ),
    }]
    blk = format_drama_block(beats, focalizer="role:qin_huiqi")
    assert blk.strip()
    assert "：：" not in blk
    assert "::" not in blk
    assert "这不是说好的数" in blk or "挡住" in blk


def test_persist_leak_scan_catches_lock_eye():
    assert find_iceberg_leak_words("门缝里的风") == []
    assert "锁眼" in find_iceberg_leak_words("匙齿探进锁眼试深浅")
    hits = scan_persist_fields_for_leaks({
        "beats": [{"text": "**水下：** 没有把锁眼那片新铜盖住"}],
        "scene_truth": "锁眼外沿",
        "draft": "干净的门缝",
    })
    words = {h["word"] for h in hits}
    fields = {h["field"] for h in hits}
    assert "锁眼" in words
    assert "beats" in fields and "scene_truth" in fields
    assert "draft" not in fields
    try:
        reject_persist_leaks({"draft": "门芯被拨开"})
    except PersistIcebergLeak as exc:
        assert exc.hits
        assert any(h["word"] == "门芯" for h in exc.hits)
    else:
        raise AssertionError("expected PersistIcebergLeak")


def test_iceberg_ok_for_false_when_leak_in_beats():
    from scribe3.stage_generate import iceberg_ok_for
    fat = "门缝里的风。" + ("铜腥炉灰空锅磕青石。" * 80)
    ch = {
        "synopsis": fat,
        "beats": [
            {"text": fat},
            {"text": fat},
            {"text": fat + "没有把锁眼那片新铜盖住"},
        ],
        "scene_truth": fat,
        "deductions": [{"text": fat}, {"text": fat}],
        "draft": fat * 3,
    }
    assert iceberg_ok_for(ch, "beats") is False
    clean = {
        "synopsis": fat,
        "beats": [{"text": fat}, {"text": fat}, {"text": fat}],
        "scene_truth": fat,
        "deductions": [{"text": fat}, {"text": fat}, {"text": fat}],
        "draft": fat * 3,
    }
    assert iceberg_ok_for(clean, "beats") is True


if __name__ == "__main__":
    test_headline_thicken_skip_is_not_finalize_gate()
    test_headline_finalize_skip_still_says_gate()
    test_causal_humanize_drops_event_ids()
    test_drama_text_slots_no_double_colon()
    test_persist_leak_scan_catches_lock_eye()
    print("ok")
