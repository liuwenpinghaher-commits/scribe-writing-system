"""chapter_spine + clue_density 金样。零 Surreal。驱动真实入口。"""
from __future__ import annotations

from scribe3.chapter_spine import (
    assemble_beat_text,
    assemble_synopsis_from_spine,
    looks_like_13slot,
    normalize_choice,
    parse_choice_ab,
    parse_spine_labels,
)
from scribe3.clue_density import adapt_v1_five_slot, evaluate_beats, evaluate_spine
from scribe3.narrative_contract import cn_len

KNOWN = {("promise", "xiang-debt"), ("storyline", "side-gate")}

G1 = {
    "setting": "还账日后第一个下午，巷口到旧库",
    "cast": "灰七；冷锅婆；灰狸",
    "bite": "天亮前不能张嘴；掌心焦黑未还",
    "goal": "灰七要在炉冷前把焦黑还回侧门",
    "obstacle": "灰狸递假铜挡路；婆子捞锅里账钱",
    "inciting": "灰狸把假铜举到灰七眼皮底下",
    "escalation": "灰七拨开假铜；婆子说账勾了门没开",
    "choice": "硬还焦黑暴露埋灰人 vs 只把纸角塞回门缝",
    "decision": "灰七不进门，把纸角朝门里推回一分",
    "cost": "账清了门更死；门内咳了一声爹的口气",
    "info_gap": "灰狸不知匙；婆子不知撕角",
    "lines": [
        {"kind": "promise", "id": "xiang-debt", "delta": "香债勾笔"},
        {"kind": "storyline", "id": "side-gate", "delta": "侧门未开"},
    ],
    "hook": "铜钱缺口硌着肋骨",
    "forbid": "锁眼、真名、灰狸知匙",
}


def test_g1_dry_13slot_bound_lines_pass():
    r = evaluate_spine(G1, known_line_ids=KNOWN)
    assert r.ok, r.errors


def test_g2_missing_choice_fails():
    s = dict(G1, choice="")
    r = evaluate_spine(s, known_line_ids=KNOWN)
    assert not r.ok
    assert "spine_choice" in r.errors


def test_g3_slogan_fails_atoms():
    slogan = {k: "查明真相" for k in (
        "goal", "obstacle", "inciting", "escalation", "choice",
        "decision", "cost", "info_gap", "hook",
    )}
    slogan["lines"] = [{"kind": "promise", "id": "xiang-debt", "delta": "x"}]
    slogan["cast"] = "灰七"
    r = evaluate_spine(slogan, known_line_ids=KNOWN)
    assert not r.ok
    assert any(e.startswith("spine_atoms") or e.startswith("spine_choice") or e.startswith("spine_slots")
               for e in r.errors)


def test_g4_smoke_padding_adapt_fails():
    smoke = "日子\n" + ("巷口风把檐口的烟和青苔指腹温凉气味锅沿灰星吹过来。" * 40)
    adapted = adapt_v1_five_slot("1. 日子\n" + smoke + "\n2. 必须发生\n空气里全是烟。")
    r = evaluate_spine(adapted, known_line_ids=KNOWN)
    assert not r.ok


def test_g5_short_dry_still_passes():
    r = evaluate_spine(G1, known_line_ids=KNOWN)
    assert r.ok
    syn = assemble_synopsis_from_spine(G1)
    assert len(syn) < 800


def test_g6_complete_sentence_over_forty_still_passes():
    s = dict(G1)
    s["goal"] = "灰七要在炉冷前把焦黑还回侧门，并确认成核点没有跟着他的指针态从门缝里再走进来一次，账还没清"
    s["cost"] = "账清了门更死；成核点开始复制他的指针态，门内咳了一声爹的口气，账勾了却没开"
    assert cn_len(s["goal"]) > 40
    r = evaluate_spine(s, known_line_ids=KNOWN)
    assert r.ok, r.errors
    assert not any(str(e).startswith("spine_slots_long") for e in r.errors)


def test_g6_huanzhangri_not_atom():
    s = dict(G1, goal="还账日")
    r = evaluate_spine(s, known_line_ids=KNOWN)
    assert not r.ok


def test_g7_beats_inherit_cast_pass():
    beats = [
        {"goal": "把假铜挡在眼皮外", "conflict": "灰狸递假铜挡路",
         "turn": "假铜被拨开落回他自己手里", "cost": "灰狸受伤账更难看", "choice": ""},
        {"goal": "把焦黑还回侧门", "conflict": "婆子说账勾了门没开",
         "turn": "门更死咳了一声", "cost": "门没开更险",
         "choice": "硬还焦黑暴露 vs 纸角塞回门缝"},
        {"goal": "守住撕角不让狸看见", "conflict": "灰狸跟在柴垛后",
         "turn": "纸角朝门里推回一分", "cost": "门内咳像爹未兑", "choice": ""},
    ]
    r = evaluate_beats(beats, spine=G1)
    assert r.ok, r.errors


def test_g8_turn_same_as_goal_fails():
    beats = [
        {"goal": "把假铜挡在眼皮外", "conflict": "灰狸递假铜挡路",
         "turn": "把假铜挡在眼皮外", "cost": "账更难看", "choice": "A暴露 vs B更险"},
        {"goal": "还焦黑回侧门", "conflict": "门没开",
         "turn": "还焦黑回侧门", "cost": "门更死", "choice": ""},
        {"goal": "守撕角", "conflict": "灰狸跟着",
         "turn": "守撕角", "cost": "未兑", "choice": ""},
    ]
    r = evaluate_beats(beats, spine=G1)
    assert not r.ok
    assert any(e.startswith("beat_turn_missing") for e in r.errors)


def test_g9_two_beats_fail_count():
    beats = [
        {"goal": "把假铜挡在眼皮外", "conflict": "灰狸递假铜挡路",
         "turn": "假铜被拨开", "cost": "账更难看", "choice": "A暴露 vs B更险"},
        {"goal": "还焦黑回侧门", "conflict": "门没开",
         "turn": "纸角塞回", "cost": "门更死", "choice": ""},
    ]
    r = evaluate_beats(beats, spine=G1)
    assert not r.ok
    assert "beat_count" in r.errors


def test_g10_empty_choice_fails():
    beats = [
        {"goal": "把假铜挡在眼皮外", "conflict": "灰狸递假铜挡路",
         "turn": "假铜被拨开", "cost": "账更难看", "choice": ""},
        {"goal": "还焦黑回侧门", "conflict": "门没开",
         "turn": "纸角塞回", "cost": "门更死", "choice": ""},
        {"goal": "守撕角", "conflict": "灰狸跟着",
         "turn": "推回一分", "cost": "未兑", "choice": ""},
    ]
    r = evaluate_beats(beats, spine=G1)
    assert not r.ok
    assert "beat_choice" in r.errors


def test_g11_placeholder_choice_fails():
    beats = [
        {"goal": "把假铜挡在眼皮外", "conflict": "灰狸递假铜挡路",
         "turn": "假铜被拨开", "cost": "账更难看", "choice": "无"},
        {"goal": "还焦黑回侧门", "conflict": "门没开",
         "turn": "纸角塞回", "cost": "门更死", "choice": "暂无"},
        {"goal": "守撕角", "conflict": "灰狸跟着",
         "turn": "推回一分", "cost": "未兑", "choice": "无选择"},
    ]
    assert normalize_choice("无") == ""
    r = evaluate_beats(beats, spine=G1)
    assert not r.ok
    assert "beat_choice" in r.errors


def test_g12_unbound_lines_plain_fail():
    s = dict(G1, lines="香债勾笔；侧门未开")
    r = evaluate_spine(s, known_line_ids=KNOWN)
    assert not r.ok
    assert "lines_unbound" in r.errors


def test_g13_unknown_id_fail():
    s = dict(G1, lines=[{"kind": "promise", "id": "not-in-book", "delta": "香债勾笔"}])
    r = evaluate_spine(s, known_line_ids=KNOWN)
    assert not r.ok
    assert "lines_unbound" in r.errors


G_WANJIE = {
    "setting": "大泄露当夜，华山北峰到裂口边缘",
    "cast": "柳岸青；沈烛；赫斯",
    "bite": "体温四十二度未退；腕上监测带还烫",
    "goal": "柳岸青要在成核点扩开前把场核碎片按回裂口",
    "obstacle": "赫斯要带他走；沈烛按住腕不让碰核",
    "inciting": "裂口涌出苍穹界灵气，袖口烧出焦边",
    "escalation": "一碰碎片，守望者要本地锁定，海同时拉他入网",
    "choice": "交碎片给沈烛换活 vs 自己按回裂口暴露双权柄",
    "decision": "柳岸青自己按回碎片，不交给沈烛",
    "cost": "大遮蔽多撕一指宽；他被标成移动真真空泡",
    "info_gap": "赫斯不知成核点；沈烛不知他听得见海",
    "lines": [
        {"kind": "promise", "id": "abyss-18mo", "delta": "十八个月深渊"},
        {"kind": "storyline", "id": "jinteng-seal", "delta": "金縢未开"},
    ],
    "hook": "裂口里有人用他母亲的口气咳了一声",
    "forbid": "场核坐标、帝的真名、集体烛照口令",
}


def test_g14_recycled_beats_off_spine_fail():
    """上章假铜戏不能当本章断角台阶。"""
    ch3_spine = dict(
        G1,
        goal="灰七要把卡住的纸角从门缝拔出来",
        obstacle="婆子按住门缝不给再碰",
        inciting="灰狸把假铜又举到他眼前",
        escalation="他拨开假铜去揭纸角，纸角断了一截",
        choice="硬拔去比断口 vs 把断角塞回门缝",
        decision="灰七把断角朝门缝推回一分",
        cost="纸角断在门里，门缝彻底咬合",
        hook="断角在门里硌着",
    )
    recycled = [
        {"goal": "把假铜挡在眼皮外", "conflict": "灰狸递假铜挡路",
         "turn": "假铜被拨开落回他自己手里", "cost": "灰狸受伤账更难看", "choice": ""},
        {"goal": "把纸角揭开门缝", "conflict": "婆子按住门缝挡路",
         "turn": "纸角被门缝咬住抽不回", "cost": "门没开更险",
         "choice": "硬把门缝撕开暴露 vs 只把纸角塞回门缝"},
        {"goal": "把纸角朝门里推回一分", "conflict": "灰狸跟在柴垛后挡路",
         "turn": "纸角推回门里", "cost": "门内咳像爹未兑", "choice": ""},
    ]
    r = evaluate_beats(recycled, spine=ch3_spine)
    assert not r.ok
    assert "beat_off_spine" in r.errors or "choice_not_staged" in r.errors


def test_g15_wanjie_gold_passes_density():
    """rev.6 万界金样必须过密度闸；不得再靠炉灰记假铜句。"""
    known = {("promise", "abyss-18mo"), ("storyline", "jinteng-seal")}
    r = evaluate_spine(G_WANJIE, known_line_ids=known)
    assert r.ok, r.errors
    beats = [
        {"goal": "挡住赫斯伸来的令牌", "conflict": "赫斯把令牌按在他腕上",
         "turn": "令牌被他拨开落回赫斯手里", "cost": "赫斯改口要交核", "choice": ""},
        {"goal": "把场核碎片按回裂口", "conflict": "沈烛按住腕不让碰核",
         "turn": "双权柄互斥，大遮蔽多撕一指宽", "cost": "裂口撕开后大遮蔽更险",
         "choice": "交碎片给沈烛换活 vs 自己按回裂口暴露双权柄"},
        {"goal": "在咳声里保住自己的名", "conflict": "海用母亲的咳声要覆盖他",
         "turn": "他报出名把寄生咳声拨开", "cost": "钩未断那声咳还在裂口", "choice": ""},
    ]
    br = evaluate_beats(beats, spine=G_WANJIE)
    assert br.ok, br.errors
    recycled = [
        {"goal": "把假铜挡在眼皮外", "conflict": "灰狸递假铜挡路",
         "turn": "假铜被拨开落回他自己手里", "cost": "灰狸受伤账更难看", "choice": ""},
        {"goal": "把焦黑还回侧门", "conflict": "婆子说账勾了门没开",
         "turn": "门更死咳了一声", "cost": "门没开更险",
         "choice": "硬还焦黑暴露 vs 纸角塞回门缝"},
        {"goal": "守住撕角不让狸看见", "conflict": "灰狸跟在柴垛后",
         "turn": "纸角朝门里推回一分", "cost": "门内咳像爹未兑", "choice": ""},
    ]
    bad = evaluate_beats(recycled, spine=G_WANJIE)
    assert not bad.ok
    assert "beat_off_spine" in bad.errors or "choice_not_staged" in bad.errors


def test_parse_choice_and_labels():
    assert parse_choice_ab("硬还焦黑暴露 vs 纸角塞回门缝")
    assert looks_like_13slot(
        "本章要：灰七要还焦黑\n挡：假铜挡路\n触发：举到眼前\n升级：拨开\n"
        "选择：A暴露 vs B更险\n决断：推回纸角\n代价：门更死\n信息差：狸不知匙\n"
        "动哪条线：promise:xiang-debt 香债勾笔\n钩：铜钱硌肋骨\n"
    )
    got = parse_spine_labels(
        "本章要：灰七要还焦黑\n挡：假铜挡路\n触发：举到眼前\n升级：拨开\n"
        "选择：A暴露 vs B更险\n决断：推回纸角\n代价：门更死\n信息差：狸不知匙\n"
        "动哪条线：promise:xiang-debt 香债勾笔\n钩：铜钱硌肋骨\n"
    )
    assert got["_source"] == "llm_13slot"
    assert got["goal"]
    syn = assemble_synopsis_from_spine(G1)
    assert "本章要" in syn or "灰七" in syn
    assert assemble_beat_text({"goal": "还焦黑", "conflict": "门没开"})


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
    print("all_pass")
