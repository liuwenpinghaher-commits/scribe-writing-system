"""Other critique entry points (facade over rules_impl)."""
from __future__ import annotations

from scribe3.critique import rules_impl as _impl

for _k, _v in vars(_impl).items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v

__all__ = sorted(n for n in globals() if not n.startswith("__") and n not in ("_impl", "_k", "_v"))
