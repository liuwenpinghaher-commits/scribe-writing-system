"""craft3 B/C: premises are events; prompt has no 21-grid; old sample fails prose_check."""
from __future__ import annotations

import json
from pathlib import Path

from scribe3.eval.card_schema import CARD_HEADINGS
from scribe3.eval.motif_split import BLACKLIST_TERMS
from scribe3.eval.premises import (
    FLOW_WORDS,
    draw_premises,
    load_premises,
    validate_premise,
)
from scribe3.eval.prose_check import check_prose_v3 as check_prose, extract_prose
from scribe3.eval.sample_scene import SHARED_CRAFT, build_prompt, build_prompt_v3

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "scribe3/eval"
OLD = ROOT / "docs/craft-samples/A1-当代职场.md"


def test_premises_at_least_12_events_not_flows():
    rows = load_premises()
    assert len(rows) >= 12
    genres = {r["genre"] for r in rows}
    assert len(genres) >= 4
    for r in rows:
        validate_premise(r)
        blob = json.dumps(r, ensure_ascii=False)
        for t in BLACKLIST_TERMS:
            assert t not in blob
        for w in FLOW_WORDS:
            assert w not in r["event"]


def test_draw_is_random_and_logged():
    a = draw_premises(n=3, seed=20260826)
    b = draw_premises(n=3, seed=20260826)
    c = draw_premises(n=3, seed=20260827)
    assert [x["id"] for x in a] == [x["id"] for x in b]
    assert [x["id"] for x in a] != [x["id"] for x in c]
    assert len({x["genre"] for x in a}) == 3


def test_v3_prompt_has_no_21_headings_and_at_most_5_rules():
    rows = load_premises()
    p = build_prompt_v3(rows[0], rules=SHARED_CRAFT[:5])
    for h in CARD_HEADINGS:
        assert f"## {h}" not in p
    assert p.count("\n- ") <= 5  # only the ≤5 craft rules
    assert "这一节" not in p
    assert rows[0]["event"] in p
    assert rows[0]["person"]["name"] in p


def test_old_v2_prompt_still_exists_for_contrast():
    p = build_prompt("当代职场", "夜班盘点差了三百块。")
    assert "作法" in p


def test_night_shift_fails_all_six_prose_checks():
    report = check_prose(OLD.read_text(encoding="utf-8"))
    assert extract_prose(OLD.read_text(encoding="utf-8"))
    reds = [r for r in report["checks"] if not r["ok"]]
    names = {r["name"] for r in reds}
    assert names == {
        "明喻密度",
        "对话冗余率",
        "答非所问",
        "开篇事件",
        "结尾总结句",
        "母题黑名单",
    }
    assert report["n_red"] == 6


def test_d_samples_pass_at_least_five():
    samples = [
        ROOT / "docs/craft-samples/D1-当代家庭.md",
        ROOT / "docs/craft-samples/D2-海运.md",
        ROOT / "docs/craft-samples/D3-幼儿园.md",
    ]
    for path in samples:
        r = check_prose(path.read_text(encoding="utf-8"))
        assert r["n_ok"] >= 5, (path.name, r)
        motif = next(c for c in r["checks"] if c["name"] == "母题黑名单")
        assert motif["ok"], path.name
