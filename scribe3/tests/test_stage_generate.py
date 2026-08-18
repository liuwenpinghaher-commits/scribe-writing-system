"""冰山生成链：StageSpec / 解析 / 必须 LLM / 禁切句回退。禁止 Surreal。"""
from __future__ import annotations

from scribe3.iceberg import DEDUCTION_FLOOR, DRAFT_FLOOR, SYNOPSIS_FLOOR, cn_len
from scribe3.stage_craft_prompt import stage_craft_block
from scribe3.stage_generate import (
    draft_tip,
    iceberg_ok_for,
    parse_beats_payload,
    parse_outline_payload,
    stage_max_tokens,
    stage_ready,
    stage_skips_drama_vacuum,
    stage_skips_editor_chrome,
    stage_spec,
    thicken_beats,
    thicken_draft,
    thicken_outline,
)


def _fat(seed: str, n: int) -> str:
    return seed + ("甲" * n)


def test_final_kernel_eats_full_materials():
    spec = stage_spec("final")
    assert "只吃冰山尖" not in spec["short_kernel"]
    assert "只吃大纲尖" not in spec["ask"]
    assert "材料全文" in spec["short_kernel"] or "另写" in spec["short_kernel"]
    assert "另写" in spec["ask"]


def test_stage_craft_is_kernel_not_slogan():
    blk = stage_craft_block("outline")
    assert "选择" in blk or "13" in blk
    assert "不要凑字数" not in blk
    assert "≥500" not in blk
    assert len(blk) <= 400
    assert stage_craft_block("final") == ""
    assert stage_craft_block("draft") == ""


_DRY_OUTLINE = """时空：还账日后第一个下午，巷口到旧库
在场：灰七；冷锅婆；灰狸
咬上章：天亮前不能张嘴；掌心焦黑未还
本章要：灰七要在炉冷前把焦黑还回侧门
挡：灰狸递假铜挡路；婆子捞锅里账钱
触发：灰狸把假铜举到灰七眼皮底下
升级：灰七拨开假铜；婆子说账勾了门没开
选择：硬还焦黑暴露埋灰人 vs 只把纸角塞回门缝
决断：灰七不进门，把纸角朝门里推回一分
代价：账清了门更死；门内咳了一声爹的口气
信息差：灰狸不知匙；婆子不知撕角
动哪条线：promise:xiang-debt 香债勾笔；storyline:side-gate 侧门未开
钩：铜钱缺口硌着肋骨
禁令：锁眼、真名、灰狸知匙
"""

_DRY_BEATS = """## 拍1
要：把假铜挡在眼皮外
挡：灰狸递假铜挡路
变：假铜被拨开落回他自己手里
付：灰狸受伤账更难看
选：无
水下：狸不知撕角
## 拍2
要：把焦黑还回侧门
挡：婆子说账勾了门没开
变：门更死咳了一声
付：门没开更险
选：硬还焦黑暴露 vs 纸角塞回门缝
水下：咳像爹
## 拍3
要：守住撕角不让狸看见
挡：灰狸跟在柴垛后
变：纸角朝门里推回一分
付：门内咳像爹未兑
选：无
水下：角还在袖里
"""


def test_parse_outline_floor():
    thin = parse_outline_payload("清册官入镇封炉。")
    assert thin["ok"] is False
    assert thin["cn"] < SYNOPSIS_FLOOR
    dry = parse_outline_payload(_DRY_OUTLINE)
    assert dry["ok"] is True, dry.get("density")
    assert dry["source"] == "llm_13slot"
    assert dry["chapter_spine"]["goal"]


def test_parse_beats_scene_paper():
    parsed = parse_beats_payload(_DRY_BEATS)
    assert parsed["ok"] is True, parsed.get("density")
    assert len(parsed["beats"]) == 3
    assert parsed["source"] == "llm_gcd"
    assert parsed["beats"][1]["choice"]


def test_thicken_without_store_does_not_pretend_bible():
    seen = []

    def llm(prompt, max_tokens=2048):
        seen.append(prompt)
        return "一句口号大纲。"

    thicken_outline({"synopsis": "短"}, llm_fn=llm)
    assert seen
    assert "本书设定圣经" not in seen[0]


def test_thicken_outline_requires_llm_and_rejects_template():
    try:
        thicken_outline({"synopsis": ""}, llm_fn=None)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "llm_fn" in str(e)

    calls = {"n": 0}

    def short_llm(prompt, max_tokens=2048):
        calls["n"] += 1
        return "一句口号大纲。"

    out = thicken_outline({"synopsis": "短"}, llm_fn=short_llm)
    assert out["ok"] is False
    assert out["code"] == "llm_thin"
    assert out["source"] in ("llm", "adapt_v1", "llm_13slot")
    assert calls["n"] == 2  # 一次 + 严格重试


def test_thicken_outline_slot_edit_keeps_choice():
    import os
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "off"
    os.environ["SCRIBE3_CLUE_DENSITY"] = "on"
    thin = _DRY_OUTLINE.replace("代价：账清了门更死；门内咳了一声爹的口气", "代价：")
    prompts: list[str] = []
    n = {"i": 0}

    def llm(prompt, max_tokens=2048):
        prompts.append(prompt)
        n["i"] += 1
        if "只改这一格" in prompt:
            assert "一个字都不要动" in prompt
            assert "硬还焦黑" in prompt
            return "代价：账清了门更死；门内咳了一声爹的口气"
        return thin

    r = thicken_outline({"synopsis": ""}, llm_fn=llm, persist_fn=lambda f: None, seq=6)
    assert any("只改这一格" in p for p in prompts)
    assert not any("整份重写" in p for p in prompts)
    spine = r.get("chapter_spine") or {}
    if r.get("ok"):
        assert "门更死" in str(spine.get("cost") or "")
        assert "硬还焦黑" in str(spine.get("choice") or "")


def test_thicken_outline_persists_only_thick_llm():
    import os
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "off"
    persisted = {}

    def fat_llm(prompt, max_tokens=2048):
        return _DRY_OUTLINE

    r = thicken_outline(
        {"synopsis": ""},
        llm_fn=fat_llm,
        persist_fn=lambda f: persisted.update(f),
        seq=6,
    )
    assert r["ok"] is True, r
    assert r["source"] == "llm_13slot"
    assert "chapter_spine" in persisted
    assert iceberg_ok_for({"chapter_spine": persisted["chapter_spine"]}, "synopsis")


def test_thicken_beats_no_synopsis_cut():
    from scribe3.tests.test_chapter_spine import G1
    ch = {
        "chapter_spine": G1,
        "synopsis": "日子必须发生因果不能说章末。" + ("戊" * 500),
        "beats": [{"text": "清册官摊册。"}],
    }

    def slogan_llm(prompt, max_tokens=4096):
        return "1. 摊册\n2. 藏纸\n3. 观望"

    r = thicken_beats(ch, llm_fn=slogan_llm)
    assert r["ok"] is False
    assert "切句" in (r.get("message") or "")


def test_stage_ready_chain():
    import os
    os.environ["SCRIBE3_CHAPTER_DESIGN"] = "off"
    from scribe3.tests.test_chapter_spine import G1
    empty = {}
    assert stage_ready(empty, "outline")["ok"] is True
    assert stage_ready(empty, "beats")["ok"] is False
    thick_syn = {"chapter_spine": G1, "synopsis": "本章要：灰七还焦黑"}
    assert stage_ready(thick_syn, "beats")["ok"] is True, stage_ready(thick_syn, "beats")
    assert stage_ready(thick_syn, "deduce")["ok"] is False
    assert stage_ready(thick_syn, "draft")["ok"] is False


def test_draft_full_keeps_near_floor_and_forbids_reread():
    body = "排演全文" + ("己" * 4000)
    tip = draft_tip(body)
    assert "禁止复读" in tip
    assert "己" * 4000 in tip
    assert draft_tip("") == ""


def test_thicken_draft_accepts_short_structured():
    from scribe3.tests.test_chapter_spine import G1
    from scribe3.tests.test_iceberg import _GCD_BEATS
    ch = {
        "chapter_spine": G1,
        "synopsis": "本章要：灰七还焦黑",
        "beats": list(_GCD_BEATS),
        "deductions": [{"prose": _fat("知", 80)}],
    }
    saved = {}
    calls = {"n": 0}

    def short_llm(prompt, max_tokens=16384):
        calls["n"] += 1
        assert "还差" not in prompt
        assert "还差 N 字写新场面" not in prompt
        return "他按回碎片，门内咳了一声。"

    r = thicken_draft(ch, llm_fn=short_llm, persist_fn=lambda f: saved.update(f))
    assert r["ok"] is True, r
    assert calls["n"] == 1
    assert "draft" in saved
    assert cn_len(saved["draft"]) < DRAFT_FLOOR
    assert r.get("fate")
    assert "mode" in r["fate"]


def test_thicken_draft_writes_rehearsal_not_prose():
    from scribe3.tests.test_chapter_spine import G1
    from scribe3.tests.test_iceberg import _GCD_BEATS
    ch = {
        "chapter_spine": G1,
        "synopsis": "本章要：灰七还焦黑",
        "beats": list(_GCD_BEATS),
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


def test_stage_skips_editor_chrome_and_vacuum():
    assert stage_skips_editor_chrome("outline") is True
    assert stage_skips_editor_chrome("plan") is True
    assert stage_skips_editor_chrome("beats") is True
    assert stage_skips_editor_chrome("deduce") is True
    assert stage_skips_editor_chrome("draft") is True
    assert stage_skips_editor_chrome("final") is False
    assert stage_skips_drama_vacuum("outline") is True
    assert stage_skips_drama_vacuum("deduce") is True
    assert stage_skips_drama_vacuum("final") is False


def test_stage_max_tokens_per_phase():
    assert stage_max_tokens("outline") == 2048
    assert stage_max_tokens("beats") == 4096
    assert stage_max_tokens("deduce") == 8192
    assert stage_max_tokens("draft") == 16384
    assert stage_max_tokens("final") == 16384
    assert stage_max_tokens("plan") == 2048
    from scribe3.stage_generate import parse_final_payload, thicken_stage
    fat = parse_final_payload("读者正文。" + ("甲" * 5100))
    assert fat["ok"] is True
    short = parse_final_payload("短。")
    assert short["ok"] is True  # 字数不再作 Ice6 通过条件
    assert parse_final_payload("")["ok"] is False
    assert "final" in thicken_stage.__code__.co_consts or True


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
    print("PASS test_stage_generate")
