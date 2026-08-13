"""Pipeline Trace fail-soft 落库。"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

from scribe3.pipeline_trace import (
    SCHEMA_VER,
    TraceBuffer,
    bind_trace_buffer,
    current_trace_buffer,
    headline_from_spans,
    pipeline_trace_enabled,
    public_chain,
    public_span,
)
from scribe3.pipeline_trace_catalog import lookup

_log = logging.getLogger("scribe3.pipeline_trace")
_LOCK = threading.Lock()
_PURGE_TS: dict[str, float] = {}
_BUFFERS: dict[str, TraceBuffer] = {}


def ttl_days() -> int:
    raw = (os.environ.get("SCRIBE3_PIPELINE_TRACE_TTL_DAYS") or "7").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 7


def _utc_now():
    return datetime.now(timezone.utc)


def remember_buffer(buf: TraceBuffer) -> None:
    if not buf or not buf.trace_id:
        return
    with _LOCK:
        _BUFFERS[buf.trace_id] = buf


def buffer_for(trace_id: str | None) -> TraceBuffer | None:
    if not trace_id:
        return current_trace_buffer()
    cur = current_trace_buffer()
    if cur is not None and cur.trace_id == trace_id:
        return cur
    with _LOCK:
        return _BUFFERS.get(trace_id)


def buffer_for_span(span_id: str | None) -> TraceBuffer | None:
    if not span_id:
        return None
    cur = current_trace_buffer()
    if cur is not None and span_id in cur._by_id:
        return cur
    with _LOCK:
        for buf in _BUFFERS.values():
            if span_id in buf._by_id:
                return buf
    return None


def start_chain(
    st: Any,
    *,
    work: str,
    chapter: int,
    kind: str,
    phase: str,
    trace_id: str,
) -> TraceBuffer | None:
    if not pipeline_trace_enabled() or not trace_id:
        return None
    buf = TraceBuffer()
    buf.start_chain(
        work=work, chapter=int(chapter or 0), kind=kind or "write",
        phase=phase or "draft", trace_id=trace_id,
    )
    if not buf.obs_on:
        return None
    bind_trace_buffer(buf)
    remember_buffer(buf)
    try:
        maybe_purge_pipeline_traces(st, work=work)
    except Exception:
        pass
    try:
        if st is not None and hasattr(st, "create_only_pipeline_chain"):
            st.create_only_pipeline_chain(trace_id, {
                "work": buf.work,
                "chapter": buf.chapter,
                "kind": buf.kind,
                "phase": buf.phase,
                "status": "in_progress",
                "cursor_step_key": buf.cursor,
                "headline": None,
                "started_at": _utc_now(),
                "ended_at": None,
                "duration_ms": None,
                "span_count": 0,
                "red_count": 0,
                "manifest_id": None,
                "actual_input_hash": None,
                "outcome_id": None,
                "outcome_status": None,
                "outcome_usage": None,
                "contrast_run_id": None,
                "contrast_summary": None,
                "notes": [],
                "schema_ver": SCHEMA_VER,
            })
    except Exception as e:
        _log.warning("start_chain fail-soft: %s", e)
        if "flush_failed" not in buf.notes:
            buf.notes.append("flush_failed")
    return buf


def flush_spans(st: Any, buf: TraceBuffer | None, *, cursor: str | None = None) -> None:
    if buf is None or not buf.obs_on or not pipeline_trace_enabled():
        return
    if cursor:
        buf.cursor = cursor
    rows = buf.drain_ready()
    try:
        if rows and st is not None and hasattr(st, "insert_pipeline_spans"):
            st.insert_pipeline_spans(rows)
        if st is not None and hasattr(st, "update_pipeline_chain"):
            st.update_pipeline_chain(buf.trace_id, buf.snapshot_chain_patch())
    except Exception as e:
        _log.warning("flush_spans fail-soft: %s", e)
        if "flush_failed" not in buf.notes:
            buf.notes.append("flush_failed")


def insert_running_span(
    st: Any,
    *,
    trace_id: str,
    step_key: str,
    work: str,
    chapter: int,
    kind: str = "write",
    extra: dict | None = None,
) -> str:
    if not pipeline_trace_enabled() or not trace_id:
        return ""
    buf = buffer_for(trace_id)
    if buf is None:
        buf = TraceBuffer()
        buf.start_chain(
            work=work, chapter=chapter, kind=kind, phase="draft", trace_id=trace_id,
        )
        remember_buffer(buf)
    sid = buf.start_span(step_key)
    if extra and sid:
        buf.apply_fields(sid, **extra)
        rec = buf._by_id.get(sid)
        if rec:
            rec.ended = False
            rec.ended_ns = 0
            rec.status = extra.get("status") or "running"
    try:
        rec = buf._by_id.get(sid)
        if rec and st is not None and hasattr(st, "insert_pipeline_spans"):
            row = rec.as_public(work=work, chapter=chapter, kind=kind)
            row["status"] = rec.status or "running"
            timing = dict(row.get("timing") or {})
            timing["ended_at"] = None
            timing["duration_ms"] = None
            row["timing"] = timing
            st.insert_pipeline_spans([row])
            rec.flushed = True
        if st is not None and hasattr(st, "update_pipeline_chain"):
            st.update_pipeline_chain(trace_id, {"cursor_step_key": step_key})
    except Exception as e:
        _log.warning("insert_running_span fail-soft: %s", e)
    return sid


def patch_span(st: Any, span_id: str, fields: dict[str, Any]) -> None:
    """终态回写：先在 buffer 打真实 ended_ns，再把 timing 一并 UPDATE。"""
    if not span_id:
        return
    store_fields = dict(fields or {})
    buf = buffer_for_span(span_id)
    if buf:
        buf.end_span(span_id, **(fields or {}))
        rec = buf._by_id.get(span_id)
        if rec:
            pub = rec.as_public(work=buf.work, chapter=buf.chapter, kind=buf.kind)
            store_fields["timing"] = pub.get("timing")
            store_fields["status"] = rec.status
            if rec.actual is not None:
                store_fields["actual"] = rec.actual
            if rec.links:
                store_fields["links"] = rec.links
            if rec.error is not None:
                store_fields["error"] = rec.error
    try:
        if st is not None and hasattr(st, "update_pipeline_span"):
            st.update_pipeline_span(span_id, store_fields)
    except Exception as e:
        _log.warning("patch_span fail-soft: %s", e)


def finish_chain(
    st: Any,
    *,
    trace_id: str | None = None,
    status: str = "ok",
    extra: dict | None = None,
) -> None:
    if not pipeline_trace_enabled():
        return
    buf = buffer_for(trace_id)
    tid = (trace_id or (buf.trace_id if buf else "")).strip()
    if not tid:
        return
    try:
        existing = None
        if st is not None and hasattr(st, "get_pipeline_chain"):
            existing = st.get_pipeline_chain(tid)
        if existing and existing.get("status") != "in_progress":
            return
        if buf:
            flush_spans(st, buf)
            buf.status = status
            buf.ended_ns = int(time.time_ns())
            pubs = [s.as_public(work=buf.work, chapter=buf.chapter, kind=buf.kind) for s in buf.spans]
            buf.headline = headline_from_spans(pubs)
            patch = buf.snapshot_chain_patch()
            started = buf.started_ns or 0
            dur = max(0.0, (buf.ended_ns - started) / 1e6) if started else None
            patch.update({
                "status": status,
                "ended_at": datetime.now(timezone.utc),
                "duration_ms": dur,
                "headline": buf.headline,
            })
        else:
            patch = {"status": status, "ended_at": datetime.now(timezone.utc)}
        if extra:
            patch.update(extra)
        if st is not None and hasattr(st, "update_pipeline_chain"):
            st.update_pipeline_chain(tid, patch)
    except Exception as e:
        _log.warning("finish_chain fail-soft: %s", e)


def maybe_purge_pipeline_traces(st: Any, *, work: str = "main") -> None:
    if st is None or not hasattr(st, "purge_pipeline_traces_older_than"):
        return
    key = str(work or "main")
    now = time.time()
    with _LOCK:
        last = _PURGE_TS.get(key, 0)
        if now - last < 6 * 3600:
            return
        _PURGE_TS[key] = now
    try:
        st.purge_pipeline_traces_older_than(ttl_days())
    except Exception as e:
        _log.warning("maybe_purge_pipeline_traces fail-soft: %s", e)


def latest_pipeline_chain(st: Any, *, kind: str = "write") -> dict | None:
    if st is None or not hasattr(st, "list_pipeline_chains"):
        return None
    try:
        rows = st.list_pipeline_chains(kind=kind, limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


def list_chains(st: Any, **kw) -> list[dict[str, Any]]:
    if st is None or not hasattr(st, "list_pipeline_chains"):
        return []
    try:
        return st.list_pipeline_chains(**kw) or []
    except Exception as e:
        _log.debug("list_chains fail-soft: %s", e)
        return []


def get_chain(st: Any, trace_id: str) -> dict | None:
    if st is None or not hasattr(st, "get_pipeline_chain"):
        return None
    try:
        return st.get_pipeline_chain(trace_id)
    except Exception:
        return None


def list_spans(st: Any, **kw) -> list[dict[str, Any]]:
    if st is None or not hasattr(st, "list_pipeline_spans"):
        return []
    try:
        return st.list_pipeline_spans(**kw) or []
    except Exception:
        return []


def live_headline(chain: dict) -> str:
    if chain.get("status") == "in_progress":
        cursor = chain.get("cursor_step_key")
        started = chain.get("started_at")
        secs = None
        try:
            if hasattr(started, "timestamp"):
                secs = max(0.0, time.time() - started.timestamp())
        except Exception:
            secs = None
        if cursor:
            return headline_from_spans([], cursor=cursor, running_s=secs or 0)
    return str(chain.get("headline") or "")


def chain_as_run_card_item(raw: dict) -> dict[str, Any]:
    cs = raw.get("contrast_summary") if isinstance(raw.get("contrast_summary"), dict) else {}
    return {
        "run_id": raw.get("contrast_run_id") or "",
        "request_id": raw.get("trace_id"),
        "outcome_id": raw.get("outcome_id"),
        "kind": raw.get("kind"),
        "chapter": raw.get("chapter"),
        "phase": raw.get("phase"),
        "created_at": raw.get("created_at"),
        "verdict": cs.get("verdict") or "green",
        "summary": cs.get("summary") or {},
        "assemble_ok": cs.get("assemble_ok"),
        "outcome_status": raw.get("outcome_status"),
        "prompt_hard_profile": (cs.get("caps") or {}).get("prompt_hard_profile") if isinstance(cs.get("caps"), dict) else None,
        "quality_flags": (cs.get("quality") or {}).get("flags") if isinstance(cs.get("quality"), dict) else cs.get("quality_flags"),
        "trace_id": raw.get("trace_id"),
    }


def publicize_chain_list_item(raw: dict) -> dict[str, Any]:
    hl = live_headline(raw)
    dur = raw.get("duration_ms")
    if raw.get("status") == "in_progress" and dur is None:
        started = raw.get("started_at")
        try:
            if hasattr(started, "timestamp"):
                dur = max(0.0, (time.time() - started.timestamp()) * 1000)
        except Exception:
            pass
    stuck = ""
    if raw.get("status") == "in_progress" and isinstance(dur, (int, float)) and dur > 10 * 60 * 1000:
        title = lookup(str(raw.get("cursor_step_key") or "")).step_title
        stuck = f"可能卡在 {title}"
    return {
        "trace_id": raw.get("trace_id"),
        "request_id": raw.get("trace_id"),
        "kind": raw.get("kind"),
        "chapter": raw.get("chapter"),
        "phase": raw.get("phase"),
        "status": raw.get("status"),
        "cursor_step_key": raw.get("cursor_step_key"),
        "headline": hl or stuck,
        "started_at": raw.get("started_at") or raw.get("created_at"),
        "duration_ms": dur,
        "span_count": raw.get("span_count"),
        "red_count": raw.get("red_count"),
        "outcome_status": raw.get("outcome_status"),
        "stuck": stuck or None,
    }


def publicize_chain_detail(raw: dict, spans: list[dict], neighbors: dict | None = None) -> dict[str, Any]:
    item = publicize_chain_list_item(raw)
    pubs = [public_span(s) for s in spans]
    pubs = [p for p in pubs if p]
    pubs.sort(key=lambda s: ((s.get("timing") or {}).get("started_at") or "", s.get("span_id") or ""))
    tree = []
    for s in pubs:
        tree.append({
            "span_id": s.get("span_id"),
            "parent_span_id": s.get("parent_span_id"),
            "step_key": s.get("step_key"),
        })
    out = public_chain({
        **raw,
        **item,
        "spans": pubs,
        "tree": tree,
        "contrast_summary": raw.get("contrast_summary"),
        **(neighbors or {}),
    }) or {}
    out["ok"] = True
    return out
