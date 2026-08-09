"""弧光派生信号纯函数 + pulse/brief 接线(无 Surreal)。"""
from __future__ import annotations

from types import SimpleNamespace

import scribe3.arc_signals as AS
import scribe3.pulse as P
from scribe3.brief import arc_directive, heartbeat_list


def test_normalize_and_main_cast_includes_major():
    assert AS.is_main_cast_importance("major")
    assert AS.is_main_cast_importance("主要角色")
    assert AS.is_main_cast_importance("protagonist")
    assert AS.is_main_cast_importance("主角")
    assert not AS.is_main_cast_importance("minor")
    assert not AS.is_main_cast_importance("extra")
    assert not AS.is_main_cast_importance("background")
    assert AS.normalize_importance_for_arc("主要角色") == "major"


def test_eligible_with_lie_or_main_cast():
    char = SimpleNamespace(id="role:甲", name="甲", traits={"importance": "major"})
    assert AS.is_arc_eligible(char, {}) is True
    assert AS.is_arc_eligible(char, {"lie": "  "}) is True  # still major
    assert AS.is_arc_eligible(
        SimpleNamespace(id="role:乙", name="乙", traits={"importance": "minor"}),
        {},
    ) is False
    assert AS.is_arc_eligible(
        SimpleNamespace(id="role:丙", name="丙", traits={"importance": "extra"}),
        {"lie": "钱能摆平一切"},
    ) is True


def test_miss_belief_directed_by_arc_type():
    # positive: belief should fall; still high → miss
    assert AS.miss_belief(80, 50, "positive", slack=15) is True
    assert AS.miss_belief(55, 50, "positive", slack=15) is False
    # fall: should rise; still low → miss
    assert AS.miss_belief(20, 50, "fall", slack=15) is True
    assert AS.miss_belief(40, 50, "fall", slack=15) is False
    # flat: abs
    assert AS.miss_belief(70, 50, "flat", slack=15) is True
    assert AS.miss_belief(60, 50, None, slack=15) is False
    assert AS.miss_belief(None, 50, "positive") is False
    assert AS.miss_belief(80, None, "positive") is False


def test_arc_beat_focus_single_overdue_and_boundaries():
    plan = [
        {"id": "b1", "beat_name": "mid", "target_chapter": 3, "lie_belief_target": 50},
        {"id": "b2", "beat_name": "climax", "target_chapter": 8, "lie_belief_target": 20},
    ]
    # target == next_ch → due
    f = AS.arc_beat_focus(plan, belief=70, next_ch=3, arc_type="disillusionment")
    assert f and f["status"] == "due" and f["beat_name"] == "mid"
    # target == next_ch-1 and miss → overdue_miss
    f2 = AS.arc_beat_focus(plan, belief=80, next_ch=4, arc_type="disillusionment")
    assert f2 and f2["status"] == "overdue_miss" and f2["beat_name"] == "mid"
    # unmeasured
    f3 = AS.arc_beat_focus(plan, belief=None, next_ch=4, arc_type="positive")
    assert f3 and f3["status"] == "overdue_unmeasured"
    # approaching next beat after pass
    f4 = AS.arc_beat_focus(plan, belief=40, next_ch=4, arc_type="disillusionment")
    assert f4 and f4["beat_name"] == "climax"
    # empty plan
    assert AS.arc_beat_focus([], belief=50, next_ch=5) is None
    # all passed
    f5 = AS.arc_beat_focus(plan, belief=10, next_ch=10, arc_type="disillusionment")
    assert f5 is None


def test_partition_empty_and_cold_start():
    chars = [
        SimpleNamespace(id="role:路人", name="路人", traits={"importance": "extra"}),
        SimpleNamespace(id="role:主角", name="主角", traits={"importance": "major"}),
    ]
    anchors = {
        "role:路人": {},
        "role:主角": {},
    }
    p = AS.partition_arc_chars(chars, anchors)
    assert len(p["with_lie"]) == 0
    assert len(p["eligible_no_lie"]) == 1
    assert p["eligible_no_lie"][0]["name"] == "主角"
    assert len(p["dormant"]) == 1


def test_directive_focus_driven_no_contradiction_on_overdue():
    anchors = {"lie": "官法大过阴律", "arc_type": "disillusionment"}
    plan = [
        {"id": "b1", "beat_name": "中点动摇", "target_chapter": 2, "lie_belief_target": 40},
    ]
    text = arc_directive("柳怀玉", anchors, plan, lie_belief=90, next_ch=5)
    assert "中点动摇" in text
    assert "逾期" in text or "已过" in text
    # must not sound like everything is fine marching to next beat only
    assert "朝下一拍缓移" not in text or "逾期" in text


def test_format_beat_decision_names_tools():
    focus = {
        "beat_name": "中点",
        "target_chapter": 3,
        "current_belief": 80,
        "target": 40,
        "status": "overdue_miss",
    }
    msg = AS.format_beat_decision("甲", focus, tools=True)
    assert "s3_add_char_state" in msg
    assert "s3_add_arc_beat" in msg
    assert "s3_set_char_anchors" in msg


def test_heartbeat_never_active_can_activate():
    chars = [{"name": "白姑", "private_agenda": "制炉", "last_active": None}]
    out = heartbeat_list(chars, next_ch=5, gap=3)
    assert len(out) == 1
    assert out[0]["name"] == "白姑"


class _FakeStore:
    """Minimal store for pulse._arc_dim / chapter_pulse without Surreal."""

    def __init__(self, chars=None, anchors=None, plans=None, beliefs=None, jumps=None):
        self._chars = chars or []
        self._anchors = anchors or {}
        self._plans = plans or {}
        self._beliefs = beliefs or {}
        self._jumps = jumps or []
        self.db_name = "test"

    def characters(self):
        return self._chars

    def char_anchors(self, cid):
        return dict(self._anchors.get(cid) or {})

    def list_arc_plan(self, cid):
        return list(self._plans.get(cid) or [])

    def latest_lie_belief(self, cid, upto):
        return self._beliefs.get(cid)

    def lie_belief_jumps(self, threshold=15):
        return list(self._jumps)

    def get_intent(self):
        return {}

    def promises_with_lifecycle(self, max_chapter=None):
        return []

    def list_relation_touches(self):
        return []

    def chapters_lite(self):
        return []

    def causal_debt_total(self):
        return 0

    def _query(self, *a, **k):
        return []


def test_pulse_empty_cast_no_false_green():
    st = _FakeStore(chars=[])
    d = P._arc_dim(st, 3)
    assert d["dimension"] == "arc"
    assert d.get("degraded") is not True
    msgs = " ".join(it["message"] for it in d["items"])
    assert "未见跳变" not in msgs
    assert "未启用" in msgs or "可忽略" in msgs
    assert d["severity"] == "info"


def test_pulse_main_missing_lie_decision_no_degraded():
    chars = [SimpleNamespace(id="role:主角", name="主角", traits={"importance": "major"})]
    st = _FakeStore(chars=chars, anchors={"role:主角": {}})
    d = P._arc_dim(st, 2)
    assert d.get("degraded") is not True
    assert d["severity"] == "decision"
    msgs = " ".join(it["message"] for it in d["items"])
    assert "Lie" in msgs or "错误信念" in msgs
    assert "未见跳变" not in msgs


def test_pulse_overdue_miss_single_decision_with_tools():
    chars = [SimpleNamespace(id="role:甲", name="甲", traits={"importance": "major"})]
    st = _FakeStore(
        chars=chars,
        anchors={"role:甲": {"lie": "钱能摆平", "arc_type": "positive"}},
        plans={"role:甲": [
            {"id": "b1", "beat_name": "动摇", "target_chapter": 2, "lie_belief_target": 40},
        ]},
        beliefs={"role:甲": 90},
    )
    d = P._arc_dim(st, 5)
    assert d.get("degraded") is not True
    assert d["severity"] == "decision"
    decisions = [it for it in d["items"] if it["severity"] == "decision"]
    # one focus decision for the char (not storm)
    assert len(decisions) >= 1
    assert any("s3_add_char_state" in it["message"] for it in decisions)
    assert any("动摇" in it["message"] for it in decisions)


def test_pulse_with_samples_healthy_message():
    chars = [SimpleNamespace(id="role:甲", name="甲", traits={})]
    st = _FakeStore(
        chars=chars,
        anchors={"role:甲": {"lie": "X", "arc_type": "flat"}},
        beliefs={"role:甲": 50},
        plans={"role:甲": []},
    )
    d = P._arc_dim(st, 3)
    assert d["severity"] == "info"
    msgs = " ".join(it["message"] for it in d["items"])
    assert "平稳" in msgs or "已采样" in msgs
    assert "未见跳变" not in msgs


def test_tracking_off():
    assert AS.is_arc_tracking_off({"arc_tracking": "off"}) is True
    assert AS.is_arc_tracking_off({"arc_tracking": "on"}) is False
    assert AS.is_arc_tracking_off(None) is False
    assert AS.is_arc_tracking_off("off") is True


def test_pulse_arc_tracking_off_short_circuit():
    """intent.arc_tracking=off → 固定静音 info，不扫 eligible。"""
    chars = [SimpleNamespace(id="role:主角", name="主角", traits={"importance": "major"})]
    st = _FakeStore(chars=chars, anchors={"role:主角": {}})
    st.get_intent = lambda: {"arc_tracking": "off"}  # type: ignore
    d = P._arc_dim(st, 2)
    assert d.get("degraded") is not True
    assert d["severity"] == "info"
    assert "关闭" in d["items"][0]["message"] or "追踪" in d["items"][0]["message"]


def test_slack_constant():
    assert AS.ARC_BELIEF_SLACK == 15
    assert P._ARC_JUMP_MAX == 15


def test_migration_115_arc_tracking_exists():
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "migrations" / "115_intent_arc_tracking.surql"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "arc_tracking" in text
    assert "intent" in text
