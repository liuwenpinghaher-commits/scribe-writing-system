"""内容质量轨：闸绿 ≠ quality_pass。"""
from scribe3.verify_content_quality import review_chapter_quality
from scribe3.tests.test_craft_compliance_gates import (
    craft_world_min, craft_chapter_scaffold,
)


def test_short_prose_fails_quality(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    store.save_chapter(seq, "沈砚推门。老道缄口。灰印一痕。", focalizer="role:沈砚")
    r = review_chapter_quality(store, seq)
    assert r.ok is False
    assert any(c.id == "Q1_LENGTH" and not c.ok for c in r.checks)


def test_quality_not_auto_pass_when_gates_would_pass(store):
    """短而干净的稿可过 C1，但质量轨必须红。"""
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    prose = "沈砚推门。他对质灰契。老道缄口。灰印与契血似有若无。"
    store.save_chapter(seq, prose, focalizer="role:沈砚")
    r = review_chapter_quality(store, seq)
    assert r.ok is False
    assert "不通过" in r.summary


def test_quality_report_shape(store):
    seq = craft_world_min(store)
    craft_chapter_scaffold(store, seq)
    store.save_chapter(seq, "x" * 100, focalizer="role:沈砚")
    d = review_chapter_quality(store, seq).to_dict()
    assert "quality_pass" in d
    assert "闸绿" in d["note"]
