"""chapter_review side table read/write (M4a)."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from scribe3.review.fp import prose_fp

_log = logging.getLogger("scribe3.review.snapshot")

# Persist only when flag on (M4a enables by setting SCRIBE3_CHAPTER_REVIEW_PERSIST=1)
def persist_enabled() -> bool:
    return (os.environ.get("SCRIBE3_CHAPTER_REVIEW_PERSIST") or "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def save_chapter_review(store, *, work: str, seq: int, payload: dict[str, Any]) -> bool:
    """Write snapshot. No-op if persist disabled or table missing."""
    if not persist_enabled():
        return False
    try:
        body = json.dumps(payload, ensure_ascii=False)
        fp = payload.get("prose_fp") or prose_fp(payload.get("prose") or "")
        # Surreal: use record chapter_review:{work}_{seq} or separate fields
        local = f"{work}_{int(seq)}".replace(":", "_")
        store._execute_write(
            "UPSERT type::record('chapter_review', $local) SET "
            "work=$work, seq=$seq, prose_fp=$fp, mode=$mode, "
            "issues_json=$issues, coverage=$cov, degraded=$deg, "
            "model_id=$mid, created_at=time::now()",
            {
                "local": local,
                "work": work,
                "seq": int(seq),
                "fp": fp,
                "mode": payload.get("mode") or "full",
                "issues": payload.get("issues") or [],
                "cov": payload.get("coverage") or {},
                "deg": payload.get("degraded_sources") or payload.get("degraded") or [],
                "mid": payload.get("model_id") or "",
            },
        )
        return True
    except Exception as e:
        _log.warning("save_chapter_review failed: %s", e)
        return False


def load_chapter_review(store, *, work: str, seq: int, current_prose: str) -> dict | None:
    """Load if prose_fp matches; else None."""
    try:
        local = f"{work}_{int(seq)}".replace(":", "_")
        rows = store._query(
            "SELECT * FROM type::record('chapter_review', $local) LIMIT 1",
            {"local": local},
        ) or []
        if not rows:
            return None
        r = rows[0]
        fp = (r.get("prose_fp") or "").strip()
        if fp != prose_fp(current_prose):
            return None
        return {
            "prose_fp": fp,
            "mode": r.get("mode"),
            "issues": r.get("issues_json") or r.get("issues") or [],
            "coverage": r.get("coverage") or {},
            "degraded": r.get("degraded") or [],
            "fp_match": True,
        }
    except Exception as e:
        _log.debug("load_chapter_review: %s", e)
        return None
