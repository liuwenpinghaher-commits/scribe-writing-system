"""写章五层细账：检查没过必须留下原因，落库必须刷进记录仪。"""
from __future__ import annotations

from types import SimpleNamespace

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
        self.logs = []
        self.chains = {}

    def insert_pipeline_events(self, rows):
        self.events.extend(rows or [])

    def insert_pipeline_artifacts(self, rows):
        self.artifacts.extend(rows or [])

    def insert_pipeline_spans(self, rows):
        self.spans.extend(rows or [])

    def insert_pipeline_logs(self, rows):
        self.logs.extend(rows or [])

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


def test_quality_loop_json_layer_body_not_empty():
    enable_pipeline_trace()
    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=1, kind="write", phase="duty", trace_id="aa" * 16)
    tok = bind_trace_buffer(buf)
    remember_buffer(buf)
    try:
        _quality_loop(
            name="duty",
            generate=lambda: {"must_happen": "甲必须挡观测", "bill": "观测变贵"},
            struct=lambda d: {"ok": False, "code": "duty_who"},
            judge_type="duty",
            judge_ctx=lambda d: {},
            llm_fn=_short_llm,
        )
        rec = buf.recorder
        outs = [a for a in (rec.artifacts if rec else []) if str(a.get("name") or "").startswith("duty.out")]
        assert outs, "duty.out must exist"
        assert "甲必须挡观测" in str(outs[0].get("body") or "")
        assert (outs[0].get("chars") or 0) > 0
    finally:
        reset_trace_buffer(tok)


def test_quality_loop_records_prompt_in():
    from scribe3.playbook.layers import _call

    enable_pipeline_trace()
    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=1, kind="write", phase="duty", trace_id="ab" * 16)
    tok = bind_trace_buffer(buf)
    remember_buffer(buf)
    try:
        def gen():
            _call(_short_llm, "【本章责】柳岸青必须在成核点前做决定。", system="s",
                  temperature=0.2, max_tokens=8)
            return {"must_happen": "做决定"}

        _quality_loop(
            name="duty",
            generate=gen,
            struct=lambda d: {"ok": False, "code": "duty_who"},
            judge_type="duty",
            judge_ctx=lambda d: {},
            llm_fn=_short_llm,
        )
        rec = buf.recorder
        ins = [a for a in (rec.artifacts if rec else []) if ".in." in str(a.get("name") or "")]
        assert ins, "prompt .in must exist"
        assert "本章责" in str(ins[0].get("body") or "")
        assert ins[0].get("kind") == "prompt"
    finally:
        reset_trace_buffer(tok)


def test_begin_discuss_trace_kind():
    from scribe3.pipeline_trace_hooks import (
        begin_discuss_trace, end_discuss_trace, note_discuss_step,
    )
    enable_pipeline_trace()
    st = _FakeStore()
    tok = bind_trace_buffer(TraceBuffer())
    try:
        mt = begin_discuss_trace(st, work="w", chapter=0)
        assert mt.get("request_id")
        note_discuss_step(
            "discuss.assemble", name="discuss.assemble.in",
            body="系统提示含柳岸青", summary="前置",
            kind="prompt",
        )
        end_discuss_trace(st, mt, ok=True)
        row = st.get_pipeline_chain(mt["request_id"])
        assert row and row.get("kind") == "discuss"
        assert any("柳岸青" in str(a.get("body") or "") for a in st.artifacts)
    finally:
        reset_trace_buffer(tok)


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
        assert "场面没立住" in str(st.chains[tid + "ok"].get("headline") or "")
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
        assert "场面没立住" in hl or "抄了戏" in hl
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


def test_after_compile_records_dropped_without_body():
    from scribe3.pipeline_trace_hooks import after_compile
    enable_pipeline_trace()
    st = _FakeStore()
    buf = TraceBuffer()
    tid = "dd" * 16
    buf.start_chain(work="w", chapter=1, kind="write", phase="draft", trace_id=tid)
    tok = bind_trace_buffer(buf)
    remember_buffer(buf)
    try:
        env = SimpleNamespace(omitted=[{
            "source_id": "mem:1", "reason": "token_budget", "block": "recent",
            "text": "秘密正文不该进丢掉清单",
        }])
        compiled = SimpleNamespace(
            envelope=env,
            manifest=SimpleNamespace(manifest_hash="mh", actual_input_hash="ah"),
        )
        after_compile(st, compiled)
        dropped = [a for a in st.artifacts if a.get("name") == "assemble.dropped"]
        assert dropped and dropped[0].get("kind") == "dropped"
        body = str(dropped[0].get("body") or "")
        assert "token_budget" in body and "mem:1" in body
        assert "秘密正文" not in body
    finally:
        reset_trace_buffer(tok)


def test_after_join_notes_prompt_hard_cap():
    from scribe3.pipeline_trace_hooks import after_join
    enable_pipeline_trace()
    st = _FakeStore()
    buf = TraceBuffer()
    tid = "ee" * 16
    buf.start_chain(work="w", chapter=1, kind="write", phase="draft", trace_id=tid)
    tok = bind_trace_buffer(buf)
    remember_buffer(buf)
    try:
        after_join(st, {
            "l2": {
                "dropped": ["codex:prompt_hard_drop"],
                "prompt_hard": 48000,
                "l2_est": 50000,
            },
            "total_enforce": {"dropped": []},
            "prompt_hard": 48000,
        })
        assert any((e.get("payload") or {}).get("tag") == "prompt_hard" for e in st.events)
        assert any(lg.get("code") == "budget.cap" for lg in st.logs)
    finally:
        reset_trace_buffer(tok)


def test_retry_of_and_stale_flag():
    from scribe3.pipeline_trace_hooks import open_write_chain
    from scribe3.pipeline_trace_store import publicize_chain_list_item
    enable_pipeline_trace()
    st = _FakeStore()
    tok = bind_trace_buffer(TraceBuffer())
    try:
        mt1 = {"request_id": "11" * 16}
        open_write_chain(st, mt1, work="w", chapter=1, kind="write", phase="draft")
        mt2 = {"request_id": "22" * 16}
        open_write_chain(st, mt2, work="w", chapter=1, kind="write", phase="draft")
        row = st.get_pipeline_chain("22" * 16)
        assert row and row.get("retry_of") == "11" * 16
        item = publicize_chain_list_item({
            "status": "in_progress",
            "duration_ms": 11 * 60 * 1000,
            "cursor_step_key": "assemble.precompute",
            "retry_of": "11" * 16,
        })
        assert item.get("stale") is True
        assert item.get("retry_of") == "11" * 16
    finally:
        reset_trace_buffer(tok)


def test_build_ctx_uses_soft_fail():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "playbook/context.py").read_text(encoding="utf-8")
    assert "soft_fail" in src
    assert "note_guide_missing" in src
    mig = (Path(__file__).resolve().parents[1] / "migrations/151_pipeline_chain_discuss_retry.surql").read_text()
    assert "discuss" in mig and "retry_of" in mig
