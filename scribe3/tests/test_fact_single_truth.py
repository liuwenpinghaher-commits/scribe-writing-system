"""记忆质量 D4：同 (entity, attribute) 单真值折叠与注入面互斥消解（无 DB 纯逻辑）。"""
from __future__ import annotations

from scribe3.fact_surface import (
    collapse_facts_single_truth,
    resolve_injection_facts,
    resolve_injection_facts_with_stats,
    values_mutually_exclusive,
)
from scribe3.ontology import Fact


def test_collapse_keeps_latest_valid_from():
    facts = [
        Fact("fact:old", "world:匙", "condition", "完整无缺", valid_from=1),
        Fact("fact:new", "world:匙", "condition", "齿边有缺口", valid_from=3),
    ]
    out = collapse_facts_single_truth(facts)
    assert len(out) == 1
    assert out[0].id == "fact:new"
    assert out[0].value == "齿边有缺口"


def test_collapse_different_attributes_both_kept_if_no_conflict():
    facts = [
        Fact("fact:a", "world:匙", "artifact", "三棱铜匙·匙柄三点星", valid_from=1),
        Fact("fact:b", "world:匙", "location", "旧库", valid_from=3),
    ]
    out = collapse_facts_single_truth(facts)
    assert len(out) == 2


def test_resolve_drops_exclusive_across_attributes():
    """根因回归：artifact 含完整无缺 + condition 缺口 → 注入面只留较新。"""
    facts = [
        Fact("fact:old", "world:三棱铜匙", "artifact",
             "匙柄内侧刻炉心印；三棱铜匙完整无缺", valid_from=1),
        Fact("fact:new", "world:三棱铜匙", "condition",
             "三棱铜匙齿边有一处新缺口，像被炉门咬过", valid_from=3),
    ]
    out = resolve_injection_facts(facts)
    assert len(out) == 1
    assert out[0].id == "fact:new"
    assert "缺口" in out[0].value
    assert "完整无缺" not in out[0].value


def test_values_mutually_exclusive():
    assert values_mutually_exclusive("完整无缺", "齿边有缺口")
    assert not values_mutually_exclusive("匙柄三点星", "旧库侧门")


def test_resolve_with_stats_counts_drops():
    facts = [
        Fact("fact:old", "world:三棱铜匙", "artifact",
             "三棱铜匙完整无缺", valid_from=1),
        Fact("fact:new", "world:三棱铜匙", "condition",
             "齿边有缺口", valid_from=3),
    ]
    kept, n = resolve_injection_facts_with_stats(facts)
    assert len(kept) == 1
    assert n >= 1


def test_collapse_dict_rows():
    rows = [
        {"id": "old", "entity_id": "role:甲", "attribute": "状态", "value": "重伤", "valid_from": 1},
        {"id": "new", "entity_id": "role:甲", "attribute": "状态", "value": "痊愈", "valid_from": 5},
    ]
    out = collapse_facts_single_truth(rows)
    assert len(out) == 1
    assert out[0]["value"] == "痊愈"


def test_collapse_tie_prefers_later_in_list():
    facts = [
        Fact("fact:a", "e", "a", "v1", valid_from=2),
        Fact("fact:b", "e", "a", "v2", valid_from=2),
    ]
    out = collapse_facts_single_truth(facts)
    assert len(out) == 1
    assert out[0].value == "v2"
