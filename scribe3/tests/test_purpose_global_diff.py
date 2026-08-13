"""P1：purpose 相对 global 北极星差集。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble_context import (
    _purpose_and_lessons_write_block,
    _purpose_diff_against_global,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


GLOBAL = "## 全局(北极星·当前弧光·开放伏笔·主要角色)\n北极星:读者感受=发冷;情感弧=下行;"


class _St:
    def __init__(self, deltas=None):
        self.deltas = deltas or []

    def get_chapter(self, seq):
        return {"deltas": self.deltas, "synopsis": "侧门油灯", "beats": []}

    def list_lessons(self, chapter=None):
        return []

    def recall_lessons(self, qtxt, k=3):
        return []


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_diff_keeps_chapter_purpose_drops_register_lecture():
    lecture = (
        "\n\n【目的合同工序】本章尚未登记目的合同:与作者聊定本章目的后,可列 "
        "delta 草单(≤7 条)。请作者在章面板登记(本对话未挂联查工具)。空合同也可正常写作。"
    )
    out = _purpose_diff_against_global(lecture, GLOBAL)
    assert "北极星已在全局段" in out
    assert "s3_register_purpose" not in out
    assert "目的合同工序" not in out


def test_diff_keeps_delta_list():
    body = (
        "【本章目的合同·必达清单】写完后逐条验收「做没做」,验的是状态变化不是好坏:\n"
        "- [fact] 侧门钥未还"
    )
    assert "侧门钥未还" in _purpose_diff_against_global(body, GLOBAL)


def test_helper_shortens_empty_when_global_has_star():
    text = _purpose_and_lessons_write_block(
        _St([]), 1, with_tools=False, global_text=GLOBAL,
    )
    assert "北极星已在全局段" in text
    assert "s3_register_purpose" not in text


def test_helper_keeps_lecture_when_no_global():
    text = _purpose_and_lessons_write_block(
        _St([]), 1, with_tools=False, global_text="",
    )
    assert "尚未登记目的合同" in text


def test_v1_passes_env_text():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "global_text=env_text or \"\"" in src
