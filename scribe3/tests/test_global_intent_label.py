"""P1：global 用「作品意图」；strip 红线留明示行。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scribe3.api.services.write_assemble_context import (
    global_iron_stripped_from_envelope,
)
from scribe3.context_budget import NOVEL_PROMPT_HARD


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000


def test_stripped_flag_from_envelope():
    env = SimpleNamespace(blocks=[
        SimpleNamespace(
            name="global",
            text="## 全局(作品意图·当前弧光·开放伏笔·主要角色)\n"
                 "- 作品意图:读者感受=发冷;情感弧=下行;红线=红线已按实验剥离\n",
        ),
    ])
    assert global_iron_stripped_from_envelope(env) is True
    assert global_iron_stripped_from_envelope(
        SimpleNamespace(blocks=[
            SimpleNamespace(name="global", text="- 作品意图:读者感受=发冷;红线=勿泄密"),
        ])
    ) is False


def test_assembler_uses_product_label():
    src = (
        Path(__file__).resolve().parents[1] / "context_assembler.py"
    ).read_text(encoding="utf-8")
    assert '## 全局(作品意图·当前弧光·开放伏笔·主要角色)' in src
    assert '作品意图:读者感受=' in src
    assert '红线已按实验剥离' in src
    # 产品文案不再用信封标题「北极星」
    assert '## 全局(北极星' not in src


def test_v1_reports_strip_flag():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "global_iron_stripped_from_envelope" in src
    assert 'bud_rep["global_iron_stripped"]' in src
