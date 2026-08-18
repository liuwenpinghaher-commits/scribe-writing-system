"""Unified artifact envelope + content sha. No I/O."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from scribe3.playbook.quote import PLAYBOOK_VERSION

STATUSES = ("draft", "frozen", "superseded", "needs_human")
_SKIP_SHA = frozenset({"sha", "status", "review"})

_TZ_SHANGHAI = timezone(timedelta(hours=8))


def artifact_sha(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in (payload or {}).items() if k not in _SKIP_SHA}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def now_iso() -> str:
    return datetime.now(_TZ_SHANGHAI).replace(microsecond=0).isoformat()


def wrap(
    schema: str,
    payload: dict[str, Any],
    *,
    source_sha: str = "",
    status: str = "draft",
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rec = dict(payload or {})
    rec["schema"] = schema
    rec["playbook_version"] = rec.get("playbook_version") or PLAYBOOK_VERSION
    if source_sha:
        rec["source_sha"] = source_sha
    rec["status"] = status if status in STATUSES else "draft"
    rec["sha"] = artifact_sha(rec)
    if review:
        rec["review"] = review
    return rec


def pass_review(*, judge_version: str = PLAYBOOK_VERSION) -> dict[str, Any]:
    return {
        "judge_version": judge_version,
        "verdict": "pass",
        "reviewed_at": now_iso(),
    }
