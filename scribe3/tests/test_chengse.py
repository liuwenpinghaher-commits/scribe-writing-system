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
    assert PLAYBOOK_VERSION == "playbook.3.2.27"
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

    opener = check_opener_announce("他是看井的人。先宣布法会从今夜起。井绳还冻着。")
    assert opener["ok"] is False
    assert opener["code"] == "opener_announce"
    ok_open = check_opener_announce("井台上还在排队。沈槐把空盏摘下来。")
    assert ok_open["ok"] is True
    altar_open = check_opener_announce("祠堂前还在开坛做法。沈槐把油罐按在心口。")
    assert altar_open["ok"] is True

    road_day = make_duty(
        seq=1,
        who=["沈槐"],
        available_cast=["沈槐"],
        day="天黑后的土路上，沈槐提着空桶往家走",
        said="认自家攒的油",
        needed="灯盏是空的",
        must_happen="沈槐把空桶提过巷口",
        kind="赶路",
    )
    assert check_duty_struct(road_day, available_cast=["沈槐"])["ok"] is True


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


def test_duty_altar_blocks_hero_and_empty_fee():
    """开坛必须交差钱、社戏信了、井灯墓还在。高人下山伏魔不过。开坛做法不当宣布法会。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct, check_opener_announce

    hook = "灯还在横担，灯芯蜷得更小。"
    stay = "桶还空着，柜上账还在杏花秤上，灯还欠着"
    heat = "路上有人说早散早烧香"
    hero = make_duty(
        seq=6, who=["沈槐"], available_cast=["沈槐"],
        day="村子还在请人开坛改运", said="把井改干净", needed="柜上油账还按着他",
        heat="村人鼓掌当社戏，信了",
        stay="灯还欠着，井还在",
        owed="柜上账还在杏花秤上，灯还欠着",
        must_happen="高人下山伏魔",
        kind="开坛", intruder="请人开坛的村长",
        bill="交差钱", bill_holder="杏花", bill_place="柜上",
    )
    hero["bite_from_prev"] = hook
    hit = check_duty_struct(
        hero, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="赶路", prev_intruder="摔桶的媳妇",
    )
    assert hit["ok"] is False
    assert hit["code"] == "duty_altar_hero"

    no_fee = make_duty(
        seq=6, who=["沈槐"], available_cast=["沈槐"],
        day="村子还在请人开坛改运", said="把井改干净", needed="家里那盏添不上",
        heat="村人鼓掌当社戏，信了",
        stay="灯还欠着，井还在",
        owed="柜上账还在杏花秤上，灯还欠着",
        must_happen="沈槐在井口开坛",
        kind="开坛", intruder="请人开坛的村长",
        bill="他把场面过了", bill_holder="杏花", bill_place="柜上",
    )
    no_fee["bite_from_prev"] = hook
    hit2 = check_duty_struct(
        no_fee, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="赶路", prev_intruder="摔桶的媳妇",
    )
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_altar_fee"

    no_heat = make_duty(
        seq=6, who=["沈槐"], available_cast=["沈槐"],
        day="村子还在请人开坛改运", said="把井改干净", needed="柜上油账还按着他",
        heat="井口又挤出一层油",
        stay="灯还欠着，井还在",
        owed="柜上账还在杏花秤上，灯还欠着",
        must_happen="沈槐被柜上油账按在井口开坛",
        kind="开坛", intruder="请人开坛的村长",
        bill="柜上油账把他按住", bill_holder="杏花", bill_place="柜上",
    )
    no_heat["bite_from_prev"] = hook
    hit3 = check_duty_struct(
        no_heat, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="赶路", prev_intruder="摔桶的媳妇",
    )
    assert hit3["ok"] is False
    assert hit3["code"] == "duty_altar_heat"

    ok = make_duty(
        seq=6, who=["沈槐"], available_cast=["沈槐"],
        day="村子还在请人开坛改运", said="把井改干净", needed="柜上油账还按着他",
        heat="村人鼓掌当社戏，信了",
        stay="灯还欠着，井还在",
        owed="柜上账还在杏花秤上，灯还欠着",
        must_happen="沈槐被柜上油账按在井口开坛",
        kind="开坛", intruder="请人开坛的村长",
        bill="柜上油账把他按住", bill_holder="杏花", bill_place="柜上",
    )
    ok["bite_from_prev"] = hook
    assert check_duty_struct(
        ok, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="赶路", prev_intruder="摔桶的媳妇",
    )["ok"] is True
    assert check_opener_announce("祠堂前还在开坛做法。沈槐把油罐按在心口。")["ok"] is True


def test_duty_feast_blocks_announce_without_table():
    """酒宴验结构：酒还不散、面子按桌、有人闯进来、嘴上贺而账还欠。不要字面「那一桌」。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    hook = "灯还在横担上。"
    stay = "灯还欠着，井还在"
    heat = "村人鼓掌当社戏，信了"
    empty = make_duty(
        seq=7, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="把队占住", needed="灯还欠着",
        heat="桌上人还在灌酒",
        stay="灯还欠着，井还在",
        owed="柜上账还在杏花秤上，灯还欠着",
        must_happen="沈槐坐下喝酒",
        kind="酒宴", intruder="贺客",
        bill="面子", bill_holder="杏花", bill_place="柜上",
    )
    empty["bite_from_prev"] = hook
    hit = check_duty_struct(
        empty, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="开坛", prev_intruder="杏花",
    )
    assert hit["ok"] is False
    assert hit["code"] == "duty_feast_day"

    no_in = make_duty(
        seq=7, who=["沈槐"], available_cast=["沈槐"],
        day="供销社柜后喜酒还没散，面子把人按在桌上",
        said="再敬一杯",
        needed="柜上油账还按着他，灯还欠着",
        heat="满屋都像还醉着",
        stay="灯还欠着，酒还坐着",
        owed="柜上账还在杏花秤上，灯还欠着",
        must_happen="沈槐被面子按在桌上敬酒",
        kind="酒宴", intruder="杏花",
        bill="面子把他按在桌上", bill_holder="杏花", bill_place="柜上",
    )
    no_in["bite_from_prev"] = hook
    hit2 = check_duty_struct(
        no_in, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="开坛", prev_intruder="杏花",
    )
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_feast_in"

    ok = make_duty(
        seq=7, who=["沈槐"], available_cast=["沈槐"],
        day="供销社柜后喜酒还没散，面子把人按在桌上",
        said="来贺一声，喝完就走",
        needed="柜上油账还按着他，灯还欠着",
        heat="棉帘一掀，屋里酒气更浓",
        stay="沈槐还坐在酒桌下首，灯还欠着",
        owed="柜上账还在杏花秤上，灯还欠着",
        must_happen="杏花掀棉帘进来，沈槐被按着敬酒",
        kind="酒宴", intruder="杏花掀棉帘进来",
        bill="面子把他按在桌上", bill_holder="杏花", bill_place="柜上",
    )
    ok["bite_from_prev"] = hook
    assert check_duty_struct(
        ok, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="开坛", prev_intruder="杏花",
    )["ok"] is True


def test_duty_jail_blocks_judge_without_rope():
    """坐牢验结构：进城找活、官差收了改口、救人的人进绳。不要清官断案、不要点名黑白。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    hook = "桶在柜边全屋看得见。"
    stay = "沈槐还坐在酒桌下首，灯还欠着"
    heat = "棉帘一掀，屋里酒气更浓"
    judge = make_duty(
        seq=8, who=["沈槐"], available_cast=["沈槐"],
        day="镇上还在找活路", said="把灯认回去",
        needed="柜上油账还按着他，灯还欠着",
        heat="官差改口叫良民",
        stay="救人的人进了绳，灯还欠着",
        owed="沈槐还坐在酒桌下首，灯还欠着",
        must_happen="官差收了小包改口，救人的人被捆走",
        kind="坐牢", intruder="官差收了小包",
        bill="救人的人进绳", bill_holder="官差", bill_place="镇上",
    )
    judge["must_happen"] = "清官断案，黑白分明"
    judge["bite_from_prev"] = hook
    hit = check_duty_struct(
        judge, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="酒宴", prev_intruder="老庚提空桶闯进来",
    )
    assert hit["ok"] is False
    assert hit["code"] == "duty_jail_judge"

    no_city = make_duty(
        seq=8, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水", said="把灯认回去",
        needed="柜上油账还按着他，灯还欠着",
        heat="官差改口叫良民",
        stay="救人的人进了绳，灯还欠着",
        owed="沈槐还坐在酒桌下首，灯还欠着",
        must_happen="官差收了小包改口，救人的人被捆走",
        kind="坐牢", intruder="官差收了小包",
        bill="救人的人进绳", bill_holder="官差", bill_place="镇上",
    )
    no_city["bite_from_prev"] = hook
    hit2 = check_duty_struct(
        no_city, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="酒宴", prev_intruder="老庚提空桶闯进来",
    )
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_jail_city"

    self_rope = make_duty(
        seq=8, who=["沈槐"], available_cast=["沈槐"],
        day="镇上还在找活路", said="把灯认回去",
        needed="柜上油账还按着他，灯还欠着",
        heat="官差改口叫良民",
        stay="沈槐进了绳，灯还欠着",
        owed="沈槐还坐在酒桌下首，灯还欠着",
        must_happen="官差收了小包改口，把沈槐捆走",
        kind="坐牢", intruder="官差收了小包",
        bill="沈槐进绳", bill_holder="官差", bill_place="镇上",
    )
    self_rope["bite_from_prev"] = hook
    hit_self = check_duty_struct(
        self_rope, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="酒宴", prev_intruder="老庚提空桶闯进来",
    )
    assert hit_self["ok"] is False
    assert hit_self["code"] == "duty_jail_rope"

    no_rope = make_duty(
        seq=8, who=["沈槐"], available_cast=["沈槐"],
        day="镇上还在找活路", said="把灯认回去",
        needed="柜上油账还按着他，灯还欠着",
        heat="官差改口叫良民",
        stay="灯还欠着，酒还坐着",
        owed="沈槐还坐在酒桌下首，灯还欠着",
        must_happen="官差收了小包改口",
        kind="坐牢", intruder="官差收了小包",
        bill="面子", bill_holder="官差", bill_place="镇上",
    )
    no_rope["bite_from_prev"] = hook
    hit3 = check_duty_struct(
        no_rope, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="酒宴", prev_intruder="老庚提空桶闯进来",
    )
    assert hit3["ok"] is False
    assert hit3["code"] == "duty_jail_rope"

    ok = make_duty(
        seq=8, who=["沈槐"], available_cast=["沈槐"],
        day="镇上还在找活路", said="把灯认回去",
        needed="柜上油账还按着他，灯还欠着",
        heat="官差改口叫良民，救人的杏花被按住",
        stay="救人的人进了绳，灯还欠着",
        owed="沈槐还坐在酒桌下首，灯还欠着",
        must_happen="官差收了小包改口，救人的人被捆走",
        kind="坐牢", intruder="官差收了小包",
        bill="救人的人进绳", bill_holder="官差", bill_place="镇上",
    )
    ok["bite_from_prev"] = hook
    assert check_duty_struct(
        ok, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="酒宴", prev_intruder="老庚提空桶闯进来",
    )["ok"] is True


def test_gen_duty_nails_savior_into_rope():
    """模型把藏东西的人写进绳时，生成层把救人进绳钉回去。"""
    from scribe3.playbook.layers import _nail_jail_duty, gen_duty

    raw = {
        "kind": "坐牢",
        "day": "镇上还在找活路",
        "must_happen": "官差收了小包改口，把沈槐捆走",
        "stay": "沈槐进了绳，灯还欠着",
        "heat": "官差改口叫良民",
        "bill": "沈槐进绳",
        "who": ["沈槐", "杏花"],
        "available_cast": ["沈槐", "杏花", "差"],
    }
    nailed = _nail_jail_duty(raw, {"available_cast": ["沈槐", "杏花", "差"]})
    assert "救人" in str(nailed.get("must_happen") or "")
    assert "杏花" in str(nailed.get("must_happen") or "")
    assert "把沈槐" not in str(nailed.get("must_happen") or "")
    assert "救人" in str(nailed.get("stay") or "")
    assert "差" in (nailed.get("who") or [])

    def llm(prompt, **kw):
        return (
            '{"day":"镇上还在找活路","said":"把账清了","needed":"灯还欠着",'
            '"mask":"他装成来报账","crack":"东西一交，官差改口","real":"救人的人进绳",'
            '"eye":"沈槐","dist":"near","cut":"绳勒上腕子",'
            '"one_line":"官差受贿","keep":"救人的杏花被捆走才倒过来",'
            '"heat":"官差改口叫良民","stay":"沈槐进了绳",'
            '"owed":"灯还欠着","kind":"坐牢","intruder":"差收了小包",'
            '"bill_holder":"差","bill_place":"镇上",'
            '"must_happen":"官差收了小包改口，把沈槐捆走",'
            '"bill":"沈槐进绳","who":["沈槐"],"forbidden_reveal":["油从哪来"]}'
        )

    out = gen_duty({"seq": 8, "available_cast": ["沈槐", "杏花", "差"], "chapter_duty": "救人的人进了绳"}, llm)
    assert out["kind"] == "坐牢"
    assert "救人" in out["must_happen"]
    assert "救人" in out["stay"]


def test_duty_skip_year_blocks_calendar_and_song():
    """跳年验结构：街上还在过的一天。补日历 / N年后说明书不过。不要铜炉歌名。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    hook = "空桶还在柜上。"
    stay = "救人的人进了绳，灯还欠着"
    heat = "官差改口叫良民，救人的杏花被按住"
    later = make_duty(
        seq=9, who=["沈槐"], available_cast=["沈槐"],
        day="六年后街上还在过",
        said="把歌改成好卖的",
        needed="灯还欠着，救人的人还在绳上",
        heat="茶馆把旧年当茶讲",
        stay="灯还欠着，街上这一天还没过完",
        owed="救人的人进了绳，灯还欠着",
        must_happen="茶馆还在讲旧年，行人还在走",
        kind="跳年", intruder="行人要改歌",
        bill="年跳了账还在", bill_holder="杏花", bill_place="绳上",
    )
    later["bite_from_prev"] = hook
    hit = check_duty_struct(
        later, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="坐牢", prev_intruder="差收了小包",
    )
    assert hit["ok"] is False
    assert hit["code"] == "duty_skip_calendar"

    song = make_duty(
        seq=9, who=["沈槐"], available_cast=["沈槐"],
        day="店还没开张的早上，街上还在过这一天",
        said="把歌改成好卖的",
        needed="灯还欠着，救人的人还在绳上",
        heat="茶馆把旧年当茶讲",
        stay="灯还欠着，街上这一天还没过完",
        owed="救人的人进了绳，灯还欠着",
        must_happen="瞎子唱《乱世铜炉》，行人要他改《十八摸》",
        kind="跳年", intruder="行人要改歌",
        bill="年跳了账还在", bill_holder="杏花", bill_place="绳上",
    )
    song["bite_from_prev"] = hook
    hit2 = check_duty_struct(
        song, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="坐牢", prev_intruder="差收了小包",
    )
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_skip_song"

    empty = make_duty(
        seq=9, who=["沈槐"], available_cast=["沈槐"],
        day="井台上还在排队打水",
        said="把账清了",
        needed="灯还欠着，救人的人还在绳上",
        heat="队又挤了一层",
        stay="灯还欠着",
        owed="救人的人进了绳，灯还欠着",
        must_happen="沈槐还在井台排队",
        kind="跳年", intruder="队尾那句",
        bill="年跳了账还在", bill_holder="杏花", bill_place="绳上",
    )
    empty["bite_from_prev"] = hook
    hit3 = check_duty_struct(
        empty, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="坐牢", prev_intruder="差收了小包",
    )
    assert hit3["ok"] is False
    assert hit3["code"] == "duty_skip_street"

    ok = make_duty(
        seq=9, who=["沈槐"], available_cast=["沈槐"],
        day="店还没开张的早上，街上还在过这一天",
        said="把歌改成好卖的",
        needed="灯还欠着，救人的人还在绳上",
        heat="茶馆把旧年当茶讲，像年已经翻了",
        stay="灯还欠着，救人的人还在绳上，街上这一天还没过完",
        owed="救人的人进了绳，灯还欠着",
        must_happen="茶馆还在讲旧年，行人还在走，有人当街要改歌",
        kind="跳年", intruder="行人要改歌",
        bill="年跳了账还在", bill_holder="杏花", bill_place="绳上",
        cut="铜子落在茶馆柜上那一声",
        one_line="年跳过去了",
        keep="店还没开张的早上和茶馆还在讲，删了只剩过场",
    )
    ok["bite_from_prev"] = hook
    assert check_duty_struct(
        ok, available_cast=["沈槐"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="坐牢", prev_intruder="差收了小包",
    )["ok"] is True


def test_gen_duty_nails_skip_year_off_calendar():
    """模型写成六年后说明书时，生成层钉回街上还在过的一天。"""
    from scribe3.playbook.layers import _nail_skip_year_duty, gen_duty

    raw = {
        "kind": "跳年",
        "day": "六年后",
        "must_happen": "补日历",
        "stay": "日子翻了",
        "heat": "年过了",
        "who": ["沈槐"],
    }
    nailed = _nail_skip_year_duty(raw, {"chapter_duty": "跳年写成街上还在过的一天"})
    assert nailed["kind"] == "跳年"
    assert "街上" in nailed["day"] or "开张" in nailed["day"]
    assert "六年" not in nailed["day"]
    assert "乱世铜炉" not in str(nailed)
    assert "十八摸" not in str(nailed)

    def llm(prompt, **kw):
        return (
            '{"day":"六年后街上还在过","said":"把歌改了","needed":"灯还欠着",'
            '"mask":"年已经翻了","crack":"茶馆帘子枯了","real":"账还欠着",'
            '"eye":"沈槐","dist":"near","cut":"铜子一响",'
            '"one_line":"跳过六年","keep":"补日历",'
            '"heat":"年过了","stay":"日子翻了",'
            '"owed":"灯还欠着","kind":"跳年","intruder":"行人",'
            '"bill_holder":"杏花","bill_place":"绳上",'
            '"must_happen":"补日历",'
            '"bill":"年跳了","who":["沈槐"],"forbidden_reveal":["油从哪来"]}'
        )

    out = gen_duty({"seq": 9, "available_cast": ["沈槐"], "chapter_duty": "街上还在过的一天"}, llm)
    assert out["kind"] == "跳年"
    assert "六年" not in out["day"]
    assert "街上" in out["day"] or "开张" in out["day"]


def test_duty_choice_blocks_ambush_and_proper():
    """选择验结构：还能跑、掉头、自己人交名。遇袭丢魂 / 铜炉专名不过。"""
    from scribe3.playbook.context import make_duty
    from scribe3.playbook.structural import check_duty_struct

    hook = "绳上的杏花远远朝这边抬了一次眼，什么也没喊，又低下去了"
    stay = "灯还欠着，救人的人还在绳上，街上这一天还没过完"
    heat = "茶馆把旧年当茶讲，像年已经翻了"
    ambush = make_duty(
        seq=10, who=["沈槐"], available_cast=["沈槐", "杏花", "师傅"],
        day="还能跑的那一截路上",
        said="求情比空口强",
        needed="他还想跑，名已经从自己人嘴里出来",
        heat="求情像把人护住了",
        stay="人不等于放了。名交出去了，灯还欠着",
        owed="灯还欠着，救人的人还在绳上",
        must_happen="遇袭丢魂",
        kind="选择", intruder="自己人抢先报名",
        bill="人交出去了", bill_holder="师傅", bill_place="路上",
        cut="自己人报名那一声",
        one_line="他救人去见人",
        keep="还能跑、自己掉头、自己人交名，删了只剩过场",
    )
    ambush["bite_from_prev"] = hook
    hit = check_duty_struct(
        ambush, available_cast=["沈槐", "杏花", "师傅"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="跳年", prev_intruder="行人要改歌",
    )
    assert hit["ok"] is False
    assert hit["code"] == "duty_choice_ambush"

    proper = make_duty(
        seq=10, who=["沈槐"], available_cast=["沈槐", "杏花", "师傅"],
        day="还能跑的那一截路上",
        said="求情比空口强",
        needed="他还想跑，名已经从自己人嘴里出来",
        heat="求情像把人护住了",
        stay="人不等于放了。名交出去了，灯还欠着",
        owed="灯还欠着，救人的人还在绳上",
        must_happen="他掉头，自己人报出圣手小青龙",
        kind="选择", intruder="自己人抢先报名",
        bill="人交出去了", bill_holder="师傅", bill_place="路上",
        cut="自己人报名那一声",
        one_line="他救人去见人",
        keep="还能跑、自己掉头、自己人交名，删了只剩过场",
    )
    proper["bite_from_prev"] = hook
    hit2 = check_duty_struct(
        proper, available_cast=["沈槐", "杏花", "师傅"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="跳年", prev_intruder="行人要改歌",
    )
    assert hit2["ok"] is False
    assert hit2["code"] == "duty_choice_name"

    no_run = make_duty(
        seq=10, who=["沈槐"], available_cast=["沈槐", "杏花", "师傅"],
        day="井台上还在排队打水",
        said="求情比空口强",
        needed="他还想跑，名已经从自己人嘴里出来",
        heat="求情像把人护住了",
        stay="人不等于放了。名交出去了，灯还欠着",
        owed="灯还欠着，救人的人还在绳上",
        must_happen="他掉头，自己人抢先报名",
        kind="选择", intruder="自己人抢先报名",
        bill="人交出去了", bill_holder="师傅", bill_place="路上",
        cut="自己人报名那一声",
        one_line="他救人去见人",
        keep="还能跑、自己掉头、自己人交名，删了只剩过场",
    )
    no_run["bite_from_prev"] = hook
    hit3 = check_duty_struct(
        no_run, available_cast=["沈槐", "杏花", "师傅"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="跳年", prev_intruder="行人要改歌",
    )
    assert hit3["ok"] is False
    assert hit3["code"] == "duty_choice_run"

    ok = make_duty(
        seq=10, who=["沈槐", "杏花", "师傅"], available_cast=["沈槐", "杏花", "师傅"],
        day="还能跑的那一截路上",
        said="求情比空口强",
        needed="他还想跑，名已经从自己人嘴里出来",
        heat="求情像把人护住了",
        stay="人不等于放了。名交出去了，灯还欠着",
        owed="灯还欠着，救人的人还在绳上",
        must_happen="他本可跑，听见自己人开口就掉头，自己人抢先把命名交出去",
        kind="选择", intruder="自己人抢先报名",
        bill="人交出去了", bill_holder="师傅", bill_place="路上",
        cut="自己人报名那一声",
        one_line="他救人去见人",
        keep="还能跑、自己掉头、自己人交名，删了只剩过场",
    )
    ok["bite_from_prev"] = hook
    assert check_duty_struct(
        ok, available_cast=["沈槐", "杏花", "师傅"], prev_hook_quote=hook,
        prev_stay=stay, prev_heat=heat, prev_kind="跳年", prev_intruder="行人要改歌",
    )["ok"] is True


def test_gen_duty_nails_choice_off_ambush():
    """模型写成遇袭丢魂时，生成层钉回还能跑、掉头、交名。"""
    from scribe3.playbook.layers import _nail_choice_duty, gen_duty

    raw = {
        "kind": "选择",
        "day": "路上",
        "must_happen": "遇袭丢魂",
        "stay": "人死了",
        "heat": "打完了",
        "who": ["沈槐"],
    }
    nailed = _nail_choice_duty(raw, {"chapter_duty": "还能跑，自己掉头交名", "available_cast": ["沈槐", "杏花", "师傅"]})
    assert nailed["kind"] == "选择"
    assert "还能跑" in nailed["day"] or "本可跑" in nailed["must_happen"]
    assert "掉头" in nailed["must_happen"]
    assert "交" in nailed["must_happen"]
    assert "圣手小青龙" not in str(nailed)
    assert "遇袭丢魂" not in nailed["must_happen"]

    def llm(prompt, **kw):
        return (
            '{"day":"路上","said":"求情","needed":"灯还欠着",'
            '"mask":"他还能走","crack":"自己人开口","real":"名交出去了",'
            '"eye":"沈槐","dist":"near","cut":"报名那一声",'
            '"one_line":"遇袭丢魂","keep":"中暗器",'
            '"heat":"打完了","stay":"人死了",'
            '"owed":"灯还欠着","kind":"选择","intruder":"师傅",'
            '"bill_holder":"师傅","bill_place":"路上",'
            '"must_happen":"遇袭丢魂",'
            '"bill":"丢魂","who":["沈槐"],"forbidden_reveal":["油从哪来"]}'
        )

    out = gen_duty({"seq": 10, "available_cast": ["沈槐", "杏花", "师傅"], "chapter_duty": "自己人交名"}, llm)
    assert out["kind"] == "选择"
    assert "掉头" in out["must_happen"]
    assert "遇袭丢魂" not in out["must_happen"]


def test_draft_copy_does_not_kill_lived_expansion():
    """场面已立住的扩写不得因跟戏 24% 重复被毙。整段搬戏才拦。"""
    play = (
        "沈槐进门先笑，说昨晚酒多，手慢没提桶，今天过来搭把手。"
        "差进来把桶提起来。杏花说油是昨晚喜酒上老庚提来的。"
        "差收起油纸包，把杏花手腕绕上去。"
    )
    lived = (
        "沈槐推门进来。他先笑，说昨晚酒多手慢，桶没提，今天过来搭把手。"
        "「差来了。」外头有人喊。"
        "差进来，棉帽压到眉毛。他把桶提起来，往沈槐面前一递。"
        "杏花说：「油是昨晚喜酒上，老庚提来的。」"
        "差收起油纸包，从后腰掏出细麻绳，把杏花手腕绕上去。"
        "沈槐站在柜台前，兜里空手，没往外掏。灯还在外头。"
    ) * 6
    hit = check_draft_struct(lived, play_text=play)
    assert hit.get("code") != "draft_copy_play", hit
    dump = play * 40 + "他又看了一眼裂口。" * 8
    bad = check_draft_struct(dump, play_text=play * 40)
    assert bad["ok"] is False
    assert bad["code"] == "draft_copy_play"


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
    from scribe3.playbook.chengse import load_zhangfa
    load_zhangfa.cache_clear()
    assert "面子把人按在桌上" in d
    assert load_zhangfa() in d
    from scribe3.playbook.chengse import load_yinwen
    load_yinwen.cache_clear()
    assert "街上还在过的一天" in d
    assert load_yinwen() in d
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
