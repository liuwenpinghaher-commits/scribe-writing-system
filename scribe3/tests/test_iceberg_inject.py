"""冰山注入：刚过闸必须全文进提示词。禁止 Surreal。"""
from __future__ import annotations

from scribe3.iceberg import clip_for, cn_len
from scribe3.stage_generate import build_stage_prompt, draft_full_block
from scribe3.api.services.write_assemble_context import _outline_block


def test_clip_for_passthrough_near_floor():
    syn = "甲" * 520
    assert clip_for("synopsis", syn) == syn
    beat = "乙" * 520
    assert clip_for("beat", beat) == beat


def test_ctx_bits_beats_not_truncated_to_200():
    ch = {
        "synopsis": "日子必须发生。" + ("丙" * 500),
        "beats": [{"text": "进场事件。" + ("丁" * 510)} for _ in range(3)],
    }
    prompt = build_stage_prompt("deduce", ch, seq=6)
    assert prompt.count("丁") >= 3 * 510
    assert "200" not in prompt or prompt.count("丁") > 600


def test_outline_block_newline_and_full_beats():
    class St:
        def get_chapter(self, _n):
            return {
                "synopsis": "戊" * 520,
                "beats": [{"text": "己" * 520}, {"text": "庚" * 520}, {"text": "辛" * 520}],
            }

    blk = _outline_block(St(), 1, mode="write")
    assert "\n1." in blk or "\n1." in blk.replace("〔节拍〕", "〔节拍〕\n")
    assert blk.count("己") == 520
    assert blk.count("庚") == 520
    assert "密≥250" not in blk
    assert " " + "己" * 20 + " " + "庚" not in blk  # 不是空格粘三拍


def test_draft_full_includes_10000():
    draft = "排演。" + ("壬" * 10000)
    blk = draft_full_block(draft)
    assert cn_len(blk) >= 10000
    assert "禁止复读" in blk


def test_deduction_full_on_draft_and_final_shape():
    from scribe3.api.services.write_assemble_context import _deduction_context_segments

    class St:
        def get_chapter(self, _n):
            return {
                "scene_truth": "炉前摊册。",
                "deductions": [
                    {"character_id": "role:沈拾灯", "prose": "### 没察觉的\n他不知侧门。" + ("癸" * 2600)},
                    {"character_id": "role:阿绣", "prose": "### 没察觉的\n她不知灯册。" + ("子" * 2600)},
                ],
            }

    segs = _deduction_context_segments(St(), 6, focalizer="role:沈拾灯")
    text = "".join(t for _, _, t in segs)
    assert text.count("癸") >= 2600
    assert text.count("子") >= 2600
    assert "他不知侧门" in text
    assert "她不知灯册" in text
