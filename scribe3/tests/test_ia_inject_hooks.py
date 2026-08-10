"""章写作 IA：must-link 去重谓词 + 钩子 SSOT（纯逻辑，无 Surreal）。

驱动真实 shipped 函数：memory_must_link / chapter_hooks / narrative_drive.ensure
在 dry_run + 假 store 上的 compose 路径。
"""
from __future__ import annotations

import os
import types

from scribe3.chapter_hooks import resolve_chapter_hook, last_beat_hook
from scribe3.memory_must_link import (
    build_must_prefix,
    inject_dedup_enabled,
    is_must_link_pin_source,
    must_link_already_pinned_from_items,
)
from scribe3.narrative_drive import ensure_narrative_drive, compose_narrative_drive_dict


class _EmptyStore:
    def get_chapter(self, seq):
        return None

    def open_promises(self):
        return []

    def facts_at(self, ch):
        return []

    def characters(self):
        return []


def test_inject_dedup_default_on(monkeypatch=None):
    os.environ.pop("SCRIBE3_INJECT_DEDUP", None)
    # settings 可能覆盖；强制 env
    os.environ["SCRIBE3_INJECT_DEDUP"] = "1"
    assert inject_dedup_enabled() is True
    os.environ["SCRIBE3_INJECT_DEDUP"] = "0"
    assert inject_dedup_enabled() is False
    os.environ["SCRIBE3_INJECT_DEDUP"] = "1"


def test_pin_predicate_rejects_false_source_kind_must_link():
    """禁止仅用 source_kind==must_link（现网 pin 从不写该 kind）。"""
    assert is_must_link_pin_source({"source_kind": "must_link", "reason": "", "source_id": "x"}) is False
    assert is_must_link_pin_source({
        "source_kind": "canonical",
        "reason": "must_link_priority",
        "source_id": "must_link:header",
    }) is True
    assert is_must_link_pin_source({
        "source_kind": "canonical",
        "reason": "",
        "source_id": "must_link:foo",
    }) is True
    fake = types.SimpleNamespace(
        source_kind="canonical", reason="must_link_priority", source_id="must_link:1",
    )
    assert is_must_link_pin_source(fake) is True


def test_must_link_already_pinned_from_items():
    items = [
        types.SimpleNamespace(
            source=types.SimpleNamespace(
                source_kind="canonical",
                reason="must_link_priority",
                source_id="must_link:header",
            ),
        ),
    ]
    assert must_link_already_pinned_from_items(items) is True
    assert must_link_already_pinned_from_items([]) is False
    assert must_link_already_pinned_from_items([
        {"source_kind": "must_link", "reason": "", "source_id": "other"},
    ]) is False


def test_build_must_prefix_short_circuits_when_pinned():
    os.environ["SCRIBE3_INJECT_DEDUP"] = "1"
    # 即使 store 有锚，pinned+dedup 也应空
    class S(_EmptyStore):
        def get_chapter(self, seq):
            return {"synopsis": "铜匙缺口", "beats": [{"text": "握匙"}]}

        def open_promises(self):
            return [{"id": "p1", "setup_chapter": 1, "text": "铜匙鉴伪"}]

    out = build_must_prefix(S(), 1, must_link_already_pinned=True)
    assert out == ""
    assert "〔压力〕" not in out

    os.environ["SCRIBE3_INJECT_DEDUP"] = "0"
    dual = build_must_prefix(S(), 1, must_link_already_pinned=True)
    # DEDUP=0 时忽略 pinned，可恢复前缀（有锚则非空）
    assert isinstance(dual, str)
    os.environ["SCRIBE3_INJECT_DEDUP"] = "1"


def test_resolve_chapter_hook_priority():
    ch = {
        "beats_meta": {"chapter_hook": "元钩子优先"},
        "beats": [{"hook": "末拍钩"}, {"text": "x"}],
        "synopsis": "钩子：大纲钩",
    }
    assert resolve_chapter_hook(ch) == "元钩子优先"

    ch2 = {
        "beats_meta": {},
        "beats": [{"text": "a"}, {"hook": "  末拍钩  "}],
        "synopsis": "钩子：大纲钩",
    }
    assert resolve_chapter_hook(ch2) == "末拍钩"

    ch3 = {
        "beats_meta": {},
        "beats": [{"text": "only"}],
        "synopsis": "",
    }
    assert resolve_chapter_hook(ch3, synopsis_meta={"hook": "大纲钩"}) == "大纲钩"

    ch4 = {"beats_meta": {}, "beats": []}
    assert resolve_chapter_hook(ch4, prev_end_hook="上章钩") == "上章钩"

    assert last_beat_hook([{"hook": ""}, {"hook": "L"}]) == "L"


def test_ensure_end_hook_uses_beats_meta_not_only_synopsis():
    """ensure dry_run：end_hook 跟 chapter_hook 链，而非仅 synopsis parse。

    旗关时 ensure 返回 None——本测临时打开 narrative_engine 旗。
    """
    import scribe3.novel_quality_flags as nqf
    prev = getattr(nqf, "narrative_engine_enabled", None)

    class Store:
        def __init__(self):
            self._ch = {
                "seq": 3,
                "synopsis": "普通梗概无钩标签",
                "beats": [
                    {"text": "拍一", "goal": "进门", "conflict": "拒", "turn": "破", "cost": "血"},
                    {"text": "拍二", "hook": "门缝里的铜匙齿"},
                ],
                "beats_meta": {"chapter_hook": "章末：铜匙齿边缺口"},
                "focalizer": "",
                "narrative_drive": {},
            }

        def get_chapter(self, seq):
            return dict(self._ch)

        def update_chapter_meta(self, seq, patch):
            self._ch.update(patch or {})

        def open_promises(self):
            return []

        def overdue_promises(self, *a, **k):
            return []

        def list_events(self, *a, **k):
            return []

        def facts_at(self, *a, **k):
            return []

        def characters(self):
            return []

        def get_purpose(self, *a, **k):
            return None

    # patch flag on for this call
    nqf.narrative_engine_enabled = lambda: True  # type: ignore
    try:
        st = Store()
        drive = ensure_narrative_drive(st, 3, force=True, dry_run=True)
        assert isinstance(drive, dict), f"got {drive!r}"
        assert drive.get("end_hook") == "章末：铜匙齿边缺口"
    finally:
        if prev is not None:
            nqf.narrative_engine_enabled = prev



def test_compose_then_resolve_override_aligns():
    meta = {"stakes": "若失败则人亡", "hook": "synopsis钩", "pressure": 5, "role": "高压"}
    drive = compose_narrative_drive_dict(meta, {}, prev_hook="", synopsis="x")
    ch = {
        "beats_meta": {"chapter_hook": "beats_meta钩"},
        "beats": [],
        "synopsis": "x",
    }
    h = resolve_chapter_hook(ch, synopsis_meta=meta)
    assert h == "beats_meta钩"
    drive["end_hook"] = h
    assert drive["end_hook"] == "beats_meta钩"
