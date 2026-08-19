"""冰山注入：只留 clip_for 与演绎上下文。禁止 Surreal。"""
from __future__ import annotations

from scribe3.iceberg import clip_for


def test_clip_for_passthrough_near_floor():
    syn = "甲" * 520
    assert clip_for("synopsis", syn) == syn
    beat = "乙" * 520
    assert clip_for("beat", beat) == beat


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
