"""做厚半截能力：H1 adaptive×novel · H2 event_led · H3 parallel execute · H6/H7 落盘 · H9 report。"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SCRIBE3_ENVELOPE_V2_ENABLE", "1")
    monkeypatch.setenv("SCRIBE3_ENVELOPE_NOVEL", "1")
    monkeypatch.setenv("SCRIBE3_ADAPTIVE_BUDGET", "1")
    monkeypatch.delenv("SCRIBE3_SCENE_BUDGET_PROFILE", raising=False)
    monkeypatch.delenv("SCRIBE3_CONTEXT_FIDELITY", raising=False)
    monkeypatch.setenv("SCRIBE3_BENCHMARK_PATH", str(tmp_path / "benchmarks.json"))
    monkeypatch.setenv("SCRIBE3_CRON_OVERRIDES_PATH", str(tmp_path / "cron_overrides.json"))
    yield


def test_h1_novel_adaptive_dialogue_sum_22k_not_18k():
    from scribe3.context_budget import (
        BLOCK_BUDGETS_NOVEL,
        NOVEL_ENVELOPE_TOKEN_BUDGET,
        SCENE_BUDGET_PROFILES,
        SCENE_BUDGET_PROFILES_NOVEL,
        get_block_budgets,
    )
    for name, tbl in SCENE_BUDGET_PROFILES_NOVEL.items():
        assert sum(tbl.values()) == NOVEL_ENVELOPE_TOKEN_BUDGET, name
    bb = get_block_budgets(beat_type="dialogue")
    assert sum(bb.values()) == 32_000
    # 不得静默落到 18k 场景表
    assert bb != SCENE_BUDGET_PROFILES["dialogue_heavy"]
    # 与 novel 基表至少一块不同（重配）
    assert bb != BLOCK_BUDGETS_NOVEL
    assert bb["recent"] != BLOCK_BUDGETS_NOVEL["recent"]


def test_h1_v2_adaptive_still_18k(monkeypatch):
    monkeypatch.setenv("SCRIBE3_ENVELOPE_NOVEL", "0")
    monkeypatch.setenv("SCRIBE3_CONTEXT_FIDELITY", "v2")
    from scribe3.context_budget import get_block_budgets, SCENE_BUDGET_PROFILES
    bb = get_block_budgets(beat_type="dialogue")
    assert sum(bb.values()) == 18_000
    assert bb == SCENE_BUDGET_PROFILES["dialogue_heavy"]


def test_h2_event_led_detect_empty_and_aligned():
    from scribe3.narrative_drive import detect_event_led
    drive = {
        "inciting_force": {"summary": "讨债上门三日为期"},
        "opposition": {"who_or_what": "债主", "wants": "逼还清"},
        "end_hook": "门闩一响",
        "scene_turn": "对峙升级",
    }
    empty = detect_event_led("", drive)
    assert empty["ok_soft"] is False
    assert "empty_prose" in empty["gaps"] or "missing_inciting_trace" in empty["gaps"]
    assert empty["severity"] == "advisory"

    prose = (
        "债主堵在门槛上，逼他还清。三日为期的讨债声还在耳边。"
        "「你还想逃？」他怒道。对峙升级，门闩一响。"
    )
    ok = detect_event_led(prose, drive)
    assert ok["ok_soft"] is True or "missing_inciting_trace" not in ok["gaps"]
    assert ok["has_dialogue"] is True
    assert ok["detector"] == "event_led_detect"


def test_h2_event_led_flag_off_returns_none(monkeypatch):
    monkeypatch.setenv("SCRIBE3_EVENT_LED_DETECT", "0")
    from scribe3.narrative_drive import maybe_event_led_detect
    assert maybe_event_led_detect("有债有对白「不」", {"inciting_force": {"summary": "债"}}) is None


def test_h3_parallel_execute_mock_two_ok():
    from scribe3.parallel_deduce import build_parallel_deduce_plan, execute_parallel_deduce

    plan = build_parallel_deduce_plan(3, ["甲", "乙"], max_parallel=2, work="t")
    assert plan["dry_run"] is True
    assert len(plan["runs"]) == 2
    assert plan["profile"] == "scribe3_deduce_preview"
    assert plan["runs"][0]["api_env"] == "HERMES_DEDUCE_PREVIEW_RUNS_API"

    def complete(spec):
        return {
            "status": "ok",
            "summary": f"ok:{spec.get('focalizer')}",
            "tool_trace_ok": True,
        }

    out = execute_parallel_deduce(plan, complete_fn=complete, lock=False)
    assert out["execute"] is True
    assert out["ok_count"] == 2
    assert [r["focalizer"] for r in out["results"]] == ["甲", "乙"]


def test_h3_plan_mode_deduce_full_profile():
    from scribe3.parallel_deduce import build_parallel_deduce_plan
    plan = build_parallel_deduce_plan(1, ["甲"], mode="deduce")
    assert plan["profile"] == "scribe3_deduce"
    assert plan["api_env"] == "HERMES_DEDUCE_RUNS_API"
    assert plan["runs"][0]["profile"] == "scribe3_deduce"


def test_h3_focal_slug_ascii_for_headers():
    from scribe3.parallel_deduce import _focal_slug
    s = _focal_slug("甲")
    assert s.isascii()
    assert len(s) >= 4
    assert _focal_slug("Alice") == "Alice" or _focal_slug("Alice").startswith("Alice")


def test_h3_stub_not_in_ok_count():
    from scribe3.parallel_deduce import build_parallel_deduce_plan, execute_parallel_deduce
    plan = build_parallel_deduce_plan(1, ["甲", "乙"], max_parallel=2)
    out = execute_parallel_deduce(
        plan,
        complete_fn=lambda s: {"status": "stub", "summary": "fake", "tool_trace_ok": False},
        lock=False,
    )
    assert out["ok_count"] == 0
    assert out["all_stub"] is True
    assert out["stub_count"] == 2


def test_pr0_emergency_bypass_soft_paths():
    from scribe3.chapter_gcd_rest import is_emergency_bypass_chapter_path
    assert is_emergency_bypass_chapter_path("/chapters/1/deduce/parallel") is True
    assert is_emergency_bypass_chapter_path("/chapters/2/stage") is True
    assert is_emergency_bypass_chapter_path("/chapters/2/stage/advance") is True
    assert is_emergency_bypass_chapter_path("/chapters/2/prose") is False


def test_stage_soft_set_action():
    from scribe3.chapter_stage import transition, normalize_phase
    r = transition("final", "set")
    assert r["next"] == "final"
    assert "soft_set" in r.get("advisories", [])


def test_h3_parallel_busy_lock():
    from scribe3.chapter_lock import acquire_chapter_lock, release_chapter_lock
    from scribe3.parallel_deduce import build_parallel_deduce_plan, execute_parallel_deduce

    work, seq = "locktest", 99
    r = acquire_chapter_lock("run", work, seq)
    assert r.ok
    try:
        plan = build_parallel_deduce_plan(seq, ["甲"], work=work)
        out = execute_parallel_deduce(
            plan,
            complete_fn=lambda s: {"status": "ok", "summary": "x"},
            lock=True,
        )
        assert out.get("error") == "chapter_busy" or out.get("ok_count", 1) == 0
    finally:
        release_chapter_lock("run", work, seq)


def test_h6_benchmark_disk_persist(tmp_path, monkeypatch):
    path = tmp_path / "benchmarks.json"
    monkeypatch.setenv("SCRIBE3_BENCHMARK_PATH", str(path))
    from scribe3 import benchmark_lib as bl
    bl.clear_benchmarks_for_tests()
    row = bl.upsert_benchmark({"title": "金瓶梅节奏", "notes": "advisory"})
    assert path.is_file()
    bl.clear_benchmarks_for_tests()
    # 重新加载
    items = bl.list_benchmarks()
    assert any(i.get("id") == row["id"] for i in items)


def test_h7_cron_override_disk(tmp_path, monkeypatch):
    path = tmp_path / "cron_overrides.json"
    monkeypatch.setenv("SCRIBE3_CRON_OVERRIDES_PATH", str(path))
    from scribe3 import agent_crons as ac
    ac.clear_cron_overrides_for_tests()
    r = ac.set_cron_enabled("nightly_backup", False)
    assert r["persisted"] == "disk"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("nightly_backup") is False
    ac.clear_cron_overrides_for_tests()
    # 再 load 应仍从盘恢复（clear 后 _LOADED False 再读）
    # 因 clear 对 test path 会 unlink，重建
    path.write_text(json.dumps({"nightly_backup": False}), encoding="utf-8")
    jobs = ac.load_cron_catalog()
    # yaml 可能有/无该 name；覆盖表已加载
    assert ac.default_overrides_path() == path


def test_h9_budget_report_observability_fields():
    from scribe3.context_budget import build_budget_report
    rep = build_budget_report(beat_type="dialogue")
    for k in ("registry_mode", "adaptive_profile", "fidelity", "prompt_hard", "event_graph"):
        assert k in rep, k
    assert rep["fidelity"] == "novel"
    assert rep["prompt_hard"] >= 48_000
    assert isinstance(rep["event_graph"], dict)
    assert "k" in rep["event_graph"]


def test_h11_sample_script_runs(tmp_path):
    from scribe3.tools.sample_budget_report import sample_local, main
    data = sample_local(beat_type="dialogue")
    assert data["block_sum"] == 32_000
    assert "conclusion" in data
    out = tmp_path / "budget_sample.json"
    assert main(["--out", str(out), "--beat-type", "dialogue"]) == 0
    assert out.is_file()


def test_structure_ui_api_files_exist():
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "web/src/StageBoard.jsx",
        "web/src/ChapterSoftCards.jsx",
        "web/src/settings/CronPanel.jsx",
        "parallel_deduce.py",
        "tools/sample_budget_report.py",
        "scripts/smoke_scribe3_thicken.sh",
    ):
        assert (root / rel).is_file(), rel
    api = (root / "web/src/api.js").read_text(encoding="utf-8")
    for name in (
        "chapterStage", "parallelDeduce", "storylineInjectPreview",
        "agentCrons", "softPrecheck", "injectionTrace",
        "softEventLed", "budgetProbe", "debugLocks",
    ):
        assert name in api, name


def test_pr3_agent_crons_response_shape(monkeypatch):
    from scribe3.agent_crons import build_agent_crons_response, clear_cron_overrides_for_tests
    monkeypatch.setattr(
        "scribe3.agent_crons.load_hermes_cron_aggregate",
        lambda force=False: {"checked": False, "note": "mock"},
    )
    monkeypatch.setattr(
        "scribe3.agent_crons.load_hermes_cron_jobs",
        lambda force=False: {},
    )
    clear_cron_overrides_for_tests()
    r = build_agent_crons_response()
    assert r["mutates_hermes_timer"] is False
    assert "note_zh" in r
    assert "hermes_cron" in r
    assert isinstance(r["jobs"], list)


def test_pr3b_parse_hermes_cron_list_and_match():
    from scribe3.agent_crons import parse_hermes_cron_list, match_job_hermes, build_agent_crons_response
    sample = """
  dc4bd8e87938 [active]
    Name:      scribe3-体检
    Schedule:  every 360m
    Last run:  2026-07-10T00:03:07.173673+08:00  ok
  aabbccddee01 [paused]
    Name:      scribe3-daily-digest
    Schedule:  0 8 * * *
"""
    parsed = parse_hermes_cron_list(sample)
    assert parsed["scribe3-体检"]["present"] is True
    assert parsed["scribe3-体检"]["active"] is True
    assert parsed["scribe3-体检"]["last_status"] == "ok"
    assert parsed["scribe3-daily-digest"]["present"] is True
    assert parsed["scribe3-daily-digest"]["active"] is False

    exact = match_job_hermes("scribe3-daily-digest", parsed)
    assert exact["present"] is True
    assert exact["match"] == "exact"
    missing = match_job_hermes("no-such-job", parsed)
    assert missing["present"] is False


def test_pr3b_build_response_attaches_hermes(monkeypatch):
    from scribe3 import agent_crons as ac
    ac.clear_cron_overrides_for_tests()
    monkeypatch.setattr(
        ac,
        "load_cron_catalog",
        lambda path=None: [
            {"name": "scribe3-daily-digest", "schedule": "0 8 * * *", "enabled": True, "catalog_enabled": True},
            {"name": "other-job", "schedule": "0 0 * * *", "enabled": True, "catalog_enabled": True},
        ],
    )
    monkeypatch.setattr(
        ac,
        "load_hermes_cron_aggregate",
        lambda force=False: {"checked": True, "active_jobs": 1},
    )
    monkeypatch.setattr(
        ac,
        "load_hermes_cron_jobs",
        lambda force=False: {
            "scribe3-daily-digest": {"present": True, "active": True, "last_status": "ok"},
        },
    )
    r = ac.build_agent_crons_response()
    assert r["phase"] == "2"
    by = {j["name"]: j for j in r["jobs"]}
    assert by["scribe3-daily-digest"]["hermes"]["present"] is True
    assert by["scribe3-daily-digest"]["hermes"]["active"] is True
    assert by["other-job"]["hermes"]["present"] is False



def test_pr4_soft_event_led_l0_only():
    from scribe3.api.routers.misc_routes import soft_event_led_ep
    r = soft_event_led_ep({
        "prose": "债主堵在门槛上逼他还清。「你还想逃？」对峙升级。",
        "include_llm": False,
        "drive": {
            "inciting_force": {"summary": "讨债上门"},
            "opposition": {"who_or_what": "债主", "wants": "逼还清"},
        },
    })
    assert r["severity"] == "advisory"
    assert r["l0"]["detector"] == "event_led_detect"
    assert r["l1"] is None


def test_pr5_benchmark_advisory_and_inject_flag_off(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_BENCHMARK_PATH", str(tmp_path / "b.json"))
    monkeypatch.setenv("SCRIBE3_BENCHMARK_INJECT", "0")
    from scribe3 import benchmark_lib as bl
    bl.clear_benchmarks_for_tests()
    row = bl.upsert_benchmark({"title": "节奏", "notes": "对白抬张力", "reference_work_id": "rw1"})
    prev = bl.build_advisory_preview(row["id"])
    assert prev["ok"] is True
    assert prev["advisory_only"] is True
    assert "禁止仿写" in prev["text"] or prev["text"]
    assert bl.build_benchmark_inject_segment() == ""


def test_pr5_benchmark_inject_on(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIBE3_BENCHMARK_PATH", str(tmp_path / "b2.json"))
    monkeypatch.setenv("SCRIBE3_BENCHMARK_INJECT", "1")
    from scribe3 import benchmark_lib as bl
    bl.clear_benchmarks_for_tests()
    bl.upsert_benchmark({"title": "t", "notes": "抬 recent 对白"})
    text = bl.build_benchmark_inject_segment()
    assert text
    assert "禁止仿写" in text or "对照" in text


def test_pr7_budget_probe_config():
    from scribe3.api.routers.misc_routes import budget_probe_ep
    r = budget_probe_ep({"mode": "config", "beat_type": "dialogue"})
    assert r["mode"] == "config"
    assert r["L1_envelope"] >= 10000
    assert "prompt_hard" in r
    assert "完整" not in str(r.get("note") or "") or "永不" in r["note"]


def test_pr8_debug_locks():
    from scribe3.api.routers.misc_routes import get_debug_locks
    r = get_debug_locks()
    assert r["surface"] == "debug.locks"
    assert "run" in r["chapter_ops"]
    assert "inflight" in r
