"""Pipeline Trace 零 I/O 合同。禁止本机 Surreal。"""
from __future__ import annotations

import hashlib

from scribe3.pipeline_trace import (
    FORBIDDEN_KEYS,
    TraceBuffer,
    disable_pipeline_trace,
    enable_pipeline_trace,
    headline_from_spans,
    l2_events_from_dropped,
    public_span,
    resolve_assemble_request_id,
)
from scribe3.pipeline_trace_catalog import lookup, parent_of
from scribe3.run_card import expected_for, make_facts


def test_public_span_strips_forbidden_keys():
    rec = {
        "span_id": "aa" * 8,
        "step_key": "assemble.seg.story_ember",
        "step_title": "上章余烬",
        "layer": "assemble",
        "status": "empty",
        "text": "【上章余烬】不该出现",
        "instructions": "系统提示词全文",
        "markers": ["破绽甲"],
        "prompt": "96k",
        "input": {"source": "hook", "text": "正文", "prompt": "x"},
        "compute": {"fn": "collect_story_fuel_segments"},
        "output": {"chars": 0, "instructions": "nope"},
    }
    pub = public_span(rec)
    assert pub is not None
    blob = str(pub)
    for bad in FORBIDDEN_KEYS:
        assert bad not in pub
        if bad in ("text", "instructions", "markers", "prompt"):
            assert f"'{bad}'" not in blob.replace("collect_story_fuel_segments", "")
    assert pub["step_title"] == "上章余烬"
    assert pub["input"]["source"] == "hook"
    assert "text" not in pub["input"]
    assert "prompt" not in pub["input"]
    assert "instructions" not in pub["output"]


def test_expected_false_without_hook():
    facts = make_facts()
    exp, reason = expected_for("story_ember", facts)
    assert exp is False
    assert reason == "no_end_hook"
    exp2, reason2 = expected_for("event_drive_hook", facts)
    assert exp2 is False


def test_l2_dropped_goes_into_events():
    ev = l2_events_from_dropped(["material_recall:drop", "codex:tail_half"])
    assert ev[0]["op"] == "drop"
    assert ev[0]["tag"] == "material_recall:drop"
    assert ev[1]["op"] == "half_cut"
    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=1, kind="write", phase="draft", trace_id="ab" * 16)
    sid = buf.start_span("budget.l2")
    buf.end_span(sid, status="ok", events=ev, output={"dropped": ["material_recall:drop"]})
    drained = buf.drain_ready()
    assert drained[0]["events"][0]["tag"] == "material_recall:drop"
    assert "text" not in drained[0]


def test_headline_is_human_not_red_green_count():
    spans = [
        {
            "step_key": "assemble.seg.story_ember",
            "step_title": "上章余烬",
            "verdict": "red",
            "actual_reason": "empty_story_ember",
        },
        {
            "step_key": "budget.l2",
            "step_title": "L2 补充裁剪",
            "verdict": "green",
            "events": [{"op": "drop", "tag": "material_recall:drop"}],
        },
        {
            "step_key": "llm.generate",
            "step_title": "模型生成",
            "status": "succeeded",
            "links": {"outcome_status": "succeeded"},
        },
    ]
    h = headline_from_spans(spans)
    assert "红" not in h and "绿" not in h
    assert "上章余烬" in h
    assert "L2" in h
    live = headline_from_spans([], cursor="llm.generate", running_s=41)
    assert "卡在" in live and "模型生成" in live and "41" in live


def test_missing_request_id_is_noop_no_uuid_mint():
    enable_pipeline_trace()
    import uuid as _uuid
    called = {"n": 0}
    real = _uuid.uuid4

    def boom():
        called["n"] += 1
        raise AssertionError("uuid4 must not mint pipeline id")

    _uuid.uuid4 = boom  # type: ignore[method-assign]
    try:
        rid, on = resolve_assemble_request_id({}, work="demo", chapter=3)
        assert on is False
        assert len(rid) == 64
        assert called["n"] == 0
        assert hashlib.sha256(rid.encode()).hexdigest()  # hex
        buf = TraceBuffer()
        buf.start_chain(work="demo", chapter=3, kind="write", phase="draft", trace_id="")
        assert buf.trace_id == "" or not buf.obs_on
        sid = buf.start_span("assemble.precompute")
        assert sid == ""
    finally:
        _uuid.uuid4 = real  # type: ignore[method-assign]
        enable_pipeline_trace()


def test_parent_tree_and_titles():
    assert parent_of("assemble.seg.story_ember") == "assemble.collect_fuel"
    assert parent_of("assemble.seg.identity") == "assemble.precompute"
    assert parent_of("budget.l2") == "compile.engine"
    assert lookup("assemble.seg.story_ember").step_title == "上章余烬"
    assert lookup("llm.generate").layer == "llm"


def test_handler_id_consumed_not_reminted():
    enable_pipeline_trace()
    rid, on = resolve_assemble_request_id({"request_id": "cd" * 16}, work="w", chapter=1)
    assert on is True
    assert rid == "cd" * 16


class _FakeStore:
    def __init__(self):
        self.inserted = []
        self.updated = []

    def create_only_pipeline_chain(self, trace_id, fields):
        return None

    def insert_pipeline_spans(self, rows):
        self.inserted.extend(list(rows or []))

    def update_pipeline_chain(self, trace_id, fields):
        return None

    def update_pipeline_span(self, span_id, fields):
        self.updated.append((span_id, dict(fields)))

    def get_pipeline_chain(self, trace_id):
        return {"trace_id": trace_id, "status": "in_progress"}


def test_llm_running_insert_has_no_end_timing_then_finish_writes_duration():
    """驱动 shipped insert_running_span + finish_ok：INSERT 不得 stamp 终态耗时。"""
    import time
    from scribe3.pipeline_trace import enable_pipeline_trace
    from scribe3.pipeline_trace_hooks import finish_ok, start_llm
    from scribe3.pipeline_trace_store import start_chain

    enable_pipeline_trace()
    st = _FakeStore()
    mt = {"request_id": "11" * 16}
    start_chain(st, work="w", chapter=2, kind="write", phase="draft", trace_id=mt["request_id"])
    sid = start_llm(st, mt, work="w", chapter=2)
    assert sid
    assert st.inserted, "start_llm must INSERT running span"
    row = st.inserted[-1]
    assert row["step_key"] == "llm.generate"
    assert row["status"] == "running"
    timing = row.get("timing") or {}
    assert timing.get("ended_at") is None
    assert timing.get("duration_ms") is None
    time.sleep(0.05)
    finish_ok(st, mt, outcome={"outcome_id": "out1", "status": "succeeded"})
    patches = [f for sid2, f in st.updated if sid2 == sid]
    assert patches, "finish_ok must UPDATE llm span"
    last = patches[-1]
    t2 = last.get("timing") or {}
    assert t2.get("ended_at"), last
    assert t2.get("duration_ms") is not None and float(t2["duration_ms"]) >= 40, t2
    assert last.get("status") == "ok"


def test_tool_end_writes_real_duration():
    import time
    from scribe3.pipeline_trace import enable_pipeline_trace
    from scribe3.pipeline_trace_hooks import end_tool, start_tool
    from scribe3.pipeline_trace_store import start_chain

    enable_pipeline_trace()
    st = _FakeStore()
    mt = {"request_id": "22" * 16}
    start_chain(st, work="w", chapter=2, kind="write", phase="draft", trace_id=mt["request_id"])
    sid = start_tool(st, mt, "s3_search", work="w", chapter=2)
    assert sid
    ins = st.inserted[-1]
    assert (ins.get("timing") or {}).get("ended_at") is None
    time.sleep(0.05)
    end_tool(st, sid, ok=True)
    patches = [f for sid2, f in st.updated if sid2 == sid]
    assert patches
    t2 = patches[-1].get("timing") or {}
    assert t2.get("ended_at")
    assert float(t2.get("duration_ms") or 0) >= 40, t2


if __name__ == "__main__":
    tests = [
        test_public_span_strips_forbidden_keys,
        test_expected_false_without_hook,
        test_l2_dropped_goes_into_events,
        test_headline_is_human_not_red_green_count,
        test_missing_request_id_is_noop_no_uuid_mint,
        test_parent_tree_and_titles,
        test_handler_id_consumed_not_reminted,
        test_llm_running_insert_has_no_end_timing_then_finish_writes_duration,
        test_tool_end_writes_real_duration,
    ]
    for fn in tests:
        fn()
        print("ok", fn.__name__)
    print("ALL_OK", len(tests))
