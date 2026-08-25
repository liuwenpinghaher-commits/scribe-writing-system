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
    assert PLAYBOOK_VERSION == "playbook.3.2.11"
    d = duty_generate({"seq": 1})
    assert "【成色·验戏不验词表】" in d
    assert "先立还在过的日子" in d
    assert "立十一件事" in d
    assert "mask" in d and "crack" in d and "real" in d
    assert "eye" in d and "dist" in d
    assert "cut" in d
    p = play_generate({"seq": 1, "duty": {}})
    assert "假破真" in p
    assert "假破真是这章的骨头" in p
    assert "两难是这章的心脏" not in p
    assert "眼睛交给当场那个人" in p
    assert "切在能听见看见的那一下" in p
    from scribe3.playbook.prompts import identity_for
    assert "两难落在哪个动作" not in identity_for("play")
    assert "眼睛交给谁" in identity_for("play")
    assert "切在哪一下" in identity_for("play")
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
        said="认自家攒的油",
        needed="灯盏是空的",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(lived, available_cast=["沈槐"])["ok"] is True

    opener = check_opener_announce("他是看井的人。开坛做法从今夜起。井绳还冻着。")
    assert opener["ok"] is False
    assert opener["code"] == "opener_announce"
    ok_open = check_opener_announce("井台上还在排队。沈槐把空盏摘下来。")
    assert ok_open["ok"] is True


def test_duty_work_blocks_appraisal_and_same_want():
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    same = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="要六两银子",
        needed="要六两银子",
        must_happen="沈槐把空盏摘下来",
    )
    hit = check_duty_struct(same, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_work_no_fight"

    tell = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="他是一个阴沉的人",
        needed="灯盏是空的",
        must_happen="沈槐把空盏摘下来",
    )
    hit2 = check_duty_struct(tell, available_cast=["沈槐"])
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_work_appraisal"


def test_duty_mask_blocks_dump_and_same_sentence():
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    dump = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="真相是灯油不是自家的",
        crack="空盏",
        real="不是自家油",
        must_happen="沈槐把空盏摘下来",
    )
    hit = check_duty_struct(dump, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_mask_dump"

    empty = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        must_happen="沈槐把空盏摘下来",
    )
    empty["mask"] = ""
    miss = check_duty_struct(empty, available_cast=["沈槐"])
    assert miss["ok"] is False
    assert miss["code"] == "duty_mask_empty"

    same = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="井台认油",
        real="井台认油",
        must_happen="沈槐把空盏摘下来",
    )
    hit2 = check_duty_struct(same, available_cast=["沈槐"])
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_mask_no_turn"

    leaked = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油不是自家油",
        crack="空盏",
        real="不是自家油",
        must_happen="沈槐把空盏摘下来",
    )
    hit3 = check_duty_struct(leaked, available_cast=["沈槐"])
    assert hit3["ok"] is False
    assert hit3["code"] == "duty_mask_dump"

    good = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(good, available_cast=["沈槐"])["ok"] is True


def test_duty_dist_blocks_lecture_and_empty_eye():
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct, check_opener_announce

    lecture = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        eye="说书站到外头报年号",
        dist="near",
        must_happen="沈槐把空盏摘下来",
    )
    hit = check_duty_struct(lecture, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_dist_lecture"

    empty = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        must_happen="沈槐把空盏摘下来",
    )
    empty["eye"] = ""
    miss = check_duty_struct(empty, available_cast=["沈槐"])
    assert miss["ok"] is False
    assert miss["code"] == "duty_eye_empty"

    outside = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        eye="作者视角旁白",
        dist="near",
        must_happen="沈槐把空盏摘下来",
    )
    hit2 = check_duty_struct(outside, available_cast=["沈槐"])
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_dist_outside"

    far_ok = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        eye="站到外头报年号",
        dist="far",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(far_ok, available_cast=["沈槐"])["ok"] is True

    near_ok = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        eye="沈槐",
        dist="near",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(near_ok, available_cast=["沈槐"])["ok"] is True

    opener = check_opener_announce("北宋，雍熙三年。井台上还在排队。")
    assert opener["ok"] is False
    assert opener["code"] == "opener_lecture"
    ok_open = check_opener_announce("井台上还在排队。沈槐把空盏摘下来。")
    assert ok_open["ok"] is True


def test_duty_cut_blocks_sigh_and_empty():
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    sigh = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        eye="沈槐",
        dist="near",
        cut="他叹了口气，夜色深了",
        must_happen="沈槐把空盏摘下来",
    )
    hit = check_duty_struct(sigh, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_cut_sigh"

    empty = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        eye="沈槐",
        dist="near",
        must_happen="沈槐把空盏摘下来",
    )
    empty["cut"] = ""
    miss = check_duty_struct(empty, available_cast=["沈槐"])
    assert miss["ok"] is False
    assert miss["code"] == "duty_cut_empty"

    vague = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        eye="沈槐",
        dist="near",
        cut="气氛转冷",
        must_happen="沈槐把空盏摘下来",
    )
    hit2 = check_duty_struct(vague, available_cast=["沈槐"])
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_cut_not_sensed"

    good = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        mask="井台认油",
        crack="空盏",
        real="不是自家油",
        eye="沈槐",
        dist="near",
        cut="空盏磕在井沿上",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(good, available_cast=["沈槐"])["ok"] is True


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
