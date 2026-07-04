"""北极星方案任务2 · causal_directives 因果欠账进 brief TDD。

蓝图 §3-②:上文 causal_complete 违规转译成下一章 brief 的三选一软指令
(补交代/转悬念/标记抽取误报);top-5 硬上限防塞爆 brief;no_event_data
整段不渲染(沿用 /causal 假绿防护语义);violation 可能是抽取漏而非叙事漏,
必须留"抽取误报"出口,绝不做硬约束。
"""
from scribe3.brief import assemble_chapter_brief, causal_directives, render_brief
from scribe3.ontology import Event


def _v(ch: int, eid: str, reason: str = "missing motivated_by_goal") -> dict:
    return {"chapter": ch, "event_id": eid, "reason": reason}


def test_causal_directives_top5_and_overflow():
    """7 条违规 → 只出 5 条指令,overflow=2,total=7;措辞含三选一与误报出口。"""
    viols = [_v(4, f"event:e{i}") for i in range(7)]
    out = causal_directives(viols, no_event_data=False)
    assert len(out["directives"]) == 5
    assert out["overflow"] == 2 and out["total"] == 7
    d = out["directives"][0]
    assert "三选一" in d and "悬念" in d and "抽取误报" in d


def test_causal_directives_no_event_data_renders_nothing():
    """no_event_data=True → 整段空(没数据≠没欠账,不出假指令)。"""
    out = causal_directives([_v(1, "event:x")], no_event_data=True)
    assert out == {"directives": [], "overflow": 0, "total": 0}


def test_causal_directives_empty_violations():
    out = causal_directives([], no_event_data=False)
    assert out == {"directives": [], "overflow": 0, "total": 0}


def test_causal_directives_reason_wording_and_recency_order():
    """缺动机/缺因果入边措辞分型;跨章违规按章序倒序取最近。"""
    viols = [_v(2, "event:老账", "missing causal_in (非首事件须有因果入边)"),
             _v(5, "event:新账", "missing motivated_by_goal")]
    out = causal_directives(viols, no_event_data=False)
    assert "缺动机" in out["directives"][0] and "event:新账" in out["directives"][0], \
        "最近章的违规应排最前"
    assert "缺因果入边" in out["directives"][1]
    assert "第5章" in out["directives"][0] and "第2章" in out["directives"][1]


def test_render_brief_causal_section_with_overflow_note():
    sections = {"arcs": [], "promises": {}, "loops": {}, "heartbeat": [],
                "stale": {}, "causal": {"directives": ["上文第4章事件「event:e0」缺动机:本章三选一——…"],
                                        "overflow": 3, "total": 8}}
    txt = render_brief(sections)
    assert "【因果欠账·三选一】" in txt
    assert "3 条" in txt, "溢出量应注记(超出部分只落面板不进 brief)"


def test_render_brief_causal_section_absent_when_empty():
    sections = {"arcs": [], "promises": {}, "loops": {}, "heartbeat": [],
                "stale": {}, "causal": {"directives": [], "overflow": 0, "total": 0}}
    assert "因果欠账" not in render_brief(sections)


def test_assemble_brief_wires_causal_from_store(store):
    """集成:上一章种一条缺动机事件 → 写第2章的 brief 含催收指令。"""
    store.add_event(Event(id="ev:清净", type="法事", story_time=1,
                          motivated_by_goal="goal:安魂", causal_in=[]))
    store.add_event(Event(id="ev:失窃", type="失窃", story_time=1,
                          motivated_by_goal=None, causal_in=[]))
    out = assemble_chapter_brief(store, seq=2)
    ca = out["sections"]["causal"]
    assert ca["total"] >= 1
    assert any("失窃" in d and "缺动机" in d for d in ca["directives"])
    assert "【因果欠账·三选一】" in out["text"]


def test_assemble_brief_causal_empty_without_events(store):
    """集成:全窗口无事件 → no_event_data 语义,段不渲染。"""
    out = assemble_chapter_brief(store, seq=2)
    assert out["sections"]["causal"] == {"directives": [], "overflow": 0, "total": 0}
    assert "因果欠账" not in out["text"]
