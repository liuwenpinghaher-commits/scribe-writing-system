"""写路径接线：handler 开链、assemble 计时、flush、关链。一律 fail-soft。"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable

from scribe3.pipeline_trace import (
    TraceBuffer,
    apply_expected,
    bind_trace_buffer,
    current_trace_buffer,
    digest_text,
    l2_events_from_dropped,
    pipeline_trace_enabled,
    prepare_emit_body,
    resolve_assemble_request_id,
)
from scribe3.pipeline_trace_catalog import lookup
from scribe3.pipeline_trace_store import (
    buffer_for,
    finish_chain,
    flush_spans,
    insert_running_span,
    patch_span,
    remember_buffer,
    start_chain,
)
from scribe3.run_card import classify_actual, expected_for, public_card, row_verdict

_log = logging.getLogger("scribe3.pipeline_trace")


def open_write_chain(
    st: Any,
    manifest_trace: dict | None,
    *,
    work: str,
    chapter: int,
    kind: str = "write",
    phase: str = "draft",
) -> str | None:
    if not isinstance(manifest_trace, dict):
        return None
    try:
        if not pipeline_trace_enabled():
            return None
        rid = str(manifest_trace.get("request_id") or "").strip()
        if not rid:
            rid = uuid.uuid4().hex
            manifest_trace["request_id"] = rid
        start_chain(
            st, work=work, chapter=int(chapter or 0),
            kind=kind, phase=phase or "draft", trace_id=rid,
        )
        return rid
    except Exception:
        _log.warning("open_write_chain fail-soft", exc_info=True)
        return None


@contextmanager
def write_chain_guard(st: Any, manifest_trace: dict | None):
    try:
        yield
    except Exception as e:
        try:
            rid = ""
            if isinstance(manifest_trace, dict):
                rid = str(manifest_trace.get("request_id") or "")
            finish_failed(st, manifest_trace, err=e)
            if not rid:
                finish_chain(st, trace_id=None, status="failed")
        except Exception:
            pass
        raise


def assemble_request_id(envelope_trace, *, work: str, chapter: int) -> str:
    rid, on = resolve_assemble_request_id(envelope_trace, work=work, chapter=chapter)
    if not on:
        return rid
    buf = current_trace_buffer()
    if buf is None and isinstance(envelope_trace, dict):
        existing = buffer_for(str(envelope_trace.get("request_id") or ""))
        if existing:
            bind_trace_buffer(existing)
    return rid


def _buf() -> TraceBuffer | None:
    if not pipeline_trace_enabled():
        return None
    return current_trace_buffer()


def timed_call(step_key: str, fn: Callable, *args, **kwargs):
    buf = _buf()
    if buf is None:
        return fn(*args, **kwargs)
    sid = buf.start_span(step_key)
    try:
        out = fn(*args, **kwargs)
        buf.end_span(sid, status="ok", actual="present" if out else "empty")
        return out
    except Exception as e:
        buf.end_span(
            sid, status="failed", actual="failed",
            error={"class": type(e).__name__, "summary": str(e)[:240]},
        )
        raise


def start_named(step_key: str) -> str:
    buf = _buf()
    if buf is None:
        return ""
    return buf.start_span(step_key)


def end_named(span_id: str, **fields) -> None:
    buf = _buf()
    if buf is None or not span_id:
        return
    buf.end_span(span_id, **fields)


def note_push(name: str, text: str | None, *, skip: str | None = None, attempted: bool = True) -> None:
    buf = _buf()
    if buf is None:
        return
    key = f"assemble.seg.{name}"
    sid = buf.span_id_for(key)
    if not sid:
        sid = buf.start_span(key)
    chars = len(text or "")
    actual, reason = classify_actual(
        name,
        domain_lengths={name: chars} if chars else {},
        skip_reason=skip,
        dropped=None,
        attempted_names={name} if attempted else set(),
    )
    meta = lookup(key)
    body, full_n, trunc = prepare_emit_body(text, name=name)
    fields = {
        "actual": actual,
        "actual_reason": reason,
        "status": actual,
        "output": {
            "shape": "block",
            "chars": chars,
            "digest": digest_text(text),
            "body": body,
            "truncated": trunc,
            "chars_full": full_n,
        },
        "compute": {"fn": meta.compute_fn},
    }
    facts = getattr(buf, "_facts", None)
    if facts is not None:
        exp, er = expected_for(name, facts)
        fields["expected"] = exp
        fields["expected_reason"] = er
        try:
            fields["verdict"] = row_verdict(exp, actual)
        except Exception:
            pass
    buf.end_span(sid, **fields)
    try:
        if skip:
            buf.append_log(sid, "skip.reason", reason=str(skip)[:32])
        else:
            buf.append_log(
                sid, "emit.shape",
                shape="block", chars=int(chars),
                status=str(actual or "ok"),
                body=text or "",
                name=str(name or ""),
            )
    except Exception:
        pass


def mark_facts(facts) -> None:
    buf = _buf()
    if buf is None:
        return
    buf._facts = facts  # type: ignore[attr-defined]
    sid = buf.start_span("assemble.freeze_expected")
    buf.end_span(sid, status="ok" if facts else "failed", actual="present" if facts else "failed")


def flush0(st: Any) -> None:
    flush_spans(st, _buf(), cursor="compile.engine")


def after_join(st: Any, bud_rep: dict | None) -> None:
    buf = _buf()
    if buf is None:
        return
    bud = bud_rep if isinstance(bud_rep, dict) else {}
    l2 = bud.get("l2") if isinstance(bud.get("l2"), dict) else {}
    te = bud.get("total_enforce") if isinstance(bud.get("total_enforce"), dict) else {}
    dropped = list(l2.get("dropped") or [])
    sid = buf.start_span("budget.l2")
    buf.end_span(
        sid,
        status="ok",
        events=l2_events_from_dropped(dropped),
        output={
            "dropped": dropped,
            "effective_l2_cap": l2.get("effective_l2_cap"),
            "l2_est": l2.get("l2_est"),
        },
    )
    o1d = list(te.get("dropped") or [])
    sid2 = buf.start_span("budget.o1")
    buf.end_span(
        sid2,
        status="ok",
        events=l2_events_from_dropped(o1d),
        output={"dropped": o1d},
    )
    flush_spans(st, buf, cursor="compile.manifest")


def after_compile(st: Any, compiled) -> None:
    buf = _buf()
    if buf is None:
        return
    try:
        buf.manifest_id = getattr(getattr(compiled, "manifest", None), "manifest_hash", None)
        buf.actual_input_hash = getattr(getattr(compiled, "manifest", None), "actual_input_hash", None)
    except Exception:
        pass
    sid = buf.span_id_for("compile.engine")
    if sid:
        buf.end_span(sid, status="ok")
    mid = buf.start_span("compile.manifest")
    buf.end_span(
        mid, status="ok",
        links={"manifest_id": buf.manifest_id},
        output={"manifest_id": buf.manifest_id, "actual_input_hash": buf.actual_input_hash},
    )
    flush_spans(st, buf, cursor="guard.epistemic")


def after_guard(st: Any, *, hits=None, leaked: bool = False) -> None:
    buf = _buf()
    if buf is None:
        return
    sid = buf.start_span("guard.epistemic")
    n = 0
    try:
        n = len(hits) if hits is not None and hasattr(hits, "__len__") else 0
    except Exception:
        n = 0
    buf.end_span(
        sid,
        status="failed" if leaked else "ok",
        actual="failed" if leaked else "present",
        output={"hit_count": n},
    )
    flush_spans(st, buf, cursor="llm.generate")


def attach_contrast(st: Any, card: dict | None) -> None:
    buf = _buf()
    if buf is None or not card:
        return
    pub = public_card(card) or {}
    # R7：对照行 actual/chars 与 span 同源
    by_name: dict[str, Any] = {}
    for rec in getattr(buf, "spans", []) or []:
        key = str(getattr(rec, "step_key", "") or "")
        name = key.split(".")[-1] if key else ""
        if name:
            by_name[name] = rec
    rows = pub.get("rows")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            rec = by_name.get(str(row.get("name") or ""))
            if rec is None:
                continue
            if rec.actual is not None:
                row["actual"] = rec.actual
            if rec.actual_reason:
                row["actual_reason"] = rec.actual_reason
            chars = (rec.output or {}).get("chars")
            if chars is not None:
                row["chars"] = chars
    buf.contrast_run_id = pub.get("run_id") or card.get("run_id")
    buf.contrast_summary = pub
    flush_spans(st, buf)


def start_llm(st: Any, manifest_trace: dict | None, *, work: str, chapter: int, kind: str = "write") -> str:
    rid = ""
    if isinstance(manifest_trace, dict):
        rid = str(manifest_trace.get("request_id") or "")
    if not rid:
        return ""
    buf = buffer_for(rid)
    if buf:
        bind_trace_buffer(buf)
    return insert_running_span(
        st, trace_id=rid, step_key="llm.generate",
        work=work, chapter=int(chapter or 0), kind=kind,
        extra={"status": "running", "actual": "running"},
    )


def start_tool(st: Any, manifest_trace: dict | None, name: str, *, work: str, chapter: int) -> str:
    from scribe3.pipeline_trace_catalog import tool_step_key
    rid = str((manifest_trace or {}).get("request_id") or "")
    if not rid:
        return ""
    return insert_running_span(
        st, trace_id=rid, step_key=tool_step_key(name),
        work=work, chapter=int(chapter or 0),
        extra={"status": "running", "actual": "running", "input": {"name": name}},
    )


def end_tool(st: Any, span_id: str, *, ok: bool = True, err: str | None = None) -> None:
    patch_span(st, span_id, {
        "status": "ok" if ok else "failed",
        "actual": "present" if ok else "failed",
        "error": ({"summary": (err or "")[:240]} if err else None),
    })


def note_llm_output(text: str | None) -> None:
    """模型产出正文进 llm.generate 的 emit.shape（帽内全文，不是只记 hash）。"""
    buf = _buf()
    if buf is None:
        return
    sid = buf.span_id_for("llm.generate")
    if not sid:
        sid = buf.start_span("llm.generate")
    raw = text or ""
    body, full, trunc = prepare_emit_body(raw, name="llm_output")
    try:
        buf.append_log(
            sid, "emit.shape",
            shape="prose", chars=len(raw),
            body=raw, name="llm_output", status="ok",
        )
        buf.apply_fields(sid, output={
            "shape": "prose", "chars": len(raw),
            "body": body, "truncated": trunc, "chars_full": full,
        })
    except Exception:
        pass


def finish_ok(st: Any, manifest_trace: dict | None, *, outcome=None) -> None:
    rid = str((manifest_trace or {}).get("request_id") or "")
    extra = {}
    if outcome is not None:
        extra = {
            "outcome_id": getattr(outcome, "outcome_id", None) or (outcome.get("outcome_id") if isinstance(outcome, dict) else None),
            "outcome_status": getattr(outcome, "status", None) or (outcome.get("status") if isinstance(outcome, dict) else None),
        }
        buf = buffer_for(rid)
        if buf:
            sid = buf.span_id_for("llm.generate")
            if sid:
                try:
                    patch_span(st, sid, {"status": "ok", "actual": "present", "links": extra})
                except Exception:
                    pass
            oid = buf.start_span("persist.outcome")
            buf.end_span(oid, status="ok", links=extra)
    finish_chain(st, trace_id=rid or None, status="ok", extra=extra)


def finish_failed(st: Any, manifest_trace: dict | None, err: BaseException | None = None) -> None:
    rid = str((manifest_trace or {}).get("request_id") or "")
    extra: dict[str, Any] = {}
    buf = buffer_for(rid) if rid else _buf()
    if err is not None and buf is not None:
        cls = type(err).__name__
        summary = str(err)[:240]
        sid = buf.span_id_for(buf.cursor or "") or (buf.spans[-1].span_id if buf.spans else "")
        if sid:
            buf.end_span(
                sid, status="failed", actual="failed",
                error={"class": cls, "summary": summary},
            )
        note = f"error:{cls}:{summary}"[:200]
        if note not in buf.notes:
            buf.notes.append(note)
        try:
            buf.append_log(
                sid or "",
                "error.raised",
                **{"class": cls, "summary": summary},
            )
        except Exception:
            pass
        extra["notes"] = list(buf.notes)
    finish_chain(st, trace_id=rid or None, status="failed", extra=extra or None)


def emit_gate_spans(
    st: Any,
    *,
    work: str,
    chapter: int,
    kind: str,
    trace_id: str,
    rows: list[dict],
    ok: bool,
    card: dict | None = None,
) -> None:
    if not pipeline_trace_enabled() or not trace_id:
        return
    try:
        mt = {"request_id": trace_id}
        buf = buffer_for(trace_id)
        if buf is None:
            open_write_chain(st, mt, work=work, chapter=chapter, kind=kind, phase=kind)
            buf = buffer_for(trace_id)
        if buf is None:
            return
        prefix = "save." if kind == "save" else "claim."
        for row in rows or []:
            name = str(row.get("name") or "")
            key = prefix + name
            sid = buf.start_span(key)
            actual = str(row.get("actual") or "absent")
            buf.end_span(
                sid,
                expected=bool(row.get("expected", True)),
                actual=actual,
                actual_reason=str(row.get("actual_reason") or ""),
                status=actual,
            )
        if card:
            attach_contrast(st, card)
        finish_chain(st, trace_id=trace_id, status="ok" if ok else "failed")
    except Exception:
        _log.warning("emit_gate_spans fail-soft", exc_info=True)
