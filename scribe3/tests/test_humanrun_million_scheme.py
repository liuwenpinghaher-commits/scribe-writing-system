"""百万字真人开书：方案条款、字数闸、执行器禁 pad/禁直写。不起 Surreal。"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_word_goal_accepted_million_not_killed():
    from scribe3.structure_budget import suggest_budget, word_goal_accepted

    assert word_goal_accepted(1_000_000) is True
    assert word_goal_accepted(45_000) is True
    assert word_goal_accepted(10_000) is False
    assert word_goal_accepted(None) is False
    b = suggest_budget(1_000_000)
    assert b["total_word_goal"] == 1_000_000
    assert b["volumes"] >= 4
    assert b["chapters"] >= 200
    assert b["advisory"] is True


def test_wcg_and_humanrun_use_word_goal_accepted():
    wcg = (ROOT / "scripts/v4_world_complete_gate.py").read_text(encoding="utf-8")
    assert "word_goal_accepted" in wcg
    assert "40000 <= twg <= 60000" not in wcg
    hr = (ROOT / "scripts/humanrun_wanjie.py").read_text(encoding="utf-8")
    assert "word_goal_accepted" in hr
    assert "40000 <= twg <= 60000" not in hr
    cl = (ROOT / "scripts/craft_loop_ssot.py").read_text(encoding="utf-8")
    assert "word_goal_accepted" in cl


def test_scheme_has_million_demo_no_pad_playbook():
    p = ROOT / "docs/plans/2026-08-23-humanrun-million.md"
    text = p.read_text(encoding="utf-8")
    assert "1000000" in text
    assert "pad" in text.lower() or "凑字" in text
    assert "s3_add" in text
    assert "tonglu.qing.blue" in text
    assert "3.2.5" in text
    assert "duty" in text and "design" in text and "deduce" in text
    assert "draft" in text and "final" in text
    v2 = (ROOT / "docs/真人作者全功能验收测试方案-v2.md").read_text(encoding="utf-8")
    assert "2026-08-23-humanrun-million.md" in v2
    assert "1000000" in v2


def test_executor_forbids_pad_and_direct_s3_http():
    src = (ROOT / "scripts/humanrun_wanjie.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "pad" not in names
    # 执行器只打 /api/works /orchestration /ai/runs /save-chapter 等，不 POST 工具名
    assert "/s3_add_" not in src
    assert "s3_add_character" not in src
    assert "--profile" in src
    assert "million" in src


def test_million_seed_real_not_padded():
    import scripts.humanrun_million_seed as m

    assert m.WORD_GOAL == 1_000_000
    assert m.BOOK_TITLE == "腕账"
    assert len(m.VOLUMES) == 4
    assert len(m.CHAPTERS) == 12
    heads = [c["synopsis"][:18] for c in m.CHAPTERS]
    assert len(set(heads)) == 12
    assert "pad(" not in inspect.getsource(m)
    assert "柳岸青" not in m.NORTH_STAR
    assert any("顾晚潮" in c["synopsis"] for c in m.CHAPTERS)
    assert m.cn_len(m.NORTH_STAR) >= 20
