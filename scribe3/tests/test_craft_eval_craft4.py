"""craft4: voice cards, interval gates, prompt/check isolation.

v5 additions: the gate is demoted to a read-only monitor, and author verdicts
are recorded as preference pairs instead of encoded as thresholds.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scribe3.eval.premises import load_premises, validate_premise
from scribe3.eval.prose_check import CHECK_KEYWORDS, check_corpus, check_file, check_prose
from scribe3.eval.sample_scene import SHARED_CRAFT, build_prompt_v4

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "docs/craft-samples"
DEMO = ROOT / "docs/worlds/两本对照/对白示范.md"
LEN_BANDS = {"惜字", "中等", "啰嗦"}


def test_every_premise_has_three_voice_cards_and_info_gap():
    rows = load_premises()
    assert len(rows) >= 12
    for r in rows:
        validate_premise(r)
        cast = r["cast"]
        assert len(cast) >= 3, r["id"]
        habits = [c["speech_habit"] for c in cast]
        assert len(set(habits)) == len(habits), r["id"]
        tics = [c["tic"] for c in cast]
        assert len(set(tics)) == len(tics), r["id"]
        for c in cast:
            assert len(c["jargon"]) >= 5, (r["id"], c["name"])
            assert "speech_len" not in c, (r["id"], c["name"])
            assert c["catchphrase"]
            assert c["never_says"]
        assert len(r.get("props") or []) >= 2, r["id"]
        gap = r["info_gap"]
        assert gap.get("knows") and gap.get("does_not_know") and gap.get("hides")


def test_dialogue_demo_has_six_excerpts():
    md = DEMO.read_text(encoding="utf-8")
    assert md.count("## ") >= 6
    assert "乱世铜炉" in md
    assert "诡秘之主" in md
    assert "点评" not in md and "评：" not in md


def test_d1d2d3_fail_v4_variance_gates():
    paths = [
        SAMPLES / "D1-当代家庭.md",
        SAMPLES / "D2-海运.md",
        SAMPLES / "D3-幼儿园.md",
    ]
    texts = [p.read_text(encoding="utf-8") for p in paths]
    report = check_corpus(texts)
    names = {c["name"]: c for c in report["checks"]}
    for key in ("对白句长标准差", "最长一句对白", "明喻密度", "跨篇重复对白"):
        assert key in names, key
        assert names[key]["ok"] is False, (key, names[key])


def test_retired_gates_are_gone():
    """两条指标与作者判断反向，已退役，不许回流。

    「内心活动占比」数的是「心里/心中/想」等标记词，逼出了「她心中一沉」；
    「26字以上占比」奖励信息倾泻式长台词，人写稿仅 4% 却毫不电报体。
    """
    report = check_prose((SAMPLES / "V4-3b-乡土-人写.md").read_text(encoding="utf-8"))
    names = {c["name"] for c in report["checks"]}
    assert "内心活动占比" not in names
    assert "26字以上对白占比" not in names


def test_gate_agrees_with_author_verdict():
    """尺子方向钉：作者判废的机器稿必须比人写稿红得多。

    改造前是反的——机器稿 9/10、人写稿 7/10。
    """
    human = SAMPLES / "V4-3b-乡土-人写.md"
    machine = SAMPLES / "V4-3-乡土.md"
    h = check_file(human)
    m = check_file(machine)
    assert h["n_red"] == 0, [c for c in h["checks"] if not c["ok"]]
    assert m["n_red"] >= 4, m["n_red"]
    for key in ("明喻密度", "无信息回合", "不接话茬", "卡片原句"):
        got = next(c for c in m["checks"] if c["name"] == key)
        assert got["ok"] is False, (key, got)


def test_prompt_does_not_contain_check_keywords():
    rows = load_premises()
    p = build_prompt_v4(rows[0], demo_md=DEMO.read_text(encoding="utf-8"))
    blob = p + "\n" + "\n".join(SHARED_CRAFT)
    # SHARED_CRAFT is not in v4 prompt; only the prompt itself is gated.
    for kw in CHECK_KEYWORDS:
        assert kw not in p, kw
    assert "## 自评" not in p
    assert "你听我说" not in p
    assert rows[0]["event"] in p
    assert rows[0]["cast"][0]["name"] in p
    assert rows[0]["cast"][0]["jargon"][0] in p
    assert "信息不对称" in p or rows[0]["info_gap"]["knows"] in p


# ---- v5：闸降级为监控 + 偏好数据 ----

def test_monitor_report_has_no_pass_fail():
    """报告里只要有及格线，人就会去追全绿，监控迟早又变回门禁。"""
    from scribe3.eval.prose_check import format_report

    md = format_report(check_file(SAMPLES / "V4-3b-乡土-人写.md"))
    for banned in ("· 过 ·", "· 红 ·", "合计", "线≥", "区间"):
        assert banned not in md, banned
    assert "乱世铜炉" in md and "诡秘之主" in md
    assert "作者判断是唯一裁决" in md


def test_reference_distribution_covers_every_reported_metric():
    from scribe3.eval.prose_check import REF, _METRIC_LABELS

    m = check_file(SAMPLES / "V4-3b-乡土-人写.md")["metrics"]
    for key, _label, _fmt in _METRIC_LABELS:
        assert key in m, key
        for book in REF:
            assert key in REF[book], (book, key)


def test_prefs_reject_vague_notes_and_self_pairs(tmp_path):
    from scribe3.eval.prefs import Pref, append_pref, load_prefs

    f = tmp_path / "prefs.jsonl"
    good = Pref(
        id="pref-0001",
        round="v5",
        premise_id="p01",
        genre="乡土",
        chosen="a.md",
        rejected="b.md",
        notes=["老金是公务员标本，不是活人"],
    )
    append_pref(good, f, check_files=False)
    assert len(load_prefs(f)) == 1

    with pytest.raises(ValueError):
        append_pref(good, f, check_files=False)  # duplicate id
    for bad in (
        {"notes": ["一般"]},
        {"notes": []},
        {"chosen": "b.md"},
    ):
        row = {**good.__dict__, "id": "pref-0002", **bad}
        with pytest.raises(ValueError):
            append_pref(row, f, check_files=False)


def test_dialogue_demo_grew_to_cover_confrontation_and_group_scenes():
    md = DEMO.read_text(encoding="utf-8")
    assert md.count("## ") >= 9
    assert "决裂" in md and "黑蛇" in md
    assert "点评" not in md and "评：" not in md


def test_monitor_numbers_never_leak_into_prompt():
    """监控可以写进交付文件给人看，但不许回流到生成侧。"""
    import inspect

    from scribe3.eval import prose_check as pc
    from scribe3.eval.sample_scene import build_prompt_v4

    rows = load_premises()
    p = build_prompt_v4(rows[0], demo_md=DEMO.read_text(encoding="utf-8"))
    for word in ("分布对照", "监控", "/千字", "标准差", "参照", "占比"):
        assert word not in p, word
    for book in pc.REF:
        for v in pc.REF[book].values():
            assert f"{v}" not in p, (book, v)
    # 提示只由处境与示范决定，拿不到任何检查结果
    sig = inspect.signature(build_prompt_v4)
    assert set(sig.parameters) == {"premise", "demo_md"}
