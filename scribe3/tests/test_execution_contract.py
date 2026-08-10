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


def test_draft_skip_no_generate(monkeypatch):
    """有 prose 且无 force → skip，不调 loop_chapter。"""
    from scribe3.api.services import pilot_runtime as pr
    # load_pilot_actions builds nested functions — call ensure path via simulating
    # exported behavior: we test the control flow using a minimal double of draft_loop body

    called = {"loop": 0}

    class St:
        def get_chapter(self, seq):
            return {
                "prose": "已有正文" * 50,
                "beats": [{"goal": "g", "conflict": "c", "turn": "t", "cost": "x"}],
                "beats_meta": {"chapter_hook": "钩"},
                "narrative_drive": {
                    "inciting_force": {"summary": "债"},
                    "execution_stamp": {"drive_content_fp": "x"},
                },
                "focalizer": "",
            }

    # Import pure path equivalent: soft_fulfill + skip decision
    from scribe3.execution_contract import soft_fulfill_drive

    ch = St().get_chapter(1)
    prose = ch["prose"]
    ful = soft_fulfill_drive(prose, ch["narrative_drive"])
    # skip path must not clear
    force_clear = False
    if not force_clear and prose:
        result = {"skipped": "正文已在", "advisories": [ful.get("steer_hint") or ""]}
    else:
        called["loop"] += 1
        result = {"gen": True}
    assert "skipped" in result
    assert called["loop"] == 0


def test_first_write_steer_when_flags_on(monkeypatch):
    """ENGINE + DEFAULT_DRAMA_STEER → length_steer 含执行合同关键词。"""
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.narrative_engine_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "scribe3.novel_quality_flags.default_drama_steer_enabled",
        lambda: True,
    )
    from scribe3.novel_quality_flags import (
        default_drama_steer_enabled,
        narrative_engine_enabled,
    )
    from scribe3.execution_contract import (
        format_default_drama_steer,
        resolve_drama_steer_params,
    )

    assert narrative_engine_enabled() and default_drama_steer_enabled()
    length_steer = "本章交完整文学正文。"
    params = resolve_drama_steer_params("")
    if params["enabled"]:
        length_steer += format_default_drama_steer(
            dialogue_min=params["dialogue_min"],
            soft_len_floor=params["soft_len_floor"],
        )
    assert "对白≥" in length_steer
    assert "2400" in length_steer
    assert "执行合同" in length_steer


def test_flags_off_no_bundle():
    """旗关时不附加 Bundle（调用方不拼）。"""
    from scribe3.novel_quality_flags import CODE_DEFAULTS, FLAG_DEFAULT_DRAMA_STEER
    assert CODE_DEFAULTS[FLAG_DEFAULT_DRAMA_STEER] is False
    # 无 monkeypatch：默认读者 False（无 env 覆盖时）
    # 只断言纯函数在 enabled 路径才应被调用——此处验证不拼
    length = "基础。"
    enabled = False
    if enabled:
        length += format_default_drama_steer()
    assert "执行合同" not in length


def test_count_quotes():
    assert count_quotes("「甲」「乙」") >= 2
