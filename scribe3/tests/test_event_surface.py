"""PR-UX0：时间线事件 label 公式（纯逻辑，无 DB）。"""
from types import SimpleNamespace

from scribe3.event_surface import (
    _first_subj_local,
    format_event_timeline_label,
)


def test_label_prefers_motivated_by_goal():
    ev = SimpleNamespace(
        type="行动",
        motivated_by_goal="焦三掌心铜炉发烫",
        participants={"SUBJ": "role:焦三"},
    )
    label, src = format_event_timeline_label(ev)
    assert src == "goal"
    assert label == "焦三掌心铜炉发烫"
    assert "行动" not in label or "铜炉" in label


def test_label_clips_long_goal():
    long = "甲" * 50
    ev = SimpleNamespace(type="行动", motivated_by_goal=long, participants={})
    label, src = format_event_timeline_label(ev)
    assert src == "goal"
    assert len(label) <= 36
    assert label.endswith("…")


def test_label_composed_from_subj_local_when_no_goal():
    ev = SimpleNamespace(
        type="对峙",
        motivated_by_goal=None,
        participants={"SUBJ": "role:蔺得岷", "OBJ": "role:赵芙南"},
    )
    label, src = format_event_timeline_label(ev)
    assert src == "composed"
    assert label == "蔺得岷 · 对峙"


def test_label_falls_back_to_type():
    ev = SimpleNamespace(type="婚宴", motivated_by_goal="", participants={})
    label, src = format_event_timeline_label(ev)
    assert src == "type"
    assert label == "婚宴"


def test_first_subj_list_slot():
    ev = SimpleNamespace(participants={"SUBJ": ["role:焦三", "role:旁人"]})
    assert _first_subj_local(ev) == "焦三"


def test_dict_ev_shape():
    label, src = format_event_timeline_label({
        "type": "行动",
        "motivated_by_goal": "偷听邪教杀彦青",
        "participants": {"SUBJ": "role:胡不为"},
    })
    assert src == "goal"
    assert "偷听" in label
