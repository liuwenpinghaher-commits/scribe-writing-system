"""Pilot action stages (P1-16): assemble executor map by phase."""
from __future__ import annotations

from scribe3.api.services.pilot_actions import (
    outline,
    beats,
    deduce,
    draft,
    check,
    deliver,
    finalize,
)

_STAGE_MODULES = (outline, beats, deduce, draft, check, deliver, finalize)

ACTION_KEYS = (
    "propose_outline",
    "expand_beats",
    "deduce",
    "draft_loop",
    "full_check",
    "deliver",
    "finalize",
)


def build_pilot_executor_body(work: str) -> dict:
    """action → callable(st, seq). Same keys as historical pilot_executor."""
    out: dict = {}
    for mod in _STAGE_MODULES:
        out.update(mod.build_actions(work))
    missing = [k for k in ACTION_KEYS if k not in out]
    if missing:
        raise RuntimeError(f"pilot stage map missing keys: {missing}")
    return {k: out[k] for k in ACTION_KEYS}
