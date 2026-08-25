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
    assert PLAYBOOK_VERSION == "playbook.3.2.21"
    d = duty_generate({"seq": 1})
    assert "【对照·真源】" in d
    assert "【成色·验戏不验词表】" not in d
    assert "把眼睛交给当场那个人" in d
    assert "不要上来就掏底牌" in d
    assert "北宋，雍熙三年" in d
    assert "立十三件事" in d
    p = play_generate({"seq": 1, "duty": {}})
    assert "【对照·真源】" in p
    assert "热闹像翻了，墓还在" in p
    from scribe3.playbook.prompts import identity_for
    assert "两难落在哪个动作" not in identity_for("play")
    dr = draft_generate({})
    assert "【对照·真源】" in dr
    f = final_generate({})
    assert "【对照·真源】" in f
    assert "多用'端的、岂料" not in f
    assert "古白话语体" not in f
    j = duty_judge({})
    assert "【对照·真源·审判】" in j
    assert "C1." not in j
    assert "八问" in j
    assert "十二问" in play_judge({})
    assert "【对照·真源·审判】" in final_judge({})
    assert "验戏，不验词表" not in final_judge({})


def test_write_protocol_drops_classical_when_on():
    _on()
    proto = _write_protocol_block()
    assert "⟦PROPOSAL" in proto
    assert "讨论" in proto and "动稿" in proto
    assert "多用'端的、岂料" not in proto
    assert "成色（验戏，不验词表）" in proto
    assert "【对照·真源】" in proto
    assert "把眼睛交给当场那个人" in proto
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


def test_duty_yin_blocks_one_line_and_same():
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

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
        cut="空盏磕在井沿上",
        must_happen="沈槐把空盏摘下来",
    )
    empty["keep"] = ""
    miss = check_duty_struct(empty, available_cast=["沈槐"])
    assert miss["ok"] is False
    assert miss["code"] == "duty_keep_empty"

    same = make_duty(
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
        one_line="他把空盏摘下来",
        keep="他把空盏摘下来",
        must_happen="沈槐把空盏摘下来",
    )
    hit = check_duty_struct(same, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_yin_same"

    slip = make_duty(
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
        one_line="他把空盏摘下来",
        keep="过场即可",
        must_happen="沈槐把空盏摘下来",
    )
    hit2 = check_duty_struct(slip, available_cast=["沈槐"])
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_yin_one_line"

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
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(good, available_cast=["沈槐"])["ok"] is True


def test_duty_flip_blocks_heat_as_turn():
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

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
        cut="空盏磕在井沿上",
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        must_happen="沈槐把空盏摘下来",
    )
    empty["stay"] = ""
    miss = check_duty_struct(empty, available_cast=["沈槐"])
    assert miss["ok"] is False
    assert miss["code"] == "duty_stay_empty"

    same = make_duty(
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
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        heat="井台上有人认了这盏油",
        stay="井台上有人认了这盏油",
        must_happen="沈槐把空盏摘下来",
    )
    hit = check_duty_struct(same, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_flip_same"

    heat_ok = make_duty(
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
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        heat="井台上有人认了这盏油",
        stay="热闹就是翻",
        must_happen="沈槐把空盏摘下来",
    )
    hit2 = check_duty_struct(heat_ok, available_cast=["沈槐"])
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_flip_heat"

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
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        heat="井台上有人认了这盏油",
        stay="灯还是空的，日子没翻",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(good, available_cast=["沈槐"])["ok"] is True


def test_duty_owed_blocks_cleared_stay():
    """上场 stay 这场必须还在过。只接 hook.quote、把 stay 清掉，不算。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    prev = "油罐仍贴在棉袄里，没一个人当众认那盏灯。"
    hook = "那盏灯在横担上烧着，火光比先前稳了些。"
    unpaid = make_duty(
        seq=2,
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
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        heat="井台上有人认了这盏油",
        stay="灯还是空的，日子没翻",
        owed="接住了横担上那句火光",
        must_happen="沈槐把空盏摘下来",
        bite_from_prev=hook,
    )
    unpaid["bite_from_prev"] = hook
    miss = check_duty_struct(
        unpaid, available_cast=["沈槐"], prev_hook_quote=hook, prev_stay=prev,
    )
    assert miss["ok"] is False
    assert miss["code"] == "duty_stay_unpaid"

    living = make_duty(
        seq=2,
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
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        heat="井台上有人认了这盏油",
        stay="沈槐还排在队尾，油罐仍贴在棉袄里",
        owed="没一个人当众认那盏灯",
        must_happen="沈槐把空盏摘下来",
        bite_from_prev=hook,
    )
    living["bite_from_prev"] = hook
    assert check_duty_struct(
        living, available_cast=["沈槐"], prev_hook_quote=hook, prev_stay=prev,
    )["ok"] is True

    ch1 = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="认自家攒的油",
        needed="灯盏是空的",
        must_happen="沈槐把空盏摘下来",
    )
    assert check_duty_struct(ch1, available_cast=["沈槐"])["ok"] is True


def test_duty_heat_blocks_same_flip():
    """热闹不得和上场同一套。假翻不犯同一种热闹。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    prev_heat = "井台上有人认了这盏油"
    prev_stay = "油罐仍贴在棉袄里，没一个人当众认那盏灯。"
    hook = "那盏灯在横担上烧着，火光比先前稳了些。"
    same = make_duty(
        seq=2,
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
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        heat=prev_heat,
        stay="沈槐还排在队尾，油罐仍贴在棉袄里",
        owed="没一个人当众认那盏灯",
        must_happen="沈槐把空盏摘下来",
    )
    same["bite_from_prev"] = hook
    hit = check_duty_struct(
        same, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=prev_stay, prev_heat=prev_heat,
    )
    assert hit["ok"] is False
    assert hit["code"] == "duty_heat_repeat"

    fresh = make_duty(
        seq=2,
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
        one_line="他把空盏摘下来",
        keep="灯油不是自家攒的，空盏才露出来",
        heat="有人趴下看井口，说黑得发亮",
        stay="沈槐还排在队尾，油罐仍贴在棉袄里",
        owed="没一个人当众认那盏灯",
        must_happen="沈槐把空盏摘下来",
    )
    fresh["bite_from_prev"] = hook
    assert check_duty_struct(
        fresh, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=prev_stay, prev_heat=prev_heat,
    )["ok"] is True


def test_duty_kind_blocks_same_day_without_intruder():
    """日子种类必填。同一种不换谁闯进来、只换节号，不过。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    hook = "那盏灯在横担上烧着，火光比先前稳了些。"
    stay = "油罐仍贴在棉袄里，没一个人当众认那盏灯。"
    heat = "井台上有人认了这盏油"
    empty = make_duty(
        seq=1, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="认自家攒的油", needed="灯盏是空的",
        must_happen="沈槐把空盏摘下来",
    )
    empty["kind"] = ""
    miss = check_duty_struct(empty, available_cast=["沈槐"])
    assert miss["ok"] is False
    assert miss["code"] == "duty_kind_empty"

    chap = make_duty(
        seq=1, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="认自家攒的油", needed="灯盏是空的",
        must_happen="沈槐把空盏摘下来", kind="换节号",
    )
    hit = check_duty_struct(chap, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_kind_chapter"

    same = make_duty(
        seq=2, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="认自家攒的油", needed="灯盏是空的",
        heat="有人趴下看井口，说黑得发亮",
        stay="沈槐还排在队尾，油罐仍贴在棉袄里",
        owed="没一个人当众认那盏灯",
        must_happen="沈槐把空盏摘下来",
        kind="同场", intruder="",
    )
    same["bite_from_prev"] = hook
    hit2 = check_duty_struct(
        same, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="同场",
    )
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_kind_same"

    newcomer = make_duty(
        seq=2, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="认自家攒的油", needed="灯盏是空的",
        heat="有人趴下看井口，说黑得发亮",
        stay="沈槐还排在队尾，油罐仍贴在棉袄里",
        owed="没一个人当众认那盏灯",
        must_happen="沈槐把空盏摘下来",
        kind="同场", intruder="队尾那人",
    )
    newcomer["bite_from_prev"] = hook
    assert check_duty_struct(
        newcomer, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="同场", prev_intruder="杏花",
    )["ok"] is True

    third = make_duty(
        seq=5, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="认自家攒的油", needed="灯盏是空的",
        heat="柜上有人把油路认到沈槐名下",
        stay="沈槐还排在队尾，油罐仍贴在棉袄里",
        owed="没一个人当众认那盏灯",
        must_happen="沈槐把空盏摘下来",
        kind="同场", intruder="又一个人",
    )
    third["bite_from_prev"] = hook
    stuck = check_duty_struct(
        third, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="同场", prev_intruder="杏花",
        same_kind_run=2,
    )
    assert stuck["ok"] is False
    assert stuck["code"] == "duty_kind_stuck"

    road = make_duty(
        seq=5, who=["沈槐"], available_cast=["沈槐"],
        day="沈槐还在往家赶路，空桶提在手里", said="今晚要把油添上", needed="柜上账还在，灯还欠着",
        heat="路上有人拦他问柜上那笔油",
        stay="桶还空着，柜上账还在杏花秤上，灯还欠着",
        owed="油罐仍贴在棉袄里，没一个人当众认那盏灯",
        must_happen="沈槐离开井台往家走",
        kind="赶路", intruder="拦路的人",
        bill_holder="杏花", bill_place="柜上",
    )
    road["bite_from_prev"] = hook
    assert check_duty_struct(
        road, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="同场", prev_intruder="杏花",
        same_kind_run=0,
    )["ok"] is True

    from scribe3.playbook.structural import infer_duty_kind
    old = {"stay": "沈槐仍在队尾，桶空着，灯还在横担上，没人当众认那盏灯。"}
    assert infer_duty_kind(old) == "同场"


def test_duty_bill_blocks_shame_swap_and_stuck_move():
    """账要换持有人或换地。换气换丢人、声称转走人地没换，不过。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    shame = make_duty(
        seq=1, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="认自家攒的油", needed="灯盏是空的",
        must_happen="沈槐把空盏摘下来",
        bill_holder="换气换丢人", bill_place="井台",
    )
    hit = check_duty_struct(shame, available_cast=["沈槐"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_bill_shame"

    stuck = make_duty(
        seq=2, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="认自家攒的油", needed="灯盏是空的",
        heat="有人趴下看井口，说黑得发亮",
        stay="沈槐还排在队尾，油罐仍贴在棉袄里",
        owed="没一个人当众认那盏灯",
        must_happen="沈槐把空盏摘下来",
        kind="赶路", bill="这笔账转走了",
        bill_holder="沈槐", bill_place="井台",
    )
    stuck["bite_from_prev"] = "那盏灯在横担上烧着，火光比先前稳了些。"
    hit2 = check_duty_struct(
        stuck, available_cast=["沈槐"],
        prev_hook_quote=stuck["bite_from_prev"],
        prev_stay="油罐仍贴在棉袄里，没一个人当众认那盏灯。",
        prev_heat="井台上有人认了这盏油",
        prev_holder="沈槐", prev_place="井台",
    )
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_bill_stuck"

    moved = make_duty(
        seq=2, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="认自家攒的油", needed="灯盏是空的",
        heat="有人趴下看井口，说黑得发亮",
        stay="沈槐还排在队尾，油罐仍贴在棉袄里",
        owed="没一个人当众认那盏灯",
        must_happen="沈槐把空盏摘下来",
        kind="赶路", bill="油账落到杏花柜上",
        bill_holder="杏花", bill_place="柜上",
    )
    moved["bite_from_prev"] = stuck["bite_from_prev"]
    assert check_duty_struct(
        moved, available_cast=["沈槐"],
        prev_hook_quote=moved["bite_from_prev"],
        prev_stay="油罐仍贴在棉袄里，没一个人当众认那盏灯。",
        prev_heat="井台上有人认了这盏油",
        prev_holder="沈槐", prev_place="井台",
    )["ok"] is True


def test_draft_len_does_not_kill_lived_scene():
    """字数不作完成。一场已立住的日子不得因不够 2000 被毙。"""
    play = "完全另一场戏，井台上没有灯。" * 40
    lived = (
        "井台上还在排队。沈槐站在队尾，棉袄里那罐油贴着心口。"
        "「灯油从哪来的？」前头有人问。"
        "杏花说：「灯不是我点的，别从我这儿重排。」"
        "老庚蹲在井台边拨泥。沈槐的桶底刮着冻地，咯地一响。"
        "灯在横担上烧着，火光比先前稳了些。"
    ) * 8
    hit = check_draft_struct(lived, play_text=play)
    assert hit.get("code") != "draft_len"
    emptyish = "井台上还在排队。沈槐站着。"
    miss = check_draft_struct(emptyish, play_text=play)
    assert miss["ok"] is False
    assert miss["code"] == "draft_len"


def test_prose_len_does_not_kill_lived_scene():
    """字数不作完成。一场已立住的日子不得因不够 1000 被毙。"""
    from scribe3.playbook.structural import check_final_struct

    lived = (
        "井台上还在排队。沈槐站在队尾，棉袄里那罐油贴着心口。"
        "「灯油从哪来的？」前头有人问。"
        "杏花说：「灯不是我点的，别从我这儿重排。」"
        "老庚蹲在井台边拨泥。沈槐的桶底刮着冻地，咯地一响。"
        "灯在横担上烧着，火光比先前稳了些。"
    ) * 8
    hit = check_final_struct(lived)
    assert hit.get("code") != "prose_len"
    emptyish = "井台上还在排队。沈槐站着。"
    miss = check_final_struct(emptyish)
    assert miss["ok"] is False
    assert miss["code"] == "prose_len"


def test_duizhao_is_generate_ssot_not_paraphrase():
    from scribe3.playbook.chengse import DUIZHAO_PATH, DuizhaoMissing, load_duizhao, _duizhao_path

    load_duizhao.cache_clear()
    raw = DUIZHAO_PATH.read_text(encoding="utf-8")
    assert _duizhao_path() == DUIZHAO_PATH
    assert load_duizhao() == raw.strip()
    d = duty_generate({"seq": 1})
    assert raw.strip() in d
    assert "CRAFT_GENERATE" not in (Path := __import__("pathlib").Path)(
        __file__
    ).resolve().parents[1].joinpath("playbook", "chengse.py").read_text(encoding="utf-8")

    missing = DuizhaoMissing("x")
    assert isinstance(missing, RuntimeError)

    other = Path("/tmp/duizhao-override.md")
    os.environ["SCRIBE3_DUIZHAO_PATH"] = str(other)
    try:
        assert _duizhao_path() == other
    finally:
        os.environ.pop("SCRIBE3_DUIZHAO_PATH", None)


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

    # generate-stage 走 app_impl 重绑后的 _pilot_llm_gen；邻居函数必须一起导出。
    from scribe3.api import app_impl as core

    assert callable(core._pilot_uses_official_complete)
    assert core._pilot_uses_official_complete("duty") is True
    assert core._pilot_llm_gen(St(), "book_x", 2, "duty", "立责任卡", max_tokens=200) == "厚卡"
