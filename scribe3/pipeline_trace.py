"""Pipeline Trace 纯函数：缓冲、白名单、headline。零 I/O，禁止 import store / facts_at。"""
from __future__ import annotations

import hashlib
import os
import re
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
    "event_count", "artifact_count", "log_count",
    "fail_reasons", "retry_of",
})
# 140+142+150+151 允许 PATCH 的列。不含 created_at（READONLY）、trace_id（CREATE 强制补，UPDATE 只进 WHERE）。
CHAIN_PATCH_KEYS = frozenset({
    "work", "chapter", "kind", "phase", "status",
    "cursor_step_key", "headline", "started_at", "ended_at", "duration_ms",
    "span_count", "red_count", "manifest_id", "actual_input_hash",
    "outcome_id", "outcome_status", "outcome_usage",
    "contrast_run_id", "contrast_summary", "notes", "schema_ver",
    "event_count", "artifact_count", "log_count",
    "fail_reasons", "retry_of",
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


def norm_fail_reasons(xs: Any) -> list[str]:
    out: list[str] = []
    for x in xs or []:
        s = str(x or "").strip()
        if s and s not in out:
            out.append(s)
    return out


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
        self.fail_reasons: list[str] = []
        self.spans: list[SpanRec] = []
        self.logs: list[dict[str, Any]] = []
        self._log_seq: int = 0
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
        self.recorder = None
        self.last_prompt: str = ""
        self.retry_of: str | None = None

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
        try:
            from scribe3.pipeline_recorder import FlightRecorder
            self.recorder = FlightRecorder(
                work=self.work, chapter=self.chapter, kind=self.kind,
                trace_id=self.trace_id,
            )
        except Exception:
            self.recorder = None

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
        rec_buf = getattr(self, "recorder", None)
        if rec_buf is not None:
            try:
                rec_buf.remember_span(sid, meta.step_key)
            except Exception:
                pass
        try:
            self.append_log(sid, "step.start")
        except Exception:
            pass
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
        try:
            dur = None
            if rec.started_ns and rec.ended_ns:
                dur = max(0.0, (rec.ended_ns - rec.started_ns) / 1e6)
            self.append_log(span_id, "step.end", status=str(rec.status or "ok"), duration_ms=dur)
        except Exception:
            pass

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
            "event_count": (getattr(self, "recorder", None).counts()[0]
                            if getattr(self, "recorder", None) is not None else 0),
            "artifact_count": (getattr(self, "recorder", None).counts()[1]
                               if getattr(self, "recorder", None) is not None else 0),
            "log_count": len(self.logs),
            "fail_reasons": list(self.fail_reasons),
            "retry_of": self.retry_of,
        }

    def red_count(self) -> int:
        return sum(1 for s in self.spans if s.verdict == "red")

    def append_log(self, span_id: str, code: str, **kw) -> str:
        rec, row = render_log(
            code, kw,
            trace_id=self.trace_id,
            span_id=span_id,
            work=self.work,
            chapter=self.chapter,
            kind=self.kind,
        )
        if rec is None:
            return ""
        rec_span = self._by_id.get(span_id)
        if rec_span is not None:
            rec["step_key"] = rec_span.step_key
            rec["step_title"] = rec_span.step_title
            rec["layer"] = rec_span.layer
            row["step_key"] = rec_span.step_key
            row["step_title"] = rec_span.step_title
            row["layer"] = rec_span.layer
            if rec.get("code") == "step.start":
                rec["message"] = f"开始 {rec_span.step_title}"
                row["message"] = rec["message"]
        self._log_seq += 1
        rec["seq"] = self._log_seq
        rec["log_id"] = _hex(8)
        row["seq"] = rec["seq"]
        row["log_id"] = rec["log_id"]
        rec["_flushed"] = False
        rec["_store"] = row
        self.logs.append(rec)
        return rec["log_id"]

    def drain_logs(self) -> list[dict[str, Any]]:
        out = []
        for rec in self.logs:
            if rec.get("_flushed"):
                continue
            rec["_flushed"] = True
            store = dict(rec.get("_store") or public_log_row_for_store(rec))
            store["log_id"] = rec.get("log_id")
            store["seq"] = rec.get("seq")
            store["step_key"] = rec.get("step_key")
            store["step_title"] = rec.get("step_title")
            store["layer"] = rec.get("layer")
            store["trace_id"] = self.trace_id
            store["work"] = self.work
            store["chapter"] = self.chapter
            store["kind"] = self.kind
            store["schema_ver"] = SCHEMA_VER
            out.append(store)
        return out


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


_THICKEN_PHASES = frozenset({
    "outline", "beats", "design", "chapter_design", "deduce", "draft", "plan", "scaffold", "meta",
    "duty", "play", "contract", "final",
})

PLAYBOOK_FAIL_LABEL = {
    "dialogue_floor": "对白不够",
    "draft_len": "字数不够",
    "prose_len": "字数不够",
    "pov_consistency": "人称翻了",
    "state_quote": "原句对不上",
    "quote_not_in_play": "原句不在戏里",
    "quote_edited": "原句改过字",
    "draft_copy_play": "抄了戏",
    "gender_pronoun": "代词翻了",
    "draft_metaphor": "像字太多",
    "final_metaphor": "像字太多",
    "needs_human": "要人看",
    "play_empty": "戏是空的",
    "draft_empty": "糙稿是空的",
    "syntax_tics": "装腔",
    "retry_replaced": "上一笔没写完，重试了",
}


def label_playbook_fail(code: str) -> str:
    c = str(code or "").strip()
    return PLAYBOOK_FAIL_LABEL.get(c, c)


def headline_from_spans(
    spans: list[dict] | list[SpanRec],
    *,
    cursor: str | None = None,
    running_s: float | None = None,
    phase: str | None = None,
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
        if s.get("verdict") == "red" or s.get("status") == "failed":
            reason = str(s.get("actual_reason") or "")
            if "skip" in reason:
                continue
            title = s.get("step_title") or s.get("step_key") or "步骤"
            human = PLAYBOOK_FAIL_LABEL.get(reason, reason)
            bits.append(f"{title}{('（' + human + '）') if human else ''}")
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
    # skip / 可读红：诚实人话，永不「对照齐全」
    for s in pubs:
        reason = str(s.get("actual_reason") or "")
        key = str(s.get("step_key") or "")
        is_finalize_skip = (
            "finalize" in key
            or "finalize" in reason
            or reason == "skip_finalize_gate"
        )
        if is_finalize_skip:
            ph = str(phase or "").strip().lower()
            if ph not in _THICKEN_PHASES:
                bits.insert(0, "定稿门跳过")
            break
        if reason in ("readable_red", "unreadble", "may_not_claim_readable"):
            bits.insert(0, "可读未宣称")
            break
    text = " · ".join(bits) if bits else ""
    try:
        from scribe3.pipeline_recorder import current_recorder
        rec = current_recorder()
        arts = getattr(rec, "artifacts", None) if rec is not None else None
        if arts:
            for a in arts:
                kind = a.get("kind") if isinstance(a, dict) else getattr(a, "kind", "")
                if kind != "fate_delta":
                    continue
                body = a.get("body") if isinstance(a, dict) else getattr(a, "body", "")
                first = str(body or "").strip().splitlines()[0] if body else ""
                if first:
                    text = first
                break
    except Exception:
        pass
    if "对照齐全" in text:
        text = text.replace("对照齐全", "步骤完成")
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


NOTE_PUSH_FORBIDDEN_CODES = frozenset({
    "read.source", "pred.eval", "assoc.produce", "assoc.consume",
    "drop.item", "budget.cap", "usage.model",
})

_ENUM_RE = re.compile(r"^[a-z0-9_.:-]+$", re.I)
SOURCE_TAGS = frozenset({
    "chapter_prev_end_hook", "chapter_story_io", "chapter_recall", "chapter_causal",
    "compile_manifest", "internal", "flag", "chapter_field", "request_extra",
    "identity_block", "protocol_block", "prefix_block", "secret_guard_block",
    "focalizer_banner", "fuel_block", "envelope_block", "tool_arg_keys", "llm_input",
    "outline", "drama_contract", "voice_anchor", "codex", "other",
})

_MSG = {
    "step.start": "开始 {step_title}",
    "step.end": "结束 {status} {duration_ms}ms",
    "read.source": "读取 {source}：{empty_zh}",
    "pred.eval": "谓词 {pred}={value}（{reason}）",
    "branch.taken": "走 {fn}:{branch}",
    "keep.item": "保留 {name}",
    "drop.item": "{op} {name}",
    "skip.reason": "整步跳过：{reason}",
    "emit.shape": "产出 {shape} {chars} 字{preview}",
    "assoc.produce": "产出可供下游消费",
    "assoc.consume": "消费 {from_step_key}",
    "error.raised": "失败 {class}",
    "usage.model": "模型 {provider} chunks={chunk_count}",
    "budget.cap": "帽 {cap} · 已用 {used}",
    "flag.eval": "旗 {flag}={value}",
    "obs.incomplete": "本步未发齐日志：{missing}",
    "other": "未登记 code",
}


def _enum(v: Any, n: int) -> str:
    s = str(v or "").strip().lower().replace(" ", "_")[:n]
    if not s or not _ENUM_RE.match(s):
        return "other"
    return s


def _hexish(v: Any, n: int) -> str:
    s = re.sub(r"[^0-9a-fA-F]", "", str(v or ""))
    return s[:n]


def ember_read_kwargs(end_hook: str, pushed_chars: int) -> dict:
    """chars_in / empty 只看章字段 end_hook，不看 _push 长度。"""
    n = len((end_hook or "").strip())
    return {"source": "chapter_prev_end_hook", "chars_in": n, "empty": n == 0}


def pred_value_from_named(fn_value, *, chars_in: int | None = None) -> bool:
    return bool(fn_value)


LOG_BODY_CAP = 4096
_LEAK_LINE = re.compile(
    r"严禁在正文出现以下破绽词[^。]*。|破绽词含：[^。]*。",
    re.S,
)


def prepare_emit_body(text: str | None, *, name: str = "") -> tuple[str, int, bool]:
    """逐步日志可存的产出正文。返回 (body, chars_full, truncated)。

    不用键名 text（全局 FORBIDDEN_KEYS）。secret_guard / 破绽词表打码。
    """
    raw = text or ""
    full = len(raw)
    nm = (name or "").lower()
    if "secret_guard" in nm or "破绽词" in raw or "leak_markers" in raw:
        raw = _LEAK_LINE.sub("破绽词：〔已打码〕", raw)
        for bad in ("铜签", "锁眼", "拨锁", "填炉底"):
            if bad in raw and "工艺密" in raw:
                raw = raw.replace(bad, "〔密〕")
    if len(raw) > LOG_BODY_CAP:
        return raw[:LOG_BODY_CAP], full, True
    return raw, full, False


def render_log(code: str, kw: dict, *, trace_id: str, span_id: str,
               work: str, chapter: int, kind: str) -> tuple[dict | None, dict | None]:
    raw_code = str(code or "").strip()
    if raw_code not in _MSG:
        kw = dict(kw or {})
        kw["missing"] = [raw_code[:32] or "unknown"]
        raw_code = "other"
    attrs: dict[str, Any] = {}
    if raw_code == "read.source":
        src = str(kw.get("source") or "other")
        if src not in SOURCE_TAGS:
            src = "other"
        attrs["source"] = src
        attrs["empty"] = bool(kw.get("empty"))
        try:
            attrs["chars_in"] = int(kw.get("chars_in") or 0)
        except (TypeError, ValueError):
            attrs["chars_in"] = 0
        if kw.get("from_span_id"):
            attrs["from_span_id"] = _hexish(kw.get("from_span_id"), 16)
    elif raw_code == "pred.eval":
        attrs["pred"] = _enum(kw.get("pred"), 32)
        attrs["value"] = kw.get("value")
        attrs["reason"] = _enum(kw.get("reason"), 32)
    elif raw_code == "emit.shape":
        attrs["shape"] = _enum(kw.get("shape"), 32)
        try:
            attrs["chars"] = int(kw.get("chars") or 0)
        except (TypeError, ValueError):
            attrs["chars"] = 0
        name = str(kw.get("name") or "")
        if kw.get("body") is not None:
            body, full, trunc = prepare_emit_body(str(kw.get("body") or ""), name=name)
            attrs["body"] = body
            attrs["chars_full"] = full if full else attrs["chars"]
            attrs["truncated"] = bool(trunc)
            if attrs["chars"] == 0 and full:
                attrs["chars"] = full
        if kw.get("outcome_id"):
            attrs["outcome_id"] = _enum(kw.get("outcome_id"), 64)
        if kw.get("status"):
            attrs["status"] = _enum(kw.get("status"), 32)
        if kw.get("hit_count") is not None:
            try:
                attrs["hit_count"] = int(kw["hit_count"])
            except (TypeError, ValueError):
                pass
        if name:
            attrs["name"] = _enum(name, 32)
    elif raw_code == "skip.reason":
        attrs["reason"] = _enum(kw.get("reason"), 32)
    elif raw_code == "error.raised":
        attrs["class"] = _enum(kw.get("class"), 64)
        attrs["summary"] = str(kw.get("summary") or "")[:240]
    elif raw_code == "assoc.consume":
        got = bool(kw.get("got"))
        hex_id = _hexish(kw.get("from_span_id"), 16)
        if got and len(hex_id) < 16:
            return None, None
        attrs["from_step_key"] = _enum(kw.get("from_step_key"), 64)
        attrs["got"] = got
        if hex_id:
            attrs["from_span_id"] = hex_id
    elif raw_code == "assoc.produce":
        attrs["digest"] = str(kw.get("digest") or "")[:64]
        try:
            attrs["chars"] = int(kw.get("chars") or 0)
        except (TypeError, ValueError):
            attrs["chars"] = 0
    elif raw_code == "step.end":
        attrs["status"] = _enum(kw.get("status"), 32)
        if kw.get("duration_ms") is not None:
            try:
                attrs["duration_ms"] = float(kw["duration_ms"])
            except (TypeError, ValueError):
                pass
    elif raw_code == "obs.incomplete":
        miss = kw.get("missing") or []
        if isinstance(miss, str):
            miss = [miss]
        attrs["missing"] = [str(x)[:32] for x in list(miss)[:32]]
    elif raw_code == "other":
        miss = kw.get("missing") or []
        if isinstance(miss, str):
            miss = [miss]
        attrs["missing"] = [str(x)[:32] for x in list(miss)[:32]]
    else:
        for k, v in (kw or {}).items():
            if k in FORBIDDEN_KEYS:
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                attrs[k] = v

    ctx = {
        "step_title": "",
        "status": attrs.get("status", ""),
        "duration_ms": attrs.get("duration_ms", ""),
        "source": attrs.get("source", ""),
        "empty_zh": "空" if attrs.get("empty") else f"{attrs.get('chars_in') or attrs.get('chars') or 0} 字",
        "pred": attrs.get("pred", ""),
        "value": attrs.get("value", ""),
        "reason": attrs.get("reason", ""),
        "fn": attrs.get("fn", ""),
        "branch": attrs.get("branch", ""),
        "name": attrs.get("name", ""),
        "op": attrs.get("op", ""),
        "shape": attrs.get("shape", ""),
        "chars": attrs.get("chars", 0),
        "from_step_key": attrs.get("from_step_key", ""),
        "class": attrs.get("class", ""),
        "provider": attrs.get("provider", ""),
        "chunk_count": attrs.get("chunk_count", ""),
        "cap": attrs.get("cap", ""),
        "used": attrs.get("used", ""),
        "flag": attrs.get("flag", ""),
        "missing": ",".join(attrs.get("missing") or []),
        "preview": (
            ("：" + str(attrs.get("body") or "").replace("\n", " ")[:80])
            if attrs.get("body") else ""
        ),
    }
    msg = _MSG.get(raw_code, "日志")
    try:
        message = msg.format(**ctx)
    except Exception:
        message = raw_code
    level = "info"
    if raw_code in ("drop.item", "obs.incomplete") or attrs.get("empty"):
        level = "warn"
    if raw_code == "error.raised":
        level = "error"
    rec = {
        "trace_id": trace_id,
        "span_id": span_id,
        "code": raw_code,
        "message": message,
        "level": level,
        "attrs": attrs,
        "ts": datetime.now(timezone.utc),
        "work": work,
        "chapter": chapter,
        "kind": kind,
        "schema_ver": SCHEMA_VER,
    }
    store = public_log_row_for_store(rec)
    return rec, store


def public_log_row_for_store(rec: dict) -> dict[str, Any]:
    ts = rec.get("ts")
    if isinstance(ts, datetime):
        pass
    else:
        ts = datetime.now(timezone.utc)
    return {
        "log_id": rec.get("log_id") or "",
        "trace_id": rec.get("trace_id") or "",
        "span_id": rec.get("span_id") or "",
        "seq": int(rec.get("seq") or 0),
        "ts": ts,
        "level": rec.get("level") or "info",
        "step_key": rec.get("step_key") or "",
        "step_title": rec.get("step_title") or "",
        "layer": rec.get("layer") or "",
        "code": rec.get("code") or "other",
        "message": rec.get("message") or "",
        "attrs": strip_forbidden(dict(rec.get("attrs") or {})),
        "work": rec.get("work") or "",
        "chapter": int(rec.get("chapter") or 0),
        "kind": rec.get("kind") or "write",
        "schema_ver": rec.get("schema_ver") or SCHEMA_VER,
    }


def public_log(rec: dict | None) -> dict | None:
    if not isinstance(rec, dict):
        return None
    attrs = rec.get("attrs") if isinstance(rec.get("attrs"), dict) else {}
    ts = rec.get("ts")
    if isinstance(ts, datetime):
        ts_out = ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    else:
        ts_out = str(ts or "")
    return {
        "log_id": rec.get("log_id"),
        "ts": ts_out,
        "level": rec.get("level"),
        "step_key": rec.get("step_key"),
        "step_title": rec.get("step_title"),
        "layer": rec.get("layer"),
        "code": rec.get("code"),
        "message": rec.get("message"),
        "empty": attrs.get("empty"),
        "value": attrs.get("value"),
        "from_span_id": attrs.get("from_span_id"),
        "body": attrs.get("body"),
        "chars": attrs.get("chars"),
        "chars_full": attrs.get("chars_full"),
        "truncated": attrs.get("truncated"),
        "trace_id": rec.get("trace_id"),
        "span_id": rec.get("span_id"),
        "chapter": rec.get("chapter"),
        "kind": rec.get("kind"),
        "attrs": strip_forbidden(attrs),
        "schema_ver": rec.get("schema_ver") or SCHEMA_VER,
    }


def completeness_check(step_key: str, logs: list, *, ctx: dict | None = None) -> list[str]:
    """最小完整性：BASE 步至少有 step.start / step.end。"""
    codes = {str(x.get("code")) for x in (logs or []) if isinstance(x, dict)}
    missing: list[str] = []
    for need in ("step.start", "step.end"):
        if need not in codes:
            missing.append(need)
    dropped = list((ctx or {}).get("dropped_tags") or [])
    if dropped:
        drop_n = sum(1 for x in logs if isinstance(x, dict) and x.get("code") == "drop.item")
        if drop_n < len(dropped):
            missing.append("drop.item")
    return missing
