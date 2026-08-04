"""Critique package — split from critique.py; stable re-exports.

Public API matches the former monolithic ``scribe3.critique`` module:
functions, constants, and private helpers used by tests/callers.
"""
from __future__ import annotations

from scribe3.critique import _common as _common
from scribe3.critique import rules as _rules

# Constants / imports from _common (including underscore names via __all__).
for _k, _v in vars(_common).items():
    if _k.startswith("__") and _k not in ("__all__",):
        continue
    if _k in ("__name__", "__file__", "__package__", "__doc__", "__spec__", "__loader__", "__cached__", "__builtins__"):
        continue
    globals()[_k] = _v

# Functions and any other bindings from rules.
for _k, _v in vars(_rules).items():
    if _k.startswith("__") and _k not in ("__all__",):
        continue
    if _k in ("__name__", "__file__", "__package__", "__doc__", "__spec__", "__loader__", "__cached__", "__builtins__"):
        continue
    globals()[_k] = _v

__all__ = sorted(
    n
    for n in globals()
    if not n.startswith("__") and n not in ("_common", "_rules", "_k", "_v")
)
