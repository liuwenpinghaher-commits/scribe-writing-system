"""Run 卡 fail-soft 落库 + 进程内 last。"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from scribe3.run_card import (
    ExpectedFacts,
    build_run_card,
    public_card,
    run_card_enabled,
)

_log = logging.getLogger("scribe3.run_card")
_LAST_RUN_CARD: dict[str, Any] = {}
_LOCK = threading.Lock()

_PERSIST_KEYS = (
    "work", "chapter", "kind", "phase", "request_id", "manifest_id",
    "actual_input_hash", "outcome_id", "outcome_status", "outcome_usage",
    "assemble_ok", "verdict", "summary", "rows", "quality", "facts",
    "caps", "l2", "density", "quality_flags", "schema_ver",
)


def remember_last_run_card(card: dict[str, Any] | None) -> None:
    if not card:
        return
    with _LOCK:
        _LAST_RUN_CARD.clear()
        _LAST_RUN_CARD.update(card)


def get_last_run_card() -> dict[str, Any]:
    with _LOCK:
        return dict(_LAST_RUN_CARD)


def run_card_persist_enabled() -> bool:
    if not run_card_enabled():
        return False
    from scribe3.feature_flags import flag_truthy, get_flag
    return flag_truthy("SCRIBE3_RUN_CARD_PERSIST")


def persist_run_card(st: Any, card: dict[str, Any]) -> bool:
    if st is None or not card:
        return False
    if not run_card_persist_enabled():
        return False
    run_id = str(card.get("run_id") or "")
    if not run_id:
        return False
    try:
        rid = card.get("request_id")
        kind = str(card.get("kind") or "write")
        if rid and hasattr(st, "get_write_run_card_by_request"):
            existing = st.get_write_run_card_by_request(str(rid), kind=kind)
            if existing:
                return True
        fields = {k: card.get(k) for k in _PERSIST_KEYS}
        st.create_only_write_run_card(run_id, fields)
        return True
    except Exception as e:
        _log.warning("persist_run_card fail-soft: %s", e)
        return False


def latest_run_card(st: Any, *, work: str | None = None, kind: str = "write") -> dict | None:
    if st is None or not hasattr(st, "list_write_run_cards"):
        return None
    try:
        rows = st.list_write_run_cards(kind=kind, limit=1)
        return rows[0] if rows else None
    except Exception as e:
        _log.debug("latest_run_card fail-soft: %s", e)
        return None


def list_run_cards(
    st: Any,
    *,
    chapter: int | None = None,
    kind: str | None = None,
    verdict: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if st is None or not hasattr(st, "list_write_run_cards"):
        return []
    try:
        return st.list_write_run_cards(
            chapter=chapter, kind=kind, verdict=verdict, limit=limit,
        ) or []
    except Exception as e:
        _log.debug("list_run_cards fail-soft: %s", e)
        return []


def get_run_card(st: Any, run_id: str) -> dict | None:
    if st is None or not hasattr(st, "get_write_run_card"):
        return None
    try:
        return st.get_write_run_card(run_id)
    except Exception as e:
        _log.debug("get_run_card fail-soft: %s", e)
        return None


def attach_outcome_to_run_card(
    st: Any,
    *,
    request_id: str,
    outcome_id: str | None,
    status: str | None,
    usage: dict | None,
    kind: str = "write",
) -> None:
    if not request_id or st is None or not hasattr(st, "update_write_run_card_outcome"):
        return
    slim_usage = None
    if isinstance(usage, dict):
        slim_usage = {
            k: usage.get(k)
            for k in (
                "input_tokens", "output_tokens", "total_tokens",
                "prompt_tokens", "completion_tokens",
            )
            if usage.get(k) is not None
        }
    st.update_write_run_card_outcome(
        request_id, outcome_id=outcome_id, status=status,
        usage=slim_usage, kind=kind,
    )


def emit_write_run_card(
    *,
    st: Any,
    work: str,
    chapter: int,
    phase: str | None = None,
    facts: ExpectedFacts | None = None,
    bud_rep: dict | None = None,
    attempted_names: set[str] | None = None,
    request_id: str | None = None,
    manifest_id: str | None = None,
    actual_input_hash: str | None = None,
    latch: dict | None = None,
    recall_text: str | None = None,
    texts: dict[str, str] | None = None,
    kind: str = "write",
    assemble_ok: bool = True,
    card: dict | None = None,
) -> dict | None:
    if not run_card_enabled():
        return None
    t0 = time.monotonic()
    try:
        if card is None:
            if facts is None:
                return None
            card = build_run_card(
                facts=facts,
                bud_rep=bud_rep,
                attempted_names=attempted_names,
                request_id=request_id,
                manifest_id=manifest_id,
                actual_input_hash=actual_input_hash,
                latch=latch,
                recall_text=recall_text,
                texts=texts,
                kind=kind,
                assemble_ok=assemble_ok,
                created_ns=time.time_ns(),
            )
        persist_run_card(st, card)
        remember_last_run_card(card)
        return card
    except Exception as e:
        _log.warning(
            "emit_write_run_card fail-soft work=%s ch=%s: %s", work, chapter, e,
            exc_info=True,
        )
        return None
    finally:
        dt = (time.monotonic() - t0) * 1000
        _log.info("run_card_emit_ms=%.1f work=%s ch=%s", dt, work, chapter)


def ttl_days() -> int:
    raw = (get_flag("SCRIBE3_RUN_CARD_TTL_DAYS") or "7").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 7


_PURGE_TS: dict[str, float] = {}


def maybe_purge_run_cards(st: Any, *, work: str = "main") -> None:
    key = str(work or "main")
    now = time.time()
    with _LOCK:
        last = _PURGE_TS.get(key, 0)
        if now - last < 6 * 3600:
            return
        _PURGE_TS[key] = now
    try:
        purge_run_cards(st)
    except Exception as e:
        _log.warning("maybe_purge_run_cards fail-soft: %s", e)


def purge_run_cards(st: Any, *, days: int | None = None) -> dict[str, Any]:
    d = ttl_days() if days is None else max(1, int(days))
    try:
        if st is not None and hasattr(st, "purge_write_run_cards_older_than"):
            st.purge_write_run_cards_older_than(d)
        return {"ok": True, "ttl_days": d}
    except Exception as e:
        _log.warning("purge_run_cards fail-soft: %s", e)
        return {"ok": False, "ttl_days": d, "error": str(e)[:160]}


def publicize(card: dict | None) -> dict | None:
    return public_card(card)
