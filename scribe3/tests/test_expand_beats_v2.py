"""PR-2 · expand_beats v2 纯函数与轻量接线（无 Surreal 子进程 / 无网络）。"""
from __future__ import annotations

import pytest

from scribe3.api.services.pilot_runtime import (
    grounding_candidate_from_beats,
    parse_beats_v1_lines,
    parse_beats_v2_output,
    _compose_beats_meta,
    _beats_from_synopsis_segments,
)


def test_parse_beats_v2_output_gcd_and_chapter_hook():
    raw = """
scene|逼出真名|对方以亲人要挟|他拒绝开口|暴露立场不可收回|闸板再裂一寸|沈砚拒绝报出名字|密|900
bridge|喘口气|||无||两人沉默|疏|
CHAPTER_HOOK|第二声裂响从闸底传来
"""
    beats, hook = parse_beats_v2_output(raw)
    assert hook == "第二声裂响从闸底传来"
    assert len(beats) == 2
    assert beats[0]["goal"] == "逼出真名"
    assert beats[0]["conflict"] == "对方以亲人要挟"
    assert beats[0]["turn"] == "他拒绝开口"
    assert beats[0]["cost"] == "暴露立场不可收回"
    assert beats[0]["text"]
    assert beats[0].get("budget") == 900
    assert beats[1]["kind"] == "bridge"
    # 末拍 hook 由 chapter_hook 回填
    assert beats[-1].get("hook") == hook


def test_grounding_candidate_includes_gcd_not_just_text():
    beats = [{
        "text": "摘要一句",
        "goal": "要过闸",
        "conflict": "闸口盘查",
        "turn": "被迫亮证",
        "cost": "身份暴露",
        "hook": "谁还在后面",
    }]
    cand = grounding_candidate_from_beats(beats)
    for token in ("摘要一句", "要过闸", "闸口盘查", "被迫亮证", "身份暴露", "谁还在后面"):
        assert token in cand


def test_parse_v1_and_synopsis_segments():
    v1 = parse_beats_v1_lines("1. 甲推门\n· 乙反锁\n")
    assert [b["text"] for b in v1] == ["甲推门", "乙反锁"]
    fb = _beats_from_synopsis_segments("第一句动作。第二句反转；第三句代价！")
    assert len(fb) >= 2
    assert all(b.get("text") for b in fb)


def test_compose_beats_meta_advisory_drama_validation():
    # 内联 good-enough v2（不依赖 Surreal / 不拉 fixture 包）
    beats = [{
        "id": "b1", "kind": "scene",
        "goal": "逼对方说出灰契下落",
        "conflict": "对方以哑姑安危要挟拒绝",
        "turn": "他没能拿到名字却逼出证据",
        "cost": "立场暴露不可收回",
        "hook": "闸板裂响",
        "text": "潮闸对峙",
    }]
    meta = _compose_beats_meta(
        beats,
        schema="v2",
        beats_source="llm_v2",
        chapter_hook="第二声裂响",
        synopsis="沈砚在潮闸前要灰契下落。",
        chapter_pressure=5,
        role="高压",
    )
    assert meta["schema"] == "v2"
    assert meta["beats_source"] == "llm_v2"
    assert meta["chapter_hook"] == "第二声裂响"
    assert "drama_validation" in meta
    assert "ok" in meta["drama_validation"]
    assert "drama_score" in meta
    assert meta["drama_score"]["gcd_scene_count"] >= 1


def test_chapter_meta_req_accepts_beats_meta():
    from scribe3.api.models import ChapterMetaReq

    req = ChapterMetaReq.model_validate({
        "beats_meta": {
            "schema": "v2",
            "beats_source": "llm_v2",
            "chapter_hook": "钩",
            "drama_validation": {"ok": True, "errors": [], "warnings": [], "drama_weak": False},
        }
    })
    dumped = req.model_dump(exclude_unset=True)
    assert "beats_meta" in dumped
    assert dumped["beats_meta"]["beats_source"] == "llm_v2"
