"""The only allowed fidelity check: literal substring after _norm.

_norm strips all whitespace and all punctuation (CJK + ASCII).
No fullwidth conversion, no stemming, no similarity.
"""
from __future__ import annotations

import unicodedata

PLAYBOOK_VERSION = "playbook.1"


def _norm(s: str) -> str:
    out: list[str] = []
    for ch in s or "":
        if ch.isspace():
            continue
        if unicodedata.category(ch).startswith("P"):
            continue
        if unicodedata.category(ch).startswith("C"):
            continue
        out.append(ch)
    return "".join(out)


def quote_in_play(quote: str, play_text: str) -> bool:
    """True iff normalize(quote) is a contiguous substring of normalize(play)."""
    q = _norm(quote)
    if not q:
        return False
    return q in _norm(play_text)
