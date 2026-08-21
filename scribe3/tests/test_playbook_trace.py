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

    def list_pipeline_chains(self, *, chapter=None, kind=None, status=None, since=None, until=None, limit=20):
        out = []
        for rec in self.chains.values():
            if chapter is not None and int(rec.get("chapter") or 0) != int(chapter):
                continue
            if kind and rec.get("kind") != kind:
                continue
            if status and rec.get("status") != status:
                continue
            out.append(rec)
        return out[: int(limit or 20)]


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
        st.create_only_pipeline_chain(tid + "ok", {"status": "in_progress"})
        buf2 = TraceBuffer()
        buf2.start_chain(work="w", chapter=1, kind="write", phase="draft", trace_id=tid + "ok")
        remember_buffer(buf2)
        st.chains[tid + "ok"]["status"] = "in_progress"
        finish_chain(st, trace_id=tid + "ok", status="ok", extra={"fail_reasons": ["draft_len"]})
        assert "过了" in str(st.chains[tid + "ok"].get("headline") or "")
        assert "字数不够" in str(st.chains[tid + "ok"].get("headline") or "")
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


def test_stale_in_progress_closed_when_retry_opens():
    from scribe3.pipeline_trace_hooks import open_write_chain
    enable_pipeline_trace()
    st = _FakeStore()
    old = "ee" * 16
    st.create_only_pipeline_chain(old, {
        "status": "in_progress", "work": "w", "chapter": 1,
        "kind": "write", "phase": "draft",
        "notes": ["fail_reasons:draft_len,draft_copy_play"],
    })
    mt: dict = {}
    try:
        rid = open_write_chain(st, mt, work="w", chapter=1, kind="write", phase="draft")
        assert rid
        assert rid != old
        assert st.chains[old]["status"] == "failed"
        hl = str(st.chains[old].get("headline") or "")
        assert "字数不够" in hl or "抄了戏" in hl
    finally:
        reset_trace_buffer(None)


def test_chain_patch_whitelist_and_create_trace_id_column():
    from scribe3.pipeline_trace import CHAIN_PATCH_KEYS
    from scribe3.store.pipeline_trace_ops import PipelineTraceOpsMixin
    from scribe3.pipeline_trace import public_chain
    from scribe3.pipeline_trace_store import publicize_chain_list_item

    assert "_CHAIN_SET" not in open(
        __import__("pathlib").Path(__file__).resolve().parents[1] / "store/pipeline_trace_ops.py",
        encoding="utf-8",
    ).read()
    assert "fail_reasons" in CHAIN_PATCH_KEYS
    assert "event_count" in CHAIN_PATCH_KEYS
    assert "trace_id" not in CHAIN_PATCH_KEYS

    class Rec(PipelineTraceOpsMixin):
        def __init__(self):
            self.calls = []
            self.rows = {}
            self.reject = set()

        def _execute_write(self, sql, params):
            self.calls.append((sql, dict(params)))
            for k in list(self.reject):
                if k in params and k != "trace_id" and f"{k}=${k}" in sql:
                    raise RuntimeError(f"Found field `{k}` that is not present")
            tid = params.get("trace_id")
            if "CREATE" in sql:
                self.rows[tid] = dict(params)
            else:
                rec = dict(self.rows.get(tid) or {})
                rec.update({k: v for k, v in params.items() if k != "trace_id"})
                rec["trace_id"] = tid
                self.rows[tid] = rec

        def get_pipeline_chain(self, tid):
            return self.rows.get(tid)

    st = Rec()
    tid = "aa" * 16
    st.create_only_pipeline_chain(tid, {
        "status": "in_progress",
        "outcome_id": "o1",
        "event_count": 2,
        "fail_reasons": [],
        "not_a_column": 1,
    })
    sql, params = st.calls[0]
    assert "CREATE" in sql
    assert "trace_id=$trace_id" in sql
    assert "not_a_column" not in sql
    assert "fail_reasons=$fail_reasons" in sql
    row = st.get_pipeline_chain(tid)
    assert row and row.get("trace_id") == tid
    st.update_pipeline_chain(tid, {
        "status": "ok",
        "outcome_id": "o1",
        "event_count": 3,
        "fail_reasons": ["draft_len"],
        "not_a_column": 1,
        "trace_id": "should-not-set",
    })
    usql, uparams = st.calls[-1]
    assert "UPDATE" in usql
    assert "trace_id=$trace_id" in usql
    assert "SET" in usql
    set_part = usql.split("SET", 1)[1].split("WHERE", 1)[0]
    assert "trace_id=" not in set_part.replace(" ", "") or "trace_id=$trace_id" not in set_part
    assert "trace_id=$trace_id" not in set_part
    assert "not_a_column" not in usql
    st.reject.add("fail_reasons")
    tid2 = "bb" * 16
    st.create_only_pipeline_chain(tid2, {"status": "in_progress", "fail_reasons": ["x"]})
    assert st.get_pipeline_chain(tid2)
    assert st.get_pipeline_chain(tid2).get("trace_id") == tid2
    assert any("fail_reasons" not in sql and "CREATE" in sql for sql, _ in st.calls if "bb" in str(_))
    listed = publicize_chain_list_item({
        "trace_id": tid, "status": "failed", "notes": ["fail_reasons:draft_len"],
    })
    assert listed.get("fail_reasons") == ["draft_len"]
    detail = public_chain({
        "trace_id": tid, "status": "failed", "fail_reasons": ["draft_copy_play"],
        "work": "w", "chapter": 1, "kind": "write",
    })
    assert detail.get("fail_reasons") == ["draft_copy_play"]


def test_note_reasons_lives_on_buffer_snapshot():
    enable_pipeline_trace()
    from scribe3.pipeline_trace_hooks import playbook_note_reasons
    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=1, kind="write", phase="draft", trace_id="ff" * 16)
    tok = bind_trace_buffer(buf)
    try:
        playbook_note_reasons(["draft_len", "draft_copy_play"])
        assert buf.fail_reasons == ["draft_len", "draft_copy_play"]
        snap = buf.snapshot_chain_patch()
        assert snap.get("fail_reasons") == ["draft_len", "draft_copy_play"]
    finally:
        reset_trace_buffer(tok)
