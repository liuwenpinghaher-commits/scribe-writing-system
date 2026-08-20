"""写章五层细账：检查没过必须留下原因，落库必须刷进记录仪。"""
from __future__ import annotations

from scribe3.pipeline_trace import (
    TraceBuffer,
    bind_trace_buffer,
    enable_pipeline_trace,
    headline_from_spans,
    reset_trace_buffer,
)
from scribe3.pipeline_trace_store import finish_chain, flush_spans, remember_buffer
from scribe3.playbook.pipeline import _quality_loop
from scribe3.playbook.structural import check_draft_struct


class _FakeStore:
    def __init__(self):
        self.events = []
        self.artifacts = []
        self.spans = []
        self.chains = {}

    def insert_pipeline_events(self, rows):
        self.events.extend(rows or [])

    def insert_pipeline_artifacts(self, rows):
        self.artifacts.extend(rows or [])

    def insert_pipeline_spans(self, rows):
        self.spans.extend(rows or [])

    def update_pipeline_chain(self, tid, patch):
        rec = dict(self.chains.get(tid) or {})
        rec.update(patch or {})
        rec["trace_id"] = tid
        self.chains[tid] = rec

    def get_pipeline_chain(self, tid):
        return self.chains.get(tid)

    def create_only_pipeline_chain(self, tid, fields):
        self.chains[tid] = {"trace_id": tid, **(fields or {}), "status": "in_progress"}


def _short_llm(prompt, **kw):
    return "短。" * 10


def test_quality_loop_records_struct_fail_reason():
    enable_pipeline_trace()
    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=1, kind="write", phase="draft", trace_id="ab" * 16)
    tok = bind_trace_buffer(buf)
    remember_buffer(buf)
    try:
        out = _quality_loop(
            name="draft",
            generate=lambda: {"text": _short_llm("")},
            struct=lambda d: check_draft_struct(d.get("text") if isinstance(d, dict) else str(d)),
            judge_type="draft",
            judge_ctx=lambda d: {},
            llm_fn=_short_llm,
        )
        assert out.get("ok") is False
        assert "draft_len" in (out.get("fail_reasons") or [])
        keys = [s.step_key for s in buf.spans]
        assert "playbook.generate" in keys
        assert "playbook.struct" in keys
        rec = buf.recorder
        kinds = [e.get("kind") for e in (rec.events if rec else [])]
        assert "gate" in kinds
        assert any((e.get("payload") or {}).get("tag") == "draft_len" for e in rec.events)
    finally:
        reset_trace_buffer(tok)


def test_flush_drains_recorder_and_failed_headline():
    enable_pipeline_trace()
    st = _FakeStore()
    buf = TraceBuffer()
    tid = "cd" * 16
    buf.start_chain(work="w", chapter=1, kind="write", phase="draft", trace_id=tid)
    tok = bind_trace_buffer(buf)
    remember_buffer(buf)
    st.create_only_pipeline_chain(tid, {"status": "in_progress", "work": "w", "chapter": 1})
    try:
        sid = buf.start_span("playbook.struct")
        rec = buf.recorder
        rec.emit(sid, "gate", summary="对白不够", payload={"got": False, "tag": "dialogue_floor", "reason": "对白不够"})
        buf.end_span(sid, status="failed", actual="failed", actual_reason="dialogue_floor", verdict="red")
        flush_spans(st, buf)
        assert st.events, "events must land"
        assert any(e.get("kind") == "gate" for e in st.events)
        finish_chain(st, trace_id=tid, status="failed", extra={"fail_reasons": ["dialogue_floor"]})
        chain = st.chains[tid]
        assert chain["status"] == "failed"
        assert "对白不够" in str(chain.get("headline") or "")
    finally:
        reset_trace_buffer(tok)


def test_headline_empty_is_not_placeholder():
    h = headline_from_spans([])
    assert h == ""
    h2 = headline_from_spans([
        {
            "step_key": "playbook.struct",
            "step_title": "检查",
            "verdict": "red",
            "status": "failed",
            "actual_reason": "dialogue_floor",
        },
    ])
    assert "对白不够" in h2
