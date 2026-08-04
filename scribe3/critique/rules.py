"""Critique rules public surface — full impl in rules_impl; families are facades.

Import ``scribe3.critique`` or ``scribe3.critique.rules`` for the complete API.
Family modules (``repetition``, ``structure_style``, ``discipline_gate``) re-export
subsets for domain-oriented imports without splitting runtime identity.
"""
from __future__ import annotations

from scribe3.critique.rules_impl import *  # noqa: F403
from scribe3.critique import rules_impl as _impl

__all__ = sorted(
    n for n in vars(_impl)
    if not n.startswith("__")
)
