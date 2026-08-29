"""铺章跟伏笔窗口走，不跟全书占比走。"""
from __future__ import annotations

from scribe3.ontology import Fact


def _p(**kw):
    row = {
        "id": "promise:abc123",
        "text": "长线",
        "status": "open",
        "setup_chapter": 10,
        "tier": "arc",
        "payoff_min": 15,
        "payoff_max": 25,
    }
    row.update(kw)
    return row


def test_pre_window_payoff_is_blocked():
    from scribe3.expand_lifetime import payoff_skip_reason

    p = _p()
    assert payoff_skip_reason(p, 12, pays_refs=set())
    assert payoff_skip_reason(p, 20, pays_refs=set()) is None


def test_book_tier_blocked_unless_named_in_pays():
    from scribe3.expand_lifetime import payoff_skip_reason

    p = _p(tier="book", payoff_min=11, payoff_max=None)
    assert payoff_skip_reason(p, 50, pays_refs=set())
    assert payoff_skip_reason(p, 50, pays_refs={"LABC123"}) is None


def test_thicken_unused_is_presence_not_count():
    """本卷有一条命题就算用到。不再数是不是满 3 条新 attribute。"""
    from scribe3.expand_lifetime import thicken_unused

    facts = [
        Fact("fact:a1", "role:验温嫂", "拒册", "一", 81, None, False, []),
        Fact("fact:old", "role:验温嫂", "旧", "前卷", 12, None, False, []),
    ]

    class St:
        def facts_at(self, ch):
            return [f for f in facts if f.valid_from <= ch]

    unused = thicken_unused(St(), ["role:验温嫂", "place:无名井"], 81, 100)
    assert unused == ["place:无名井"]


def test_assert_batch_depth_passes_when_named_entity_has_one_fact():
    from scribe3.expand_lifetime import assert_volume_lifetime

    facts = [
        Fact("fact:a1", "role:验温嫂", "拒册", "一", 81, None, False, []),
    ]

    class St:
        def facts_at(self, ch):
            return [f for f in facts if f.valid_from <= ch]

        def list_promises(self):
            return []

    vol = {"charter": {"chapter_range": [81, 100],
                       "thickens": [{"oid": "role:验温嫂", "why": "验"}]}}
    assert_volume_lifetime(St(), vol, 81, 100)


def test_assert_batch_depth_fails_when_named_entity_unused():
    from scribe3.expand_lifetime import assert_volume_lifetime

    class St:
        def facts_at(self, ch):
            return []

        def list_promises(self):
            return []

    vol = {"charter": {"chapter_range": [81, 100],
                       "thickens": [{"oid": "role:验温嫂", "why": "验"}]}}
    try:
        assert_volume_lifetime(St(), vol, 91, 100)
        raise AssertionError("未用到必须抛")
    except ValueError as e:
        assert "验温嫂" in str(e)
        assert "新 attribute" not in str(e)


def test_assert_does_not_throw_on_headliner_share():
    from scribe3.expand_lifetime import assert_volume_lifetime

    facts = [Fact(f"fact:{i}", "role:柳岸青", f"a{i}", "事", 81, None, False, [])
             for i in range(8)]

    class St:
        def facts_at(self, ch):
            return list(facts)

        def list_promises(self):
            return []

    vol = {"charter": {"chapter_range": [81, 100], "thickens": []}}
    assert_volume_lifetime(St(), vol, 81, 90)


def test_overdue_unpaid_fails_volume_end():
    from scribe3.expand_lifetime import assert_volume_lifetime

    class St:
        def facts_at(self, ch):
            return []

        def list_promises(self):
            return [_p(setup_chapter=70, payoff_min=71, payoff_max=80, status="open",
                       tier="chapter")]

    vol = {"charter": {"chapter_range": [81, 100], "thickens": []}}
    try:
        assert_volume_lifetime(St(), vol, 91, 100)
        raise AssertionError("逾期未收必须抛")
    except ValueError as e:
        assert "逾期" in str(e)


def test_persist_skips_pre_window_payoff():
    from scribe3.tools.expand_wanjie_chapters import persist

    paid = []

    class St:
        def list_volumes(self):
            return [{"id": "v7", "charter": {
                "chapter_range": [121, 140], "pays": [], "holdovers": []}}]

        def list_promises(self):
            return [_p(id="promise:abc123", setup_chapter=121, payoff_min=126,
                       payoff_max=136, tier="arc", status="open")]

        def save_chapter(self, *a, **k):
            return None

        def update_chapter_meta(self, *a, **k):
            return True

        def add_fact(self, *a, **k):
            return None

        def add_knowledge(self, *a, **k):
            return None

        def plant_promise(self, *a, **k):
            return None

        def advance_promise(self, pid, seq):
            paid.append((pid, seq))

        def entity(self, oid):
            return True

        def add_entity(self, *a, **k):
            return None

        def add_faction(self, *a, **k):
            return None

    persist(St(), [{
        "seq": 122, "title": "试", "synopsis": "x" * 40,
        "new_facts": [], "learns": [], "hides": [], "plant": [],
        "payoff": [{"ref": "Labc123", "how": "太早"}],
    }], "v7")
    assert paid == []


def test_assert_volume_end_fails_p1_when_hero_owns_every_chapter():
    from scribe3.expand_lifetime import assert_volume_lifetime
    from scribe3.ontology import Fact

    class St:
        def facts_at(self, ch):
            return [Fact("fact:h", "role:柳岸青", "付温", "半成", 141, None, False, [])]

        def list_promises(self):
            return []

        def chapters_lite(self):
            return [{"seq": i, "focalizer": "role:柳岸青", "plot_action": "买"}
                    for i in range(141, 161)]

    vol = {"charter": {
        "chapter_range": [141, 160], "thickens": [],
        "alt_focalizers": [{"oid": "role:兰因", "why": "她自己揭账"}],
    }}
    try:
        assert_volume_lifetime(St(), vol, 151, 160)
        raise AssertionError("视角独占必须抛")
    except ValueError as e:
        assert "兰因" in str(e)


def test_assert_mid_volume_does_not_throw_p1():
    """P1 是卷规则。前半批还没写到兰因那章，不能在半卷就炸。"""
    from scribe3.expand_lifetime import assert_volume_lifetime
    from scribe3.ontology import Fact

    class St:
        def facts_at(self, ch):
            return [Fact("fact:h", "role:柳岸青", "付温", "半成", 141, None, False, [])]

        def list_promises(self):
            return []

        def chapters_lite(self):
            return [{"seq": i, "focalizer": "role:柳岸青", "plot_action": "买"}
                    for i in range(141, 151)]

    vol = {"charter": {
        "chapter_range": [141, 160], "thickens": [],
        "alt_focalizers": [{"oid": "role:兰因", "why": "她自己揭账"}],
    }}
    assert_volume_lifetime(St(), vol, 141, 150)


def test_plot_action_is_allowed_chapter_meta():
    from scribe3.chapter_meta_codec import CHAPTER_META_ALLOWED

    assert "plot_action" in CHAPTER_META_ALLOWED
