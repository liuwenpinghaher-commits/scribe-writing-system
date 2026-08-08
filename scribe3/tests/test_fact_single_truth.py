"""记忆质量 D4：同 (entity, attribute) 单真值折叠与 supersede 语义（无 DB 纯逻辑）。"""
from __future__ import annotations

from scribe3.ontology import Fact
from scribe3.store.facts_knowledge import collapse_facts_single_truth


def test_collapse_keeps_latest_valid_from():
    facts = [
        Fact("fact:old", "world:匙", "condition", "完整无缺", valid_from=1),
        Fact("fact:new", "world:匙", "condition", "齿边有缺口", valid_from=3),
    ]
    out = collapse_facts_single_truth(facts)
    assert len(out) == 1
    assert out[0].id == "fact:new"
    assert out[0].value == "齿边有缺口"


def test_collapse_different_attributes_both_kept():
    facts = [
        Fact("fact:a", "world:匙", "artifact", "三棱铜匙", valid_from=1),
        Fact("fact:b", "world:匙", "condition", "有缺口", valid_from=3),
    ]
    out = collapse_facts_single_truth(facts)
    assert len(out) == 2
    vals = {f.attribute: f.value for f in out}
    assert vals["artifact"] == "三棱铜匙"
    assert vals["condition"] == "有缺口"


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
