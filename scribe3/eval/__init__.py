"""craft-eval holdout freeze checks."""
from __future__ import annotations

import hashlib
from pathlib import Path

EVAL = Path(__file__).resolve().parent


def holdout_blob() -> bytes:
    p = EVAL / "holdout.json"
    data = p.read_bytes()
    if not data.endswith(b"\n"):
        data += b"\n"
    return data


def holdout_sha256() -> str:
    return hashlib.sha256(holdout_blob()).hexdigest()


def verify_holdout_hash() -> str:
    expected = (EVAL / "holdout.sha256").read_text(encoding="utf-8").strip()
    got = holdout_sha256()
    if got != expected:
        raise RuntimeError(f"holdout.json hash drifted: {got} != {expected}")
    return got
