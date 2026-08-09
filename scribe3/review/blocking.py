"""Single blocking predicate for triage + advisory filter (KD-14)."""
from __future__ import annotations

from scribe3.review.schema import S1_BLOCKING_TYPES


def is_blocking_issue(iss: dict | None) -> bool:
    """Whether an issue belongs in loop.triage blocking list.

    Rules:
    - degeneration + S1/blocking → True
    - pressure + S1/blocking → True
    - S1 + type in S1_BLOCKING_TYPES → True
    - setting with S1 must NOT block (type not in whitelist)
    """
    if not iss:
        return False
    meta = iss.get("meta") or {}
    sev = str(meta.get("severity") or iss.get("severity") or "")
    t = iss.get("type") or iss.get("kind") or ""
    sev_u = sev.upper()
    if t == "degeneration" and sev_u in ("S1", "BLOCKING"):
        return True
    if t == "pressure" and sev_u in ("S1", "BLOCKING"):
        return True
    if sev_u == "S1" and t in S1_BLOCKING_TYPES:
        return True
    return False
