"""冰山生成链：StageSpec / 解析 / 必须 LLM / 禁切句回退。禁止 Surreal。"""
from __future__ import annotations

import pytest

from scribe3.iceberg import BEAT_EACH_FLOOR, DEDUCTION_FLOOR, DRAFT_FLOOR, SYNOPSIS_FLOOR
from scribe3.stage_craft_prompt import stage_craft_block
from scribe3.stage_generate import (
    draft_tip,
    iceberg_ok_for,
    parse_beats_payload,
    parse_outline_payload,
    stage_max_tokens,
    stage_ready,
    thicken_beats,
    thicken_draft,
    thicken_outline,
)


def _fat(seed: str, n: int) -> str:
    return seed + ("甲" * n)


def test_stage_craft_is_kernel_not_slogan():
    blk = stage_craft_block("outline")
    assert "500" in blk
    assert "不要凑字数" not in blk
    assert len(blk) <= 400
    assert stage_craft_block("final") == ""
    assert stage_craft_block("draft") == ""


def test_parse_outline_floor():
    thin = parse_outline_payload("清册官入镇封炉。")
    assert thin["ok"] is False
    assert thin["cn"] < SYNOPSIS_FLOOR
    fat = parse_outline_payload(
        "日子：炉前核册。\n必须发生：缺页贴腕。\n因：三笔夜税。\n"
        "不能说：炉契全文。\n章末未决：侧门谁开。\n" + ("乙" * 500)
    )
    assert fat["ok"] is True
    assert "必须发生" in fat["parts"]
    assert "不能说" in fat["parts"]


def test_parse_beats_scene_paper():
    paper = "\n".join(
        f"## 拍{i}\n进场：炉前。\n事件：摊册。\n翻转：反咬。\n出场：把柄。\n水下：他早知道。\n"
        + ("丙" * 720)
        for i in (1, 2, 3)
    )
    parsed = parse_beats_payload(paper)
    assert parsed["ok"] is True
    assert len(parsed["beats"]) == 3
    assert all(n >= BEAT_EACH_FLOOR for n in parsed["each"])
    assert parsed["source"] == "llm"


def test_thicken_outline_requires_llm_and_rejects_template():
    with pytest.raises(ValueError, match="llm_fn"):
        thicken_outline({"synopsis": ""}, llm_fn=None)

    calls = {"n": 0}

    def short_llm(prompt, max_tokens=2048):
        calls["n"] += 1
        return "一句口号大纲。"

    out = thicken_outline({"synopsis": "短"}, llm_fn=short_llm)
    assert out["ok"] is False
    assert out["code"] == "llm_thin"
    assert out["source"] == "llm"
    assert calls["n"] == 2  # 一次 + 严格重试


def test_thicken_outline_persists_only_thick_llm():
    persisted = {}

    def fat_llm(prompt, max_tokens=2048):
        return (
            "日子：清册日炉前摊灯册。\n必须发生：缺页贴上旧烫疤。\n"
            "因：三笔夜税未入炉。\n不能说：侧门开法。\n章末未决：霍三刀还在巷口。\n"
            + ("丁" * 480)
        )

    r = thicken_outline(
        {"synopsis": "短口号"},
        llm_fn=fat_llm,
        persist_fn=lambda f: persisted.update(f),
        seq=6,
    )
    assert r["ok"] is True
    assert r["source"] == "llm"
    assert persisted["synopsis"].startswith("日子")
    assert iceberg_ok_for({"synopsis": persisted["synopsis"]}, "synopsis")


def test_thicken_beats_no_synopsis_cut():
    ch = {
        "synopsis": "日子必须发生因果不能说章末。" + ("戊" * 500),
        "beats": [{"text": "清册官摊册。"}],
    }

    def slogan_llm(prompt, max_tokens=4096):
        return "1. 摊册\n2. 藏纸\n3. 观望"

    r = thicken_beats(ch, llm_fn=slogan_llm)
    assert r["ok"] is False
    assert "切句" in (r.get("message") or "")


def test_stage_ready_chain():
    empty = {}
    assert stage_ready(empty, "outline")["ok"] is True
    assert stage_ready(empty, "beats")["ok"] is False
    thick_syn = {"synopsis": _fat("因果大纲", 500)}
    assert stage_ready(thick_syn, "beats")["ok"] is True
    assert stage_ready(thick_syn, "deduce")["ok"] is False
    assert stage_ready(thick_syn, "draft")["ok"] is False


def test_draft_full_keeps_near_floor_and_forbids_reread():
    body = "排演全文" + ("己" * 4000)
    tip = draft_tip(body)
    assert "禁止复读" in tip
    assert "己" * 4000 in tip
    assert draft_tip("") == ""


def test_thicken_draft_writes_rehearsal_not_prose():
    ch = {
        "synopsis": _fat("大纲", 500),
        "beats": [{"text": _fat("拍", 700)} for _ in range(3)],
        "deductions": [{"prose": _fat("知", DEDUCTION_FLOOR)}],
    }
    saved = {}

    def fat_draft(prompt, max_tokens=16384):
        return "排演走场。" + ("庚" * DRAFT_FLOOR)

    r = thicken_draft(ch, llm_fn=fat_draft, persist_fn=lambda f: saved.update(f))
    assert r["ok"] is True
    assert r["source"] == "llm"
    assert "draft" in saved
    assert "prose" not in saved
    assert iceberg_ok_for({**ch, "draft": saved["draft"]}, "draft")


def test_stage_max_tokens_per_phase():
    assert stage_max_tokens("outline") == 2048
    assert stage_max_tokens("beats") == 4096
    assert stage_max_tokens("deduce") == 8192
    assert stage_max_tokens("draft") == 16384
    assert stage_max_tokens("final") == 16384
    assert stage_max_tokens("plan") == 2048
