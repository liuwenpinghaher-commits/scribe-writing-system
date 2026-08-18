"""章设计合成闸：纯函数金样。禁止 Surreal。"""
from __future__ import annotations

import os

from scribe3.chapter_spine import parse_choice_ab
from scribe3.clue_density import (
    _ab_same,
    chapter_design_mode,
    evaluate_chapter_design,
)
from scribe3.iceberg import design_half_block, persist_fields_blocked
from scribe3.design_attempt import first_passed, record_attempt
from scribe3.stage_generate import (
    _DESIGN_ASK,
    _BEATS_ASK,
    _OUTLINE_ASK,
    _split_beat_chunks,
    dispatch_design_stage,
    merge_chapter_design,
    parse_chapter_design_payload,
    parse_designated_beat,
    planning_system_prompt,
    thicken_chapter_design,
)
from scribe3.tests.test_chapter_spine import G1, KNOWN
from scribe3.tests.test_iceberg import _GCD_BEATS
from scribe3.tests.test_stage_generate import _DRY_BEATS, _DRY_OUTLINE
from scribe3.world_surface import extra_authors, extra_gold, extra_gold_blocked

# 指定拍（默认拍2）必须落下 decision/cost 内容词，否则旗 on 报 beat_off_spine
_GOLD_BEATS = [
    dict(_GCD_BEATS[0]),
    {
        **_GCD_BEATS[1],
        "turn": "门更死咳了一声；纸角朝门里推回一分",
        "cost": "账清了门更死；门内咳像爹未兑",
    },
    dict(_GCD_BEATS[2]),
]


def setup_module():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"


def test_chapter_design_mode_default_on():
    old = os.environ.get("SCRIBE3_CHAPTER_DESIGN")
    try:
        os.environ.pop("SCRIBE3_CHAPTER_DESIGN", None)
        assert chapter_design_mode() in ("on", "off")
        os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
        assert chapter_design_mode() == "on"
        os.environ["SCRIBE3_CHAPTER_DESIGN"] = "off"
        assert chapter_design_mode() == "off"
        os.environ["SCRIBE3_CHAPTER_DESIGN"] = "typo"
        assert chapter_design_mode() == "off"
    finally:
        if old is None:
            os.environ.pop("SCRIBE3_CHAPTER_DESIGN", None)
        else:
            os.environ["SCRIBE3_CHAPTER_DESIGN"] = old


def test_ab_same_table():
    p1 = parse_choice_ab("交核 vs 自按")
    p1b = parse_choice_ab("把碎片交出去 vs 自己按回去")
    assert p1 and p1b and _ab_same(p1, p1b)
    p2 = parse_choice_ab("硬还焦黑暴露埋灰人 vs 只把纸角塞回门缝")
    p2b = parse_choice_ab("硬还焦黑暴露 vs 纸角塞回门缝")
    assert p2 and p2b and _ab_same(p2, p2b)
    p3 = parse_choice_ab("交碎片给沈烛换活 vs 自己按回裂口暴露双权柄")
    assert p3 and _ab_same(p3, p3)
    n1 = parse_choice_ab("开门 vs 关门")
    assert p1 and n1 and not _ab_same(p1, n1)
    n2 = parse_choice_ab("硬还焦黑暴露 vs 纸角塞回门缝")
    p3n = parse_choice_ab("交碎片给沈烛换活 vs 自己按回裂口")
    assert p3n and n2 and not _ab_same(p3n, n2)
    n3 = parse_choice_ab("交令牌 vs 按住腕")
    assert p1 and n3 and not _ab_same(p1, n3)


def test_design_ask_does_not_fail_whole_page_on_forty_chars():
    assert "每槽汉字≤40" not in _DESIGN_ASK
    assert "超了整份作废" not in _DESIGN_ASK
    long = dict(G1)
    long["goal"] = "沈拾灯要在大遮蔽闭锁前按场核成核，并确认成核点没有把他的指针态复制进金縢箱锁里"
    r = evaluate_chapter_design(long, list(_GOLD_BEATS), known_line_ids=KNOWN)
    assert r.ok, r.errors
    assert not any(str(e).startswith("spine_slots_long") for e in r.errors)


def test_planning_paper_has_no_lock_words():
    sys = planning_system_prompt()
    assert "责任" in sys
    assert "侧门开法" not in sys
    assert "拨锁" not in sys


def test_merge_keeps_passed_slots():
    base_beats = [dict(b) for b in _GOLD_BEATS]
    spine, beats = merge_chapter_design(
        G1, base_beats,
        {"hook": "新钩还悬着"},
        [{}, {"choice": "硬还焦黑暴露 vs 纸角塞回门缝"}, {}],
    )
    assert spine["goal"] == G1["goal"]
    assert spine["hook"] == "新钩还悬着"
    assert beats[0]["goal"] == base_beats[0]["goal"]
    assert "硬还" in (beats[1].get("choice") or "")


def test_design_exam_allows_full_sentence_without_prescribed_verb():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    beats = [dict(b) for b in _GOLD_BEATS]
    beats[0]["turn"] = "他看见自己站在箱的另一侧，烧痕还在加深"
    r = evaluate_chapter_design(G1, beats, known_line_ids=KNOWN)
    assert r.ok, r.errors
    assert not any(str(e).startswith("beat_gcd") for e in r.errors)


def test_evaluate_chapter_design_gold():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    r = evaluate_chapter_design(G1, list(_GOLD_BEATS), known_line_ids=KNOWN)
    assert r.ok, r.errors
    half = evaluate_chapter_design(G1, [], known_line_ids=KNOWN)
    assert not half.ok
    assert "beat_count" in half.errors or any("beat" in e for e in half.errors)


def test_second_choice_and_not_staged():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    beats = [dict(b) for b in _GOLD_BEATS]
    beats[0]["choice"] = "开门 vs 关门"
    r = evaluate_chapter_design(G1, beats, known_line_ids=KNOWN)
    assert not r.ok
    assert "second_choice" in r.errors
    beats2 = [dict(b) for b in _GOLD_BEATS]
    beats2[1]["choice"] = ""
    r2 = evaluate_chapter_design(G1, beats2, known_line_ids=KNOWN)
    assert "choice_not_staged" in r2.errors


def test_parse_chapter_design_gold():
    gold = _DRY_OUTLINE + "\n选拍：2\n" + _DRY_BEATS
    parsed = parse_chapter_design_payload(gold)
    assert parsed["ok"] is True
    assert parsed["chapter_spine"]["goal"]
    assert len(parsed["beats"]) >= 3
    assert parsed["designated_beat"] == 2
    only_spine = parse_chapter_design_payload(_DRY_OUTLINE)
    assert only_spine["ok"] is False
    assert only_spine["code"] == "design_beats_unparsed"
    assert _split_beat_chunks(_DRY_OUTLINE, fallback=False) == []


def test_parse_choice_slash_ab():
    from scribe3.chapter_spine import parse_choice_ab
    from scribe3.clue_density import _ab_same
    a = parse_choice_ab("交核 / 自按")
    b = parse_choice_ab("把碎片交出去 / 自己按回去")
    assert a and b and _ab_same(a, b)


def test_parse_designated_beat_rules():
    assert parse_designated_beat("选拍：3", 3) == 3
    assert parse_designated_beat("选拍：9", 3) == 2
    assert parse_designated_beat("选拍：x", 3) == 2
    assert parse_designated_beat("没有标签", 3) == 2
    assert parse_designated_beat("选拍：1", 1) == 1


def test_extra_gold_does_not_scan_ask():
    assert extra_gold(_DESIGN_ASK) == []
    assert extra_gold(_OUTLINE_ASK) == []
    assert extra_gold(_BEATS_ASK) == []
    assert extra_gold_blocked("请按拍2演出选择", "draft") == []
    assert extra_gold_blocked("请按拍2演出选择", "final") == []
    assert extra_gold("请按拍2演出选择") == []
    assert extra_gold("## 拍1\n要：把假铜挡在眼皮外") == ["extra_gold"]
    assert extra_gold("拍1：把假铜挡在眼皮外") == ["extra_gold"]
    assert extra_gold(_DRY_OUTLINE) == ["extra_gold"]
    assert extra_gold("请把选择写清楚，不要口号") == []
    assert extra_authors("必须有一句母亲咳") == ["extra_authors"]


def test_dispatch_beats_stage_merged():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    hit = dispatch_design_stage("beats", {}, extra="")
    assert hit and hit.get("code") == "stage_merged"
    ready = {
        "chapter_spine": G1,
        "beats": list(_GOLD_BEATS),
    }
    skip = dispatch_design_stage("beats", ready, extra="")
    assert skip and skip.get("ok") is True
    assert "章设计已过" in (skip.get("skipped") or "")


def test_persist_design_half_top_code():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_CLUE_DENSITY"] = "on"
    blk = persist_fields_blocked({"chapter_spine": G1}, existing={})
    assert blk
    assert blk["code"] == "design_half"
    assert any(m.get("id") == "design_half" for m in blk.get("missing") or [])
    half = design_half_block("spine_without_beats")
    assert half["code"] == "design_half"


def test_persist_repair_merged_choice_mismatch():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_CLUE_DENSITY"] = "on"
    existing = {"chapter_spine": G1, "beats": list(_GOLD_BEATS)}
    new_spine = dict(G1, choice="开门 vs 关门")
    blk = persist_fields_blocked({"chapter_spine": new_spine}, existing=existing)
    assert blk
    ids = [m.get("id") for m in (blk.get("missing") or [])]
    assert "choice_not_staged" in ids or "choice_not_staged" in (blk.get("message") or "")


def test_thicken_full_rewrite_not_slot_patch():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    gold = _DRY_OUTLINE + "\n选拍：2\n" + _DRY_BEATS
    thin = gold.replace("选：硬还焦黑暴露 vs 纸角塞回门缝", "选：无")
    prompts: list[str] = []
    n = {"i": 0}

    def llm(prompt, max_tokens=4096):
        prompts.append(prompt)
        n["i"] += 1
        return thin if n["i"] == 1 else gold

    r = thicken_chapter_design({}, llm_fn=llm, persist_fn=lambda f: None, seq=1)
    assert not any("只补没过" in p for p in prompts)
    assert any("整份重写" in p for p in prompts)
    assert len(prompts) >= 2
    assert r.get("attempts")


def test_thicken_chapter_design_does_not_persist_thin():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    called = {"n": 0}

    def llm(prompt, max_tokens=4096):
        return "一句口号。"

    def persist(fields):
        called["n"] += 1

    out = thicken_chapter_design({}, llm_fn=llm, persist_fn=persist)
    assert out.get("ok") is False
    assert called["n"] == 0


def test_thicken_chapter_design_persists_once_on_gold():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    persisted = {}
    gold = _DRY_OUTLINE + "\n" + _DRY_BEATS

    def llm(prompt, max_tokens=4096):
        return gold

    r = thicken_chapter_design(
        {},
        llm_fn=llm,
        persist_fn=lambda f: persisted.update(f),
        seq=1,
    )
    if r.get("ok"):
        assert "chapter_spine" in persisted
        assert "beats" in persisted
        assert (persisted.get("beats_meta") or {}).get("schema_design") == "chapter_design.v1"
    else:
        # 命运闸可能拦无钟地；不得半稿
        assert "chapter_spine" not in persisted or "beats" in persisted


# ── 接得上这本书 ──────────────────────────────────────────────

from scribe3.clue_density import (
    BindableLine,
    DesignBook,
    choice_is_mirror,
    design_book_mode,
    extract_focus_names,
    same_landmark,
    topic_grams,
    topics_overlap,
)
from scribe3.iceberg import persist_fields_blocked, sync_design_surface
from scribe3.stage_generate import merge_chapter_design, merge_clock_place_patch

_PTR = BindableLine("promise", "ptr-line", "成核点开始复制他的指针态")
_BOX = BindableLine("promise", "box-line", "金縢箱锁未开，谁先碰谁付账")
_KNOWN_WB = {("promise", "ptr-line"), ("promise", "box-line")}


def _wb(**kw) -> DesignBook:
    base = dict(
        seq=1,
        title="华山成核",
        focus_names=("沈拾灯",),
        character_names=frozenset(),
        item_names=frozenset({"金縢之箱", "场核碎片"}),
        place_names=frozenset(),
        term_names=frozenset({"指针态", "成核点", "场核", "金縢", "伪真空"}),
        bindable_lines=(_PTR, _BOX),
        prev_place_name="",
        prev_hook="",
    )
    base.update(kw)
    return DesignBook(**base)


def _wb_spine(**kw) -> dict:
    row = {
        "setting": "甲辰年腊月廿八夜，华山北峰灯亭",
        "cast": "沈拾灯；金縢箱锁",
        "bite": "灯亭已热，箱未开",
        "goal": "沈拾灯要按场核成核，确认成核点没有外溢",
        "obstacle": "金縢箱锁只认同频，脚步变贵",
        "inciting": "第七盏灯无风自转",
        "escalation": "场核不在岩里，在第八盏灯",
        "choice": "交核 vs 自按",
        "decision": "沈拾灯把场核按回自己腕里",
        "cost": "大遮蔽撕开一档，成核点开始跟他的指针态渗光",
        "info_gap": "他知场核在腕；箱锁不知",
        "lines": [{"kind": "promise", "id": "ptr-line", "delta": "成核点开始复制他的指针态"}],
        "hook": "金縢账还没人认",
        "forbid": "无",
        "schema": "chapter_spine.v1",
    }
    row.update(kw)
    return row


def _wb_beats(choice: str = "交核 vs 自按") -> list[dict]:
    return [
        {
            "id": "b1", "goal": "沈拾灯沿七灯找到场核", "conflict": "箱锁按住灯亭",
            "turn": "场核在第八盏灯里", "cost": "右腕陷进灯口", "choice": "",
        },
        {
            "id": "b2", "goal": "必须交核还是自按", "conflict": "箱锁回弹",
            "turn": "他自按场核进腕", "cost": "大遮蔽撕开一档", "choice": choice,
        },
        {
            "id": "b3", "goal": "用脉搏给金縢裂缝上拍", "conflict": "箱缝只开一角",
            "turn": "账卡在缝里", "cost": "金縢账还没人认", "choice": "",
        },
    ]


def test_design_book_mode_default_on():
    old_d = os.environ.get("SCRIBE3_DESIGN_BOOK")
    old_c = os.environ.get("SCRIBE3_CHAPTER_DESIGN")
    try:
        os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
        os.environ.pop("SCRIBE3_DESIGN_BOOK", None)
        assert design_book_mode() == "on"
        os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
        assert design_book_mode() == "on"
        os.environ["SCRIBE3_DESIGN_BOOK"] = "off"
        assert design_book_mode() == "off"
        os.environ["SCRIBE3_DESIGN_BOOK"] = "typo"
        assert design_book_mode() == "off"
        os.environ["SCRIBE3_CHAPTER_DESIGN"] = "off"
        os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
        assert design_book_mode() == "off"
    finally:
        if old_d is None:
            os.environ.pop("SCRIBE3_DESIGN_BOOK", None)
        else:
            os.environ["SCRIBE3_DESIGN_BOOK"] = old_d
        if old_c is None:
            os.environ.pop("SCRIBE3_CHAPTER_DESIGN", None)
        else:
            os.environ["SCRIBE3_CHAPTER_DESIGN"] = old_c


def test_form_exam_without_book_still_gold():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    r = evaluate_chapter_design(G1, list(_GOLD_BEATS), known_line_ids=KNOWN)
    assert r.ok, r.errors


def test_empty_bible_focus_plus_box_ok():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    names = extract_focus_names("焦点沈拾灯", {"focalizer": "role:沈拾灯"})
    assert "沈拾灯" in names
    book = _wb(focus_names=names)
    r = evaluate_chapter_design(
        _wb_spine(), _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert r.ok, r.errors


def test_invented_names_fail():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    book = _wb()
    for cast in ("周青臣；沈拾灯", "两个抬箱人；沈拾灯", "守观老道周青臣"):
        r = evaluate_chapter_design(
            _wb_spine(cast=cast), _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
        )
        assert "cast_invented" in r.errors, (cast, r.errors)
    r = evaluate_chapter_design(
        _wb_spine(cast="沈拾灯；金縢箱锁；民初年落成的铁铸灯亭"),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "cast_invented" not in r.errors, r.errors
    r = evaluate_chapter_design(
        _wb_spine(cast="焦点=沈拾灯；对手=金縢之箱；见证=华山北峰"),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "cast_invented" not in r.errors, r.errors


def test_place_rules():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    book = _wb(seq=2, prev_place_name="华山北峰", prev_hook="金縢账还没人认")
    spine = _wb_spine(bite="金縢箱缝还在渗")
    beats = _wb_beats()
    r = evaluate_chapter_design(
        spine, beats, known_line_ids=_KNOWN_WB, book=book,
        place={"name": "侧门旧库", "delta": 0},
    )
    assert "place_name_mismatch" in r.errors or "place_travel_unsaid" in r.errors
    r = evaluate_chapter_design(
        spine, beats, known_line_ids=_KNOWN_WB, book=book,
        place={"name": "华山北峰伪真空口", "delta": 0},
    )
    assert "place_name_mismatch" not in r.errors, r.errors
    r = evaluate_chapter_design(
        spine, beats, known_line_ids=_KNOWN_WB, book=book,
        place={"name": "华山西峰", "delta": 0},
    )
    assert "place_travel_unsaid" in r.errors or "place_name_mismatch" in r.errors
    r = evaluate_chapter_design(
        _wb_spine(setting="夜，灯亭未动", bite="金縢箱缝还在渗"),
        beats, known_line_ids=_KNOWN_WB, book=book,
        place={"name": "医院", "delta": 2},
    )
    assert "place_travel_unsaid" in r.errors
    r = evaluate_chapter_design(
        _wb_spine(setting="从灯亭搬到伪真空口", bite="金縢箱缝还在渗"),
        beats, known_line_ids=_KNOWN_WB, book=book,
        place={"name": "华山北峰伪真空口", "delta": 2},
    )
    assert "place_travel_unsaid" not in r.errors, r.errors
    r = evaluate_chapter_design(
        _wb_spine(setting="伪真空口外缘向华山北峰折返的崖道上", bite="金縢箱缝还在渗"),
        beats, known_line_ids=_KNOWN_WB, book=book,
        place={"name": "伪真空口", "delta": 1},
    )
    assert "place_travel_unsaid" not in r.errors, r.errors
    r = evaluate_chapter_design(
        _wb_spine(setting="沿栈道折返到华山北峰医疗站", bite="金縢箱缝还在渗"),
        beats, known_line_ids=_KNOWN_WB,
        book=_wb(seq=2, prev_place_name="伪真空口", prev_hook="金縢账还没人认"),
        place={"name": "华山北峰", "delta": 0},
    )
    assert "place_travel_unsaid" not in r.errors, r.errors
    assert same_landmark("华山北峰", "华山北峰伪真空口")
    assert same_landmark("华山北峰灯亭", "华山北峰")
    assert not same_landmark("华山北峰", "华山西峰")


def test_clock_jump_only_delta_ge_2():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    book = _wb(seq=2, prev_place_name="华山北峰", prev_hook="金縢账还没人认")
    spine = _wb_spine(bite="金縢箱缝还在渗")
    beats = _wb_beats()
    r = evaluate_chapter_design(
        spine, beats, known_line_ids=_KNOWN_WB, book=book,
        clock={"span": "day", "delta": 0},
        place={"name": "华山北峰", "delta": 0},
    )
    assert "clock_jump_unsaid" not in r.errors, r.errors
    r = evaluate_chapter_design(
        spine, beats, known_line_ids=_KNOWN_WB, book=book,
        clock={"span": "stretch", "delta": 2},
        place={"name": "华山北峰", "delta": 0},
    )
    assert "clock_jump_unsaid" in r.errors


def test_bite_rules():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    r = evaluate_chapter_design(
        _wb_spine(bite="接上一口余烬"), _wb_beats(),
        known_line_ids=_KNOWN_WB, book=_wb(seq=1),
    )
    assert "bite_false_prev" in r.errors
    r = evaluate_chapter_design(
        _wb_spine(bite="灯亭已热，箱未开"), _wb_beats(),
        known_line_ids=_KNOWN_WB, book=_wb(seq=1),
    )
    assert "bite_false_prev" not in r.errors, r.errors
    book2 = _wb(seq=2, prev_hook="金縢账还没人认", prev_place_name="华山北峰")
    r = evaluate_chapter_design(
        _wb_spine(bite="金縢箱缝还在渗"), _wb_beats(),
        known_line_ids=_KNOWN_WB, book=book2,
        place={"name": "华山北峰", "delta": 0},
    )
    assert "bite_off_hook" not in r.errors, r.errors
    r = evaluate_chapter_design(
        _wb_spine(bite="箱缝还在渗"), _wb_beats(),
        known_line_ids=_KNOWN_WB,
        book=_wb(seq=2, prev_hook="成核点开始复制他的指针态", prev_place_name="华山北峰"),
        place={"name": "华山北峰", "delta": 0},
    )
    assert "bite_off_hook" in r.errors


def test_line_rules_title_first():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    book = _wb(title="金縢箱锁")
    r = evaluate_chapter_design(
        _wb_spine(lines=[{"kind": "promise", "id": "ptr-line", "delta": ""}]),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "line_delta_empty" in r.errors
    r = evaluate_chapter_design(
        _wb_spine(lines=[{"kind": "promise", "id": "ptr-line", "delta": "他把账本翻到下一页"}]),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=_wb(title="华山成核"),
    )
    assert "line_off_topic" in r.errors
    r = evaluate_chapter_design(
        _wb_spine(
            goal="",
            lines=[{"kind": "promise", "id": "ptr-line", "delta": "成核点开始复制他的指针态"}],
        ),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "line_wrong_bind" in r.errors
    r = evaluate_chapter_design(
        _wb_spine(
            goal="按场核成核确认成核点",
            lines=[{"kind": "promise", "id": "ptr-line", "delta": "成核点开始复制他的指针态"}],
        ),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "line_wrong_bind" in r.errors
    r = evaluate_chapter_design(
        _wb_spine(lines=[{
            "kind": "promise", "id": "box-line",
            "delta": "箱锁开了一缝，账还没人认",
        }]),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "line_wrong_bind" not in r.errors, r.errors
    assert "line_off_topic" not in r.errors, r.errors
    r = evaluate_chapter_design(
        _wb_spine(
            goal="按金縢箱锁抽出第一笔账",
            lines=[{"kind": "promise", "id": "ptr-line", "delta": "成核点开始复制他的指针态"}],
        ),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=_wb(title="夜观"),
    )
    assert "line_wrong_bind" in r.errors


def test_choice_mirror_strips_left_right():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    from scribe3.chapter_spine import parse_choice_ab
    assert not choice_is_mirror(parse_choice_ab("交核 vs 自按"))
    assert choice_is_mirror(parse_choice_ab("左半身按进缝 vs 右半身按进缝"))
    assert choice_is_mirror(parse_choice_ab("左半身留下 vs 右半身留下"))
    r = evaluate_chapter_design(
        _wb_spine(choice="左半身留下 vs 右半身留下"),
        _wb_beats("左半身留下 vs 右半身留下"),
        known_line_ids=_KNOWN_WB, book=_wb(),
    )
    assert "choice_mirror" in r.errors


def test_allow_keys_keeps_choice():
    spine, beats = merge_chapter_design(
        _wb_spine(choice="交核 vs 自按"),
        _wb_beats("交核 vs 自按"),
        _wb_spine(choice="左半身留下 vs 右半身留下", lines=[{
            "kind": "promise", "id": "box-line", "delta": "箱锁开了一缝",
        }]),
        [{"choice": "左半身留下 vs 右半身留下"}, {}, {}],
        allow_keys={"lines"},
    )
    assert spine["choice"] == "交核 vs 自按"
    assert "箱锁" in str(spine["lines"])


def test_place_patch_this_round_wins():
    clock, place = merge_clock_place_patch(
        {"span": "scene", "delta": 1},
        {"name": "侧门旧库", "delta": 0},
        {},
        {"name": "华山北峰"},
        allow_keys={"place.name", "place.delta", "place.stay_reason",
                    "clock.span", "clock.delta", "clock.freeze_reason"},
    )
    assert place["name"] == "华山北峰"


def test_sync_synopsis_overwrite_vs_synopsis_only_vs_flag_off():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    existing = {"synopsis": "许鹘从伪真空口把账抽出，唐绞用单锚压缝"}
    out = sync_design_surface({"chapter_spine": _wb_spine()}, existing)
    assert "许鹘" not in (out.get("synopsis") or "")
    assert "沈拾灯" in (out.get("synopsis") or "")
    only = sync_design_surface({"synopsis": "许鹘还在"}, existing)
    assert only["synopsis"] == "许鹘还在"
    old = os.environ.get("SCRIBE3_DESIGN_BOOK")
    try:
        os.environ["SCRIBE3_DESIGN_BOOK"] = "off"
        kept = sync_design_surface({"chapter_spine": _wb_spine()}, existing)
        assert "synopsis" not in kept
    finally:
        if old is None:
            os.environ.pop("SCRIBE3_DESIGN_BOOK", None)
        else:
            os.environ["SCRIBE3_DESIGN_BOOK"] = old


def test_involved_empty_vs_hit():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    out = sync_design_surface({"chapter_spine": _wb_spine()}, {})
    assert out.get("involved_characters") == []

    class _St:
        def characters(self):
            return [{"id": "role:沈拾灯", "name": "沈拾灯"}]

    hit = sync_design_surface({"chapter_spine": _wb_spine()}, {}, store=_St())
    assert hit.get("involved_characters")


def test_store_without_book_fail_loud():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    blk = persist_fields_blocked(
        {"chapter_spine": _wb_spine(), "beats": _wb_beats()},
        existing={},
        known_line_ids=_KNOWN_WB,
        store=object(),
        book=None,
    )
    assert blk
    ids = [m.get("id") for m in (blk.get("missing") or [])]
    assert "design_book_missing" in ids


def test_open_lines_block_uses_title_for_storyline():
    class _St:
        def list_promises(self):
            return [{"id": "p1", "text": "成核点开始复制他的指针态"}]
        def list_storylines(self):
            return [{"id": "s1", "title": "金縢未开", "notes": "主线"}]
        def get_promise(self, pid):
            return {"id": pid, "text": "成核点开始复制他的指针态"}
        def get_storyline(self, pid):
            return {"id": pid, "title": "金縢未开"}

    from scribe3.chapter_spine import known_line_ids_from_store
    # 桩没有 known_line_ids_from_store 协议，直接测拼装函数内部 list
    from scribe3.stage_generate import _line_text_from_row
    assert _line_text_from_row({"title": "金縢未开", "notes": "主线"}, kind="storyline") == "金縢未开"
    assert "复制" in _line_text_from_row({"text": "成核点开始复制他的指针态"}, kind="promise")


def test_topic_grams_gold():
    book = _wb()
    assert topics_overlap("金縢箱锁", "金縢箱锁未开，谁先碰谁付账", book)
    assert not topics_overlap("金縢箱锁", "成核点开始复制他的指针态", book)
    assert topics_overlap("金縢箱缝还在渗", "金縢账还没人认", book)
    assert "开始" not in topic_grams("成核点开始复制他的指针态", book)


def test_cast_paren_and_item_tail_not_invented():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    from scribe3.clue_density import invented_cast_names
    book = _wb(item_names=frozenset({"金縢之箱", "场核碎片"}), focus_names=("沈拾灯",))
    assert not invented_cast_names(
        "焦点=沈拾灯；对手/见证=金縢之箱（在伪真空口内侧浮定）。", book,
    )
    assert not invented_cast_names(
        "焦点=沈拾灯；见证=金縢之箱、第九盏灯、场核碎片。", book,
    )
    book2 = _wb(
        item_names=frozenset({"九鼎", "场核碎片"}),
        character_names=frozenset({"柳岸青"}),
        focus_names=("柳岸青",),
    )
    assert not invented_cast_names(
        "焦点=柳岸青；对手=九鼎（悬于伪真空口上方的物件/机制）；见证=场核碎片（随行归位）。",
        book2,
    )
    assert not invented_cast_names(
        "焦点=柳岸青；对手/见证=九鼎与金縢之箱并置于伪真空口上方；无新造人名。",
        book2,
    )
    r = evaluate_chapter_design(
        _wb_spine(cast="焦点=沈拾灯；对手/见证=金縢之箱（在伪真空口内侧浮定）。"),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "cast_invented" not in r.errors, r.errors
    r = evaluate_chapter_design(
        _wb_spine(cast="周青臣；金縢之箱（在口内侧）"),
        _wb_beats(), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "cast_invented" in r.errors


def test_must_happen_empty_skips():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    r = evaluate_chapter_design(
        _wb_spine(), _wb_beats(), known_line_ids=_KNOWN_WB, book=_wb(),
    )
    assert "event_unmet" not in r.errors, r.errors
    assert "who_unmet" not in r.errors, r.errors
    assert "bill_unmet" not in r.errors, r.errors


def test_duty_event_and_bill_and_who():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    from scribe3.clue_density import extract_duty
    who, event, bill = extract_duty(
        "谁：柳岸青按碎片；沈烛切断观测\n事：把碎片交出去还是自己按回去\n账：大遮蔽改锁，世界认他的心跳"
    )
    assert "沈烛" in who and "按回去" in event and "大遮蔽" in bill
    book = _wb(
        character_names=frozenset({"柳岸青", "沈烛", "赫斯"}),
        focus_names=("柳岸青",),
        duty_who="柳岸青按碎片；沈烛切断观测；赫斯要带走",
        duty_event="把碎片交出去，还是自己按回去",
        duty_bill="大遮蔽改锁，世界开始认他的心跳",
        must_happen="把碎片交出去，还是自己按回去",
    )
    r = evaluate_chapter_design(
        _wb_spine(goal="沈拾灯要在灯亭吞核", choice="吞核 vs 按回第八盏灯", decision="他吞核",
                  cast="沈拾灯；金縢箱锁", cost="灯亭发热"),
        _wb_beats("吞核 vs 按回第八盏灯"),
        known_line_ids=_KNOWN_WB, book=book,
    )
    assert "event_unmet" in r.errors or "who_unmet" in r.errors or "bill_unmet" in r.errors
    r = evaluate_chapter_design(
        _wb_spine(
            cast="柳岸青；沈烛；赫斯",
            goal="柳岸青要把场核碎片按回裂口，不交给守火人；沈烛切断观测，赫斯要带走",
            obstacle="沈烛切断观测耦合，赫斯要把他标成样本",
            choice="把碎片交出去 vs 自己按回去",
            decision="他自己按回碎片",
            cost="大遮蔽改锁，世界开始认他的心跳",
        ),
        _wb_beats("把碎片交出去 vs 自己按回去"),
        known_line_ids=_KNOWN_WB, book=book,
    )
    assert "event_unmet" not in r.errors, r.errors
    assert "who_unmet" not in r.errors, r.errors
    assert "bill_unmet" not in r.errors, r.errors
    r = evaluate_chapter_design(
        _wb_spine(
            cast="柳岸青；赫斯",
            goal="柳岸青要把场核碎片按回裂口",
            choice="把碎片交出去 vs 自己按回去",
            decision="他自己按回碎片",
            cost="大遮蔽改锁，世界开始认他的心跳",
        ),
        _wb_beats("把碎片交出去 vs 自己按回去"),
        known_line_ids=_KNOWN_WB, book=book,
    )
    assert "who_unmet" in r.errors


def test_first_passed_uses_whole_version_not_stitch():
    a = record_attempt(1, {"ok": True, "chapter_spine": {"choice": "去医院 vs 找箱"}, "beats": [1, 2, 3]}, None)
    a["exam_ok"] = False
    a["errors"] = ["bill_unmet"]
    b = record_attempt(2, {"ok": True, "chapter_spine": {"choice": "开箱 vs 焊死"}, "beats": [1, 2, 3]}, None)
    b["exam_ok"] = True
    b["errors"] = []
    win = first_passed([a, b])
    assert win is b
    assert win["chapter_spine"]["choice"] == "开箱 vs 焊死"
    assert first_passed([a]) is None


def test_duty_bill_body_heat_not_world_word():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    book = _wb(
        duty_event="去医院降温，还是连夜去找金縢",
        duty_bill="四十二度退不下去，箱子开始裂",
        must_happen="去医院降温，还是连夜去找金縢",
    )
    r = evaluate_chapter_design(
        _wb_spine(
            goal="去医院降温，还是连夜去找金縢",
            choice="去医院降温 vs 连夜去找金縢",
            decision="他进医院降温",
            cost="四十二度退不下去，金縢箱壁开始裂",
            lines=[{"kind": "promise", "id": "box-line", "delta": "箱锁开了一缝，账还没人认"}],
        ),
        _wb_beats("去医院降温 vs 连夜去找金縢"),
        known_line_ids=_KNOWN_WB, book=book,
    )
    assert "bill_unmet" not in r.errors, r.errors


def test_must_happen_binds_same_topic_line():
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "on"
    os.environ["SCRIBE3_DESIGN_BOOK"] = "on"
    book = _wb(must_happen="去医院降温 vs 连夜找金縢")
    gold_choice = "去医院降温 vs 连夜找金縢"
    r = evaluate_chapter_design(
        _wb_spine(
            goal="柳岸青要在去医院降温和连夜找金縢之间选一条",
            choice=gold_choice,
            decision="他连夜找金縢",
            lines=[{"kind": "promise", "id": "box-line", "delta": "箱锁开了一缝，账还没人认"}],
        ),
        _wb_beats(gold_choice), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "line_wrong_bind" not in r.errors, r.errors
    r = evaluate_chapter_design(
        _wb_spine(
            goal="柳岸青要在去医院降温和连夜找金縢之间选一条",
            choice=gold_choice,
            decision="他连夜找金縢",
            lines=[{"kind": "promise", "id": "ptr-line", "delta": "成核点开始复制他的指针态"}],
        ),
        _wb_beats(gold_choice), known_line_ids=_KNOWN_WB, book=book,
    )
    assert "line_wrong_bind" in r.errors
