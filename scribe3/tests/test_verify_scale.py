"""验收单必须接上系统已有的完整度，不许另起炉灶。

verify_scale 曾经报「全部通过」，同时 79% 角色缺「他要什么」「他让人付出什么」。
setting_completeness 早就算出这个数，验收单没接。
"""
from __future__ import annotations

from scribe3.tools.verify_scale import Report, check_completeness


class _CompStore:
    def __init__(self, result):
        self._result = result

    def setting_completeness(self):
        return dict(self._result)


def test_empty_shells_fail_the_gate():
    """现库基线：char_issue_ratio 0.789 / score 64，必须不过关。"""
    rep = Report()
    check_completeness(_CompStore({
        "char_issue_ratio": 0.789,
        "completeness_score": 64,
        "char_issues": [{"name": "甲", "issues": ["缺他要什么"]}],
        "missing_dimensions": ["势力/组织"],
        "total_chars": 19,
    }), rep)
    assert any("空壳" in t or "char_issue" in t for t in rep.failed)
    assert any("完整度" in t or "completeness" in t for t in rep.failed)


def test_thick_book_passes_completeness():
    rep = Report()
    check_completeness(_CompStore({
        "char_issue_ratio": 0.2,
        "completeness_score": 84,
        "char_issues": [],
        "missing_dimensions": [],
        "total_chars": 10,
    }), rep)
    assert rep.failed == []


def test_thresholds_are_the_plan_numbers():
    """不许为了让现库通过而调低。方案书写死 ≤0.3 / ≥80。"""
    from scribe3.tools.verify_scale import CHAR_ISSUE_RATIO_MAX, COMPLETENESS_SCORE_MIN

    assert CHAR_ISSUE_RATIO_MAX == 0.3
    assert COMPLETENESS_SCORE_MIN == 80


class _DepthStore:
    """check_depth 只吃公开方法。空命题让厚度/空间真空过，专门打悬置闸。"""

    def __init__(self, volumes, promises, rules=(), facts=()):
        self._volumes = volumes
        self._promises = promises
        self._rules = list(rules)
        self._facts = list(facts)

    def facts_at(self, until):
        return [f for f in self._facts if int(getattr(f, "valid_from", 0) or 0) <= until]

    def list_world_rules(self):
        return list(self._rules)

    def list_volumes(self):
        return list(self._volumes)

    def list_promises(self):
        return list(self._promises)


def _vols(*ends):
    prev = 0
    out = []
    for i, e in enumerate(ends, 1):
        out.append({"sort_order": i, "title": f"卷{i}",
                    "charter": {"chapter_range": [prev + 1, e]}})
        prev = e
    return out


def test_suspense_gate_uses_cross_open_not_all_closed():
    """假闸：末卷还有开口线 → all_closed 为假 → 绿；显示却是跨卷未收 0。

    把关必须用同一个数：跨卷未收 / 总线数 ≥15%，以及终卷前每卷至少一条。
    """
    from scribe3.tools.verify_scale import check_depth

    promises = [
        {"setup_chapter": 4, "payoff_chapter": 8, "status": "paid"},
        {"setup_chapter": 4, "payoff_chapter": 25, "status": "paid"},
        {"setup_chapter": 55, "payoff_chapter": None, "status": "open"},
    ]
    rep = Report()
    check_depth(_DepthStore(_vols(20, 40, 60), promises), rep, 60)
    assert any("跨卷未收" in t for t in rep.failed), rep.failed
    assert any("终卷前" in t for t in rep.failed), rep.failed


def test_obstacle_zero_is_reported_not_gated():
    """旧闸「至少一条被引用」在触发率为 0 时才会红，有一条就永绿。

    没有书内比例依据，改为只报不拦：代价全空、一条没触发，也不进 failed。
    """
    import io
    from contextlib import redirect_stdout
    from scribe3.tools.verify_scale import check_depth

    rules = [
        {"name": "光子投票", "cost": "扣体温"},
        {"name": "空规矩", "cost": ""},
    ]
    # 两卷、无线：悬置会红，但障碍不许跟着红。
    rep = Report()
    buf = io.StringIO()
    with redirect_stdout(buf):
        check_depth(_DepthStore(_vols(20, 40), [], rules=rules), rep, 40)
    out = buf.getvalue()
    assert "只报不拦" in out
    assert "有代价" in out
    assert not any("障碍" in t for t in rep.failed), rep.failed


def test_suspense_both_gates_pass_when_early_volumes_still_hang():
    from scribe3.tools.verify_scale import check_depth

    promises = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 4, "payoff_chapter": 8, "status": "paid"},
        {"setup_chapter": 25, "payoff_chapter": 30, "status": "paid"},
        {"setup_chapter": 45, "payoff_chapter": None, "status": "open"},
    ]
    # 跨卷未收 2/5 = 40% ≥15%；卷1、卷2 各一条未收。
    rep = Report()
    check_depth(_DepthStore(_vols(20, 40, 60), promises), rep, 60)
    assert not any("跨卷未收" in t or "终卷前" in t for t in rep.failed), rep.failed


def _fact(local, entity, attr, value, ch=1):
    from scribe3.ontology import Fact
    return Fact(f"fact:{local}", entity, attr, value, ch, None, False, [])


def test_check_depth_positive_control_thin_entities():
    """已知薄实体必须让 ≤2 / ≤4 闸变红。空命题 le2=0 不算干净。"""
    from scribe3.tools.verify_scale import check_depth

    facts = [_fact(f"t{i}", f"role:薄{i}", "面目", "一句话", 1) for i in range(5)]
    hanging = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
    ]
    rep = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging, facts=facts), rep, 40)
    assert any("≤2" in t for t in rep.failed), rep.failed
    assert any("≤4" in t for t in rep.failed), rep.failed


def test_check_depth_positive_control_singleton_places():
    """8 个互不嵌套的地点 = 一区一地点 100%，空间闸必须红。"""
    from scribe3.tools.verify_scale import check_depth

    facts = [_fact(f"p{i}", f"place:城{i}", "位置", "一句话", 1) for i in range(8)]
    hanging = [
        {"setup_chapter": 4, "payoff_chapter": None, "status": "open"},
        {"setup_chapter": 25, "payoff_chapter": None, "status": "open"},
    ]
    rep = Report()
    check_depth(_DepthStore(_vols(20, 40), hanging, facts=facts), rep, 40)
    assert any("一区一地点" in t for t in rep.failed), rep.failed
