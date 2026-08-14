"""逐步日志必须带上产出正文（不是只记字数）。驱动 shipped render_log / note_push。"""
from __future__ import annotations

from scribe3.pipeline_trace import (
    LOG_BODY_CAP,
    TraceBuffer,
    prepare_emit_body,
    public_log,
    render_log,
)
from scribe3.pipeline_trace_hooks import note_llm_output, note_push


def test_prepare_emit_body_keeps_segment_and_redacts_leaks():
    body, n, trunc = prepare_emit_body("【上章余烬】炉火舔着膛。", name="story_ember")
    assert "炉火舔着膛" in body
    assert n == len("【上章余烬】炉火舔着膛。")
    assert trunc is False
    dirty = "严禁在正文出现以下破绽词: 铜签、锁眼、拨锁。其余可写。"
    red, _, _ = prepare_emit_body(dirty, name="secret_guard")
    assert "铜签" not in red or "已打码" in red
    assert "已打码" in red
    long = "炉" * (LOG_BODY_CAP + 80)
    cut, full, trunc = prepare_emit_body(long, name="outline")
    assert trunc is True
    assert full == LOG_BODY_CAP + 80
    assert len(cut) == LOG_BODY_CAP


def test_render_log_emit_shape_stores_body_not_just_chars():
    rec, store = render_log(
        "emit.shape",
        {"shape": "block", "chars": 9, "body": "炉火舔着膛。", "name": "story_ember"},
        trace_id="ab" * 16, span_id="cd" * 8, work="book_x", chapter=6, kind="write",
    )
    assert rec is not None
    assert rec["attrs"]["body"] == "炉火舔着膛。"
    assert "炉火舔着膛" in rec["message"]
    assert "text" not in rec["attrs"]
    pub = public_log({**rec, "step_key": "assemble.seg.story_ember", "step_title": "上章余烬"})
    assert pub["body"] == "炉火舔着膛。"
    assert pub["chars"] == 9
    assert store["attrs"]["body"] == "炉火舔着膛。"


def test_note_push_log_contains_full_block():
    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=6, kind="write", phase="final", trace_id="ef" * 16)
    from scribe3.pipeline_trace import bind_trace_buffer, reset_trace_buffer
    tok = bind_trace_buffer(buf)
    try:
        buf.start_span("assemble.seg.drama_contract")
        note_push("drama_contract", "〔必须发生〕清册官摊灯册。霍三刀巷口按鞘。")
        rows = buf.drain_logs()
    finally:
        reset_trace_buffer(tok)
    emits = [r for r in rows if r.get("code") == "emit.shape"]
    assert emits
    body = (emits[0].get("attrs") or {}).get("body") or ""
    assert "必须发生" in body
    assert "清册官摊灯册" in body


def test_admin_page_renders_log_body():
    from pathlib import Path
    page = (
        Path(__file__).resolve().parents[1] / "web/src/admin/RunLogsPage.jsx"
    ).read_text(encoding="utf-8")
    assert "run-log-body" in page
    assert "lg.body" in page or "attrs.body" in page


def test_note_llm_output_lands_on_generate_span():
    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=6, kind="write", phase="final", trace_id="11" * 16)
    from scribe3.pipeline_trace import bind_trace_buffer, reset_trace_buffer
    tok = bind_trace_buffer(buf)
    try:
        buf.start_span("llm.generate")
        note_llm_output("正午的日头晒在镇口晒谷场上。")
        rows = buf.drain_logs()
    finally:
        reset_trace_buffer(tok)
    emits = [r for r in rows if r.get("code") == "emit.shape"]
    assert any("晒谷场" in str((r.get("attrs") or {}).get("body") or "") for r in emits)


if __name__ == "__main__":
    test_prepare_emit_body_keeps_segment_and_redacts_leaks()
    test_render_log_emit_shape_stores_body_not_just_chars()
    test_note_push_log_contains_full_block()
    test_admin_page_renders_log_body()
    test_note_llm_output_lands_on_generate_span()
    print("PASS test_pipeline_log_emit_body")
