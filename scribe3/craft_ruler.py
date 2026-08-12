"""GAP-15/19：技法标尺对标 — DTW 距离 + 理想曲线。

纯函数、可复现；不宣称文学分。
"""
from __future__ import annotations

from typing import Any, Sequence


# 理想「起承转合」情绪曲线（-5…+5），长度 8 可重采样
IDEAL_EMOTION_CURVE: tuple[float, ...] = (
    -1.0, -0.5, 0.5, 1.5, 2.5, 0.0, -2.0, 1.0,
)

# GAP-15：对外稳定导出（SSOT 仍为 quality.rubrics；此处 re-export 便于 import）
try:
    from scribe3.quality.rubrics import CORE_DIMENSIONS as CORE_DIMENSIONS
except Exception:  # pragma: no cover
    CORE_DIMENSIONS = ()


def resample_series(series: Sequence[float], n: int) -> list[float]:
    """线性重采样到长度 n。"""
    if n <= 0:
        return []
    s = [float(x) for x in series] if series else [0.0]
    if len(s) == 1:
        return [s[0]] * n
    out: list[float] = []
    for i in range(n):
        pos = i * (len(s) - 1) / max(1, n - 1)
        lo = int(pos)
        hi = min(lo + 1, len(s) - 1)
        t = pos - lo
        out.append(s[lo] * (1 - t) + s[hi] * t)
    return out


def dtw_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """标准 DTW 欧氏路径代价（对称）。"""
    if not a and not b:
        return 0.0
    aa = list(a) or [0.0]
    bb = list(b) or [0.0]
    n, m = len(aa), len(bb)
    inf = 1e18
    dp = [[inf] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(aa[i - 1] - bb[j - 1])
            dp[i][j] = cost + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return float(dp[n][m])


def align_to_ideal(
    series: Sequence[float],
    *,
    ideal: Sequence[float] | None = None,
) -> dict[str, Any]:
    """将序列对标理想曲线，返回距离与归一相似度。"""
    ideal_s = list(ideal) if ideal is not None else list(IDEAL_EMOTION_CURVE)
    n = max(len(ideal_s), 4)
    a = resample_series(series, n)
    b = resample_series(ideal_s, n)
    dist = dtw_distance(a, b)
    # 归一：最大可能粗估 n*10
    sim = max(0.0, min(1.0, 1.0 - dist / max(1.0, n * 10.0)))
    return {
        "dtw_distance": round(dist, 4),
        "similarity": round(sim, 4),
        "series_resampled": [round(x, 3) for x in a],
        "ideal_resampled": [round(x, 3) for x in b],
        "surface": "craft_ruler.align",
        "advisory": True,
        "not_a_score": "literary_quality",
    }


def craft_ruler_report(
    emotion_points: Sequence[dict[str, Any]] | Sequence[float],
) -> dict[str, Any]:
    """从情绪点列表生成对标报告。"""
    series: list[float] = []
    for p in emotion_points or []:
        if isinstance(p, (int, float)):
            series.append(float(p))
        elif isinstance(p, dict):
            v = p.get("emotion", p.get("value", p.get("tension")))
            try:
                series.append(float(v))
            except Exception:
                series.append(0.0)
    align = align_to_ideal(series)
    # GAP-15：对接 quality CORE_DIMENSIONS 作为对标轴
    dims: list[dict[str, Any]] = []
    try:
        from scribe3.quality.rubrics import CORE_DIMENSIONS
        # 将情绪序列相似度映射到 emotional_effect 轴，其余轴给中性 0.5 占位
        sim = float(align.get("similarity") or 0)
        for d in CORE_DIMENSIONS:
            score = sim if d.key == "emotional_effect" else 0.5
            dims.append({
                "key": d.key,
                "label": d.label,
                "score": round(score, 4),
                "source": "craft_ruler.dtw" if d.key == "emotional_effect" else "neutral_placeholder",
            })
    except Exception:
        dims = []
    return {
        **align,
        "n_points": len(series),
        "ideal_name": "qichengzhuanhe_v0",
        "core_dimensions": dims,
        "dimension_ssot": "scribe3.quality.rubrics.CORE_DIMENSIONS",
    }
