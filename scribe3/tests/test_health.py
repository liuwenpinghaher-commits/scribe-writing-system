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
