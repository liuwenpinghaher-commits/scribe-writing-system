"""冰山只留 clip_for。evaluate_iceberg / persist 闸已废。禁止 Surreal。"""
from __future__ import annotations

from scribe3.iceberg import (
    clip_for,
    evaluate_iceberg,
    persist_fields_blocked,
    should_block_prose_write,
    sync_design_surface,
)


def test_evaluate_iceberg_is_passthrough():
    r = evaluate_iceberg({"synopsis": "一句口号"}, for_phase="draft")
    assert r["ok"] is True
    assert r["missing"] == []


def test_persist_fields_never_blocks():
    assert persist_fields_blocked({"synopsis": "口号"}) is None
    assert persist_fields_blocked({"beats": [{"text": "短"}]}) is None
    assert persist_fields_blocked({"title": "第六章"}) is None


def test_sync_design_surface_returns_fields():
    fields = {"goal": "x"}
    assert sync_design_surface(fields) == fields


def test_clip_for_keeps_short_and_caps_long():
    short = "短文"
    assert clip_for("synopsis", short) == short
    long = "甲" * 8000
    clipped = clip_for("synopsis", long)
    assert len(clipped) <= 2500
    assert clipped.startswith("甲")


def test_thicken_phases_are_not_blocked():
    assert should_block_prose_write("outline", write_intent=True) is False
    assert should_block_prose_write("beats", write_intent=True) is False
    assert should_block_prose_write("deduce", write_intent=True) is False
    assert should_block_prose_write("draft", write_intent=True) is True
    assert should_block_prose_write("final", write_intent=True) is True
    assert should_block_prose_write("draft", write_intent=False) is False
