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


def test_three_tier_gates_and_scorer_v2():
    from scribe3.memory_gain import (
        score_prose_heuristic_v2, three_tier_gates, comparison_protocol,
    )
    a = score_prose_heuristic_v2(
        "覃灰七" * 5 + "三棱铜匙缺口" + "冷锅婆" + "一炉香债" + ("正文" * 1200),
        "缺口",
        label="A",
    )
    b = score_prose_heuristic_v2(
        "覃灰七" * 2 + "铜腥" * 10 + ("正文" * 900),
        "缺口",
        label="B",
    )
    # 铜腥多不应把 B 的 echo 抬到与 A 同档
    assert a["canon_echo"] >= b["canon_echo"]
    keys = ("coherence", "canon_echo", "contradiction")
    avg_a = sum(a[k] for k in keys) / 3
    avg_b = sum(b[k] for k in keys) / 3
    g = three_tier_gates(avg_a, avg_b, a, b)
    assert "engineering_gate" in g and "machine_pass_rule_met" in g
    assert g["pass_rule_met"] == g["machine_pass_rule_met"]
    assert g["human_pass_rule_met"] is None
    p = comparison_protocol()
    assert "escalation" in p["tracks"]["track2_memory_contrib"]


def test_iron_strip_mode(monkeypatch):
    import os
    import scribe3.memory_gain as mg
    os.environ["SCRIBE3_MEMORY_IRON_IN_ABLATION"] = "strip"
    assert mg.iron_strip_mode() == "strip"
    assert mg.should_strip_iron_laws() is True
    os.environ["SCRIBE3_MEMORY_IRON_IN_ABLATION"] = "keep"
    assert mg.iron_strip_mode() == "keep"
    assert mg.should_strip_iron_laws() is False


def test_reorder_l1_first_prioritizes_must():
    from scribe3.context_assembler import ContextAssembler

    class _Src:
        def __init__(self, sid, reason=""):
            self.source_id = sid
            self.reason = reason

    class _I:
        def __init__(self, text, sid, reason=""):
            self.text = text
            self.source = _Src(sid, reason)

    noise = _I("- 噪声杂项" * 5, "noise:1")
    must = _I("- 〔压力〕物件「匙」当前状态：缺口", "must_link:x", "must_link_priority")
    ca = ContextAssembler.__new__(ContextAssembler)
    out = ContextAssembler._reorder_l1_first(ca, [noise, must])
    assert "压力" in out[0].text
    assert out[0] is must


def test_build_must_prefix_respects_ablation(monkeypatch):
    import scribe3.memory_must_link as mml
    monkeypatch.setattr(mml, "ablation_disables_must_link", lambda: True)
    assert mml.build_must_prefix(None, 1) == ""
