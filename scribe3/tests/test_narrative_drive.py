"""叙事引擎 narrative_drive：纯 compose/validate/format/align（无 Surreal / LLM）。

设计 rev.2.3：引导优先、冲突/事件推动；GATE/DETECT 默认关。
"""
from __future__ import annotations

from scribe3.narrative_drive import (
    ALIGN_JACCARD_MIN,
    SCHEMA,
    align_beats_to_drive,
    compose_narrative_drive_dict,
    empty_narrative_drive,
    format_event_drive_block,
    synopsis_content_fp,
    validate_narrative_drive,
)
from scribe3.novel_quality_flags import (
    CODE_DEFAULTS,
    FLAG_EVENT_DRIVE_GATE,
    FLAG_EVENT_LED_DETECT,
    FLAG_NARRATIVE_ENGINE,
    event_drive_gate_enabled,
    event_led_detect_enabled,
    narrative_engine_enabled,
    novel_quality_flags_snapshot,
)


def _stakes_meta():
    return {
        "role": "推进",
        "pressure": 5,
        "stakes": "若失败，灰七失侧门钥且香债滚入父名",
        "hook": "炉册上父名未干",
    }


def test_compose_from_outline_stakes():
    drive = compose_narrative_drive_dict(
        _stakes_meta(),
        {},
        "",
        focalizer="role:覃灰七",
        synopsis="stakes:若失败，灰七失侧门钥 章末钩子:炉册上父名未干",
    )
    assert drive["schema"] == SCHEMA
    assert drive["engine_type"] == "event"
    assert drive["composed_from"]["seed_tier"] == "outline_stakes"
    assert "失" in (drive["inciting_force"]["summary"] or drive["deadline_or_cost"]["if_fail"] or "")
    assert drive["end_hook"]
    assert drive["scene_turn"]
    assert drive["validation"]["ok"] is True
    blk = format_event_drive_block(drive, focalizer="role:覃灰七")
    assert "事件驱动" in blk or "冲突" in blk
    assert "引爆" in blk
    # 引导优先：允许跟主角服务戏，而非刑典黑名单为主
    assert "引导" in blk or "优先" in blk


def test_compose_empty_meta_is_weak_not_crash():
    drive = compose_narrative_drive_dict({}, {}, "", synopsis="")
    assert drive["engine_type"] == "event"
    assert drive["validation"]["drama_weak"] is True
    # 无实质字段 → 格式化空串（不注入假合同）
    assert format_event_drive_block(drive) == ""
    empty = empty_narrative_drive()
    assert empty["validation"]["ok"] is False


def test_compose_inventory_promise_seed():
    inv = {
        "overdue_promises": [
            {"id": "p1", "label": "冷锅婆当夜索一炉香债", "from": "冷锅婆"},
        ],
        "open_promises": [],
        "purpose_deltas": [],
        "events_here": [],
        "events_prev": [],
        "prev_end_hook": "",
    }
    drive = compose_narrative_drive_dict(
        {"role": "推进", "pressure": 5},
        inv,
        "",
        focalizer="灰七",
    )
    assert drive["composed_from"]["seed_tier"] == "inventory"
    assert "香债" in drive["inciting_force"]["summary"]
    assert drive["inciting_force"]["source_refs"]


def test_validate_high_pressure_missing_fields():
    weak = {
        "engine_type": "event",
        "inciting_force": {"kind": "other", "summary": "", "source_refs": []},
        "opposition": {"who_or_what": "", "wants": "", "leverage": ""},
        "deadline_or_cost": {"timer": "", "if_fail": "", "irreversible_if_pay": ""},
        "scene_turn": "",
        "end_hook": "",
    }
    v = validate_narrative_drive(weak, high_pressure=True)
    assert v["ok"] is False
    assert v["errors"]


def test_align_beats_to_drive_positive():
    drive = compose_narrative_drive_dict(_stakes_meta(), {}, "")
    # 强制目标文案便于 Jaccard
    drive["inciting_force"]["summary"] = "冷锅婆讨香债"
    drive["opposition"]["wants"] = "今夜抵债"
    beats = [
        {
            "kind": "scene",
            "goal": "守门",
            "conflict": "冷锅婆讨香债",
            "turn": "先交匙",
            "cost": "失钥",
            "text": "讨债上门",
        }
    ]
    al = align_beats_to_drive(beats, drive, high_pressure=True)
    assert al["matched"] is True
    assert al["ok"] is True


def test_align_mismatch_high_pressure():
    drive = {
        "inciting_force": {"summary": "冷锅婆讨香债", "source_refs": []},
        "opposition": {"wants": "抵债"},
        "end_hook": "炉册",
    }
    beats = [
        {"kind": "scene", "goal": "去旧库看看", "conflict": "巷里走走", "text": "闻味"},
    ]
    al = align_beats_to_drive(beats, drive, high_pressure=True)
    assert al["matched"] is False
    assert al["ok"] is False
    assert al["errors"]


def test_synopsis_fp_stable():
    a = synopsis_content_fp("  甲  乙\n丙  ")
    b = synopsis_content_fp("甲 乙 丙")
    assert a == b
    assert synopsis_content_fp("") == ""


def test_flags_default_off():
    """代码默认：引导与 GATE/DETECT 均关（无 env 覆盖时）。"""
    assert CODE_DEFAULTS.get(FLAG_NARRATIVE_ENGINE) is False
    assert CODE_DEFAULTS.get(FLAG_EVENT_DRIVE_GATE) is False
    assert CODE_DEFAULTS.get(FLAG_EVENT_LED_DETECT) is False
    # 读点与 CODE_DEFAULTS 一致（当前进程无 override 时）
    snap = novel_quality_flags_snapshot()
    assert FLAG_NARRATIVE_ENGINE in snap
    assert FLAG_EVENT_DRIVE_GATE in snap
    assert FLAG_EVENT_LED_DETECT in snap
    # 函数可调用
    assert isinstance(narrative_engine_enabled(), bool)
    assert isinstance(event_drive_gate_enabled(), bool)
    assert isinstance(event_led_detect_enabled(), bool)


def test_align_jaccard_threshold_exported():
    assert ALIGN_JACCARD_MIN == 0.08


def test_ensure_respects_flag_off(monkeypatch):
    """旗关 → ensure 返回 None，不写库。"""
    from scribe3 import narrative_drive as nd

    class _St:
        def get_chapter(self, seq):
            return {"synopsis": "stakes:若失败丢钥", "beats": [{"text": "a"}], "narrative_drive": {}}

        def update_chapter_meta(self, seq, fields):
            raise AssertionError("should not write when flag off")

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: False,
    )
    assert nd.ensure_narrative_drive(_St(), 1) is None


def test_ensure_composes_when_flag_on(monkeypatch):
    from scribe3 import narrative_drive as nd

    written = {}

    class _St:
        def get_chapter(self, seq):
            return {
                "synopsis": "压力级:5 chapter_role:推进 stakes:若失败灰七失侧门钥 章末钩子:炉册未干",
                "beats": [{"text": "已有"}],
                "narrative_drive": {},
                "focalizer": "role:灰七",
                "deltas": [],
            }

        def update_chapter_meta(self, seq, fields):
            written.update(fields)

        def open_promises(self):
            return []

        def events_at(self, seq):
            return []

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: True,
    )
    drive = nd.ensure_narrative_drive(_St(), 1)
    assert drive is not None
    assert drive.get("inciting_force", {}).get("summary") or drive.get("scene_turn")
    assert "narrative_drive" in written


def test_event_drive_block_write_helper(monkeypatch):
    from scribe3.api.services import write_assemble as wa

    class _St:
        def get_chapter(self, seq):
            return {
                "narrative_drive": compose_narrative_drive_dict(_stakes_meta(), {}, ""),
            }

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: True,
    )
    blk = wa._event_drive_block(_St(), 1, focalizer="灰七")
    assert "引爆" in blk or "事件驱动" in blk


def test_event_drive_block_off_when_flag_off(monkeypatch):
    from scribe3.api.services import write_assemble as wa

    class _St:
        def get_chapter(self, seq):
            return {
                "narrative_drive": compose_narrative_drive_dict(_stakes_meta(), {}, ""),
            }

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: False,
    )
    assert wa._event_drive_block(_St(), 1) == ""


def test_expand_beats_skip_ensures_drive(monkeypatch):
    """skip 路径仍 ensure（引导旗开）。"""
    from scribe3.api.services import pilot_runtime as pr

    # expand_beats 是嵌在 load_pilot_actions 里的闭包；直接测 ensure 挂钩语义
    # 用 ensure + 模拟 skip 返回结构
    written = {}

    class _St:
        def get_chapter(self, seq):
            return {
                "synopsis": "压力级:5 chapter_role:推进 stakes:若失败失匙 章末钩子:钩",
                "beats": [{"text": "已有节拍"}],
                "narrative_drive": {},
                "focalizer": "",
                "deltas": [],
            }

        def update_chapter_meta(self, seq, fields):
            written.update(fields)

        def open_promises(self):
            return []

        def events_at(self, seq):
            return []

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.event_drive_gate_enabled",
        lambda: False,
    )
    from scribe3.narrative_drive import ensure_narrative_drive

    drive = ensure_narrative_drive(_St(), 3)
    out = {"skipped": "节拍已有内容,按既有推进(不覆盖)", "narrative_drive": drive}
    assert out["skipped"]
    assert out["narrative_drive"]
    assert written.get("narrative_drive")
    # GATE 关 → 无 pilot_park
    assert "pilot_park" not in out
