"""Critique rules body — phase parts in one shared namespace (PR-EH-11b).

Parts under ``rules_parts/`` are for navigation; runtime ``exec`` into this
module so cross-part free names behave like the historical monolith.
"""
from __future__ import annotations

from pathlib import Path

_PART_DIR = Path(__file__).resolve().parent / "rules_parts"
_PARTS = ['01_text_utils', '02_repetition', '03_style', '04_quality', '05_prompts', '06_craft', '07_timeline']
_PREAMBLE = '"""Public critique detectors and rewrites (includes private helpers for name resolution)."""\nfrom __future__ import annotations\n\nfrom scribe3.critique._common import *  # noqa: F403\n\n'

def _bootstrap() -> None:
    g = globals()
    exec(compile(_PREAMBLE, str(Path(__file__).with_name("_rules_preamble.py")), "exec"), g)
    for name in _PARTS:
        path = _PART_DIR / f"{name}.py"
        src = path.read_text(encoding="utf-8")
        exec(compile(src, str(path), "exec"), g)

_bootstrap()
del _bootstrap, _PREAMBLE, _PART_DIR, _PARTS, Path
