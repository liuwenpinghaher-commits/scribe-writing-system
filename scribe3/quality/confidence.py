"""质量评价置信度计算与三轴合并。"""
from __future__ import annotations


def compute_confidence(
    *,
    coverage: float,
    evidence_validity_rate: float,
    calibration_reliability: float,
    independence: float,
    stability: float,
) -> float:
    coverage = max(0.0, min(1.0, coverage))
    evidence_validity_rate = max(0.0, min(1.0, evidence_validity_rate))
    calibration_reliability = max(0.0, min(1.0, calibration_reliability))
    independence = max(0.0, min(1.0, independence))
    stability = max(0.0, min(1.0, stability))

    base = (
        0.30 * coverage
        + 0.30 * evidence_validity_rate
        + 0.15 * calibration_reliability
        + 0.15 * independence
        + 0.10 * stability
    )
    penalty = 1.0
    if coverage < 0.5:
        penalty *= 0.6
    if evidence_validity_rate < 0.3:
        penalty *= 0.4
    return max(0.0, min(1.0, base * penalty))


def merge_three_axes(
    *,
    author: int | None,
    system: int | None,
    reference: int | None,
    weights: tuple[float, float, float],
) -> float | None:
    if author is None:
        return None
    w_a, w_s, w_r = weights
    parts = [author * w_a]
    total_w = w_a
    if system is not None:
        parts.append(system * w_s)
        total_w += w_s
    if reference is not None:
        parts.append(reference * w_r)
        total_w += w_r
    if total_w == 0:
        return None
    return sum(parts) / total_w
