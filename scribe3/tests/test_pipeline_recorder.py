"""飞行记录仪纯函数。禁止 Surreal。"""
from __future__ import annotations

import json

from scribe3.pipeline_recorder import (
    FlightRecorder,
    completeness_check,
    dump_story_inputs,
    strip_recorder_forbidden,
)
from scribe3.pipeline_trace import headline_from_spans


def _rec() -> FlightRecorder:
    return FlightRecorder(work="w", chapter=6, kind="write", trace_id="ab" * 16, enabled=True)


def test_strip_keeps_text_key():
    out = strip_recorder_forbidden({"text": "余烬原文", "leak_markers": ["铜签"], "ok": 1})
    assert out["text"] == "余烬原文"
    assert "leak_markers" not in out


def test_dump_story_inputs_keys_complete():
    dump = dump_story_inputs({
        "chapter": 16,
        "prior_consequences": "他回头看了一眼铜炉，没说话。",
        "contract": {"desire": "要夺回铜印", "obstacle": "师兄先到了库房",
                     "turn": "发现印匣是空的", "cost": "把妹妹的行踪暴露给对家"},
        "evidence_must_show": ["袖口那粒铜渣"],
        "voice": {"label": "冷短"},
        "recall_context": "- 铜炉.守夜人：还在东厢",
        "causal_graph": "- 第15章 印匣被调包",
    })
    assert dump["prior_consequences"].startswith("他回头")
    assert dump["contract"]["desire"] == "要夺回铜印"
    assert dump["presence"]["prior_consequences"] is True
    body = json.dumps(dump, ensure_ascii=False)
    assert "prior_consequences" in body
    rec = _rec()
    aid = rec.put_artifact(kind="story_inputs", name="chapter_story_io", body=body, media="json")
    assert len(aid) == 16
    rec.emit("s1", "read", artifact_ids=[aid], payload={"text": dump["prior_consequences"][:80]})
    ev = rec.events[-1]
    assert ev["payload"]["text"].startswith("他回头")


def test_ember_fixture_a_empty_hook():
    rec = _rec()
    dump = dump_story_inputs({"chapter": 2, "prior_consequences": ""})
    rec.put_artifact(kind="story_inputs", name="chapter_story_io",
                     body=json.dumps(dump, ensure_ascii=False), media="json")
    hook = dump["prior_consequences"]
    empty = len(hook.strip()) == 0
    rec.remember_span("sp", "assemble.seg.story_ember")
    rec.emit("sp", "read", empty=empty, payload={"source": "chapter_prev_end_hook", "text": hook})
    rec.emit("sp", "pred", pred="prev_end_hook", pred_value=bool(hook.strip()),
             payload={"inputs": {"chars": len(hook), "empty": empty}})
    rec.put_artifact(kind="fuel_block", name="story_ember", body="")
    assert rec.events[0]["empty"] is True
    assert rec.events[1]["pred_value"] is False


def test_ember_fixture_b_hook_not_pushed():
    rec = _rec()
    dump = dump_story_inputs({"chapter": 2, "prior_consequences": "有钩子字"})
    rec.put_artifact(kind="story_inputs", name="chapter_story_io",
                     body=json.dumps(dump, ensure_ascii=False), media="json")
    hook = dump["prior_consequences"]
    rec.remember_span("sp", "assemble.seg.story_ember")
    rec.emit("sp", "read", empty=len(hook.strip()) == 0,
             payload={"source": "chapter_prev_end_hook", "text": hook})
    rec.emit("sp", "pred", pred="prev_end_hook", pred_value=bool(hook.strip()))
    rec.put_artifact(kind="fuel_block", name="story_ember", body="")
    assert rec.events[0]["empty"] is False
    assert rec.events[1]["pred_value"] is True


def test_three_produces_first_name_keeps_first_id():
    rec = _rec()
    rec.remember_span("p", "assemble.compile")
    a = rec.put_artifact(kind="segment", name="identity", body="身份段")
    rec.produce("p", a, name="identity")
    b = rec.put_artifact(kind="segment", name="prefix", body="前缀段")
    rec.produce("p", b, name="prefix")
    c = rec.put_artifact(kind="segment", name="story_ember", body="余烬段")
    rec.produce("p", c, name="story_ember")
    assert rec._produced_by_name["identity"] == a
    assert rec._produced_by_name["prefix"] == b
    assert rec._produced_by_name["story_ember"] == c
    assert len(rec._produced_by_key["assemble.compile"]) == 3


def test_half_cut_overrides_name_keeps_both_ids():
    rec = _rec()
    rec.remember_span("p", "budget.l2")
    before = rec.put_artifact(kind="drop_before", name="material_recall", body="长素材")
    rec.produce("p", before, name="material_recall")
    after = rec.put_artifact(kind="drop_after", name="material_recall", body="短素材")
    rec.produce("p", after, name="material_recall")
    assert rec._produced_by_name["material_recall"] == after
    assert rec._produced_by_key["budget.l2"] == [before, after]


def test_joined_meta_consume_llm():
    rec = _rec()
    rec.remember_span("c", "assemble.compile")
    rec.remember_span("l", "llm.generate")
    j = rec.put_artifact(kind="joined_meta", name="compile_joined",
                         body=json.dumps({"order": ["a"], "chars_total": 10}, ensure_ascii=False),
                         media="json")
    rec.produce("c", j, name="compile_joined")
    eid = rec.consume("l", artifact_id=j)
    assert eid
    ev = rec.events[-1]
    assert ev["kind"] == "consume"
    assert ev["from_artifact_id"] == j


def test_secret_guard_without_redact_rejected():
    rec = _rec()
    assert rec.put_artifact(kind="segment", name="secret_guard", body="破绽词含：铜签。") == ""
    ok = rec.put_artifact(kind="segment", name="secret_guard", body="破绽词含：铜签。",
                          redact="secret_guard")
    assert ok
    body = rec.artifacts[-1]["body"]
    assert "已打码" in body


def test_over_cap_truncated_body_nonempty():
    rec = _rec()
    long = "炉" * 16400
    aid = rec.put_artifact(kind="segment", name="outline", body=long)
    assert aid
    art = rec.artifacts[-1]
    assert art["truncated"] is True
    assert art["chars_full"] == 16400
    assert art["body"]
    assert len(art["body"]) == 16384
    assert art["digest"]


def test_join_chars_survive_drain_and_consume_segments():
    rec = _rec()
    rec.remember_span("p", "assemble.seg.prefix")
    rec.remember_span("e", "assemble.seg.story_ember")
    rec.remember_span("io", "assemble.load_story_inputs")
    rec.remember_span("j", "compile.manifest")
    io = rec.put_artifact(
        kind="story_inputs", name="chapter_story_io",
        body='{"presence":{"contract":true}}', media="json",
    )
    rec.produce("io", io, name="chapter_story_io")
    a = rec.put_artifact(kind="segment", name="prefix", body="前缀十二字整")
    rec.produce("p", a, name="prefix")
    b = rec.put_artifact(kind="segment", name="story_ember", body="亥正三刻烟囱风")
    rec.produce("e", b, name="story_ember")
    rec.put_artifact(kind="fuel_block", name="story_ember", body="亥正三刻烟囱风")
    rec.drain()
    assert rec.artifacts == []
    snap = rec.snapshot_join()
    assert snap["order"] == ["prefix", "story_ember"]
    assert snap["chars_total"] == len("前缀十二字整") + len("亥正三刻烟囱风")
    assert snap["segment_artifact_ids"] == [a, b]
    rec.consume("j", artifact_id=a, role="input")
    rec.consume("j", artifact_id=b, role="input")
    rec.consume("j", name="chapter_story_io", role="input")
    kinds = [e["kind"] for e in rec.events if e["kind"] == "consume"]
    assert len(kinds) == 3
    consumed = [e["from_artifact_id"] for e in rec.events if e["kind"] == "consume"]
    assert consumed == [a, b, io]


def test_call_llm_notes_usage_chars():
    from scribe3.pipeline_trace import TraceBuffer, bind_trace_buffer
    from scribe3.pipeline_recorder import FlightRecorder
    from scribe3.stage_generate import _call_llm, resolve_stage_focalizer

    assert resolve_stage_focalizer("", {"focalizer": "role:qin_huiqi"}) == "role:qin_huiqi"
    assert resolve_stage_focalizer("role:x", {"focalizer": "role:qin_huiqi"}) == "role:x"

    buf = TraceBuffer()
    buf.start_chain(work="w", chapter=4, kind="write", phase="draft", trace_id="ab" * 16)
    rec = FlightRecorder(work="w", chapter=4, enabled=True)
    buf.recorder = rec
    bind_trace_buffer(buf)
    out = _call_llm(lambda prompt, max_tokens=10: "亥正三刻烟囱风倒灌。", "prompt", 20)
    assert "亥正三刻" in out
    usages = [e for e in rec.events if e.get("kind") == "usage"]
    assert usages
    assert usages[-1]["payload"]["output_chars"] == len("亥正三刻烟囱风倒灌。")
    bind_trace_buffer(None)


def test_strip_codex_pad_drops_slogan():
    from scribe3.api.services.write_assemble_blocks import strip_codex_pad
    raw = (
        "表层目标:拦住覃灰七。这不是口号，是巷里炉灰和铜腥贴在骨头上的实感。"
        "这不是口号，是巷里炉灰和铜腥贴在骨头上的实感。恐惧:侧门。"
    )
    out = strip_codex_pad(raw)
    assert "这不是口号" not in out
    assert "拦住覃灰七" in out


def test_strip_codex_pad_collapses_triple_repeat_and_empty():
    from scribe3.api.services.write_assemble_blocks import strip_codex_pad
    assert strip_codex_pad("") == ""
    raw = "这一句必须留下八字以上；这一句必须留下八字以上；这一句必须留下八字以上。"
    out = strip_codex_pad(raw)
    assert out.count("这一句必须留下八字以上") == 1


def test_assemble_v1_does_not_double_produce_ember_fuel():
    from pathlib import Path
    text = Path(__file__).resolve().parents[1].joinpath(
        "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert 'kind="fuel_block"' not in text
    assert "story_ember_fuel" not in text
    assert 'kind="segment", name=name' in text


def test_consume_missing_id_returns_none():
    rec = _rec()
    rec.remember_span("a", "assemble.compile")
    rec.produce("a", rec.put_artifact(kind="segment", name="x", body="1"), name="x")
    rec.produce("a", rec.put_artifact(kind="segment", name="y", body="2"), name="y")
    assert rec.consume("b", from_step_key="assemble.compile") is None
    assert rec.consume("b", artifact_id="not-hex") is None


def test_headline_never_contrast_ok():
    h = headline_from_spans([])
    assert "对照齐全" not in h


def test_completeness_unstarted_silent():
    assert completeness_check("assemble.load_story_inputs", [], [], ctx={"started": False}) == []


def test_pipeline_recorder_default_on_and_settings_off():
    """无覆盖默认开；env/设置 0/false 才关。禁止 Surreal。"""
    import os
    from scribe3.pipeline_recorder import pipeline_recorder_enabled

    old = os.environ.get("SCRIBE3_PIPELINE_RECORDER")
    try:
        os.environ.pop("SCRIBE3_PIPELINE_RECORDER", None)
        assert pipeline_recorder_enabled() is True
        os.environ["SCRIBE3_PIPELINE_RECORDER"] = "0"
        assert pipeline_recorder_enabled() is False
        os.environ["SCRIBE3_PIPELINE_RECORDER"] = "false"
        assert pipeline_recorder_enabled() is False
        os.environ["SCRIBE3_PIPELINE_RECORDER"] = "1"
        assert pipeline_recorder_enabled() is True
    finally:
        if old is None:
            os.environ.pop("SCRIBE3_PIPELINE_RECORDER", None)
        else:
            os.environ["SCRIBE3_PIPELINE_RECORDER"] = old


def test_completeness_hard_load():
    miss = completeness_check("assemble.load_story_inputs", [], [], ctx={"started": True})
    assert "story_inputs" in miss
    rec = _rec()
    rec.remember_span("s", "assemble.load_story_inputs")
    aid = rec.put_artifact(kind="story_inputs", name="chapter_story_io", body="{}", media="json")
    rec.emit("s", "read")
    rec.produce("s", aid)
    miss2 = completeness_check(
        "assemble.load_story_inputs", rec.events, rec.artifacts, ctx={"started": True},
    )
    assert miss2 == []
