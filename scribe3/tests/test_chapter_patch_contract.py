"""U2：sanitize merge + persist false + 漂移判定（不启 Surreal）。"""
from __future__ import annotations

from scribe3.narrative_contract import (
    contract_content_fp,
    load_scene_suggest,
    sanitize_narrative_contract_write,
    suggest_scene_contract,
)


def test_sanitize_patch_turn_keeps_scene_voice():
    prev = {
        "desire": "灰七要去侧门查昨夜脚印与匙齿",
        "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
        "turn": "热灰抵半债并把假片扔给灰狸",
        "cost": "暂禁侧门且父名挂上夜审阴影",
        "bindings": {"scene_voice": {"register": "冷硬"}, "narrative_drive_fp": "abc123"},
    }
    out = sanitize_narrative_contract_write(
        {"turn": "热灰抵半债后假片打发灰狸走了"},
        source="author",
        prev=prev,
    )
    assert out["turn"].startswith("热灰抵半债后")
    assert out["desire"] == prev["desire"]
    assert out["bindings"]["scene_voice"]["register"] == "冷硬"
    assert out["bindings"]["narrative_drive_fp"] == "abc123"
    assert out["source"] == "author"


def test_empty_to_empty_fp_not_drift():
    a = contract_content_fp(None)
    b = contract_content_fp({})
    c = contract_content_fp({"desire": "", "obstacle": "", "turn": "", "cost": ""})
    assert a == b == c


def test_stale_plan_fp_differs_after_write():
    old = {
        "desire": "灰七要去侧门查昨夜脚印与匙齿",
        "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
        "turn": "热灰抵半债并把假片扔给灰狸",
        "cost": "暂禁侧门且父名挂上夜审阴影",
    }
    new = dict(old)
    new["turn"] = "热灰抵半债后改口不认假片"
    assert contract_content_fp(old) != contract_content_fp(new)


def test_suggest_persist_false_no_write():
    sug = suggest_scene_contract({"title": "空"})
    assert sug["persist"] is False
    assert "briefing" in sug


class _Store:
    def __init__(self):
        self.ch = {
            2: {
                "seq": 2,
                "title": "债",
                "narrative_drive": {
                    "inciting_force": {"summary": "昨夜脚印未散想再查侧门"},
                    "end_hook": "门外还有人",
                },
            },
            1: {
                "seq": 1,
                "narrative_contract": {
                    "desire": "灰七要去侧门查昨夜脚印与匙齿",
                    "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
                    "turn": "热灰抵半债并把假片扔给灰狸",
                    "cost": "暂禁侧门且父名挂上夜审阴影",
                },
                "narrative_drive": {"end_hook": "锅里还烫"},
            },
        }

    def get_chapter(self, seq):
        return self.ch.get(int(seq), {})

    def open_promises(self):
        return []


def test_load_scene_suggest_has_prev_and_persist_false():
    sug = load_scene_suggest(_Store(), 2)
    assert sug["persist"] is False
    assert sug["briefing"]["prev"]["seq"] == 1
    assert "热灰抵半债" in (sug["briefing"]["prev"]["contract"].get("turn") or "")
