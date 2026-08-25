"""成色：拆古白话、尺子进生成/审判、过滤闸。不启 Surreal。"""
from __future__ import annotations

import os

from scribe3.api.services.write_assemble_blocks import _write_protocol_block
from scribe3.playbook.chengse import check_chengse_filter
from scribe3.playbook.prompts import (
    draft_generate,
    duty_generate,
    duty_judge,
    final_generate,
    final_judge,
    play_generate,
    play_judge,
)
from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.structural import check_draft_struct, check_final_last_mile


def _on() -> None:
    os.environ["SCRIBE3_CHENGSE_CRAFT"] = "1"


def _off() -> None:
    os.environ["SCRIBE3_CHENGSE_CRAFT"] = "0"


def test_version_and_prompts_carry_craft():
    _on()
    assert PLAYBOOK_VERSION == "playbook.3.2.6"
    d = duty_generate({"seq": 1})
    assert "【成色·验戏不验词表】" in d
    assert "先立还在过的日子" in d
    p = play_generate({"seq": 1, "duty": {}})
    assert "假破真" in p
    dr = draft_generate({})
    assert "切在能听见看见" in dr
    f = final_generate({})
    assert "端的" in f and "岂料" in f
    j = duty_judge({})
    assert "C1." in j and "C7." in j
    assert "八问" in j
    assert "十二问" in play_judge({})
    assert "验戏，不验词表" in final_judge({})


def test_write_protocol_drops_classical_when_on():
    _on()
    proto = _write_protocol_block()
    assert "⟦PROPOSAL" in proto
    assert "讨论" in proto and "动稿" in proto
    assert "多用'端的、岂料" not in proto
    assert "成色（验戏，不验词表）" in proto
    assert "先立还在过的日子" in proto


def test_write_protocol_legacy_when_off():
    _off()
    try:
        proto = _write_protocol_block()
        assert "多用'端的、岂料" in proto
        assert "成色（验戏，不验词表）" not in proto
    finally:
        _on()


def test_filter_blocks_narration_classical():
    _on()
    hit = check_chengse_filter("端的是人如流水。井台上还有人排队。")
    assert hit["ok"] is False
    assert hit["code"] == "chengse_classical"


def test_filter_allows_dialogue_classical():
    _on()
    hit = check_chengse_filter("「端的是冷。」杏花说。井台上还有人排队。")
    assert hit["ok"] is True


def test_filter_blocks_tonglu_name():
    _on()
    hit = check_chengse_filter("胡不为进了供销社。柜上还在过秤。")
    assert hit["ok"] is False
    assert hit["code"] == "chengse_tonglu_name"


def test_filter_blocks_empty_summary_tail():
    _on()
    hit = check_chengse_filter("井台上还有人。夜色深了。")
    assert hit["ok"] is False
    assert hit["code"] == "chengse_empty_summary"


def test_filter_off_does_not_block():
    _off()
    try:
        hit = check_chengse_filter("端的是人如流水。胡不为走了。夜色深了。")
        assert hit["ok"] is True
    finally:
        _on()


def test_draft_struct_hits_chengse_after_dialogue_floor():
    _on()
    play = "完全另一场戏，井台上没有灯。" * 40
    pad = "「按回去。」他说。\n他按住盒子，袖口发烫。沈烛把任务书推过来。\n"
    draft = "端的是冷得很。" + pad * 80
    hit = check_draft_struct(draft, play_text=play)
    assert hit["ok"] is False
    assert hit["code"] == "chengse_classical"


def test_final_last_mile_hits_empty_summary():
    _on()
    prose = ("他按回碎片，袖口发烫。" * 120) + "夜色深了。"
    hit = check_final_last_mile(prose)
    assert hit["ok"] is False
    assert hit["code"] == "chengse_empty_summary"


def test_pilot_codex_kind_uses_official_complete(monkeypatch):
    """设定写厚不得走 _assemble_write_instructions（misc_helpers 未绑定该名）。"""
    from scribe3.api.services import misc_helpers as mh

    assert mh._pilot_uses_official_complete("character") is True
    assert mh._pilot_uses_official_complete("codex-batch") is True
    called = {}

    class _R:
        content = "厚卡"
        model = "x"
        usage = {"total_tokens": 1}

    def fake_complete(ask, **kwargs):
        called["ask"] = ask
        called["system"] = kwargs.get("system")
        return _R()

    monkeypatch.setattr("scribe3.llm.hermes_complete_result", fake_complete)
    monkeypatch.setattr("scribe3.llm.default_model", lambda: "x")

    class St:
        def _query(self, *a, **k):
            return []

        def _execute_write(self, *a, **k):
            return None

    out = mh._pilot_llm_gen(St(), "book_x", 1, "character", "写厚沈槐", max_tokens=200)
    assert out == "厚卡"
    assert called["ask"] == "写厚沈槐"
