"""Execution Contract 纯函数 + 旗默认 + draft 路径语义（无 Surreal / LLM）。

设计：docs/plans/2026-08-10-narrative-rootcause-optimal-execution.md rev.1.1
"""
from __future__ import annotations

from scribe3.execution_contract import (
    DEFAULT_SOFT_LEN_FLOOR,
    attach_execution_stamp,
    build_execution_stamp,
    count_quotes,
    drive_content_fp,
    drive_prose_drift,
    format_default_drama_steer,
    merge_pilot_card_dict,
    preserve_execution_stamp,
    resolve_drama_steer_params,
    soft_fulfill_drive,
)
from scribe3.novel_quality_flags import (
    CODE_DEFAULTS,
    FLAG_DEFAULT_DRAMA_STEER,
    FLAG_DRIVE_PROSE_DRIFT,
    FLAG_EVENT_DRIVE_GATE,
    FLAG_EVENT_LED_DETECT,
    FLAG_SOFT_FULFILL,
    FLAG_SOFT_FULFILL_RESTEER,
)


def test_format_default_drama_steer_has_floors():
    s = format_default_drama_steer(dialogue_min=4, soft_len_floor=2400)
    assert "对白≥4" in s
    assert "2400" in s
    assert "执行合同" in s
    assert "戏优先" in s or "优先" in s
    assert DEFAULT_SOFT_LEN_FLOOR == 2400


def test_resolve_opt_out_dialogue():
    p = resolve_drama_steer_params("本章用日记体，无对白")
    assert p["enabled"] is False


def test_soft_fulfill_never_blocking():
    ful = soft_fulfill_drive("短。", None, dialogue_min=4, soft_len_floor=2400)
    assert ful["severity"] == "advisory"
    assert ful["ok_soft"] is False
    assert "dialogue_low" in ful["gaps"]
    assert ful.get("severity") != "blocking"


def test_soft_fulfill_pass2_like_no_length_only_fail():
    # ~2983 可见字 + 高引号 → 不应有 short_and_dialogue_low
    body = "「你欠的东西，该还了。」" * 50 + "他站在门前。" * 200
    # pad to ~3000 cn
    while len(__import__("re").sub(r"\s+", "", body)) < 2980:
        body += "炉火还在烧。"
    ful = soft_fulfill_drive(body, None, dialogue_min=4, soft_len_floor=2400)
    assert ful["prose_cn"] >= 2400
    assert ful["quotes"] >= 4
    assert "short_and_dialogue_low" not in ful["gaps"]
    # 有对白时不应仅因长度失败
    assert ful["severity"] == "advisory"


def test_collapse_combo_short_low_dialogue():
    ful = soft_fulfill_drive("他走了。", None, dialogue_min=4, soft_len_floor=2400)
    assert ful["collapse_combo"] is True


def test_stamp_preserve_on_recompose():
    prev = {
        "synopsis_fp": "aaa",
        "inciting_force": {"summary": "旧债"},
        "execution_stamp": {
            "drive_content_fp": "deadbeef",
            "prose_fp_at_write": "cafe",
        },
    }
    new = {
        "synopsis_fp": "bbb",
        "inciting_force": {"summary": "新债"},
        "version": 2,
    }
    out = preserve_execution_stamp(new, prev)
    assert out["execution_stamp"]["drive_content_fp"] == "deadbeef"


def test_drive_content_fp_ignores_version():
    d1 = {
        "synopsis_fp": "x",
        "version": 1,
        "inciting_force": {"summary": "债"},
        "opposition": {"who_or_what": "婆", "wants": "还"},
        "end_hook": "h",
        "scene_turn": "t",
        "stakes_line": "s",
    }
    d2 = dict(d1)
    d2["version"] = 99
    assert drive_content_fp(d1) == drive_content_fp(d2)


def test_drift_when_core_changes():
    drive = {
        "synopsis_fp": "s1",
        "inciting_force": {"summary": "新"},
        "opposition": {"who_or_what": "a", "wants": "b"},
        "end_hook": "h",
        "scene_turn": "t",
        "stakes_line": "s",
        "execution_stamp": {
            "drive_content_fp": "0000000000000000",
            "synopsis_fp": "s1",
        },
    }
    dr = drive_prose_drift(drive, "正文")
    assert dr["drift"] is True
    assert "建议" in dr["advisory"] or "advisory" in dr["advisory"].lower() or "合同" in dr["advisory"]


def test_merge_pilot_card_preserves_keys():
    prev = {"buckets": {"redline": 1}, "soft_fulfill": {"ok_soft": False}}
    out = merge_pilot_card_dict(prev, {"buckets": {"redline": 2, "story": 0}})
    assert out["buckets"]["redline"] == 2
    assert out["soft_fulfill"]["ok_soft"] is False


def test_attach_execution_stamp():
    drive = {
        "synopsis_fp": "abc",
        "inciting_force": {"summary": "债"},
        "opposition": {"who_or_what": "x", "wants": "y"},
    }
    stamped = attach_execution_stamp(drive, "「还债。」正文若干")
    assert "execution_stamp" in stamped
    assert stamped["execution_stamp"].get("drive_content_fp")
    assert stamped["execution_stamp"].get("prose_fp_at_write")


def test_flags_default_safe():
    assert CODE_DEFAULTS.get(FLAG_DEFAULT_DRAMA_STEER) is False
    assert CODE_DEFAULTS.get(FLAG_SOFT_FULFILL) is False
    assert CODE_DEFAULTS.get(FLAG_DRIVE_PROSE_DRIFT) is False
    assert CODE_DEFAULTS.get(FLAG_SOFT_FULFILL_RESTEER) is False
    assert CODE_DEFAULTS.get(FLAG_EVENT_DRIVE_GATE) is False
    assert CODE_DEFAULTS.get(FLAG_EVENT_LED_DETECT) is False


def test_plan_draft_loop_skip_existing_prose():
    """shipped plan_draft_loop：有 prose 且无 force → action=skip。"""
    from scribe3.execution_contract import plan_draft_loop

    plan = plan_draft_loop(
        prose="已有正文" * 40,
        steer="",
        has_drama=True,
        drive={"inciting_force": {"summary": "债"}},
        narrative_engine=True,
        default_drama_steer=True,
        soft_fulfill_on=True,
        drift_on=False,
        resteer_on=False,
        craft_novel=False,
        seq=2,
    )
    assert plan["action"] == "skip"
    assert plan["skipped"]
    assert plan["force_clear"] is False
    assert "msg" in plan and plan["msg"] == ""


def test_plan_draft_loop_first_write_bundle():
    """shipped plan_draft_loop：无 prose + flags on → generate msg 含执行合同。"""
    from scribe3.execution_contract import plan_draft_loop

    plan = plan_draft_loop(
        prose="",
        steer="",
        has_drama=False,
        drive={},
        narrative_engine=True,
        default_drama_steer=True,
        soft_fulfill_on=False,
        drift_on=False,
        resteer_on=False,
        craft_novel=False,
        seq=1,
    )
    assert plan["action"] == "generate"
    assert "执行合同" in plan["msg"]
    assert "对白≥4" in plan["msg"] or "对白≥" in plan["msg"]
    assert "2400" in plan["msg"]
    assert "执行合同" in plan["length_steer"]


def test_assemble_draft_length_steer_flags_off():
    """shipped assemble_draft_length_steer：旗关不加 Bundle。"""
    from scribe3.execution_contract import assemble_draft_length_steer

    s = assemble_draft_length_steer(
        craft_novel=False,
        narrative_engine=False,
        default_drama_steer=False,
        author_steer="",
    )
    assert "执行合同" not in s
    assert "4800" in s  # base steer still present


def test_real_draft_loop_first_write_calls_loop_chapter(monkeypatch):
    """真 draft_loop（_pilot_executor）首写：loop_chapter 收到含 Bundle 的 msg。"""
    import scribe3.api.services.pilot_runtime as pr

    class FakeReq:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    calls: list = []

    def fake_loop(req, work=None):
        calls.append({"msg": getattr(req, "msg", None), "work": work})
        return {"ok": True, "generated": True}

    pr.LoopChapterReq = FakeReq
    pr.loop_chapter = fake_loop
    pr._pilot_steer = lambda st, seq: ""

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled", lambda: True)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.default_drama_steer_enabled", lambda: True)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.soft_fulfill_enabled", lambda: False)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.drive_prose_drift_enabled", lambda: False)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.soft_fulfill_resteer_enabled", lambda: False)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.craft_novel_enabled", lambda: False)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.event_drive_gate_enabled", lambda: False)

    class St:
        def get_chapter(self, seq):
            return {
                "prose": "",
                "beats": [],
                "beats_meta": {},
                "narrative_drive": {},
                "focalizer": "",
            }

        def update_chapter_meta(self, *a, **k):
            return None

        def _execute_write(self, *a, **k):
            return None

    # structural: draft_loop must reference plan_draft_loop
    assert "plan_draft_loop" in pr._pilot_executor("t")["draft_loop"].__code__.co_names

    out = pr._pilot_executor("book_t")["draft_loop"](St(), 1)
    assert out.get("generated") is True or out.get("ok") is True
    assert calls, "loop_chapter must be called"
    msg = calls[0]["msg"] or ""
    assert "执行合同" in msg
    assert "对白≥" in msg
    assert "2400" in msg


def test_real_draft_loop_skip_no_loop_chapter(monkeypatch):
    """真 draft_loop：有 prose 时 skip，不调用 loop_chapter。"""
    import scribe3.api.services.pilot_runtime as pr

    class FakeReq:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    calls: list = []

    def fake_loop(req, work=None):
        calls.append(req)
        return {"ok": True}

    pr.LoopChapterReq = FakeReq
    pr.loop_chapter = fake_loop
    pr._pilot_steer = lambda st, seq: ""

    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled", lambda: False)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.default_drama_steer_enabled", lambda: False)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.soft_fulfill_enabled", lambda: True)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.drive_prose_drift_enabled", lambda: False)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.soft_fulfill_resteer_enabled", lambda: False)
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.craft_novel_enabled", lambda: False)

    class St:
        def get_chapter(self, seq):
            return {
                "prose": "已有正文内容" * 30,
                "beats": [],
                "beats_meta": {},
                "narrative_drive": {"inciting_force": {"summary": "债"}},
                "focalizer": "",
            }

        def _execute_write(self, *a, **k):
            raise AssertionError("skip must not clear prose")

    out = pr._pilot_executor("book_t")["draft_loop"](St(), 2)
    assert "skipped" in out
    assert calls == []


def test_count_quotes():
    assert count_quotes("「甲」「乙」") >= 2
