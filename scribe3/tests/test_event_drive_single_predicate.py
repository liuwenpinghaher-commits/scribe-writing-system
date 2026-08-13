"""P1：event_drive / hook 单点判定 + empty_event_drive。禁止本机 Surreal。"""
from __future__ import annotations

from pathlib import Path

from scribe3.api.services.write_assemble import get_write_soft_fail_counters
from scribe3.api.services.write_assemble_context import _event_drive_block
from scribe3.context_budget import L0_NEVER_CUT, NOVEL_PROMPT_HARD


CONTRACT = {
    "desire": "灰七要去侧门查昨夜脚印与匙齿",
    "obstacle": "冷锅婆香债拦门加上灰狸缠斗",
    "turn": "热灰抵半债并把假片扔给灰狸",
    "cost": "暂禁侧门且父名挂上夜审阴影",
}

DRIVE = {
    "inciting_force": {"summary": "债上门"},
    "opposition": {"wants": "讨债"},
    "scene_turn": "拦门",
    "end_hook": "门外还有脚步",
}


class _St:
    def __init__(self, ch):
        self.ch = ch

    def get_chapter(self, _n):
        return self.ch


def test_hard_budget():
    assert NOVEL_PROMPT_HARD == 48000
    assert "event_drive" in L0_NEVER_CUT
    assert "event_drive_hook" not in L0_NEVER_CUT


def test_helper_does_not_reread_chapter_contract(monkeypatch):
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled", lambda: True,
    )
    # 章上有合同，但调用方没传 → 不得擅自走 hook
    st = _St({"narrative_contract": CONTRACT, "narrative_drive": DRIVE})
    full = _event_drive_block(st, 5)
    assert "优先执行" in (full or "")
    hook = _event_drive_block(st, 5, contract=CONTRACT, has_scene=True)
    assert "优先执行" not in (hook or "")
    assert "章末还悬着" in (hook or "")


def test_same_predicate_and_empty_counter_in_v1_source():
    src = (
        Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    ).read_text(encoding="utf-8")
    assert "has_scene=_ed_is_hook" in src
    assert '_record_write_soft_fail("empty_event_drive")' in src
    assert src.count("_ed_is_hook = contract_has_scene_fields(_ed_contract)") == 1
    assert "elif not _ed_is_hook:" in src


def test_flag_off_returns_empty(monkeypatch):
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled", lambda: False,
    )
    assert _event_drive_block(_St({"narrative_drive": DRIVE}), 5) == ""
