"""P1：outline 半裁保拍砍纲。禁止本机 Surreal。"""
from __future__ import annotations

from scribe3.context_budget import (
    NOVEL_PROMPT_HARD,
    _half_cut_segment,
    apply_l2_trim,
    enforce_total_prompt_budget,
)


def _outline_text(*, syn_n=800, beat_n=800) -> str:
    return (
        "## 本章大纲/节拍(据此展开正文,勿另起炉灶)\n"
        f"〔大纲〕{'甲' * syn_n}\n"
        f"〔节拍〕1.抵达义庄验尸。{'乙' * beat_n}\n"
        "写作要求:严格按各情节点字数预算分配笔墨,预算内欠账的密点优先补足,不得均匀注水。"
    )


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_half_cut_keeps_beats_drops_synopsis():
    raw = _outline_text()
    cut = _half_cut_segment("outline", raw)
    assert len(cut) <= len(raw) // 2 + 8
    assert "〔节拍〕" in cut
    assert "抵达义庄" in cut
    assert "写作要求" in cut
    assert cut.count("甲") < 800
    assert "大纲已裁" in cut or "〔大纲〕" not in cut or cut.count("甲") < 200


def test_half_cut_other_name_still_tail():
    s = "x" * 100
    cut = _half_cut_segment("codex", s)
    assert cut == ("x" * 50) + "…"


def test_l2_trim_keeps_beats_when_outline_is_victim():
    raw = _outline_text()
    segs = [
        {"name": "prefix", "layer": "redline", "text": "P"},
        {"name": "outline", "layer": "supplemental", "text": raw},
    ]
    joined, rep = apply_l2_trim(
        segs, supplemental_hard=400, prompt_hard=800, l0_est=1, l1_est=1,
    )
    dropped = " ".join(rep.get("dropped") or [])
    assert "outline" in dropped
    assert "抵达义庄" in joined
    assert "〔节拍〕" in joined
    assert joined.count("甲") < 800


def test_total_budget_keep_beats():
    raw = _outline_text()
    segs = [{"name": "outline", "layer": "supplemental", "text": raw}]
    out, rep = enforce_total_prompt_budget(segs, budget=400)
    assert "抵达义庄" in (out[0].get("text") if out else "")
    assert any("outline" in str(x) for x in (rep.get("dropped") or []))
