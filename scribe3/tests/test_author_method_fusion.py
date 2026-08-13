"""38 融合：检索别名、可见性、无计划零字节、清单不进组装。打真实函数。"""
from __future__ import annotations

from pathlib import Path

from scribe3.author_method.catalog import (
    AR_FILES,
    CATALOG,
    FEMALE_ID,
    list_catalog,
    read_body,
    visible_count,
)
from scribe3.author_method.panels import CHECKLIST_ITEMS, checklist_prompt_text
from scribe3.craft_skills import list_skills, read_skill
from scribe3.story_move import (
    OH_STORY_SOURCE_STEMS,
    load_seed_cards,
    render_story_move_segment,
    retrieve_story_move,
    same_formula_family,
)


def test_catalog_visible_37_hides_female():
    assert len(CATALOG) == 38
    vis = list_catalog(include_hidden=False)
    ids = {r["id"] for r in vis}
    assert FEMALE_ID not in ids
    assert visible_count() == 37
    assert all(read_body(r["id"]).strip() for r in CATALOG)
    assert sum(1 for r in CATALOG if r["ar"]) == 25
    assert AR_FILES == {r["id"] for r in CATALOG if r["ar"]}


def test_craft_skills_still_four_and_no_banned_table():
    skills = list_skills()
    assert len(skills) == 4
    slugs = {s["slug"] for s in skills}
    assert slugs == {"场景转换", "对话潜台词", "节奏控制", "限知视角"}
    joined = "\n".join(read_skill(s["slug"]) for s in skills)
    assert "_BANNED_LEXICON" not in joined
    assert "anti-ai-writing.md" not in joined


def test_five_cards_and_retrieve_aliases():
    cards = load_seed_cards()
    assert [c["slug"] for c in cards] == [
        "triangle_info",
        "bond_tear",
        "one_word_crush",
        "speech_wither",
        "withhold_escalate",
    ]
    for q in ("欲扬先抑", "金锁三拍", "装逼打脸", "暗牌"):
        hit = retrieve_story_move(q)
        assert len(hit) == 1
        assert hit[0]["slug"] == "triangle_info", q
    tear = retrieve_story_move("羁绊撕裂")
    assert len(tear) == 1
    assert tear[0]["slug"] == "bond_tear"
    assert tear[0]["slug"] != "triangle_info"
    assert retrieve_story_move("心死")[0]["slug"] == "speech_wither"
    assert retrieve_story_move("压制")[0]["slug"] == "one_word_crush"
    assert retrieve_story_move("延宕")[0]["slug"] == "withhold_escalate"


def test_same_formula_family_triangle_not_bond():
    cards = {c["slug"]: c for c in load_seed_cards()}
    assert same_formula_family(cards["triangle_info"], {
        "formula_family": "false_break_true",
        "formula": {"arrow": "假→破→真", "beats": []},
    })
    assert not same_formula_family(cards["triangle_info"], cards["bond_tear"])


def test_no_approved_plan_zero_bytes():
    empty = render_story_move_segment({}, enabled=True)
    assert empty["text"] == ""
    assert empty["meta"]["applied"] is False
    flagged_off = render_story_move_segment(
        {"approved": True, "benyi": "穷", "move_id": "triangle_info", "validation": {"ok": True}},
        enabled=False,
    )
    assert flagged_off["text"] == ""
    ok = render_story_move_segment(
        {"approved": True, "benyi": "穷", "move_id": "triangle_info", "validation": {"ok": True}},
        enabled=True,
    )
    assert "三角" in ok["text"]
    assert ok["meta"]["applied"] is True
    for stem in OH_STORY_SOURCE_STEMS:
        assert stem not in ok["text"]


def test_checklist_never_enters_prompt():
    selected = [i for i, _ in CHECKLIST_ITEMS]
    assert checklist_prompt_text(selected) == ""
    assert checklist_prompt_text(None) == ""
    plan_text = render_story_move_segment(
        {"approved": True, "benyi": "穷", "move_id": "triangle_info", "validation": {"ok": True}},
        enabled=True,
    )["text"]
    for cid, label in CHECKLIST_ITEMS:
        assert cid not in plan_text
        assert label not in plan_text


def test_physical_order_story_move_before_final_reminder():
    from scribe3.context_budget import generation_physical_order_names
    names = generation_physical_order_names()
    assert names.index("storyline_polish") < names.index("story_move")
    assert names.index("story_move") < names.index("final_reminder")
    from scribe3.injection_registry import SEGMENT_REGISTRY
    assert any(s.name == "story_move" for s in SEGMENT_REGISTRY)


def test_flag_registered():
    from scribe3.feature_flags import FLAG_REGISTRY
    names = {f.name for f in FLAG_REGISTRY}
    assert "SCRIBE3_MOVE_LIBRARY" in names
    from scribe3.review.blocking import is_blocking_issue
    assert is_blocking_issue({"type": "discourse.hook_plan", "meta": {"severity": "S1"}}) is False
