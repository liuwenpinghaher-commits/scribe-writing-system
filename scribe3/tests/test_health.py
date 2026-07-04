"""S4 · 体检(cron 调)的 TDD。

把"连贯性=可跑查询"聚合成跨章健康报告:每章 causal_complete,汇总违规。
干净则 [SILENT](cron 只在异常时通知)。设计可扩展(后续加伏笔超期/泄露扫描)。
"""
from scribe3.ontology import Event
from scribe3.health import health_report, render_markdown


def test_health_clean_empty(store):
    rep = health_report(store, up_to=2)
    assert rep.clean
    assert render_markdown(rep) == "[SILENT]"


def test_health_flags_causal_violation(store):
    store.add_event(Event("ev:逃", "逃", story_time=1))   # 无 motivated_by_goal
    rep = health_report(store, up_to=1)
    assert not rep.clean
    assert any(ev == "ev:逃" for _ch, ev, _r in rep.causal_violations)
    md = render_markdown(rep)
    assert md != "[SILENT]" and "ev:逃" in md


def test_max_chapter_helper(store):
    assert store.max_chapter() == 0
    store.add_event(Event("ev:a", "x", story_time=3, motivated_by_goal="g"))
    assert store.max_chapter() == 3


# ============================================================
# 批C · H-1 体检 cron 走 _overdue_flag 单源(审计 H-1)
# ============================================================
def test_health_book_tier_promise_never_overdue(store):
    """H-1: book 级伏笔永不超期,cron 不应误报(此前 setup+SPAN<up_to 恒真)。"""
    store.plant_promise("书级悬念(贯穿全书)", setup_chapter=1, tier="book")
    rep = health_report(store, up_to=50)
    assert not any(p.get("tier") == "book" for p in rep.overdue_promises), \
        "book 级伏笔永不超期,cron 不应误报"


def test_health_red_herring_never_overdue(store):
    """H-1: red_herring 障眼法不判超期(与 /promises、/quality 单源一致)。"""
    store.plant_promise("障眼法线索", setup_chapter=1, kind="red_herring")
    rep = health_report(store, up_to=50)
    assert not any(p.get("kind") == "red_herring" for p in rep.overdue_promises), \
        "red_herring 不应被 cron 判超期"


def test_health_real_overdue_still_flagged(store):
    """H-1 回归:真超期 chapter 级伏笔仍被 cron 标记(与 _overdue_flag 一致)。"""
    store.plant_promise("该收未收的伏笔", setup_chapter=1, tier="chapter")  # pmax=4
    rep = health_report(store, up_to=10)
    assert any("该收未收" in p.get("text", "") for p in rep.overdue_promises), \
        "真超期伏笔仍应被 cron 标记"
