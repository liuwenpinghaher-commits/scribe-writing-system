"""Shared discipline ↔ deterministic resonance table (L0/L1)."""
from __future__ import annotations

from typing import Any


def discipline_resonance(
    violations: set[str] | list[str],
    *,
    leaks: list | None = None,
    issues: list[dict] | None = None,
    qc_breakdown: dict | None = None,
) -> bool:
    """True if discipline violations co-fire with deterministic anchors → S1."""
    _viol = set(violations or [])
    _god_kinds = {
        (i.get("meta") or {}).get("kind")
        for i in (issues or [])
        if i.get("type") == "god_view"
    }
    return bool(
        ("knowledge_leak" in _viol and (bool(leaks) or "god_spoiler" in _god_kinds))
        or ("god_view" in _viol and bool(_god_kinds & {"god_spoiler", "explain_causality"}))
        or ("exposition_dump" in _viol and (qc_breakdown or {}).get("oversaturation", 0) > 0)
    )


def l1_marker_resonance(
    finding: dict[str, Any],
    *,
    leak_markers_hit: bool,
) -> bool:
    """Elevate L1 when deterministic marker path also hit (KD-7)."""
    return bool(leak_markers_hit and finding)
