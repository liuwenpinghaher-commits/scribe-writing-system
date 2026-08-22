"""DED-12 / CRS-01：三套质量体系合成一章健康度。"""
from __future__ import annotations

from typing import Any


def aggregate_chapter_health(
    *,
    playbook: dict | None = None,
    post_check: dict | None = None,
    review: dict | None = None,
) -> dict[str, Any]:
    pb = playbook or {}
    pc = post_check or {}
    rv = review or {}
    pb_status = str(pb.get("status") or pb.get("verdict") or pb.get("ok") or "unknown")
    pc_verdict = str(pc.get("verdict") or pc.get("status") or "unknown")
    rv_cov = rv.get("coverage") if rv.get("coverage") is not None else rv.get("status") or "unknown"
    blocking = bool(
        pb.get("ok") is False
        or pc_verdict in ("blocking", "fail", "needs_human")
        or str(rv.get("verdict") or "") in ("blocking", "fail")
    )
    if blocking:
        grade = "red"
    elif pc_verdict in ("advisory", "warn") or pb_status in ("advisory",):
        grade = "yellow"
    else:
        grade = "green"
    return {
        "playbook_status": pb_status,
        "post_check_verdict": pc_verdict,
        "review_coverage": rv_cov,
        "overall_grade": grade,
        "blocking": blocking,
    }
