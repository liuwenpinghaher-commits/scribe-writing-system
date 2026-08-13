"""P1：brief_must 相对大纲/场面合同差集。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble_context import (
    _brief_must_item_covered,
    _brief_must_sections_write_block,
    _filter_brief_must_against_cover,
    _outline_contract_cover_text,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


CONTRACT = {
    "desire": "灰七要去侧门查昨夜脚印与匙齿",
    "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
    "turn": "热灰抵半债并把假片扔给灰狸",
    "cost": "暂禁侧门且父名挂上夜审阴影",
    "bindings": {"evidence_must_show": ["空锅里一撮热灰"]},
}


class _St:
    def get_chapter(self, seq):
        return {
            "synopsis": "灰七要去侧门查昨夜脚印与匙齿",
            "beats": [{"text": "热灰抵半债并把假片扔给灰狸"}],
            "narrative_contract": CONTRACT,
        }


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_cover_text_includes_outline_and_contract():
    cover = _outline_contract_cover_text(_St(), 5)
    assert "脚印与匙齿" in cover
    assert "热灰抵半债" in cover
    assert "空锅里一撮热灰" in cover
    assert "香债拦门" in cover


def test_item_covered_matches_inner_payload():
    cover = _outline_contract_cover_text(_St(), 5)
    assert _brief_must_item_covered("灰七要去侧门查昨夜脚印与匙齿", cover)
    assert _brief_must_item_covered("【伏笔·本章指令】空锅里一撮热灰", cover)
    assert not _brief_must_item_covered("井底的名字还没揭", cover)


def test_filter_drops_echo_keys_keeps_unique():
    sec = {
        "promises": {
            "directives": ["灰七要去侧门查昨夜脚印与匙齿", "井底的名字还没揭"],
            "reminders": ["空锅里一撮热灰"],
            "decisions": [],
        },
        "arcs": ["【角色弧光·灰七】谎念未破"],
        "causal": {"directives": ["热灰抵半债并把假片扔给灰狸"]},
    }
    cover = _outline_contract_cover_text(_St(), 5)
    out, n = _filter_brief_must_against_cover(sec, cover)
    assert n >= 3
    assert out["promises"]["directives"] == ["井底的名字还没揭"]
    assert out["promises"]["reminders"] == []
    assert out["causal"]["directives"] == []
    assert out["arcs"] == ["【角色弧光·灰七】谎念未破"]


def test_write_block_uses_real_helper_and_drops_echoes():
    import scribe3.brief as brief_mod

    def fake_brief(st, seq, focalizer=""):
        return {
            "sections": {
                "purpose": {"text": "不该进 must"},
                "drama_contract": {"text": "戏剧合同也不该进"},
                "promises": {
                    "directives": ["灰七要去侧门查昨夜脚印与匙齿", "井底的名字还没揭"],
                    "reminders": ["空锅里一撮热灰"],
                    "decisions": [],
                },
                "arcs": ["【角色弧光·灰七】谎念未破"],
            }
        }

    orig = brief_mod.assemble_chapter_brief
    brief_mod.assemble_chapter_brief = fake_brief
    try:
        text = _brief_must_sections_write_block(
            _St(), 5, focalizer="role:灰七", must_link_already_pinned=True,
        )
    finally:
        brief_mod.assemble_chapter_brief = orig
    assert "井底的名字还没揭" in text
    assert "谎念未破" in text
    assert "脚印与匙齿" not in text
    assert "空锅里一撮热灰" not in text
    assert "不该进 must" not in text
    assert "戏剧合同也不该进" not in text
    assert "已省略与大纲/场面合同重复" in text


def test_v1_still_calls_shipped_helper():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "_brief_must_sections_write_block(st, chapter, focalizer=focalizer or \"\")" in src
    assert '_push("brief_must"' in src
