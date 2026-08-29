"""P1 视角不得独占 / P2 手段不得单一。

规则形态：指到具体对象（哪一章、哪个人、哪一类动作），不设比例闸。
"""
from __future__ import annotations

from scribe3.ontology import Fact


HERO = "role:柳岸青"
LAN = "role:兰因"


def _fact(local, entity, attr, value, ch):
    return Fact(f"fact:{local}", entity, attr, value, ch, None, False, [])


def _ch(seq, *, foc=HERO, action="买", title="章"):
    return {"seq": seq, "title": title, "focalizer": foc, "plot_action": action}


class St:
    def __init__(self, chapters=(), facts=()):
        self._chapters = list(chapters)
        self._facts = list(facts)

    def chapters_lite(self):
        return list(self._chapters)

    def facts_at(self, ch):
        return [f for f in self._facts if f.valid_from <= ch]

    def list_promises(self):
        return []


def _vol(alt=LAN, lo=141, hi=160):
    return {
        "charter": {
            "chapter_range": [lo, hi],
            "thickens": [],
            "alt_focalizers": [{"oid": alt, "why": "这一卷她自己揭账，不是旁观。"}],
        }
    }


def test_normalize_action_only_accepts_the_eight():
    from scribe3.plot_rules import normalize_action

    assert normalize_action("揭发") == "揭发"
    assert normalize_action(" 买 ") == "买"
    assert normalize_action("其他") is None
    assert normalize_action("付温") is None
    assert normalize_action("") is None


def test_p1_all_hero_is_deficit():
    """150/150 柳岸青：点名的兰因没有一章自己办事。"""
    from scribe3.plot_rules import plot_deficits

    chapters = [_ch(i) for i in range(141, 161)]
    facts = [_fact(f"h{i}", HERO, "付温", "半成", i) for i in range(141, 161)]
    msgs = plot_deficits(St(chapters, facts), _vol(), 141, 160, hero=HERO)
    assert any("兰因" in m and "视角" in m for m in msgs)


def test_p1_alt_pov_watching_hero_is_still_deficit():
    """限知换成兰因、命题仍全是柳岸青办事 = 旁观，不算交差。"""
    from scribe3.plot_rules import plot_deficits

    chapters = [_ch(i, foc=LAN if i == 150 else HERO) for i in range(141, 161)]
    facts = [_fact(f"h{i}", HERO, "付温", "半成", i) for i in range(141, 161)]
    msgs = plot_deficits(St(chapters, facts), _vol(), 141, 160, hero=HERO)
    assert any("兰因" in m for m in msgs)


def test_p1_alt_pov_acting_clears(tmp_path=None):
    """0→1：兰因限知且本章有一条关于她自己的命题。"""
    from scribe3.plot_rules import plot_deficits

    chapters = [_ch(i, foc=LAN if i == 150 else HERO,
                    action="揭发" if i == 150 else "买")
                for i in range(141, 161)]
    facts = [_fact(f"h{i}", HERO, "付温", "半成", i) for i in range(141, 161)]
    facts.append(_fact("lan", LAN, "揭账", "当场点破名册", 150))
    msgs = plot_deficits(St(chapters, facts), _vol(), 141, 160, hero=HERO)
    assert not any("视角" in m or "兰因" in m for m in msgs)


def test_p2_all_buy_is_deficit():
    from scribe3.plot_rules import plot_deficits

    chapters = [_ch(150, foc=LAN, action="买")] + [_ch(i) for i in range(141, 160)]
    facts = [_fact("lan", LAN, "揭账", "当场点破名册", 150)]
    facts += [_fact(f"h{i}", HERO, "付温", "半成", i) for i in range(141, 161)]
    msgs = plot_deficits(St(chapters, facts), _vol(), 141, 160, hero=HERO)
    assert any("同一类" in m or "动作" in m for m in msgs)
    assert "买" in " ".join(msgs)


def test_p2_two_classes_clear():
    """0→1：同一卷里出现两类动作就过，不数比例。"""
    from scribe3.plot_rules import plot_deficits

    chapters = [_ch(i, action="买") for i in range(141, 160)]
    chapters.append(_ch(160, foc=LAN, action="揭发"))
    facts = [_fact("lan", LAN, "揭账", "当场点破名册", 160)]
    facts += [_fact(f"h{i}", HERO, "付温", "半成", i) for i in range(141, 161)]
    msgs = plot_deficits(St(chapters, facts), _vol(), 141, 160, hero=HERO)
    assert msgs == []


def test_p2_unclassified_is_not_a_second_class():
    """缺标注或「其他」不能冒充第二类。"""
    from scribe3.plot_rules import plot_deficits

    chapters = [_ch(i, action="买") for i in range(141, 159)]
    chapters.append(_ch(159, foc=LAN, action=""))
    chapters.append(_ch(160, foc=LAN, action="其他"))
    facts = [_fact("lan", LAN, "揭账", "当场点破名册", 160)]
    facts += [_fact(f"h{i}", HERO, "付温", "半成", i) for i in range(141, 161)]
    msgs = plot_deficits(St(chapters, facts), _vol(), 141, 160, hero=HERO)
    assert any("同一类" in m or "动作" in m for m in msgs)


def test_volume_plot_block_names_the_two_rules_and_current_ledger():
    from scribe3.plot_rules import volume_plot_block

    chapters = [_ch(141), _ch(142)]
    text = volume_plot_block(
        St(chapters), 141, 150,
        hero=HERO,
        alt_focalizers=[{"oid": LAN, "why": "她自己揭账"}],
    )
    assert "兰因" in text
    assert "买" in text
    assert "自己" in text
    assert "同一类" in text or "不得全是" in text
