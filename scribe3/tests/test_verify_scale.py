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
