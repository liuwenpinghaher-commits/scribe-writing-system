"""PR-6b · soft-pass 双旗 × detector 矩阵（纯函数；无 Surreal / 无 LLM）。

矩阵：(soft_p, soft_ai) × {only pressure, only ai, both, +leaks, park_stroll}
→ only_soft (advisory) vs park (hard)。
"""
from __future__ import annotations

import pytest

from scribe3.novel_quality_flags import (
    FLAG_PILOT_SOFT_AI_GRADE,
    FLAG_PILOT_SOFT_PRESSURE,
    LOG_FIELD_SOFT_AI,
    LOG_FIELD_SOFT_P,
    SOFT_DETS_AI_GRADE,
    SOFT_DETS_PRESSURE,
    full_check_blocking_is_only_soft,
    full_check_soft_detectors,
    soft_pass_category_flags,
    soft_pass_detectors_for,
)
from scribe3.settings import invalidate_cache


def _b(*dets: str) -> list[dict]:
    return [{"detector": d} for d in dets]


def _clear_settings(monkeypatch, **env: str | None) -> None:
    """清 override 缓存并设置/删除 env（flags 热读 get_setting）。"""
    for k in (FLAG_PILOT_SOFT_PRESSURE, FLAG_PILOT_SOFT_AI_GRADE):
        if k in env:
            v = env[k]
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)
        else:
            monkeypatch.delenv(k, raising=False)
    invalidate_cache()


# ── soft_pass_detectors_for 集合构建 ──────────────────────────────


def test_soft_dets_defaults_both_true_include_pressure_and_ai():
    """代码默认双开 → soft 含 pressure + AI（现网可达）。"""
    soft = soft_pass_detectors_for(True, True)
    assert "pressure_metrics" in soft
    assert "park_stroll" in soft
    assert "aggregate_ai_grade" in soft
    assert soft == (SOFT_DETS_PRESSURE | SOFT_DETS_AI_GRADE)


def test_soft_dets_pressure_off_excludes_pressure():
    soft = soft_pass_detectors_for(False, True)
    assert "pressure_metrics" not in soft
    assert "park_stroll" not in soft
    assert soft == SOFT_DETS_AI_GRADE


def test_soft_dets_ai_off_excludes_ai():
    soft = soft_pass_detectors_for(True, False)
    assert "aggregate_ai_grade" not in soft
    assert soft == SOFT_DETS_PRESSURE


def test_soft_dets_both_off_empty():
    assert soft_pass_detectors_for(False, False) == frozenset()


# ── only_soft 决策矩阵 ────────────────────────────────────────────

# (soft_p, soft_ai, detectors, expect_only_soft)
_MATRIX = [
    # 代码默认：双 soft
    (True, True, ("pressure_metrics",), True),
    (True, True, ("park_stroll",), True),
    (True, True, ("aggregate_ai_grade",), True),
    (True, True, ("pressure_metrics", "aggregate_ai_grade"), True),
    (True, True, ("find_leaks",), False),
    (True, True, ("pressure_metrics", "find_leaks"), False),
    # 质量模式：关 pressure soft，开 AI soft
    (False, True, ("pressure_metrics",), False),
    (False, True, ("park_stroll",), False),
    (False, True, ("aggregate_ai_grade",), True),
    (False, True, ("pressure_metrics", "aggregate_ai_grade"), False),
    (False, True, ("find_leaks",), False),
    # 仅 pressure soft
    (True, False, ("pressure_metrics",), True),
    (True, False, ("aggregate_ai_grade",), False),
    (True, False, ("pressure_metrics", "aggregate_ai_grade"), False),
    (True, False, ("find_leaks",), False),
    # 最严：双关 → 一律硬
    (False, False, ("pressure_metrics",), False),
    (False, False, ("aggregate_ai_grade",), False),
    (False, False, ("pressure_metrics", "aggregate_ai_grade"), False),
    (False, False, ("find_leaks",), False),
]


@pytest.mark.parametrize(
    "soft_p,soft_ai,dets,expect",
    _MATRIX,
    ids=[
        f"p={p}_ai={a}_{'+'.join(d) or 'empty'}_soft={e}"
        for p, a, d, e in _MATRIX
    ],
)
def test_full_check_only_soft_matrix(soft_p, soft_ai, dets, expect):
    soft = soft_pass_detectors_for(soft_p, soft_ai)
    got = full_check_blocking_is_only_soft(_b(*dets), soft)
    assert got is expect


def test_empty_blocking_never_only_soft():
    soft = soft_pass_detectors_for(True, True)
    assert full_check_blocking_is_only_soft([], soft) is False


def test_soft_pass_category_flags():
    cats = soft_pass_category_flags(_b("pressure_metrics", "aggregate_ai_grade"))
    assert cats[LOG_FIELD_SOFT_P] is True
    assert cats[LOG_FIELD_SOFT_AI] is True
    cats2 = soft_pass_category_flags(_b("find_leaks"))
    assert cats2[LOG_FIELD_SOFT_P] is False
    assert cats2[LOG_FIELD_SOFT_AI] is False
    cats3 = soft_pass_category_flags(_b("park_stroll"))
    assert cats3[LOG_FIELD_SOFT_P] is True
    assert cats3[LOG_FIELD_SOFT_AI] is False


def test_full_check_soft_detectors_reads_code_defaults(monkeypatch):
    """未设 env 时读 REGISTRY 默认（双 True）。"""
    _clear_settings(monkeypatch)
    soft = full_check_soft_detectors()
    assert "pressure_metrics" in soft
    assert "aggregate_ai_grade" in soft


def test_full_check_soft_detectors_env_pressure_off(monkeypatch):
    _clear_settings(
        monkeypatch,
        **{FLAG_PILOT_SOFT_PRESSURE: "0", FLAG_PILOT_SOFT_AI_GRADE: "1"},
    )
    soft = full_check_soft_detectors()
    assert "pressure_metrics" not in soft
    assert "park_stroll" not in soft
    assert "aggregate_ai_grade" in soft


def test_full_check_soft_detectors_env_ai_off(monkeypatch):
    _clear_settings(
        monkeypatch,
        **{FLAG_PILOT_SOFT_PRESSURE: "1", FLAG_PILOT_SOFT_AI_GRADE: "0"},
    )
    soft = full_check_soft_detectors()
    assert "pressure_metrics" in soft
    assert "aggregate_ai_grade" not in soft
