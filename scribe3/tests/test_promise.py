"""S7② · 伏笔/promise 跟踪 + 超期告警 + 生命周期(plant id / abandon / touch / timeline)。

promise=被开启、须闭合的张力。埋下(setup)→ 推进(touch/clue)→ 回收(payoff)或弃置(abandoned)。
"""
from scribe3.health import health_report
from scribe3.verify_craft_compliance import gate_a


def test_plant_and_list(store):
    store.plant_promise("铜炉会反噬", setup_chapter=1)
    store.plant_promise("赵芙南身世存疑", setup_chapter=2, kind="red_herring")
    ps = store.list_promises()
    assert len(ps) == 2
    assert any(p["text"] == "铜炉会反噬" and p["status"] == "open" for p in ps)


def test_plant_returns_stable_id(store):
    """plant_promise 必须返回稳定 id,可供 advance/touch 直接使用(不扫全表猜)。"""
    planted = store.plant_promise("灰契会反噬立契人", setup_chapter=1, tier="chapter")
    assert isinstance(planted, dict)
    assert planted.get("id"), planted
    pid = planted["id"]
    got = store.get_promise(pid)
    assert got is not None
    assert got["text"] == "灰契会反噬立契人"
    assert got["status"] == "open"
    assert got["payoff_min"] == 2 and got["payoff_max"] == 4


def test_advance_closes_promise(store):
    planted = store.plant_promise("铜炉会反噬", setup_chapter=1)
    pid = planted["id"]
    store.advance_promise(pid, payoff_chapter=5)
    assert store.open_promises() == []
    c = store.get_promise(pid)
    assert c["status"] == "closed" and c["payoff_chapter"] == 5


def test_abandon_removes_from_open_and_a6(store):
    """abandoned 是一等结案:不进 open_promises / effective_open / GATE-A。"""
    # 先铺最低 GATE-A 辅信(intent 等由 conftest/其它测处理时可能为空——只测 open 过滤)
    a = store.plant_promise("要弃的伏笔", setup_chapter=1)
    b = store.plant_promise("还开着的", setup_chapter=1)
    assert len(store.open_promises()) == 2
    assert store.abandon_promise(a["id"]) is True
    opens = store.open_promises()
    assert len(opens) == 1 and opens[0]["id"] == b["id"]
    abandoned = store.get_promise(a["id"])
    assert abandoned["status"] == "abandoned"
    # effective_open 不含 abandoned
    eff = store.effective_open_promises()
    assert all(p["id"] != a["id"] for p in eff)
    # ledger 独立栏
    led = store.promise_ledger(slack=3)
    assert any(r["id"] == a["id"] for r in led.get("abandoned") or [])
    assert all(r["id"] != a["id"] for r in led.get("open") or [])


def test_mark_herring_not_abandoned(store):
    """障眼法是 kind,不是 abandoned status。"""
    p = store.plant_promise("假线索", setup_chapter=1)
    assert store.mark_promise_herring(p["id"]) is True
    row = store.get_promise(p["id"])
    assert row["kind"] == "red_herring"
    assert row["status"] == "open"  # 仍 open,但非有效欠账
    assert p["id"] not in {x["id"] for x in store.effective_open_promises()}
    led = store.promise_ledger(slack=3)
    assert any(r["id"] == p["id"] for r in led.get("red_herring") or [])
    assert not any(r["id"] == p["id"] for r in led.get("abandoned") or [])


def test_patch_tier_recomputes_window(store):
    """改 tier 且未显式给窗口 → update_promise 重算 payoff_min/max。"""
    p = store.plant_promise("近场", setup_chapter=2, tier="chapter")
    assert p["payoff_min"] == 3 and p["payoff_max"] == 5
    ok = store.update_promise(p["id"], {"tier": "arc", "resolution": "答案在第十七章"})
    assert ok is True
    row = store.get_promise(p["id"])
    assert row["tier"] == "arc"
    assert row["payoff_min"] == 7 and row["payoff_max"] == 17  # 2+5 .. 2+15


def test_manual_touch_updates_lifecycle_refresh(store):
    p = store.plant_promise("要推进", setup_chapter=1)
    store.add_promise_touch(p["id"], chapter=2, evidence="腕印发烫")
    life = store.promises_with_lifecycle(max_chapter=2)
    row = next(x for x in life if x["id"] == p["id"])
    assert row["refresh_count"] >= 1
    assert row["last_refresh_at"] == 2


def test_clue_writes_refresh_touch(store):
    """clue ≡ soft touch:add_promise_clue 必须同步 promise_touch。"""
    p = store.plant_promise("草蛇", setup_chapter=1)
    store.add_promise_clue(p["id"], note="灰印一闪", chapter=2)
    clues = store.get_promise(p["id"])["clues"]
    assert any(c.get("note") == "灰印一闪" for c in clues)
    touches = store.list_promise_touches(p["id"])
    assert any(t.get("chapter") == 2 and "灰印" in (t.get("evidence") or "") for t in touches)
    life = next(x for x in store.promises_with_lifecycle(max_chapter=2) if x["id"] == p["id"])
    assert life["refresh_count"] >= 1 and life["last_refresh_at"] == 2


def test_promise_timeline_orders_events(store):
    p = store.plant_promise("时间线测", setup_chapter=1)
    store.add_promise_clue(p["id"], note="中途暗示", chapter=2)
    store.advance_promise(p["id"], payoff_chapter=4)
    tl = store.promise_timeline(p["id"])
    assert tl is not None
    kinds = [e["kind"] for e in tl["events"]]
    assert "plant" in kinds
    assert "clue" in kinds or "touch" in kinds
    assert "closed" in kinds
    chapters = [e["chapter"] for e in tl["events"]]
    assert chapters == sorted(chapters)


def test_abandoned_timeline_event(store):
    p = store.plant_promise("弃置测", setup_chapter=1)
    store.abandon_promise(p["id"])
    tl = store.promise_timeline(p["id"])
    assert any(e["kind"] == "abandoned" for e in tl["events"])


def test_health_flags_overdue(store):
    store.plant_promise("超期伏笔", setup_chapter=1)
    rep = health_report(store, up_to=6)         # 1 + 3 < 6 → 超期
    assert any("超期伏笔" in p["text"] for p in rep.overdue_promises)
    assert not rep.clean


def test_recent_promise_not_overdue(store):
    store.plant_promise("新埋伏笔", setup_chapter=5)
    rep = health_report(store, up_to=6)         # 5 + 3 = 8 > 6 → 未超期
    assert rep.overdue_promises == []


def test_abandoned_not_overdue_in_health(store):
    planted = store.plant_promise("本会超期但已弃", setup_chapter=1)
    store.abandon_promise(planted["id"])
    rep = health_report(store, up_to=10)
    assert not any("本会超期" in (x.get("text") or "") for x in rep.overdue_promises)
