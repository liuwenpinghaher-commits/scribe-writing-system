"""Pilot action map builder (PR-EH-8).

Keeps action implementations in this module; ``pilot_runtime._pilot_executor``
is a thin re-export so rebind and tests keep the same entrypoint name.
"""
from __future__ import annotations

import logging
from typing import Any, Callable


def build_pilot_executor(work: str) -> dict[str, Callable]:
    """Return pilot step action map for ``work`` (same keys as historical executor)."""
    # Deferred import avoids import cycle: pilot_runtime imports pilot_steps at call time only.
    import scribe3.api.services.pilot_runtime as pr

    # Re-use the historical nested implementation still defined on pilot_runtime
    # as ``_pilot_executor_body`` after the thin-wrapper split.
    return pr._pilot_executor_body(work)


def pilot_action_keys() -> tuple[str, ...]:
    return (
        "propose_outline",
        "expand_beats",
        "deduce",
        "draft_loop",
        "full_check",
        "deliver",
        "finalize",
    )
