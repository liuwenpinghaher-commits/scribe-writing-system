"""章节落库的两道坎，都是实测撞出来的。

一、实体 id 归位。提示词写死了只许用 `role:`/`place:`/`org:`，模型仍零星写 `loc:`。
旧代码打一行警告就继续 `add_fact`，于是命题带着 `loc:`/`world:`/`hist:` 进了库——
能被新鲜度统计到、却永远关联不上实体，一致性检查和限知帧全都照不到。

二、隐瞒不能共用属性名。`facts_at` 末尾要过 `resolve_injection_facts` 做同键折叠
（注入面单真），36-100 章把所有隐瞒都写成 `attribute="隐瞒"`，结果写进 71 条、
读回来只剩 7 条——每个角色一条。
"""

from __future__ import annotations

import pytest

from scribe3.ontology import Fact
from scribe3.tools.expand_wanjie_chapters import canon_oid, hide_attr, resolve_payoff


@pytest.mark.parametrize("raw,want", [
    ("role:纪棠", "role:纪棠"),
    ("place:共鸣塔", "place:共鸣塔"),
    ("org:名讳司", "org:名讳司"),
    ("loc:忘川驿", "place:忘川驿"),
    ("location:渡口", "place:渡口"),
    ("char:柳岸青", "role:柳岸青"),
    ("person:沈烛", "role:沈烛"),
    ("faction:共签会", "org:共签会"),
    ("ROLE:纪棠", "role:纪棠"),
    ("  place: 共鸣塔  ", "place:共鸣塔"),
])
def test_known_prefixes_land_in_ontology(raw, want):
    assert canon_oid(raw) == want


@pytest.mark.parametrize("raw", [
    "", None, "没有冒号", "world:地球", "hist:开元之乱", "ev:某事", "fact:某条",
    "role:", "  :  ",
])
def test_unrecognized_is_refused_not_guessed(raw):
    """认不出就返回 None，由调用方整条跳过。

    `world:` / `hist:` 是上一轮真混进库的两个，这里钉死它们不许再被放行。
    `ev:` / `fact:` 在本体里另有其表，不是命题主语，同样不接。
    """
    assert canon_oid(raw) is None


def _hide(local, who, what, ch):
    return Fact(f"fact:{local}", who, hide_attr(what),
                f"对外人瞒：{what}", ch, None, True, [])


def test_one_person_can_hide_many_things():
    """同时瞒多件事必须都读得回来——这是限知模型的日常，不是边界情况。"""
    from scribe3.fact_surface import resolve_injection_facts

    facts = [_hide(f"h{i}", "role:沈烛", f"第{i}件事", 36 + i) for i in range(5)]
    assert len(resolve_injection_facts(facts)) == 5


def test_hiding_the_same_thing_twice_still_folds():
    """同一件事重复瞒该单真——折叠语义本身是对的，不能因为修 bug 把它一起关掉。"""
    from scribe3.fact_surface import resolve_injection_facts

    facts = [_hide("h1", "role:沈烛", "裂纹温度", 36),
             _hide("h2", "role:沈烛", "裂纹温度", 40)]
    out = resolve_injection_facts(facts)
    assert len(out) == 1
    assert out[0].valid_from == 40, "留下的该是后面那条"


def test_hide_attr_is_stable_and_bounded():
    assert hide_attr("裂纹温度") == hide_attr("  裂纹温度  ") == "隐瞒·裂纹温度"
    assert hide_attr("很长" * 40).startswith("隐瞒·")
    assert len(hide_attr("很长" * 40)) <= len("隐瞒·") + 24


# ---------- 收线：编号引用优先于模糊匹配 ----------

class PromiseStore:
    def __init__(self, rows):
        self._rows = rows

    def list_promises(self):
        return list(self._rows)


_LINES = [
    {"id": "promise:abc123", "text": "谁在袖口标的价", "status": "open"},
    {"id": "promise:def456", "text": "北峰那一夜谁按的核", "status": "open"},
    {"id": "promise:ghi789", "text": "已经收过的线", "status": "paid"},
]


def test_payoff_resolves_by_reference():
    """提示词把编号发下去，收线就是精确引用，不看模型复述得准不准。"""
    st = PromiseStore(_LINES)
    assert resolve_payoff(st, {"ref": "Labc123"}) == "abc123"
    assert resolve_payoff(st, {"ref": "labc123"}) == "abc123", "大小写不该卡住"


def test_reference_wins_over_misleading_text():
    """编号在就认编号。模型抄错原话是常事，编号抄错少见。"""
    st = PromiseStore(_LINES)
    got = resolve_payoff(st, {"ref": "Ldef456", "text": "谁在袖口标的价"})
    assert got == "def456"


def test_falls_back_to_text_when_no_reference():
    st = PromiseStore(_LINES)
    assert resolve_payoff(st, {"text": "北峰那一夜谁按的核"}) == "def456"


def test_will_not_pay_a_line_that_is_already_closed():
    st = PromiseStore(_LINES)
    assert resolve_payoff(st, {"ref": "Lghi789"}) is None
    assert resolve_payoff(st, {"ref": "L不存在"}) is None
