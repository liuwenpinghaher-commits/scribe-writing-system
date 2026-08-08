"""D3/D5：must-link 与作者复述检测（纯逻辑，无 DB）。"""
from __future__ import annotations

from scribe3.memory_must_link import (
    collect_must_anchors,
    detect_author_restated_canon,
    is_minimal_steer,
    minimal_chapter_steer,
    pin_must_first,
)


class _FakeStore:
    def get_chapter(self, seq):
        return {
            "title": "第四章·缺口",
            "synopsis": "覃灰七发现三棱铜匙齿边有缺口，循旧库侧门痕迹。",
            "beats": [{"text": "握匙看缺口"}],
            "focalizer": "role:覃灰七",
        }

    def open_promises(self):
        return [
            {"id": "p1", "setup_chapter": 1, "text": "三棱铜匙与炉心印鉴伪"},
            {"id": "p2", "setup_chapter": 1, "text": "合炉夜还香债"},
        ]

    def facts_at(self, ch):
        from scribe3.ontology import Fact
        return [
            Fact("fact:1", "world:三棱铜匙", "condition", "齿边有缺口", valid_from=3),
            Fact("fact:2", "world:无关", "x", "y", valid_from=1),
        ]

    def characters(self):
        class C:
            def __init__(self, id, name, importance=""):
                self.id, self.name, self.importance = id, name, importance
        return [
            C("role:覃灰七", "覃灰七", "protagonist"),
            C("role:冷锅婆", "冷锅婆", "major"),
        ]


def test_collect_must_anchors_prefers_synopsis_overlap():
    a = collect_must_anchors(_FakeStore(), 4, limit=10)
    texts = " ".join(x["text"] for x in a)
    assert "三棱铜匙" in texts or "缺口" in texts
    assert "开放伏笔" in texts or "鉴伪" in texts
    assert "覃灰七" in texts


def test_detect_restated_when_user_pastes_bible():
    anchors = collect_must_anchors(_FakeStore(), 4)
    msg = (
        "请按已有设定写：覃灰七拿着三棱铜匙，匙上有缺口，还要推进三棱铜匙与炉心印鉴伪，"
        "合炉夜还香债，冷锅婆在侧。设定都在这里了别忘了。"
    )
    r = detect_author_restated_canon(msg, anchors, threshold=0.5)
    assert r["ratio"] >= 0.5
    assert r["restated"] is True or len(r["hit"]) >= 2


def test_detect_not_restated_minimal_intent():
    anchors = collect_must_anchors(_FakeStore(), 4)
    msg = "继续写第四章，压力再紧一点，别解释设定。"
    r = detect_author_restated_canon(msg, anchors, threshold=0.8)
    assert r["restated"] is False


def test_pin_must_first():
    out = pin_must_first(
        ["- world:x a=1", "- other"],
        ["- 〔必需〕world:x a=1", "- 〔必需〕promise"],
    )
    assert out[0].startswith("- 〔必需〕")
    assert len([x for x in out if "world:x a=1" in x]) == 1


def test_minimal_steer_has_no_long_bible():
    s = minimal_chapter_steer(4, "缺口", "覃灰七", "匙坏了要查侧门")
    assert "极简指令" in s
    assert "禁止在指令中复述全书设定" in s
    assert len(s) < 400


def test_is_minimal_steer_env(monkeypatch):
    monkeypatch.setenv("SCRIBE3_MEMORY_STEER_MODE", "minimal")
    assert is_minimal_steer() is True
    monkeypatch.setenv("SCRIBE3_MEMORY_STEER_MODE", "full")
    assert is_minimal_steer() is False


def test_collect_must_anchors_no_chapter_still_has_promises():
    """讨论态无 chapter：仍应钉住开放伏笔与主角。"""
    a = collect_must_anchors(_FakeStore(), None, limit=10, query="铜匙 缺口")
    texts = " ".join(x["text"] for x in a)
    assert "开放伏笔" in texts or "鉴伪" in texts or "香债" in texts
    assert "覃灰七" in texts or "主角" in texts or "三棱" in texts
