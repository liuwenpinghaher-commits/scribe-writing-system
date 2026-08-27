"""A: sample_scene uses shared craft only, never playbook or either book's names."""
from __future__ import annotations

import ast
from pathlib import Path

from scribe3.eval.sample_scene import (
    BANNED_TOKENS,
    SHARED_CRAFT,
    build_prompt,
    parse_sample,
    write_sample,
)

EVAL = Path(__file__).resolve().parents[1] / "eval"
ROOT = Path(__file__).resolve().parents[2]


def test_sample_scene_does_not_import_playbook():
    src = (EVAL / "sample_scene.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "playbook" not in alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "playbook" not in node.module


def test_prompt_carries_shared_craft_not_either_book():
    prompt = build_prompt("当代职场", "夜班盘点差了三百块，店长说账不平谁也别走。")
    for line in SHARED_CRAFT:
        assert line in prompt
    for token in BANNED_TOKENS:
        assert token not in prompt
    assert "古代武侠" in prompt or "江湖" in prompt
    assert "维多利亚" in prompt or "神秘学" in prompt


def test_parse_sample_splits_prose_and_self_eval():
    raw = """# 夜班
## 正文
店里灯还亮着。她把第三遍小票按在柜台上。

## 自评
- 眼睛：跟进盘点的人。见「她把第三遍小票按在柜台上」。
"""
    doc = parse_sample(raw)
    assert "第三遍小票" in doc["prose"]
    assert "眼睛" in doc["self_eval"]


def test_write_sample_is_not_a_gate(tmp_path):
    dest = tmp_path / "A1-当代职场.md"
    write_sample(
        dest,
        genre="当代职场",
        situation="夜班盘点差了三百块。",
        prose="她把第三遍小票按在柜台上。",
        self_eval="- 眼睛：跟进盘点的人。",
        calls=1,
        tokens=1200,
        provider="coding",
    )
    text = dest.read_text(encoding="utf-8")
    assert "不作任何闸的证据" in text
    assert "不进 Surreal" in text
    assert "当代职场" in text
