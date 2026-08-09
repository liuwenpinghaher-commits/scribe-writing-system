"""prose_fp helper — MUST match chapter_analysis._prose_fp (KD-19)."""
from __future__ import annotations

import hashlib


def prose_fp(prose: str | None) -> str:
    """16-hex sha256 of UTF-8 prose; same as chapter_analysis._prose_fp."""
    return hashlib.sha256((prose or "").encode("utf-8")).hexdigest()[:16]


def assert_parity_with_chapter_analysis() -> None:
    from scribe3.chapter_analysis import _prose_fp as ca_fp
    samples = ["", "甲", "hello\n世界", "a" * 1000]
    for s in samples:
        assert prose_fp(s) == ca_fp(s), (s[:20], prose_fp(s), ca_fp(s))
