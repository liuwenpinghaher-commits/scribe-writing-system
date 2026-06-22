"""S7② · 伏笔/promise 跟踪 + 超期告警(护城河:无竞品自动告警伏笔超期)。

promise=被开启、须闭合的张力。埋下(setup)→ 回收(payoff)。开着超过 N 章未收=超期→体检告警。
"""
from scribe3.health import health_report


def test_plant_and_list(store):
    store.plant_promise("铜炉会反噬", setup_chapter=1)
    store.plant_promise("赵芙南身世存疑", setup_chapter=2, kind="red_herring")
    ps = store.list_promises()
    assert len(ps) == 2
    assert any(p["text"] == "铜炉会反噬" and p["status"] == "open" for p in ps)


def test_advance_closes_promise(store):
    store.plant_promise("铜炉会反噬", setup_chapter=1)
    pid = store.list_promises()[0]["id"]
    store.advance_promise(pid, payoff_chapter=5)
    assert store.open_promises() == []
    c = store.list_promises()[0]
    assert c["status"] == "closed" and c["payoff_chapter"] == 5


def test_health_flags_overdue(store):
    store.plant_promise("超期伏笔", setup_chapter=1)
    rep = health_report(store, up_to=6)         # 1 + 3 < 6 → 超期
    assert any("超期伏笔" in p["text"] for p in rep.overdue_promises)
    assert not rep.clean


def test_recent_promise_not_overdue(store):
    store.plant_promise("新埋伏笔", setup_chapter=5)
    rep = health_report(store, up_to=6)         # 5 + 3 = 8 > 6 → 未超期
    assert rep.overdue_promises == []
