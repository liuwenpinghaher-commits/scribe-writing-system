"""v4 记忆表面：消融模式、注入单真、对照协议、主锚过滤（纯逻辑，无 DB）。"""
from __future__ import annotations

import os

from scribe3.fact_surface import (
    normalize_state_attribute,
    resolve_injection_facts,
    resolve_injection_facts_with_stats,
    values_mutually_exclusive,
)
from scribe3.memory_gain import comparison_protocol
from scribe3.memory_must_link import (
    ablation_disables_fact_injection,
    ablation_disables_must_link,
    ablation_mode,
    format_fact_as_drama,
    must_link_limit,
)
from scribe3.ontology import Fact


def test_normalize_state_attribute_unifies_slots():
    assert normalize_state_attribute("condition", "齿边有缺口") == "state"
    assert normalize_state_attribute("status", "重伤") == "state"
    assert normalize_state_attribute("location", "旧库") == "location"


def test_resolve_injection_drops_dual_truth():
    facts = [
        Fact("fact:old", "world:三棱铜匙", "artifact",
             "三棱铜匙完整无缺", valid_from=1),
        Fact("fact:new", "world:三棱铜匙", "condition",
             "齿边有缺口", valid_from=4),
    ]
    kept, dropped = resolve_injection_facts_with_stats(facts)
    assert len(kept) == 1
    assert dropped >= 1
    assert "缺口" in kept[0].value
    assert "完整无缺" not in kept[0].value
    assert values_mutually_exclusive("完整无缺", "齿边有缺口")


def test_ablation_modes(monkeypatch):
    import scribe3.memory_must_link as mml
    monkeypatch.setattr(
        mml, "_setting_str", lambda k, d="": os.environ.get(k) or d)
    monkeypatch.setenv("SCRIBE3_MEMORY_ABLATION", "no_must_facts")
    assert ablation_mode() == "no_must_facts"
    assert ablation_disables_must_link() is True
    assert ablation_disables_fact_injection() is True
    monkeypatch.setenv("SCRIBE3_MEMORY_ABLATION", "none")
    assert ablation_mode() == "none"
    assert ablation_disables_must_link() is False


def test_comparison_protocol_v2_tracks():
    p = comparison_protocol()
    assert p["name"] == "memory_gain_ab_v2"
    assert "track2_memory_contrib" in p["tracks"]
    assert p["tracks"]["track2_memory_contrib"]["primary"] is True
    assert "no_must_facts" in p["tracks"]["track2_memory_contrib"]["env_b"]


def test_format_fact_drama_not_checklist():
    t = format_fact_as_drama("world:三棱铜匙", "state", "齿边有缺口")
    assert "·state=" not in t
    assert "物件" in t or "状态" in t


def test_main_cast_filters_extra():
    from scribe3.context_assembler import _main_cast_names

    class C:
        def __init__(self, name, imp):
            self.name = name
            self.traits = {"importance": imp}

    names = _main_cast_names([
        C("覃灰七", "protagonist"),
        C("冷锅婆", "major"),
        C("王二嫂", "extra"),
        C("路人甲", "extra"),
    ], limit=10)
    assert "覃灰七" in names
    assert "冷锅婆" in names
    assert "王二嫂" not in names


def test_must_link_limit_bounds(monkeypatch):
    import scribe3.memory_must_link as mml
    monkeypatch.setattr(
        mml, "get_setting", lambda k: (_ for _ in ()).throw(RuntimeError("no")),
        raising=False,
    )
    # force env path via failing get_setting inside must_link_limit
    monkeypatch.setenv("SCRIBE3_MUST_LINK_LIMIT", "8")
    # patch get_setting import failure path
    def _boom(key):
        raise RuntimeError("skip settings")
    monkeypatch.setattr(
        "scribe3.settings.get_setting", _boom, raising=False)
    n = must_link_limit(10)
    assert 3 <= n <= 24
