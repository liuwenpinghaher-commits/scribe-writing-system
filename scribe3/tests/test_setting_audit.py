"""设定间一致性扫描。

判据来自方案 `docs/plans/2026-08-27-setting-scale.md` 第五节：
往库里注入 20 条已知矛盾，要查出 ≥15 条。这里把那 20 条固化成用例。
"""

from __future__ import annotations

from scribe3.ontology import Fact, KnowledgeEdge
from scribe3.setting_audit import (
    Contradiction,
    scan,
    scan_bad_windows,
    scan_knowledge_before_fact,
    scan_value_conflicts,
    scan_wide_secrets,
)


def _f(local, entity, attr, value, vfrom, vto=None, secret=False):
    return Fact(f"fact:{local}", entity, attr, value, vfrom, vto, secret, [])


def _e(who, local, since):
    return KnowledgeEdge(who, f"fact:{local}", since_chapter=since)


class FoldingStore:
    """行为对齐真实 store：`facts_at` 走 D4 同键折叠，`facts_unfolded_at` 不折叠。

    早先的用例都直接调 `scan_value_conflicts(facts)`，绕开了读路径，
    于是没人发现 `scan()` 当时读的是折叠后的命题——真实库上那类检查恒为空。
    """

    def __init__(self, facts, edges=()):
        self._facts, self._edges = list(facts), list(edges)

    def facts_unfolded_at(self, chapter):
        return [f for f in self._facts
                if f.valid_from <= chapter
                and (f.valid_to is None or f.valid_to > chapter)]

    def facts_at(self, chapter):
        from scribe3.fact_surface import resolve_injection_facts
        return resolve_injection_facts(self.facts_unfolded_at(chapter))

    def load_knowledge(self):
        return list(self._edges)


# ---------- 逐类 ----------

def test_value_conflict_when_windows_overlap():
    facts = [_f("a", "role:门主", "姓氏", "姓王", 300),
             _f("b", "role:门主", "姓氏", "姓李", 2000)]
    got = scan_value_conflicts(facts)
    assert len(got) == 1
    assert got[0].kind == "value_conflict"
    assert "姓王" in got[0].detail and "姓李" in got[0].detail


def test_value_conflict_not_flagged_when_superseded():
    """旧条目设了 valid_to（换代），是正常的设定演进，不是打架。"""
    facts = [_f("a", "role:门主", "姓氏", "姓王", 300, 2000),
             _f("b", "role:门主", "姓氏", "姓李", 2000)]
    assert scan_value_conflicts(facts) == []


def test_value_conflict_ignores_identical_values():
    facts = [_f("a", "loc:山", "高度", "三千丈", 10),
             _f("b", "loc:山", "高度", "三千丈", 50)]
    assert scan_value_conflicts(facts) == []


def test_knowledge_before_fact():
    facts = [_f("x", "role:甲", "身世", "他是遗孤", 100)]
    got = scan_knowledge_before_fact(facts, [_e("role:乙", "x", 50)])
    assert len(got) == 1
    assert got[0].kind == "knowledge_before_fact"
    assert got[0].severity == "error"


def test_knowledge_at_or_after_fact_is_fine():
    facts = [_f("x", "role:甲", "身世", "他是遗孤", 100)]
    assert scan_knowledge_before_fact(facts, [_e("role:乙", "x", 100)]) == []
    assert scan_knowledge_before_fact(facts, [_e("role:乙", "x", 101)]) == []


def test_bad_window():
    got = scan_bad_windows([_f("x", "role:甲", "职务", "在任", 100, 50)])
    assert len(got) == 1 and got[0].kind == "bad_window"


def test_wide_secret():
    facts = [_f("s", "role:甲", "私生子", "他有个私生子", 10, secret=True)]
    edges = [_e(f"role:人{i}", "s", 20) for i in range(5)]
    got = scan_wide_secrets(facts, edges)
    assert len(got) == 1
    assert got[0].severity == "warn", "瞒不住是提醒，不是逻辑错"


def test_wide_secret_excludes_reader():
    """读者知道不算走漏——那是戏剧反讽，正是要的效果。"""
    facts = [_f("s", "role:甲", "私生子", "他有个私生子", 10, secret=True)]
    edges = [_e("reader", "s", 20)] + [_e(f"role:人{i}", "s", 20) for i in range(2)]
    assert scan_wide_secrets(facts, edges) == []


def test_non_secret_never_flagged():
    facts = [_f("p", "role:甲", "住处", "住城南", 10)]
    edges = [_e(f"role:人{i}", "p", 20) for i in range(9)]
    assert scan_wide_secrets(facts, edges) == []


# ---------- 判据：20 条注入，要查出 ≥15 ----------

def _twenty_known_contradictions() -> tuple[list, list, int]:
    """20 条人工确认的矛盾，混在 40 条干净设定里。"""
    facts: list = []
    edges: list = []
    expected = 0

    # 1-8：同实体同属性并存冲突
    for i in range(8):
        facts += [_f(f"c{i}a", f"role:人{i}", "出身", f"生在城东{i}", 10 + i),
                  _f(f"c{i}b", f"role:人{i}", "出身", f"生在漠北{i}", 100 + i)]
        expected += 1

    # 9-14：先知道后成立
    for i in range(6):
        facts.append(_f(f"k{i}", f"org:门{i}", "掌门", f"掌门是第{i}代", 500 + i))
        edges.append(_e(f"role:知情{i}", f"k{i}", 100 + i))
        expected += 1

    # 15-17：坏窗口
    for i in range(3):
        facts.append(_f(f"w{i}", f"loc:地{i}", "归属", f"归第{i}宗", 200 + i, 100 + i))
        expected += 1

    # 18-20：秘密走漏
    for i in range(3):
        facts.append(_f(f"s{i}", f"role:秘{i}", "把柄", f"第{i}桩旧案", 50, secret=True))
        edges += [_e(f"role:传{i}{j}", f"s{i}", 60) for j in range(5)]
        expected += 1

    # 干净的 40 条：各自独立、时间正确、非秘密
    for i in range(40):
        facts.append(_f(f"ok{i}", f"role:清白{i}", f"属性{i}", f"值{i}", 10 + i))
        edges.append(_e(f"role:清白{i}", f"ok{i}", 20 + i))

    return facts, edges, expected


def test_detection_rate_meets_the_bar():
    """判据必须端到端走 `scan()`，不能绕开读路径逐个函数调。"""
    facts, edges, expected = _twenty_known_contradictions()
    assert expected == 20, "注入的应当正好 20 条"

    found = scan(FoldingStore(facts, edges))
    assert len(found) >= 15, f"只查出 {len(found)}/20，低于判据 15"


def test_scan_sees_conflicts_the_injection_surface_hides():
    """同键冲突里必有一条会被注入面折掉——scan 得读未折叠命题才看得见。

    这是真库上撞出来的：36-100 章扫出 0 条矛盾，不是因为干净，
    是因为 `scan` 当时读的是 `facts_at`。
    """
    facts = [_f("a", "role:甲", "姓氏", "姓王", 300),
             _f("b", "role:甲", "姓氏", "姓李", 300)]
    st = FoldingStore(facts)
    assert len(st.facts_at(99999)) == 1, "前提：注入面确实会把冲突折成一条"

    assert [c.kind for c in scan(st)] == ["value_conflict"]


def test_scan_falls_back_when_store_has_no_unfolded_reader():
    """老 store 没有 facts_unfolded_at 时不能直接炸，退回 facts_at。"""

    class LegacyStore:
        def facts_at(self, chapter):
            return [_f("a", "role:甲", "职务", "在任", 100, 50)]

        def load_knowledge(self):
            return []

    assert [c.kind for c in scan(LegacyStore())] == ["bad_window"]


def test_no_false_positives_on_clean_data():
    """40 条干净设定不该报任何一条——误报会让人不看结果。"""
    facts = [_f(f"ok{i}", f"role:清白{i}", f"属性{i}", f"值{i}", 10 + i) for i in range(40)]
    edges = [_e(f"role:清白{i}", f"ok{i}", 20 + i) for i in range(40)]

    assert scan(FoldingStore(facts, edges)) == [], "干净数据不该有误报"


def test_report_separates_errors_from_warnings():
    from scribe3.setting_audit import report

    items = [Contradiction("value_conflict", "error", "role:甲", "打架了", (1, 2)),
             Contradiction("wide_secret", "warn", "role:乙", "瞒不住", (3,))]
    text = report(items)
    assert "1 处矛盾" in text and "1 处提醒" in text
    assert report([]) == "没查到矛盾。"
