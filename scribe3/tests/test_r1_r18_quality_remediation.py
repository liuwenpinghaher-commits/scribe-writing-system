"""R1–R18 纯函数：剥尾/禁元/headline/装段/scene_cover/leak/账本。禁止 Surreal。"""
from __future__ import annotations

from scribe3.anti_meta_narration import scan_anti_meta
from scribe3.craft_leak_scan import scan_craft_leaks, sheath_canon_block
from scribe3.drama_beats import format_drama_block
from scribe3.pipeline_trace import (
    TraceBuffer,
    ember_read_kwargs,
    headline_from_spans,
    pred_value_from_named,
    public_log,
    render_log,
)
from scribe3.prose_sanitize import (
    fill_placeholder_title,
    sanitize_for_persist,
    strip_machine_tail,
    strip_pollution,
    visible_length,
)
from scribe3.reader_ready import beat_scene_keywords, scene_cover


DIRTY_TAIL = (
    "炉火舔着膛。沈拾灯没动。{'scope': 'chapter', 'prose': '炉火舔着膛。', 'fallback': True}"
)
DIRECTOR = "开写前先理一条线：账与心。正文如下：\n\n## 第二章 夜税\n\n清早霜没化尽。"


def test_r1_strip_machine_tail_and_fallback():
    clean = strip_machine_tail(DIRTY_TAIL)
    assert "fallback" not in clean
    assert "scope" not in clean
    assert "炉火舔着膛" in clean
    san = sanitize_for_persist(DIRTY_TAIL)
    assert "fallback" not in san["prose"]
    assert "machine_tail" in san["reasons"]


def test_r1_r2_director_and_anti_meta_blocking():
    r = scan_anti_meta(DIRECTOR)
    ids = r.get("claim_blocking_ids") or []
    assert "M7" in ids
    assert r.get("ok_for_claim") is False
    peeled = strip_pollution(DIRECTOR)
    assert "开写前" not in peeled
    assert "正文如下" not in peeled
    assert "霜没化尽" in peeled


def test_r16_visible_length_strips_pollution():
    n_raw = len("".join(DIRTY_TAIL.split()))
    n_vis = visible_length(DIRTY_TAIL)
    assert n_vis < n_raw
    assert n_vis == visible_length(strip_pollution(DIRTY_TAIL))


def test_r3_headline_never_contrast_complete():
    h = headline_from_spans([])
    assert "对照齐全" not in h
    skip = headline_from_spans([{
        "step_key": "save.finalize_gate",
        "step_title": "定稿门",
        "verdict": "green",
        "actual_reason": "skipped_by_flag",
    }])
    assert "跳过" in skip
    assert "对照齐全" not in skip


def test_r5_drama_slogan_beats_nonempty():
    blk = format_drama_block([
        {"text": "霍三刀下令封炉一夜。"},
        {"text": "阿绣以身挡炉。"},
    ], focalizer="role:沈拾灯")
    assert blk.strip()
    assert "必须发生" in blk
    assert "封炉" in blk


def test_r12_scene_cover_slogan_hits_scene_words():
    beats = [
        {"text": "霍三刀下令封炉一夜。"},
        {"text": "沈拾灯想起灯芯里的父债。"},
        {"text": "阿绣以身挡炉，封炉未成。"},
    ]
    prose = "霍三刀说今晚封炉一夜。沈拾灯看见灯芯。阿绣挡在炉前。"
    keys = beat_scene_keywords(beats[0]["text"])
    assert any(k in prose for k in keys)
    sc = scene_cover(prose, beats, [])
    assert sc["total"] == 3
    assert sc["valid"] >= 2
    assert sc["ok"] is True
    assert sc["beat_ratio"] >= 2 / 3


def test_r9_r11_r13_craft_leaks():
    ch4 = "老桂把铜签伸进锁眼拨了两下，门轴没响。"
    leaks = scan_craft_leaks(ch4, focalizer="role:阿绣")
    kinds = {x["kind"] for x in leaks}
    assert "side_door" in kinds
    ch5 = "头一个名字便得拿自个儿去填炉底。这不是胡话，是炉契。"
    leaks5 = scan_craft_leaks(ch5, focalizer="role:沈拾灯")
    assert any(x["kind"] == "furnace_covenant" for x in leaks5)
    ch3 = "阿绣说你当年在军中欠了一条人命。"
    leaks3 = scan_craft_leaks(ch3, focalizer="role:沈拾灯")
    assert any(x["kind"] == "unearned_knowing" for x in leaks3)
    sheath = scan_craft_leaks("这鞘是你爹的东西。", "role:沈拾灯")
    assert any(x["kind"] == "sheath_contradiction" for x in sheath)
    assert "霍三刀" in sheath_canon_block()


def test_r15_placeholder_title():
    got = fill_placeholder_title("第3章", "霍三刀逼沈拾灯封炉一夜", 3)
    assert got.startswith("第3章·")
    assert "霍三刀" in got
    assert fill_placeholder_title("第五章·当众揭册", "x", 5) == "第五章·当众揭册"


def test_r17_append_log_chinese_and_ember_not_from_push():
    a = ember_read_kwargs("", 0)
    assert a["empty"] is True and a["chars_in"] == 0
    b = ember_read_kwargs("有钩子字", 0)
    assert b["empty"] is False and b["chars_in"] > 0
    assert pred_value_from_named(True) is True
    rec, store = render_log(
        "read.source",
        {"source": "chapter_prev_end_hook", "empty": True, "chars_in": 0},
        trace_id="ab" * 16, span_id="cd" * 8, work="book_x", chapter=1, kind="write",
    )
    assert rec is not None
    assert "读取" in rec["message"]
    pub = public_log({**rec, "step_key": "assemble.seg.story_ember", "step_title": "上章余烬", "log_id": "1"})
    assert pub["step_key"] == "assemble.seg.story_ember"
    assert pub["empty"] is True
    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=2, kind="write", phase="draft", trace_id="ef" * 16)
    sid = buf.start_span("assemble.seg.outline")
    buf.append_log(sid, "read.source", source="outline", empty=False, chars_in=12)
    buf.end_span(sid, status="ok", actual="present", output={"chars": 12})
    rows = buf.drain_logs()
    assert rows
    assert any(r.get("step_key") == "assemble.seg.outline" for r in rows)
    assert any("开始" in (r.get("message") or "") or r.get("code") == "step.start" for r in rows)


def test_r4_author_copy_string_in_source():
    from pathlib import Path
    src = (
        Path(__file__).resolve().parents[1] / "api/routers/misc_routes.py"
    ).read_text(encoding="utf-8")
    assert "已存草稿（不可宣称可读）" in src
    assert "skipped_by_flag" in src
    ui = (
        Path(__file__).resolve().parents[1] / "web/src/WriteLayout.jsx"
    ).read_text(encoding="utf-8")
    assert "author_copy" in ui
    page = (
        Path(__file__).resolve().parents[1] / "web/src/admin/RunLogsPage.jsx"
    ).read_text(encoding="utf-8")
    assert "pipelineLogs" in page
    assert "run-logs-lines" in page
    assert "对照齐全" not in page


if __name__ == "__main__":
    test_r1_strip_machine_tail_and_fallback()
    test_r1_r2_director_and_anti_meta_blocking()
    test_r16_visible_length_strips_pollution()
    test_r3_headline_never_contrast_complete()
    test_r5_drama_slogan_beats_nonempty()
    test_r12_scene_cover_slogan_hits_scene_words()
    test_r9_r11_r13_craft_leaks()
    test_r15_placeholder_title()
    test_r17_append_log_chinese_and_ember_not_from_push()
    test_r4_author_copy_string_in_source()
    print("PASS test_r1_r18_quality_remediation")
