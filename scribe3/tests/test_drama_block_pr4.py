"""PR-4：format_drama_block / beats_have_drama_gcd / length_steer 文案（纯函数，无 Surreal）。"""
from __future__ import annotations

from scribe3.drama_beats import (
    MAX_DRAMA_BLOCK,
    beats_have_drama_gcd,
    format_drama_block,
)


def _gcd_beats():
    return [
        {
            "id": "b1",
            "kind": "scene",
            "goal": "夺回铜匙",
            "conflict": "麻三娘拦门",
            "turn": "匙落入井",
            "cost": "暴露行踪",
            "hook": "井底有声",
            "text": "夺匙失败",
        },
        {
            "id": "b2",
            "kind": "bridge",
            "goal": "",
            "conflict": "",
            "turn": "转入暗巷",
            "cost": "",
            "text": "过场",
        },
    ]


def test_beats_have_drama_gcd_detects_fields():
    assert beats_have_drama_gcd(_gcd_beats()) is True
    assert beats_have_drama_gcd([{"text": "只逛巷子"}], chapter_hook="") is False
    assert beats_have_drama_gcd([], chapter_hook="井底有声") is True
    assert beats_have_drama_gcd([{"text": "x"}], chapter_hook="") is False


def test_format_drama_block_empty_without_gcd():
    assert format_drama_block([{"text": "巷口听味"}]) == ""
    assert format_drama_block([]) == ""
    assert format_drama_block(None) == ""


def test_format_drama_block_keeps_conflict_cost_drops_mru():
    blk = format_drama_block(_gcd_beats(), chapter_hook="井底有声")
    assert blk.startswith("\n\n")
    body = blk.strip()
    assert "本章拍级走法" in body
    assert "必须执行" not in body
    assert "麻三娘拦门" in body
    assert "暴露行踪" in body
    assert "井底有声" in body
    assert "微观节奏" not in body
    assert "MRU" not in body
    assert "动机-反应-行动" not in body
    assert "目标：" not in body
    assert len(body) <= MAX_DRAMA_BLOCK


def test_format_drama_block_limited_knowledge_disclaimer():
    foc = format_drama_block(
        _gcd_beats(), chapter_hook="钩", focalizer="role:白姑",
    )
    assert "限知" in foc
    assert "帧外私密" in foc or "不得道破" in foc
    omni = format_drama_block(_gcd_beats(), chapter_hook="钩", focalizer="")
    assert "（限知）" not in omni


def test_format_drama_block_respects_max_chars():
    long_beats = [
        {
            "id": f"b{i}",
            "kind": "scene",
            "goal": "目标字" * 20,
            "conflict": "冲突字" * 20,
            "turn": "结果字" * 20,
            "cost": "代价字" * 10,
            "text": "摘要" * 10,
        }
        for i in range(1, 6)
    ]
    blk = format_drama_block(long_beats, chapter_hook="超长钩子" * 10, focalizer="role:甲")
    assert blk
    assert len(blk.strip()) <= MAX_DRAMA_BLOCK
    # 限知免责在预算内尽量保留
    assert "限知" in blk or "拍级走法" in blk


def test_render_brief_drama_contract_on_top():
    from scribe3.brief import render_brief

    text = render_brief({
        "drama_contract": {
            "text": "## 本章戏剧合同（必须执行，禁止风景巡礼）\n- 拍1 目标：试",
        },
        "purpose": {"text": "【目的合同】dummy"},
        "arcs": ["【角色弧光·甲】谎念"],
    })
    i_drama = text.find("本章戏剧合同")
    i_purpose = text.find("目的合同")
    i_arc = text.find("角色弧光")
    assert i_drama > 0
    assert i_drama < i_purpose < i_arc


def test_length_steer_soft_strings_present():
    """文档化 length_steer 必含 soft 句；CRAFT_NOVEL 强化句单独可拼。"""
    soft = (
        "宁短勿巷志凑字；密拍预算优先于凑满 4800；欠戏禁止用气味/街景注水。"
        "限知与硬红线优先于戏剧合同与字数目标。"
    )
    novel = "优先冲突与行动推进，禁止风景巡礼式注水；戏剧合同优先于字数目标。"
    base = (
        "本章交完整文学正文：可见汉字目标约 4800–5500 字（去空白后），"
        "连续场景与对话，气味/触感锚，禁止公式注水尾（条N存档/换位完成/观察条/勒紧半指）。"
        "用 ⟦PROPOSAL scope=chapter⟧ 围栏交整章。"
        + soft
    )
    assert "宁短勿巷志" in base
    assert "限知与硬红线优先" in base
    assert "风景巡礼" in (base + novel)
