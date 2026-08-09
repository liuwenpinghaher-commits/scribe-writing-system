"""M5: project existing multi-finding discipline + advisory ten-dim stubs without double LLM."""
from __future__ import annotations

from typing import Any

from scribe3.review.normalize import normalize_issues


def discipline_multi_findings(
    violations: list[str] | None,
    *,
    chapter: int,
    cut_after: str = "",
    range_: list[int] | None = None,
    severity: str = "S2",
    resonance: bool = False,
) -> list[dict]:
    """One issue per discipline kind (L0 multi-finding) instead of a single joined message."""
    raw = []
    for idx, v in enumerate(violations or []):
        sev = "S1" if resonance else severity
        raw.append({
            "id": f"issue:discipline:{chapter}:{idx}:{v}",
            "source": "discipline",
            "type": "discipline",
            "kind": str(v),
            "severity": sev,
            "title": f"纪律·{v}",
            "reason": f"语义纪律命中：{v}",
            "message": f"语义纪律命中：{v}",
            "chapter": chapter,
            "range": range_ or [0, 0],
            "text": cut_after or "",
            "meta": {
                "severity": sev,
                "resonance": resonance,
                "detector": "discipline",
                "track": "L",
                "violations": [v],
            },
            "suggested_action": "按批注消除该硬伤，保持叙事意图。",
        })
    return normalize_issues(raw, chapter=chapter)


def project_quality_dim_advisory(
    scores: dict[str, Any] | None,
    *,
    chapter: int,
) -> list[dict]:
    """Project ten-dim scores as S3/S4 advisory only (never blocking)."""
    if not scores:
        return []
    raw = []
    for idx, (dim, val) in enumerate(scores.items()):
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        if num >= 7.0:
            continue  # only surface weak dims
        sev = "S3" if num < 5.0 else "S4"
        raw.append({
            "id": f"issue:quality_dim:{chapter}:{idx}",
            "source": "quality_dim",
            "type": "quality_dim",
            "kind": str(dim),
            "severity": sev,
            "title": f"十维·{dim}",
            "reason": f"维度 {dim} 得分 {num}（advisory，不进 blocking）",
            "message": f"{dim}={num}",
            "chapter": chapter,
            "range": [0, 0],
            "meta": {"severity": sev, "track": "L", "score": num},
            "suggested_action": "参考十维短评改进，不自动回炉。",
        })
    return normalize_issues(raw, chapter=chapter)
