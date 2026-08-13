"""P1：material_recall 与 envelope reference 去重标题。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble_context import (
    _drop_material_cands_already_in_reference,
    _material_recall_block,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


class _Ent:
    id = "role:甲"
    name = "甲"
    traits = {}


class _St:
    def get_chapter(self, seq):
        return {"synopsis": "密室审讯囚犯"}

    def all_entities(self):
        return [_Ent()]

    def material_recall(self, query, chapter, k=5, mentioned_entities=None):
        return [
            {
                "material_id": "m:dup",
                "title": "密室白描",
                "summary": "冷硬的密室描写",
                "body": "寒气逼人",
                "ref_tags": ["手法"],
                "score": 1.0,
            },
            {
                "material_id": "m:keep",
                "title": "井绳手法",
                "summary": "只借收绳节奏",
                "body": "别搬专名",
                "ref_tags": ["手法"],
                "score": 0.9,
            },
        ]

    def add_material_reference(self, *a, **k):
        return None


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_drop_helper_removes_title_already_in_reference():
    cands = [
        {"title": "密室白描", "summary": "a"},
        {"title": "井绳手法", "summary": "b"},
    ]
    ref = "## 参考素材(借鉴非事实)\n- 素材:密室白描\n"
    kept, n = _drop_material_cands_already_in_reference(cands, ref)
    assert n == 1
    assert [c["title"] for c in kept] == ["井绳手法"]


def test_block_drops_title_already_in_reference():
    ref = "## 参考素材(借鉴非事实,不得当作故事内事实)\n- 素材:密室白描\n"
    text = _material_recall_block(
        _St(), 1, phase="draft", reference_text=ref,
    )
    assert "井绳手法" in text
    assert "密室白描" not in text
    assert "参考记忆" in text


def test_block_keeps_title_when_reference_empty():
    text = _material_recall_block(_St(), 1, phase="draft", reference_text="")
    assert "密室白描" in text
    assert "井绳手法" in text


def test_v1_passes_envelope_text_into_material_recall():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "reference_text=env_text or \"\"" in src
    assert "_material_recall_block(" in src
