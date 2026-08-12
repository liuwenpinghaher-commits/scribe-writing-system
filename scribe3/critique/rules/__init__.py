"""Critique rules package (package C)."""
from __future__ import annotations

from scribe3.critique.rules import timeline as _timeline

globals().update({
    k: v for k, v in vars(_timeline).items()
    if not k.startswith("__")
})
