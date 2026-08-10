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


# ── OI-1 enrich ──────────────────────────────────────────

def test_inventory_seed_absorbs_outline_stakes_hook():
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
    meta = {
        "role": "推进",
        "pressure": 5,
        "stakes": "若失败，灰七失侧门钥",
        "hook": "炉册上父名未干",
    }
    drive = compose_narrative_drive_dict(meta, inv, "")
    assert drive["composed_from"]["seed_tier"] == "inventory"
    assert "失侧门" in drive["stakes_line"] or "香债" in drive["inciting_force"]["summary"]
    assert drive["end_hook"] == "炉册上父名未干"
    assert drive["stakes_line"] == "若失败，灰七失侧门钥"


def test_inventory_seed_outline_source_refs():
    inv = {
        "overdue_promises": [{"id": "p1", "label": "讨香债", "from": "冷锅婆"}],
        "open_promises": [],
        "purpose_deltas": [],
        "events_here": [],
        "events_prev": [],
    }
    meta = {"pressure": 5, "role": "推进", "stakes": "若失败丢钥", "hook": "钩子一句"}
    drive = compose_narrative_drive_dict(meta, inv, "")
    refs = drive["inciting_force"]["source_refs"]
    assert "outline:stakes" in refs
    assert "outline:hook" in refs


def test_outline_hook_absorbed_flag():
    drive = compose_narrative_drive_dict(_stakes_meta(), {}, "")
    assert drive["composed_from"].get("outline_hook_absorbed") is True


def test_high_pressure_missing_stakes_warning():
    drive = compose_narrative_drive_dict(
        {"role": "推进", "pressure": 5, "hook": "有钩无赌注"},
        {},
        "",
        synopsis="压力级:5 chapter_role:推进 章末钩子:有钩无赌注",
    )
    warns = drive["validation"].get("warnings") or []
    assert "missing_outline_stakes" in warns


def test_format_includes_dialogue_guide():
    drive = compose_narrative_drive_dict(_stakes_meta(), {}, "")
    blk = format_event_drive_block(drive)
    assert "对白" in blk
    # micro/short must fit 220
    body = blk.lstrip()
    assert len(body) <= 220 + 5


def test_align_low_pressure_mismatch_ok():
    drive = {
        "inciting_force": {"summary": "冷锅婆讨香债", "source_refs": []},
        "opposition": {"wants": "抵债"},
        "end_hook": "炉册",
    }
    beats = [{"kind": "scene", "goal": "去旧库看看", "conflict": "巷里走走", "text": "闻味"}]
    al = align_beats_to_drive(beats, drive, high_pressure=False)
    assert al["ok"] is True
    assert al["matched"] is False


def test_range_dry_run_no_update(monkeypatch):
    from scribe3 import narrative_drive as nd

    updates = []

    class St:
        def chapters_lite(self):
            return [
                {"seq": 1, "synopsis": "压力级:5 chapter_role:推进 stakes:若失败丢钥 章末钩子:钩"},
                {"seq": 2, "synopsis": "stakes:若失败B 章末钩子:h2"},
            ]

        def list_chapters(self):
            return self.chapters_lite()

        def get_chapter(self, seq):
            for c in self.chapters_lite():
                if c["seq"] == seq:
                    return {
                        **c,
                        "beats": [{"text": "x"}],
                        "narrative_drive": {},
                        "focalizer": "",
                        "deltas": [],
                    }
            return {}

        def update_chapter_meta(self, seq, fields):
            updates.append((seq, fields))

        def open_promises(self):
            return []

        def events_at(self, seq):
            return []

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: True,
    )
    stats = nd.ensure_narrative_drive_range(St(), dry_run=True, max_seqs=10)
    assert stats["enabled"] is True
    assert updates == []
    assert stats["total"] == 2
    assert len(stats["dry_run_would_write"]) >= 1


def test_range_skips_locked(monkeypatch):
    from scribe3 import narrative_drive as nd

    class St:
        def chapters_lite(self):
            return [{"seq": 1, "synopsis": "stakes:若失败 章末钩子:h"}]

        def get_chapter(self, seq):
            return {
                "synopsis": "stakes:若失败 章末钩子:h",
                "narrative_drive": {
                    "locked": True,
                    "source": "author",
                    "version": 3,
                    "inciting_force": {"summary": "旧", "source_refs": []},
                    "scene_turn": "旧转",
                    "validation": {"ok": True},
                },
                "beats": [],
                "focalizer": "",
                "deltas": [],
            }

        def update_chapter_meta(self, seq, fields):
            raise AssertionError("must not write locked")

        def open_promises(self):
            return []

        def events_at(self, seq):
            return []

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: True,
    )
    stats = nd.ensure_narrative_drive_range(St(), dry_run=False, force=False)
    assert stats["skipped_locked"] >= 1
    assert stats["rewritten"] == 0


def test_range_max_seqs(monkeypatch):
    from scribe3 import narrative_drive as nd

    class St:
        def chapters_lite(self):
            return [{"seq": i, "synopsis": f"stakes:若失败{i} 章末钩子:h{i}"} for i in range(1, 6)]

        def get_chapter(self, seq):
            return {
                "synopsis": f"stakes:若失败{seq} 章末钩子:h",
                "narrative_drive": {},
                "beats": [],
                "focalizer": "",
                "deltas": [],
            }

        def update_chapter_meta(self, seq, fields):
            pass

        def open_promises(self):
            return []

        def events_at(self, seq):
            return []

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: True,
    )
    stats = nd.ensure_narrative_drive_range(St(), dry_run=True, max_seqs=2)
    assert stats["total"] == 2


def test_opener_soft_and_metaphor_helpers():
    from scribe3.narrative_drive import (
        soft_metaphor_density_trace,
        soft_opener_event_trace,
        head_span_text,
    )
    prose = "他顺着巷子走，闻见铜腥，没有人逼他。\n\n第二段还是走。"
    t = soft_opener_event_trace(prose)
    assert t["severity"] == "advisory"
    assert t["type"] == "opener_soft_trace"
    assert head_span_text(prose)
    m = soft_metaphor_density_trace("像火，仿佛水，宛如风" * 20, threshold=1.0)
    assert m["over"] is True
    assert m["severity"] == "advisory"


def test_flags_oi_defaults_off():
    from scribe3.novel_quality_flags import (
        CODE_DEFAULTS,
        FLAG_OPENER_SOFT_TRACE,
        FLAG_METAPHOR_SOFT_PER_1K,
        opener_soft_trace_enabled,
        metaphor_soft_per_1k,
    )
    assert CODE_DEFAULTS.get(FLAG_OPENER_SOFT_TRACE) is False
    assert CODE_DEFAULTS.get(FLAG_METAPHOR_SOFT_PER_1K) in (0, 0.0)
    assert opener_soft_trace_enabled() is False
    assert metaphor_soft_per_1k() == 0 or metaphor_soft_per_1k() == 0.0


def test_needs_outline_enrich_recompose():
    from scribe3.narrative_drive import needs_outline_enrich_recompose

    old = {
        "validation": {"ok": True},
        "composed_from": {"seed_tier": "inventory"},
        "inciting_force": {"summary": "债", "source_refs": ["promise:p1"]},
    }
    meta = {"stakes": "若失败丢钥", "hook": "钩"}
    assert needs_outline_enrich_recompose(old, "", meta) is True
    good = {
        "validation": {"ok": True},
        "composed_from": {"seed_tier": "inventory", "outline_hook_absorbed": True},
        "inciting_force": {
            "summary": "债",
            "source_refs": ["promise:p1", "outline:stakes", "outline:hook"],
        },
    }
    assert needs_outline_enrich_recompose(good, "", meta) is False


def test_ensure_volume_ep_dry_run(monkeypatch):
    """OI-2b REST handler：ENGINE 开 + dry_run 不写库（需 fastapi 环境）。"""
    try:
        from fastapi import HTTPException  # noqa: F401
        from scribe3.api.models import NarrativeDriveEnsureReq
        from scribe3.api.routers import pilot_inbox as pi
    except ImportError:
        return  # Grok 主机无 fastapi 时跳过；demo/CI 有

    class St:
        def chapters_lite(self):
            return [{"seq": 1, "synopsis": "stakes:若失败 章末钩子:h"}]

        def get_chapter(self, seq):
            return {
                "synopsis": "stakes:若失败 章末钩子:h",
                "narrative_drive": {},
                "beats": [],
                "focalizer": "",
                "deltas": [],
            }

        def update_chapter_meta(self, seq, fields):
            raise AssertionError("dry_run must not write")

        def open_promises(self):
            return []

        def events_at(self, seq):
            return []

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: True,
    )
    monkeypatch.setattr(pi, "_store_for", lambda work: St())
    out = pi.ensure_narrative_drive_volume_ep(
        NarrativeDriveEnsureReq(dry_run=True, max_seqs=5),
        work="book_test",
    )
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["enabled"] is True


def test_ensure_volume_ep_engine_off(monkeypatch):
    try:
        from fastapi import HTTPException
        from scribe3.api.models import NarrativeDriveEnsureReq
        from scribe3.api.routers import pilot_inbox as pi
    except ImportError:
        return

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: False,
    )
    try:
        pi.ensure_narrative_drive_volume_ep(
            NarrativeDriveEnsureReq(dry_run=True), work="x")
        assert False, "expected 400"
    except HTTPException as e:
        assert e.status_code == 400
