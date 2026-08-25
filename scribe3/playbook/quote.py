"""The only allowed fidelity check: literal substring after _norm.

_norm strips all whitespace and all punctuation (CJK + ASCII).
No fullwidth conversion, no stemming, no similarity.
"""
from __future__ import annotations

import re
import unicodedata

PLAYBOOK_VERSION = "playbook.3.2.22"


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


def _compact_keep_punct(s: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    idx: list[int] = []
    for i, ch in enumerate(s or ""):
        if ch.isspace():
            continue
        chars.append(ch)
        idx.append(i)
    return "".join(chars), idx


def quote_span(quote: str, source: str) -> tuple[int, int] | None:
    """Whitespace-flexible, punctuation-strict span of quote inside source."""
    q, _ = _compact_keep_punct(quote)
    if not q:
        return None
    s, idx = _compact_keep_punct(source)
    pos = s.find(q)
    if pos < 0:
        return None
    return idx[pos], idx[pos + len(q) - 1] + 1


def _starts_at_boundary(source: str, lo: int) -> bool:
    j = lo - 1
    while j >= 0 and source[j].isspace():
        j -= 1
    if j < 0:
        return True
    return unicodedata.category(source[j]).startswith("P")


def quote_is_slice(quote: str, source: str) -> bool:
    """True iff quote is a contiguous slice of source (keep punct, skip spaces).

    Must start at a clause boundary (text start or after punctuation) so
    prefix-trimming like 我希望你今晚 → 你今晚 fails.
    """
    span = quote_span(quote, source)
    if not span:
        return False
    return _starts_at_boundary(source, span[0])


_SENT = re.compile(r"(?<=[。！？\n])")


def snap_quote(quote: str, source: str) -> str:
    """Map a drifted quote onto a literal slice of source. Empty if none."""
    src = source or ""
    span = quote_span(quote, src)
    if span:
        return src[span[0] : span[1]].strip()
    qn = _norm(quote)
    if len(qn) < 4:
        return ""
    n = 8 if len(qn) >= 8 else max(4, len(qn) // 2)
    grams = [qn[i : i + n] for i in range(len(qn) - n + 1)] or [qn]
    best = ""
    score = 0
    for sent in _SENT.split(src):
        piece = (sent or "").strip()
        if not piece:
            continue
        nn = _norm(piece)
        sc = sum(1 for g in grams if g and g in nn)
        if sc > score:
            score, best = sc, piece
    if score <= 0 or not best:
        return ""
    if len(best) > 50:
        best = best[:50]
    return best.strip()
