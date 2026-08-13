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


if __name__ == "__main__":
    tests = [
        test_public_span_strips_forbidden_keys,
        test_expected_false_without_hook,
        test_l2_dropped_goes_into_events,
        test_headline_is_human_not_red_green_count,
        test_missing_request_id_is_noop_no_uuid_mint,
        test_parent_tree_and_titles,
        test_handler_id_consumed_not_reminted,
    ]
    for fn in tests:
        fn()
        print("ok", fn.__name__)
    print("ALL_OK", len(tests))
