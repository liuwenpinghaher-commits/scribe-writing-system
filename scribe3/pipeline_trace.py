"""Pipeline Trace 纯函数：缓冲、白名单、headline。零 I/O，禁止 import store / facts_at。"""
from __future__ import annotations

import hashlib
import os
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from scribe3.pipeline_trace_catalog import SCHEMA_VER, lookup, parent_of, tool_step_key
from scribe3.run_card import expected_for, make_facts, row_verdict

FORBIDDEN_KEYS = frozenset({
    "text", "instructions", "markers", "prompt", "arguments",
    "secret", "leak_markers", "input_text",
})
PUBLIC_SPAN_KEYS = frozenset({
    "span_id", "parent_span_id", "trace_id", "work", "chapter", "kind",
    "step_key", "step_title", "layer", "tier", "zone", "status",
    "expected", "expected_reason", "actual", "actual_reason", "verdict",
    "input", "compute", "output", "timing", "events", "quality", "error",
    "links", "schema_ver", "created_at",
})
PUBLIC_CHAIN_KEYS = frozenset({
    "trace_id", "request_id", "work", "chapter", "kind", "phase", "status",
    "cursor_step_key", "headline", "started_at", "ended_at", "duration_ms",
    "span_count", "red_count", "manifest_id", "actual_input_hash",
    "outcome_id", "outcome_status", "outcome_usage", "contrast_run_id",
    "contrast_summary", "notes", "schema_ver", "created_at",
    "prev_trace_id", "next_trace_id", "spans", "tree",
})
SPAN_CAP = 128
SPAN_JSON_SOFT = 4000

_BUF: ContextVar["TraceBuffer | None"] = ContextVar("scribe3_pt_buf", default=None)
_DISABLED: ContextVar[bool] = ContextVar("scribe3_pt_off", default=False)


def pipeline_trace_enabled() -> bool:
    if _DISABLED.get():
        return False
    raw = os.environ.get("SCRIBE3_PIPELINE_TRACE")
    if raw is None or str(raw).strip() == "":
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def preview_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_PIPELINE_TRACE_PREVIEW") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def disable_pipeline_trace() -> None:
    _DISABLED.set(True)


def enable_pipeline_trace() -> None:
    _DISABLED.set(False)


def current_trace_buffer() -> "TraceBuffer | None":
    return _BUF.get()


def bind_trace_buffer(buf: "TraceBuffer | None"):
    return _BUF.set(buf)


def reset_trace_buffer(token) -> None:
    try:
        _BUF.reset(token)
    except Exception:
        _BUF.set(None)


def _now_ns() -> int:
    return time.time_ns()


def _iso(ns: int | None) -> str | None:
    if not ns:
        return None
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _hex(n: int) -> str:
    return os.urandom(n).hex()


def strip_forbidden(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: strip_forbidden(v)
            for k, v in obj.items()
            if k not in FORBIDDEN_KEYS
        }
    if isinstance(obj, list):
        return [strip_forbidden(x) for x in obj]
    return obj


def digest_text(text: str | None) -> str | None:
    raw = (text or "").encode("utf-8")
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()


def l2_events_from_dropped(dropped: list[str] | None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for d in dropped or []:
        tag = str(d)
        if not tag:
            continue
        if any(tag.endswith(s) for s in (":tail_half", ":keep_beats", ":total_half")):
            op = "half_cut"
        else:
            op = "drop"
        events.append({"op": op, "tag": tag})
    return events


def resolve_assemble_request_id(
    envelope_trace: dict | None,
    *,
    work: str = "main",
    chapter: int = 1,
) -> tuple[str, bool]:
    """返回 (ContextRequest.request_id, obs_on)。禁止 uuid4。缺 id → 观测 no-op。"""
    rid = str((envelope_trace or {}).get("request_id") or "").strip()
    if rid:
        return rid, True
    buf = current_trace_buffer()
    if buf is not None and buf.trace_id:
        return str(buf.trace_id), True
    disable_pipeline_trace()
    fallback = hashlib.sha256(
        f"obs-noop\0{work}\0{chapter}\0{time.time_ns()}".encode()
    ).hexdigest()
    return fallback, False


@dataclass
class SpanRec:
    span_id: str
    parent_span_id: str | None
    trace_id: str
    step_key: str
    step_title: str
    layer: str
    status: str = "running"
    expected: bool | None = None
    expected_reason: str | None = None
    actual: str | None = None
    actual_reason: str | None = None
    verdict: str | None = None
    input: dict = field(default_factory=dict)
    compute: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    timing: dict = field(default_factory=dict)
    events: list = field(default_factory=list)
    quality: dict = field(default_factory=dict)
    error: dict | None = None
    links: dict = field(default_factory=dict)
    tier: str | None = None
    zone: str | None = None
    flushed: bool = False
    ended: bool = False
    started_ns: int = 0
    ended_ns: int = 0

    def as_public(self, *, work: str = "", chapter: int = 0, kind: str = "write") -> dict[str, Any]:
        dur = None
        if self.started_ns and self.ended_ns:
            dur = max(0.0, (self.ended_ns - self.started_ns) / 1e6)
        row = {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_id": self.trace_id,
            "work": work,
            "chapter": chapter,
            "kind": kind,
            "step_key": self.step_key,
            "step_title": self.step_title,
            "layer": self.layer,
            "tier": self.tier,
            "zone": self.zone,
            "status": self.status,
            "expected": self.expected,
            "expected_reason": self.expected_reason,
            "actual": self.actual,
            "actual_reason": self.actual_reason,
            "verdict": self.verdict,
            "input": strip_forbidden(dict(self.input or {})),
            "compute": strip_forbidden(dict(self.compute or {})),
            "output": strip_forbidden(dict(self.output or {})),
            "timing": {
                "started_at": _iso(self.started_ns),
                "ended_at": _iso(self.ended_ns) if self.ended else None,
                "duration_ms": dur,
            },
            "events": strip_forbidden(list(self.events or [])),
            "quality": strip_forbidden(dict(self.quality or {})),
            "error": strip_forbidden(self.error) if self.error else None,
            "links": strip_forbidden(dict(self.links or {})),
            "schema_ver": SCHEMA_VER,
        }
        return {k: v for k, v in row.items() if k in PUBLIC_SPAN_KEYS}


class TraceBuffer:
    def __init__(self) -> None:
        self.trace_id: str = ""
        self.work: str = "main"
        self.chapter: int = 1
        self.kind: str = "write"
        self.phase: str = "draft"
        self.cursor: str | None = None
        self.notes: list[str] = []
        self.spans: list[SpanRec] = []
        self._by_id: dict[str, SpanRec] = {}
        self._by_key: dict[str, str] = {}
        self.started_ns: int = 0
        self.ended_ns: int = 0
        self.status: str = "in_progress"
        self.manifest_id: str | None = None
        self.actual_input_hash: str | None = None
        self.outcome_id: str | None = None
        self.outcome_status: str | None = None
        self.outcome_usage: dict | None = None
        self.contrast_run_id: str | None = None
        self.contrast_summary: dict | None = None
        self.headline: str | None = None
        self.obs_on: bool = True

    def start_chain(
        self,
        *,
        work: str,
        chapter: int,
        kind: str,
        phase: str,
        trace_id: str,
    ) -> None:
        if not pipeline_trace_enabled() or not trace_id:
            self.obs_on = False
            return
        self.trace_id = str(trace_id)
        self.work = str(work or "main")
        self.chapter = int(chapter or 0)
        self.kind = str(kind or "write")
        self.phase = str(phase or "draft")
        self.started_ns = _now_ns()
        self.status = "in_progress"
        self.obs_on = True
        self.cursor = "assemble.precompute"

    def _cap_hit(self) -> bool:
        return len(self.spans) >= SPAN_CAP

    def start_span(self, step_key: str, *, parent: str | None = None) -> str:
        if not self.obs_on or not pipeline_trace_enabled() or not self.trace_id:
            return ""
        if self._cap_hit():
            if "span_cap" not in self.notes:
                self.notes.append("span_cap")
            return ""
        meta = lookup(step_key)
        parent_key = parent if parent is not None else meta.parent_key
        parent_span = None
        if parent_key:
            if parent_key in self._by_id:
                parent_span = parent_key
            else:
                parent_span = self._by_key.get(parent_key)
        sid = _hex(8)
        rec = SpanRec(
            span_id=sid,
            parent_span_id=parent_span,
            trace_id=self.trace_id,
            step_key=meta.step_key,
            step_title=meta.step_title,
            layer=meta.layer,
            tier=meta.tier,
            zone=meta.zone,
            started_ns=_now_ns(),
            compute={"fn": meta.compute_fn} if meta.compute_fn else {},
            input={"source": meta.source} if meta.source else {},
        )
        self.spans.append(rec)
        self._by_id[sid] = rec
        self._by_key[meta.step_key] = sid
        self.cursor = meta.step_key
        return sid

    def apply_fields(self, span_id: str, **fields: Any) -> None:
        """改字段，不打 ended。running INSERT 用这个。"""
        if not span_id or span_id not in self._by_id:
            return
        rec = self._by_id[span_id]
        for k in (
            "status", "expected", "expected_reason", "actual", "actual_reason",
            "verdict", "error",
        ):
            if k in fields and fields[k] is not None:
                setattr(rec, k, fields[k])
        for k in ("input", "compute", "output", "quality", "links"):
            if k in fields and isinstance(fields[k], dict):
                cur = getattr(rec, k) or {}
                cur.update(strip_forbidden(fields[k]))
                setattr(rec, k, cur)
        if "events" in fields and isinstance(fields["events"], list):
            rec.events = strip_forbidden(fields["events"])
        if rec.expected is not None and rec.actual and rec.verdict is None:
            try:
                rec.verdict = row_verdict(bool(rec.expected), rec.actual)  # type: ignore[arg-type]
            except Exception:
                pass

    def end_span(self, span_id: str, **fields: Any) -> None:
        if not span_id or span_id not in self._by_id:
            return
        rec = self._by_id[span_id]
        rec.ended = True
        rec.ended_ns = _now_ns()
        self.apply_fields(span_id, **fields)
        if not rec.status or rec.status == "running":
            rec.status = rec.actual or "ok"

    def patch_span(self, span_id: str, **fields: Any) -> None:
        self.end_span(span_id, **fields)
        rec = self._by_id.get(span_id)
        if rec:
            rec.ended = True

    def span_id_for(self, step_key: str) -> str:
        return self._by_key.get(step_key, "")

    def drain_ready(self) -> list[dict[str, Any]]:
        out = []
        for rec in self.spans:
            if rec.ended and not rec.flushed:
                rec.flushed = True
                out.append(rec.as_public(
                    work=self.work, chapter=self.chapter, kind=self.kind,
                ))
        return out

    def snapshot_chain_patch(self) -> dict[str, Any]:
        red = sum(1 for s in self.spans if s.verdict == "red")
        return {
            "cursor_step_key": self.cursor,
            "span_count": len(self.spans),
            "red_count": red,
            "notes": list(self.notes),
            "manifest_id": self.manifest_id,
            "actual_input_hash": self.actual_input_hash,
            "outcome_id": self.outcome_id,
            "outcome_status": self.outcome_status,
            "outcome_usage": self.outcome_usage,
            "contrast_run_id": self.contrast_run_id,
            "contrast_summary": self.contrast_summary,
            "headline": self.headline,
        }

    def red_count(self) -> int:
        return sum(1 for s in self.spans if s.verdict == "red")


def public_span(span: dict | SpanRec | None, **ctx) -> dict | None:
    if span is None:
        return None
    if isinstance(span, SpanRec):
        return span.as_public(**ctx)
    if not isinstance(span, dict):
        return None
    cleaned = strip_forbidden(dict(span))
    out = {k: cleaned.get(k) for k in PUBLIC_SPAN_KEYS if k in cleaned}
    for nest in ("input", "compute", "output", "quality", "links", "error"):
        if nest in out:
            out[nest] = strip_forbidden(out[nest])
    if "events" in out:
        out["events"] = strip_forbidden(out["events"])
    return out


def public_chain(chain: dict | None) -> dict | None:
    if not isinstance(chain, dict):
        return None
    cleaned = strip_forbidden(dict(chain))
    out = {k: cleaned.get(k) for k in PUBLIC_CHAIN_KEYS if k in cleaned}
    if "spans" in cleaned and isinstance(cleaned["spans"], list):
        out["spans"] = [public_span(s) for s in cleaned["spans"] if public_span(s)]
    if "contrast_summary" in out and isinstance(out["contrast_summary"], dict):
        cs = strip_forbidden(out["contrast_summary"])
        out["contrast_summary"] = {
            k: cs.get(k)
            for k in (
                "run_id", "verdict", "summary", "rows", "quality",
                "quality_flags", "assemble_ok", "chapter", "kind",
            )
            if k in cs
        }
    if out.get("trace_id") and "request_id" not in out:
        out["request_id"] = out.get("trace_id")
    return out


def headline_from_spans(
    spans: list[dict] | list[SpanRec],
    *,
    cursor: str | None = None,
    running_s: float | None = None,
) -> str:
    pubs: list[dict] = []
    for s in spans:
        if isinstance(s, SpanRec):
            pubs.append(s.as_public())
        elif isinstance(s, dict):
            pubs.append(s)
    if cursor and running_s is not None:
        title = lookup(cursor).step_title
        return f"卡在 {title}（进行中 {int(running_s)}s）"[:80]
    bits: list[str] = []
    for s in pubs:
        if s.get("verdict") == "red":
            title = s.get("step_title") or s.get("step_key") or "步骤"
            reason = s.get("actual_reason") or ""
            bits.append(f"{title}{('（' + reason + '）') if reason else ''}")
        if len(bits) >= 3:
            break
    for s in pubs:
        if s.get("step_key") == "budget.l2":
            ev = s.get("events") or []
            tags = [e.get("tag") for e in ev if isinstance(e, dict) and e.get("tag")]
            if not tags:
                dropped = (s.get("output") or {}).get("dropped") or []
                tags = [str(t) for t in dropped]
            drops = [t for t in tags if ":drop" in str(t) or str(t).endswith("drop")]
            if drops:
                bits.append("L2 丢 " + "、".join(str(t).split(":")[0] for t in drops[:3]))
    for s in pubs:
        if s.get("step_key") == "llm.generate":
            st = s.get("outcome_status") or (s.get("links") or {}).get("outcome_status")
            st = st or s.get("status") or s.get("actual")
            if st:
                bits.append(f"模型 {st}")
    text = " · ".join(bits) if bits else "对照齐全"
    return text[:80]


def apply_expected(rec: SpanRec, facts) -> None:
    name = rec.step_key
    if name.startswith("assemble.seg."):
        name = name[len("assemble.seg."):]
        exp, reason = expected_for(name, facts or make_facts())
        rec.expected = exp
        rec.expected_reason = reason


def ancestor_ids(spans: list[dict], span_id: str) -> set[str]:
    by = {s.get("span_id"): s for s in spans if isinstance(s, dict)}
    out: set[str] = set()
    cur = by.get(span_id)
    while cur and cur.get("parent_span_id"):
        pid = cur.get("parent_span_id")
        out.add(pid)
        cur = by.get(pid)
    return out


def descendant_ids(spans: list[dict], span_id: str) -> set[str]:
    kids: dict[str, list[str]] = {}
    for s in spans:
        if not isinstance(s, dict):
            continue
        p = s.get("parent_span_id")
        if p:
            kids.setdefault(p, []).append(s.get("span_id"))
    out: set[str] = set()
    stack = list(kids.get(span_id) or [])
    while stack:
        n = stack.pop()
        if not n or n in out:
            continue
        out.add(n)
        stack.extend(kids.get(n) or [])
    return out
