"""Critique rules facade (PR-EH-11).

Implementation lives in ``rules_impl_body``; this module re-exports the full public
and private surface so ``from scribe3.critique.rules_impl import …`` keeps working
(including names not listed in ``rules_impl_body.__all__``).
"""
from __future__ import annotations

import scribe3.critique.rules_impl_body as _body

# Full re-export (body's __all__ only lists a subset of private helpers).
for _name in dir(_body):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_body, _name)

del _name, _body
