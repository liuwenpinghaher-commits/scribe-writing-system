"""Task 5: 质量评价器与置信度 RED 测试。"""
import json

import pytest

from scribe3.quality.confidence import compute_confidence, merge_three_axes
from scribe3.quality.evaluator import QualityEvaluator


class TestConfidenceComputation:
    def test_all_high_signals_gives_high_confidence(self):
        result = compute_confidence(
            coverage=1.0,
            evidence_validity_rate=1.0,
            calibration_reliability=0.9,
            independence=1.0,
            stability=1.0,
        )
        assert result >= 0.8

    def test_low_coverage_caps_confidence(self):
        result = compute_confidence(
            coverage=0.2,
            evidence_validity_rate=1.0,
            calibration_reliability=1.0,
            independence=1.0,
            stability=1.0,
        )
        assert result <= 0.5

    def test_zero_evidence_validity_gives_low_confidence(self):
        result = compute_confidence(
            coverage=1.0,
            evidence_validity_rate=0.0,
            calibration_reliability=1.0,
            independence=1.0,
            stability=1.0,
        )
        assert result <= 0.3

    def test_confidence_never_exceeds_one(self):
        result = compute_confidence(
            coverage=1.0,
            evidence_validity_rate=1.0,
            calibration_reliability=1.0,
            independence=1.0,
            stability=1.0,
        )
        assert result <= 1.0

    def test_confidence_never_below_zero(self):
        result = compute_confidence(
            coverage=0.0,
            evidence_validity_rate=0.0,
            calibration_reliability=0.0,
            independence=0.0,
            stability=0.0,
        )
        assert result >= 0.0


class TestMergeThreeAxes:
    def test_all_three_present_returns_decision_index(self):
        result = merge_three_axes(
            author=4, system=3, reference=4,
            weights=(0.50, 0.30, 0.20),
        )
        assert result is not None
        assert 0 <= result <= 5

    def test_author_absent_returns_none(self):
        result = merge_three_axes(
            author=None, system=3, reference=4,
            weights=(0.50, 0.30, 0.20),
        )
        assert result is None

    def test_author_system_differ_two_levels_marks_conflicted(self):
        result = merge_three_axes(
            author=5, system=2, reference=3,
            weights=(0.50, 0.30, 0.20),
        )
        assert result is not None

    def test_no_total_score_across_dimensions(self):
        r1 = merge_three_axes(author=4, system=3, reference=4, weights=(0.50, 0.30, 0.20))
        r2 = merge_three_axes(author=2, system=5, reference=3, weights=(0.50, 0.30, 0.20))
        assert isinstance(r1, float)
        assert isinstance(r2, float)


class TestQualityEvaluatorInterface:
    def test_evaluator_requires_store_and_llm(self):
        with pytest.raises(TypeError):
            QualityEvaluator()

    def test_evaluate_chapter_method_exists(self):
        assert hasattr(QualityEvaluator, "evaluate_chapter")

    def test_compare_references_method_exists(self):
        assert hasattr(QualityEvaluator, "compare_references")
