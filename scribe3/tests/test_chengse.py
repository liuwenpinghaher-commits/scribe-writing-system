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
    assert PLAYBOOK_VERSION == "playbook.3.2.7"
    d = duty_generate({"seq": 1})
    assert "【成色·验戏不验词表】" in d
    assert "先立还在过的日子" in d
    p = play_generate({"seq": 1, "duty": {}})
    assert "假破真" in p
    dr = draft_generate({})
    assert "切在能听见看见" in dr
    f = final_generate({})
    assert "端的" in f and "岂料" in f
    assert "多用'端的、岂料" not in f
    assert "古白话语体" not in f
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


def test_write_protocol_never_teaches_classical():
    """关旗不回古白话教学；主路径也不教词表。"""
    _on()
    proto_on = _write_protocol_block()
    assert "多用'端的、岂料" not in proto_on
    assert "古白话语体" not in proto_on
    assert "志怪笔记体" not in proto_on
    assert "花脚毛驴" not in proto_on
    _off()
    try:
        proto = _write_protocol_block()
        assert "多用'端的、岂料" not in proto
        assert "古白话语体" not in proto
        assert "志怪笔记体" not in proto
        assert "成色（验戏，不验词表）" not in proto
        assert "⟦PROPOSAL" in proto
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


def test_duty_day_blocks_identity_announce():
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct, check_opener_announce

    announce = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="他是看井的人，开篇钩子先扔出去",
        must_happen="报身份",
    )
    hit = check_duty_struct(announce, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_day_announce"

    empty = make_duty(seq=1, who=["沈槐"], available_cast=["沈槐"], day="", must_happen="摘灯")
    empty["day"] = ""
    miss = check_duty_struct(empty, available_cast=["沈槐"])
    assert miss["ok"] is False
    assert miss["code"] == "duty_day_empty"

    lived = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(lived, available_cast=["沈槐"])["ok"] is True

    opener = check_opener_announce("他是看井的人。开坛做法从今夜起。井绳还冻着。")
    assert opener["ok"] is False
    assert opener["code"] == "opener_announce"
    ok_open = check_opener_announce("井台上还在排队。沈槐把空盏摘下来。")
    assert ok_open["ok"] is True


def test_source_has_no_classical_teaching_path():
    """教学路径必须从源码消失，不能只靠关旗绕开。"""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    blobs = [
        (root / "playbook" / "chengse.py").read_text(encoding="utf-8"),
        (root / "api" / "services" / "write_assemble_blocks.py").read_text(encoding="utf-8"),
        (root / "api" / "app_impl.py").read_text(encoding="utf-8"),
    ]
    joined = "\n".join(blobs)
    assert "PROTOCOL_STYLE_LEGACY" not in joined
    assert "_LUANSHI_EXEMPLAR" not in joined
    assert "多用'端的、岂料" not in joined
    assert "古白话语体" not in joined


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
