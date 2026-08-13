"""P0-1：三燃料接线打 shipped 入口（load → collect → join）。禁止本机 Surreal。"""
from __future__ import annotations

from scribe3.api.services.write_assemble import get_write_soft_fail_counters
from scribe3.api.services.write_assemble_context import (
    _causal_chain_for_write,
    _hybrid_recall_for_write,
    collect_story_fuel_segments,
    load_chapter_story_inputs,
)
from scribe3.context_budget import (
    L0_NEVER_CUT,
    L2_DROP_PRIORITY,
    join_generation_segments,
    ordered_generation_segments,
)
from scribe3.story_constraint_prompt import format_story_fuel_parts


class _Fact:
    def __init__(self, entity_id, attribute, value, secret=False):
        self.entity_id = entity_id
        self.attribute = attribute
        self.value = value
        self.secret = secret


class _Ev:
    def __init__(self, eid, title="开一线"):
        self.id = eid
        self.title = title
        self.effects = [{"k": 1}]


class _Store:
    def __init__(self, *, boom_causal=False, secret=True):
        self.boom_causal = boom_causal
        self.secret = secret

    def get_chapter(self, seq):
        if int(seq) == 4:
            return {"seq": 4, "narrative_drive": {"end_hook": "门外还有脚步"}}
        return {
            "seq": 5,
            "synopsis": "侧门还亮着一盏油灯",
            "narrative_contract": {
                "desire": "灰七要去侧门查昨夜脚印与匙齿",
                "turn": "热灰抵半债并把假片扔给灰狸",
            },
        }

    def hybrid_recall(self, query, chapter, k=5):
        assert query
        assert "脚印" in query or "侧门" in query or "热灰" in query
        return [
            _Fact("role:灰七", "debt", "香债未清", secret=False),
            _Fact("role:冷锅婆", "true_name", "铜炉鬼", secret=self.secret),
        ]

    def events_at(self, seq):
        if int(seq) in (4, 5):
            return [_Ev("ev:i1-0")]
        return []

    def causal_chain(self, eid, direction="backward", max_depth=3):
        if self.boom_causal:
            raise RuntimeError("db down")
        assert not str(eid).startswith("ev:")
        return [{"id": "n1", "seq": 4, "title": "听见咳"}]


def test_fuels_not_in_l0_never_cut():
    for name in ("story_ember", "story_recall", "story_causal"):
        assert name not in L0_NEVER_CUT
    assert L2_DROP_PRIORITY["story_recall"] > L2_DROP_PRIORITY["story_causal"]
    assert L2_DROP_PRIORITY["story_causal"] > L2_DROP_PRIORITY["story_ember"]


def test_load_inputs_and_collect_segments():
    st = _Store()
    inputs = load_chapter_story_inputs(st, 5)
    assert "门外还有脚步" in inputs["prior_consequences"]
    assert "香债未清" in inputs["recall_context"]
    assert "铜炉鬼" not in inputs["recall_context"]
    assert "私密" in inputs["recall_context"]
    assert "听见咳" in inputs["causal_graph"]
    segs = collect_story_fuel_segments(inputs)
    names = [s["name"] for s in segs]
    assert names == ["story_ember", "story_recall", "story_causal"]
    assert all(s["layer"] == "supplemental" for s in segs)
    assert "【上章余烬】" in segs[0]["text"]
    assert "【世界此刻】" in segs[1]["text"]
    assert "【前因后果】" in segs[2]["text"]


def test_join_order_ember_before_drive():
    segs = [
        {"name": "prefix", "layer": "redline", "text": "P"},
        {"name": "event_drive", "layer": "redline", "text": "DRIVE"},
        {"name": "story_ember", "layer": "supplemental", "text": "【上章余烬】\n门外"},
        {"name": "narrative_contract", "layer": "redline", "text": "【本章必须发生的场面】"},
    ]
    ordered = ordered_generation_segments(segs)
    names = [s["name"] for s in ordered]
    assert names.index("narrative_contract") < names.index("story_ember")
    assert names.index("story_ember") < names.index("event_drive")
    joined, _rep = join_generation_segments(segs)
    assert joined.index("【本章必须发生的场面】") < joined.index("【上章余烬】")
    assert joined.index("【上章余烬】") < joined.index("DRIVE")


def test_secret_masked_on_recall_entry():
    text = _hybrid_recall_for_write(_Store(secret=True), 5)
    assert "铜炉鬼" not in text
    assert "私密" in text


def test_causal_fail_records_soft_fail():
    before = get_write_soft_fail_counters().get("empty_story_causal", 0)
    assert _causal_chain_for_write(_Store(boom_causal=True), 5) == ""
    after = get_write_soft_fail_counters().get("empty_story_causal", 0)
    assert after == before + 1


def test_empty_inputs_record_empty_fuels():
    before = dict(get_write_soft_fail_counters())
    segs = collect_story_fuel_segments({})
    assert segs == []
    now = get_write_soft_fail_counters()
    for name in ("empty_story_ember", "empty_story_recall", "empty_story_causal"):
        assert now.get(name, 0) >= before.get(name, 0) + 1


def test_assemble_v1_calls_collect_story_fuel_segments():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "api/services/write_assemble_v1.py"
    text = src.read_text(encoding="utf-8")
    assert "collect_story_fuel_segments(_inputs, work=work)" in text


def test_format_fuel_parts_headers():
    fuel = format_story_fuel_parts(
        prior_consequences="门外脚步",
        recall_context="- role:x.state：可见",
        causal_graph="- 第4章 听见咳",
    )
    assert set(fuel) == {"story_ember", "story_recall", "story_causal"}
