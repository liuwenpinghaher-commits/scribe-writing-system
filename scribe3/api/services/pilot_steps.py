"""Pilot action map builder (PR-EH-8 / P1-16 phase modules).

``pilot_runtime._pilot_executor`` remains the rebind entrypoint name.
"""
from __future__ import annotations

from typing import Callable

from scribe3.api.services.pilot_actions import ACTION_KEYS, build_pilot_executor_body


def build_pilot_executor(work: str) -> dict[str, Callable]:
    """Return pilot step action map for ``work`` (same keys as historical executor)."""
    return build_pilot_executor_body(work)


def pilot_action_keys() -> tuple[str, ...]:
    return ACTION_KEYS
