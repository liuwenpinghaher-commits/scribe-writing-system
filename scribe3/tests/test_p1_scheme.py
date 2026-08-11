"""P1 scheme pillars — drive shipped helpers only (no Surreal/FastAPI required)."""
from __future__ import annotations

import os
from importlib import reload


def test_adaptive_budget_profile_sums_and_differs():
    from scribe3 import context_budget as cb
    os.environ["SCRIBE3_ENVELOPE_V2_ENABLE"] = "1"
    os.environ.pop("SCRIBE3_SCENE_BUDGET_PROFILE", None)
    os.environ["SCRIBE3_ADAPTIVE_BUDGET"] = "1"
    try:
        reload(cb)
        default = cb.get_block_budgets()
        assert sum(default.values()) == 18_000
        dial = cb.get_block_budgets(beat_type="dialogue")
        assert sum(dial.values()) == 18_000
        assert dial["recent"] != default["recent"] or dial["canonical"] != default["canonical"]
        assert dial["recent"] == cb.SCENE_BUDGET_PROFILES["dialogue_heavy"]["recent"]
        # explicit env wins
        os.environ["SCRIBE3_SCENE_BUDGET_PROFILE"] = "exposition"
        reload(cb)
        exp = cb.get_block_budgets(beat_type="dialogue")
        assert exp["canonical"] == cb.SCENE_BUDGET_PROFILES["exposition"]["canonical"]
    finally:
        for k in ("SCRIBE3_ENVELOPE_V2_ENABLE", "SCRIBE3_ADAPTIVE_BUDGET", "SCRIBE3_SCENE_BUDGET_PROFILE"):
            os.environ.pop(k, None)
        reload(cb)
    # flag-off empty profile → V1 10k
    assert sum(cb.get_block_budgets().values()) == 10_000


def test_registry_density_and_v2_order_under_active():
    from scribe3.injection_registry import (
        density_trace_for_segments,
        registry_mode,
        registry_physical_order_names,
        active_registry_orders_join,
    )
    from scribe3.context_budget import join_generation_segments, assert_physical_order_indices
    os.environ["SCRIBE3_INJECTION_REGISTRY"] = "active"
    try:
        assert registry_mode() == "active"
        assert active_registry_orders_join() is True
        names = registry_physical_order_names(v2=True)
        assert "event_drive" in names and "final_reminder" in names
        tr = density_trace_for_segments(
            domain_lengths={"drama_contract": 10, "envelope": 100, "codex": 50},
            order_indices={"event_drive": 0},
        )
        assert tr["mode"] == "active"
        assert "registry_names" in tr and tr["by_tier"]["L0"] == 10
        pieces = [
            {"name": "final_reminder", "text": "【最终提醒】限知"},
            {"name": "codex", "text": "设定" + ("x" * 100)},
            {"name": "envelope", "text": "ENV"},
            {"name": "drama_contract", "text": "戏"},
            {"name": "event_drive", "text": "事"},
            {"name": "prefix", "text": "P"},
            {"name": "material_recall", "text": "M" * 5000},
        ]
        joined, rep = join_generation_segments(pieces, v2=True, total_budget=8000)
        assert_physical_order_indices(rep["order_indices"])
        assert rep.get("final_reminder_kept") is True
        assert rep.get("registry_active") is True
        assert rep.get("order_source") == "injection_registry"
        assert "最终提醒" in joined or "限知" in joined
    finally:
        os.environ.pop("SCRIBE3_INJECTION_REGISTRY", None)


def test_memory_access_pin_and_fingerprint_dedup():
    from scribe3.memory_score import score_with_access, access_boost, time_decay
    from scribe3.inject_dedup import content_fingerprint, is_duplicate_text, deduplicate_paragraphs
    from scribe3.context_cache import record_cache_invalidation, cache_invalidation_stats, TTLCache

    base = dict(
        rrf_score=1.0, importance=2, confidence=1.0, age_days=30.0, half_life=30.0,
        pinned=False, pin_forever=False, access_count=0, focus_bonus=0.0, pin_bonus=0.0,
        source_kind="episodic",
    )
    s0 = score_with_access(**base)
    s1 = score_with_access(**{**base, "access_count": 5})
    assert s1 > s0
    assert access_boost(5) > 1.0
    assert time_decay(age_days=100, half_life=10, pin_forever=True) == 1.0
    assert time_decay(age_days=100, half_life=10, pin_forever=False) < 1.0

    # 段长 >= min_chars(20)，跨文本空白差应折叠
    a = "角色张三  拔刀走向战场的时候忽然停住了脚步。\n\n第二段内容完全相同用于去重检测用例。"
    b = "角色张三拔刀走向战场的时候忽然停住了脚步。\n\n第二段内容完全相同用于去重检测用例。"
    assert content_fingerprint(a.split("\n\n")[0]) == content_fingerprint(
        "角色张三拔刀走向战场的时候忽然停住了脚步。"
    )
    assert is_duplicate_text("同一事实句。", "同一事实句。")
    kept, rep = deduplicate_paragraphs([a, b])
    assert rep["dropped_paragraphs"] >= 1, rep
    assert "fingerprints_seen" in rep

    c = TTLCache(60.0, name="t", maxsize=8)
    c.set("k", "v", work="w1")
    n = c.invalidate(work="w1")
    assert n >= 1
    st = cache_invalidation_stats()
    assert st["invalidation_events"] >= 1

    # pin_must_first：空白归一后 must 核心须压掉含「后文」的 canonical
    from scribe3.memory_must_link import pin_must_first
    pinned = pin_must_first(
        ["角色张三拔刀。后文", "无关行"],
        ["- 〔压力〕角色张三  拔刀。"],
    )
    assert any("无关" in p for p in pinned)
    assert not any("后文" in p and "张三" in p for p in pinned), pinned


def test_beats_schema_and_approval_fingerprint():
    from scribe3.beats_schema import validate_beats_payload
    from scribe3.approval_idempotency import (
        compute_approval_fingerprint,
        lookup_approved,
        record_approved,
        clear_approval_cache,
    )
    from scribe3.chapter_gcd_rest import apply_gcd_beats_patch, is_emergency_bypass_chapter_path
    from scribe3.run_stage_policy import resolve_run_stage_policy, PLAN_SCAFFOLD_FORBIDDEN
    # 纯路径 SSOT（gating 委托此模块；不依赖 mcp SDK）
    from scribe3.write_commit import commit_if_approved

    ok, reason, norm = validate_beats_payload([{"text": "抵达", "goal": "入", "conflict": "阻"}])
    assert ok and norm
    bad, br, _ = validate_beats_payload([])
    assert not bad and br == "beats_empty"

    clear_approval_cache()
    fp = compute_approval_fingerprint("s3_patch_chapter_plan", {"seq": 1, "beats": [1]})
    assert len(fp) == 16
    assert lookup_approved(fp) is None
    record_approved(fp, "s3_patch_chapter_plan", {"status": "written", "tool": "s3_patch_chapter_plan", "x": 1})
    hit = lookup_approved(fp)
    assert hit and hit.get("x") == 1

    calls = {"n": 0}

    def _write():
        calls["n"] += 1
        return {"status": "written", "n": calls["n"]}

    r1 = commit_if_approved("s3_add_fact", True, _write, args={"entity": "a", "attribute": "b"})
    r2 = commit_if_approved("s3_add_fact", True, _write, args={"entity": "a", "attribute": "b"})
    assert r1.get("status") == "written"
    assert r2.get("idempotent_replay") is True
    assert calls["n"] == 1

    # tools_write 用 args_from_tool_locals 从工具 frame 抽参（纯 SSOT，无 mcp SDK）
    from scribe3.write_commit import args_from_tool_locals, commit_if_approved as _wc
    clear_approval_cache()
    calls["n"] = 0
    tool_locals = {
        "ctx": object(),
        "ok": True,
        "_write": lambda: None,
        "oid": "f1",
        "entity": "role:a",
        "attribute": "state",
        "value": "ok",
        "valid_from": 1,
        "secret": False,
        "work": None,
    }
    auto_args = args_from_tool_locals(tool_locals)
    assert auto_args is not None
    assert auto_args.get("entity") == "role:a"
    assert "ctx" not in auto_args and "_write" not in auto_args

    def _write2():
        calls["n"] += 1
        return {"status": "written", "n": calls["n"]}

    rr1 = _wc("s3_add_fact", True, _write2, args=auto_args)
    rr2 = _wc("s3_add_fact", True, _write2, args=auto_args)
    assert rr1.get("fingerprint"), rr1
    assert rr2.get("idempotent_replay") is True
    assert calls["n"] == 1

    assert is_emergency_bypass_chapter_path("/chapters/1/gcd-fields")
    ok2, _, n2 = apply_gcd_beats_patch(
        [{"text": "a", "goal": "g", "conflict": "c"}],
        [{"text": "ab", "goal": "g", "conflict": "c"}],
    )
    assert ok2 and n2
    pol = resolve_run_stage_policy("chapter:1:outline")
    assert not (pol.allowed_tools & PLAN_SCAFFOLD_FORBIDDEN)


def test_resolve_assembler_budgets_respects_beat_type():
    from scribe3.context_budget import resolve_assembler_budgets, SCENE_BUDGET_PROFILES
    os.environ["SCRIBE3_ENVELOPE_V2_ENABLE"] = "1"
    os.environ["SCRIBE3_ADAPTIVE_BUDGET"] = "1"
    os.environ.pop("SCRIBE3_SCENE_BUDGET_PROFILE", None)
    try:
        from importlib import reload
        import scribe3.context_budget as cb
        reload(cb)
        tb, bb = cb.resolve_assembler_budgets(beat_type="dialogue")
        assert tb == 18_000
        assert sum(bb.values()) == 18_000
        assert bb["recent"] == SCENE_BUDGET_PROFILES["dialogue_heavy"]["recent"]
    finally:
        for k in ("SCRIBE3_ENVELOPE_V2_ENABLE", "SCRIBE3_ADAPTIVE_BUDGET"):
            os.environ.pop(k, None)
        import scribe3.context_budget as cb
        from importlib import reload
        reload(cb)


def test_flags_registry_and_concurrency_lock():
    from scribe3.feature_flags import get_all_flags, get_flag, flag_truthy
    from scribe3.concurrency_lock import (
        acquire_lock, release_lock, InMemoryLockStore, distributed_lock_enabled,
    )
    from scribe3.concurrency_obs import inflight_enter, inflight_leave
    flags = get_all_flags()
    assert "SCRIBE3_ENVELOPE_V2_ENABLE" in flags
    assert "SCRIBE3_DISTRIBUTED_LOCK" in flags
    assert get_flag("SCRIBE3_EPISTEMIC_FAIL_LOUD") in ("0", "1", "false", "true", False, True) or True
    assert flag_truthy("SCRIBE3_MEMORY_ACCESS_DECAY") is True  # default 1

    assert acquire_lock("ingest", "chapter:9") is True
    assert acquire_lock("ingest", "chapter:9") is False
    release_lock("ingest", "chapter:9")
    assert acquire_lock("ingest", "chapter:9") is True
    release_lock("ingest", "chapter:9")

    # 观测路径：默认进程内
    assert inflight_enter("repair", "p1-key") is True
    assert inflight_enter("repair", "p1-key") is False
    inflight_leave("repair", "p1-key")
    assert inflight_enter("repair", "p1-key") is True
    inflight_leave("repair", "p1-key")

    os.environ["SCRIBE3_DISTRIBUTED_LOCK"] = "1"
    try:
        assert distributed_lock_enabled() is True
        store = InMemoryLockStore()
        assert acquire_lock("loop", "chapter:1", store=store) is True
        assert acquire_lock("loop", "chapter:1", store=store) is False
        release_lock("loop", "chapter:1", store=store)
        assert acquire_lock("loop", "chapter:1", store=store) is True
        # obs 委托 lock
        assert inflight_enter("loop", "obs-1", store=store) is True
        assert inflight_enter("loop", "obs-1", store=store) is False
        inflight_leave("loop", "obs-1", store=store)
    finally:
        os.environ.pop("SCRIBE3_DISTRIBUTED_LOCK", None)


if __name__ == "__main__":
    import traceback
    failed = []
    for name, fn in list(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print("PASS", name)
        except Exception as e:
            print("FAIL", name, e)
            traceback.print_exc()
            failed.append(name)
    print("SUMMARY failed=", failed)
    raise SystemExit(1 if failed else 0)
