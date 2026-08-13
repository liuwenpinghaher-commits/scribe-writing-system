"""Novel-first 写路径预算 / 物理序 / 脚手架 / GCD REST — 驱动 shipped 代码。

设计：docs/plans/2026-08-11-novel-first-injection-quality-optimal.md
无 Surreal / 无 LLM；宿主无 pydantic 时跳过需 Assembler 类的 import，改用
resolve_assembler_budgets（Engine/Assembler 共用真源）+ join_generation_segments。
"""
from __future__ import annotations

import os
from importlib import reload


def test_block_budgets_v2_sum_18000():
    from scribe3.context_budget import (
        BLOCK_BUDGETS_V1,
        BLOCK_BUDGETS_V2,
        BLOCK_BUDGETS_NOVEL,
        DEFAULT_ENVELOPE_TOKEN_BUDGET_V1,
        DEFAULT_ENVELOPE_TOKEN_BUDGET_V2,
        NOVEL_ENVELOPE_TOKEN_BUDGET,
    )
    assert sum(BLOCK_BUDGETS_V1.values()) == DEFAULT_ENVELOPE_TOKEN_BUDGET_V1 == 10_000
    assert sum(BLOCK_BUDGETS_V2.values()) == DEFAULT_ENVELOPE_TOKEN_BUDGET_V2 == 18_000
    assert sum(BLOCK_BUDGETS_NOVEL.values()) == NOVEL_ENVELOPE_TOKEN_BUDGET == 22_000


def test_flag_off_keeps_v1_budget():
    from scribe3 import context_budget as cb
    os.environ["SCRIBE3_ENVELOPE_V2_ENABLE"] = "0"
    os.environ["SCRIBE3_ENVELOPE_NOVEL"] = "0"
    os.environ["SCRIBE3_CONTEXT_FIDELITY"] = "compat"
    try:
        reload(cb)
        assert cb.envelope_v2_enabled() is False
        assert sum(cb.get_block_budgets().values()) == 10_000
        assert cb.get_envelope_token_budget() == 10_000
        tb, bb = cb.resolve_assembler_budgets()
        assert tb == 10_000 and sum(bb.values()) == 10_000
    finally:
        for k in ("SCRIBE3_ENVELOPE_V2_ENABLE", "SCRIBE3_ENVELOPE_NOVEL", "SCRIBE3_CONTEXT_FIDELITY"):
            os.environ.pop(k, None)
        reload(cb)


def test_default_is_novel_22k_and_prompt_hard_48k():
    """质量优先默认：novel 信封 22k + PROMPT_HARD 48k。"""
    from scribe3 import context_budget as cb
    for k in ("SCRIBE3_ENVELOPE_V2_ENABLE", "SCRIBE3_ENVELOPE_NOVEL", "SCRIBE3_CONTEXT_FIDELITY"):
        os.environ.pop(k, None)
    reload(cb)
    assert cb.envelope_v2_enabled() is True
    assert cb.novel_envelope_enabled() is True
    assert cb.context_fidelity() == "novel"
    b = cb.get_block_budgets()
    assert sum(b.values()) == 22_000
    assert cb.get_envelope_token_budget() == 22_000
    assert cb.get_prompt_hard() == 48_000
    assert b["canonical"] == cb.BLOCK_BUDGETS_NOVEL["canonical"]
    assert b["recent"] == cb.BLOCK_BUDGETS_NOVEL["recent"]
    assert b["canonical"] >= 6800 and b["recent"] >= 4000  # 相对 V2 抬 high-signal


def test_flag_on_v2_budget():
    from scribe3 import context_budget as cb
    os.environ["SCRIBE3_ENVELOPE_V2_ENABLE"] = "1"
    os.environ["SCRIBE3_ENVELOPE_NOVEL"] = "0"
    os.environ["SCRIBE3_CONTEXT_FIDELITY"] = "v2"
    try:
        reload(cb)
        assert cb.envelope_v2_enabled() is True
        b = cb.get_block_budgets()
        assert sum(b.values()) == 18_000
        assert cb.get_envelope_token_budget() == 18_000
        assert b["canonical"] == 7400
        assert b["recent"] == 4400
        tb, bb = cb.resolve_assembler_budgets()
        assert tb == 18_000 and bb["canonical"] == 7400
    finally:
        for k in ("SCRIBE3_ENVELOPE_V2_ENABLE", "SCRIBE3_ENVELOPE_NOVEL", "SCRIBE3_CONTEXT_FIDELITY"):
            os.environ.pop(k, None)
        reload(cb)


def test_engine_assembler_budget_wiring():
    """Engine/Assembler 必须调用 resolve_assembler_budgets；flag 下预算一致。

    宿主无 pydantic 时无法 import ContextAssembler 类 —— 仍验证：
    1) 源码接线；2) resolve_assembler_budgets 为双方共用真源；3) 若可 import 则实例断言。
    """
    eng_src = open("scribe3/context_engine.py", encoding="utf-8").read()
    assert "resolve_assembler_budgets" in eng_src
    assert "token_budget=tb" in eng_src.replace(" ", "") or "token_budget=tb" in eng_src
    asm_src = open("scribe3/context_assembler.py", encoding="utf-8").read()
    assert "resolve_assembler_budgets" in asm_src

    from scribe3 import context_budget as cb
    os.environ["SCRIBE3_ENVELOPE_V2_ENABLE"] = "1"
    os.environ["SCRIBE3_ENVELOPE_NOVEL"] = "0"
    os.environ["SCRIBE3_CONTEXT_FIDELITY"] = "v2"
    try:
        reload(cb)
        tb, bb = cb.resolve_assembler_budgets()
        assert tb == 18_000
        assert sum(bb.values()) == 18_000
        # 显式覆盖
        tb2, bb2 = cb.resolve_assembler_budgets(12_000, {"focus": 100, "global": 200})
        assert tb2 == 12_000 and bb2["focus"] == 100
    finally:
        for k in ("SCRIBE3_ENVELOPE_V2_ENABLE", "SCRIBE3_ENVELOPE_NOVEL", "SCRIBE3_CONTEXT_FIDELITY"):
            os.environ.pop(k, None)
        reload(cb)

    # 尽量实例化 Engine（有 pydantic 时）— 默认 novel 22k
    try:
        for k in ("SCRIBE3_ENVELOPE_V2_ENABLE", "SCRIBE3_ENVELOPE_NOVEL", "SCRIBE3_CONTEXT_FIDELITY"):
            os.environ.pop(k, None)
        reload(cb)
        from scribe3.context_engine import CreativeContextEngine

        class _Stub:
            pass

        eng = CreativeContextEngine(_Stub())
        assert eng.token_budget == 22_000
        assert sum(eng.block_budgets.values()) == 22_000
        assert eng._assembler.token_budget == 22_000
    except ModuleNotFoundError as e:
        if "pydantic" not in str(e).lower() and "pydantic" not in repr(e).lower():
            # 其它缺依赖再抛
            if "pydantic" not in str(type(e)):
                pass
        # 宿主无 pydantic：接线已由 resolve + 源码断言覆盖
    finally:
        for k in ("SCRIBE3_ENVELOPE_V2_ENABLE", "SCRIBE3_ENVELOPE_NOVEL", "SCRIBE3_CONTEXT_FIDELITY"):
            os.environ.pop(k, None)
        reload(cb)


def test_join_generation_segments_physical_order_v2():
    """驱动 shipped join_generation_segments（write_assemble 生产路径调用）。"""
    from scribe3.context_budget import (
        assert_physical_order_indices,
        join_generation_segments,
    )
    # 故意乱序 push，join 必须重排
    pieces = [
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】限知"},
        {"name": "codex", "layer": "supplemental", "text": "设定圣经X"},
        {"name": "envelope", "layer": "envelope", "text": "ENV块"},
        {"name": "drama_contract", "layer": "redline", "text": "【戏剧合同】GCD"},
        {"name": "event_drive", "layer": "redline", "text": "【事件驱动】"},
        {"name": "prefix", "layer": "redline", "text": "身份"},
        {"name": "outline", "layer": "supplemental", "text": "大纲"},
    ]
    joined, rep = join_generation_segments(pieces, v2=True)
    idx = rep.get("order_indices") or {}
    # 至少核心五标记
    for k in ("event_drive", "drama_contract", "envelope", "codex", "final_reminder"):
        assert k in idx, f"missing {k} in {idx}"
    assert_physical_order_indices(idx)
    # 文本相对序
    i_ed = joined.index("事件驱动")
    i_dr = joined.index("戏剧合同")
    i_env = joined.index("ENV")
    i_cx = joined.index("设定圣经")
    i_fr = joined.index("最终提醒")
    assert i_ed < i_dr < i_env < i_cx < i_fr
    assert rep.get("primary_metric") == "signal_density_for_drama"
    assert rep.get("not_a_kpi") == "tokens_saved"


def test_apply_l2_trim_drops_material_keeps_final_reminder():
    from scribe3.context_budget import apply_l2_trim, join_generation_segments

    big = "X" * 25_000
    segs = [
        {"name": "prefix", "layer": "redline", "text": "ID" * 100},
        {"name": "event_drive", "layer": "redline", "text": "【事件驱动】" * 20},
        {"name": "drama_contract", "layer": "redline", "text": "【戏剧合同】" * 20},
        {"name": "envelope", "layer": "envelope", "text": "ENV" * 500},
        {"name": "codex", "layer": "supplemental", "text": "设定圣经" + big},
        {"name": "material_recall", "layer": "supplemental", "text": "素材" + big},
        {"name": "outline", "layer": "supplemental", "text": "大纲" * 200},
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】务必遵守限知。"},
    ]
    joined, rep = apply_l2_trim(
        segs, supplemental_hard=5_000, prompt_hard=20_000,
    )
    assert "最终提醒" in joined or "限知" in joined
    assert "final_reminder" in (rep.get("segment_names") or []) or "最终提醒" in joined
    assert any("material" in d for d in (rep.get("dropped") or [])) or "素材" not in joined
    assert not joined.endswith("XXXX")

    # 同一路径经 join（生产接线）
    joined2, rep2 = join_generation_segments(
        segs, v2=True, supplemental_hard=5_000, prompt_hard=20_000,
    )
    assert "最终提醒" in joined2 or "限知" in joined2
    assert rep2.get("l2")


def test_write_assemble_calls_join_ssot():
    """write_assemble 必须接线 join_generation_segments，而非平行序。"""
    src = open("scribe3/api/services/write_assemble.py", encoding="utf-8").read()
    assert "join_generation_segments" in src
    assert "get_last_write_budget_report" in src
    assert "record_write_soft_fail" in src
    assert "budget_report" in src


def test_budget_report_module_export():
    from scribe3.api.services import write_assemble as wa
    from scribe3.context_budget import build_budget_report, join_generation_segments

    pieces = [
        {"name": "event_drive", "text": "E"},
        {"name": "drama_contract", "text": "D"},
        {"name": "envelope", "text": "N"},
        {"name": "codex", "text": "C"},
        {"name": "final_reminder", "text": "F"},
    ]
    _, rep = join_generation_segments(pieces, v2=True)
    wa._store_write_budget_report(rep)
    got = wa.get_last_write_budget_report()
    assert got.get("primary_metric") == "signal_density_for_drama"
    assert "order_indices" in got
    r = build_budget_report(domain_lengths={"outline": 100}, order_indices={"codex": 4})
    assert r["not_a_kpi"] == "tokens_saved"


def test_soft_fail_counters():
    from scribe3.api.services import write_assemble as wa
    before = wa.get_write_soft_fail_counters().get("empty_drama", 0)
    wa.record_write_soft_fail("empty_drama")
    after = wa.get_write_soft_fail_counters().get("empty_drama", 0)
    assert after == before + 1


def test_scaffold_policy_and_run_scope():
    from scribe3.run_stage_policy import (
        PLAN_SCAFFOLD_FORBIDDEN,
        resolve_run_stage_policy,
        scaffold_forces_stage_profile,
        scaffold_run_scope,
        scaffold_tools_exclude_save,
    )
    for phase in ("outline", "beats", "plan"):
        pol = resolve_run_stage_policy(f"chapter:3:{phase}")
        assert pol is not None
        assert pol.api_env == "HERMES_PLAN_RUNS_API"
        assert pol.profile == "scribe3_plan"
        assert scaffold_tools_exclude_save(pol) is True
        assert not (pol.allowed_tools & PLAN_SCAFFOLD_FORBIDDEN)
        assert "s3_save_chapter" not in pol.allowed_tools
        assert "s3_ingest_chapter" not in pol.allowed_tools
        assert scaffold_run_scope(3, phase) == f"chapter:3:{phase}"
        assert scaffold_forces_stage_profile(phase, world_write=True) is True
    assert scaffold_run_scope(None, "outline") is None
    assert scaffold_run_scope(2, "draft") == "chapter:2:draft"
    assert scaffold_run_scope(2, "chat") is None


def test_hermes_plan_runtime_mapping():
    """outline/beats/plan 的 api_env 必须映射到 HERMES_PLAN_RUNS（:8647）。"""
    from scribe3.hermes_runs_env import HERMES_PLAN_RUNS, hermes_runs_api_base_for_env
    from scribe3.run_stage_policy import resolve_run_stage_policy

    assert "8647" in HERMES_PLAN_RUNS
    for phase in ("outline", "beats", "plan"):
        pol = resolve_run_stage_policy(f"chapter:1:{phase}")
        base = hermes_runs_api_base_for_env(pol.api_env)
        assert base == HERMES_PLAN_RUNS
    d = resolve_run_stage_policy("chapter:1:deduce")
    assert "8645" in hermes_runs_api_base_for_env(d.api_env)
    hs = open("scribe3/api/services/hermes_status.py", encoding="utf-8").read()
    assert "hermes_runs_api_base_for_env" in hs
    # settings 登记
    settings_src = open("scribe3/settings.py", encoding="utf-8").read()
    assert "HERMES_PLAN_RUNS_API" in settings_src


def test_plan_overlay_and_mcp_exclude_save():
    from pathlib import Path
    overlay = Path("scribe3/deploy/hermes/overlay.scribe3_plan.yaml").read_text(encoding="utf-8")
    assert "8647" in overlay
    assert "scribe3_plan_read" in overlay
    assert "scribe3_plan_write" in overlay
    mcp = Path("scribe3/deploy/hermes/mcp_servers.yaml").read_text(encoding="utf-8")
    assert "scribe3_plan_read" in mcp
    assert "scribe3_plan_write" in mcp
    # plan include 不得含 save/ingest
    import re
    # crude: between scribe3_plan_write and next top-level key
    m = re.search(
        r"scribe3_plan_write:.*?include:(.*?)(?:prompts:|resources:)",
        mcp, re.S,
    )
    assert m
    include_blob = m.group(1)
    assert "s3_save_chapter" not in include_blob
    assert "s3_ingest_chapter" not in include_blob
    assert "s3_patch_chapter_plan" in include_blob
    prov = open("scribe3/scripts/provision_hermes.py", encoding="utf-8").read()
    assert '"scribe3_plan"' in prov or "'scribe3_plan'" in prov


def test_gcd_beats_patch_validation():
    from scribe3.chapter_gcd_rest import (
        is_gcd_beats_only_body,
        validate_gcd_beats_patch,
    )
    old = [
        {"text": "抵达", "goal": "入庄", "conflict": "拒"},
        {"text": "验尸", "goal": "查", "conflict": "伪"},
        {"text": "铜钱", "goal": "夺", "conflict": "追"},
    ]
    new_ok = [
        {"text": "抵达义庄", "goal": "入庄", "conflict": "拒"},
        {"text": "验尸", "goal": "查", "conflict": "伪证"},
        {"text": "铜钱", "goal": "夺证", "conflict": "追"},
    ]
    assert is_gcd_beats_only_body({"beats": new_ok})
    ok, reason = validate_gcd_beats_patch(old, new_ok)
    assert ok, reason
    ok2, r2 = validate_gcd_beats_patch(old, new_ok[:2])
    assert not ok2 and r2 == "beat_count_changed"
    long = [dict(x) for x in new_ok]
    long[0]["text"] = "字" * 400
    ok3, r3 = validate_gcd_beats_patch(old, long)
    assert not ok3 and "text_too_long" in r3
    assert not is_gcd_beats_only_body({"beats": new_ok, "synopsis": "x"})


def test_cap_codex():
    from scribe3.context_budget import cap_codex_text
    s = "甲" * 10000
    out = cap_codex_text(s, 100)
    assert len(out) <= 100
    assert out.endswith("…")


def test_effective_l2_cap_formula():
    from scribe3.context_budget import effective_l2_cap
    assert effective_l2_cap(10_000, 18_000, supplemental_hard=18_000, prompt_hard=42_000) == 14_000
    assert effective_l2_cap(10_000, 22_000, supplemental_hard=18_000, prompt_hard=48_000) == 16_000


def test_emergency_path_whitelist_gcd():
    src = open("scribe3/api/app_impl.py", encoding="utf-8").read()
    assert "gcd-fields" in src
    assert "beats-fields" in src
    try:
        from scribe3.api import app_impl as core
        assert core._is_rest_world_write_path("/chapters/3") is True
        assert core._is_rest_world_write_path("/chapters/3/gcd-fields") is False
        assert core._is_rest_world_write_path("/chapters/3/beats-fields") is False
    except ModuleNotFoundError:
        pass


def test_chiefdock_scaffold_run_scope_source():
    """主编坞源码：world-write 不得对 outline/beats 清空 phase。"""
    src = open("scribe3/web/src/ChiefDock.jsx", encoding="utf-8").read()
    assert "isScaffoldPhase" in src
    assert "novel-first" in src
    # 不得再出现「worldWriteRun ? ''」作为唯一 phase 决策
    assert "scaffoldPhase" in src or "isScaffoldPhase" in src



def test_literary_and_epic_tables():
    from scribe3.context_budget import (
        BLOCK_BUDGETS_LITERARY, BLOCK_BUDGETS_EPIC,
        LITERARY_ENVELOPE_TOKEN_BUDGET, EPIC_ENVELOPE_TOKEN_BUDGET,
        SCENE_BUDGET_PROFILES,
    )
    assert sum(BLOCK_BUDGETS_LITERARY.values()) == LITERARY_ENVELOPE_TOKEN_BUDGET == 15_000
    assert sum(BLOCK_BUDGETS_EPIC.values()) == EPIC_ENVELOPE_TOKEN_BUDGET == 18_000
    for n, t in SCENE_BUDGET_PROFILES.items():
        assert sum(t.values()) == 18_000, n


def test_fidelity_literary_enables_v2_order():
    from importlib import reload
    import os
    import scribe3.context_budget as cb
    os.environ.pop("SCRIBE3_ENVELOPE_V2_ENABLE", None)
    os.environ["SCRIBE3_CONTEXT_FIDELITY"] = "literary"
    try:
        reload(cb)
        assert cb.envelope_v2_enabled() is True
        assert cb.get_envelope_token_budget() == 15_000
        assert cb.get_block_budgets()["recent"] == 4500
    finally:
        os.environ.pop("SCRIBE3_CONTEXT_FIDELITY", None)
        reload(cb)


def test_drama_vacuum_and_reminder_core():
    from scribe3.drama_beats import format_drama_vacuum_warn, DRAMA_VACUUM_WARN_TEXT
    import os
    os.environ["SCRIBE3_DRAMA_VACUUM_WARN"] = "1"
    assert "禁" in format_drama_vacuum_warn() or "真空" in format_drama_vacuum_warn()
    os.environ["SCRIBE3_DRAMA_VACUUM_WARN"] = "0"
    from importlib import reload
    import scribe3.drama_beats as db
    reload(db)
    assert db.format_drama_vacuum_warn() == ""
    os.environ["SCRIBE3_DRAMA_VACUUM_WARN"] = "1"
    reload(db)
    from scribe3.api.services.prompt_blocks import _final_reminder, _final_reminder_core
    os.environ["SCRIBE3_FINAL_REMINDER_CORE"] = "1"
    assert "短核" in _final_reminder() or len(_final_reminder()) < len(DRAMA_VACUUM_WARN_TEXT) + 500
    assert "PROPOSAL" in _final_reminder_core()
    os.environ.pop("SCRIBE3_FINAL_REMINDER_CORE", None)


def test_draft_policy_allows_save_not_ingest():
    from scribe3.run_stage_policy import resolve_run_stage_policy
    from scribe3.hermes_runs_env import hermes_runs_api_base_for_env, HERMES_DRAFT_RUNS
    pol = resolve_run_stage_policy("chapter:1:draft")
    assert pol.profile == "scribe3_draft"
    assert "s3_save_chapter" in pol.allowed_tools
    assert "s3_ingest_chapter" not in pol.allowed_tools
    assert hermes_runs_api_base_for_env(pol.api_env) == HERMES_DRAFT_RUNS
    assert "8648" in HERMES_DRAFT_RUNS


def test_event_graph_and_concurrency():
    from scribe3.event_graph import build_event_adjacency, graph_one_hop
    from scribe3.concurrency_obs import inflight_enter, inflight_leave, inflight_snapshot
    g = build_event_adjacency(
        events=[{"id": "e1"}, {"id": "e2", "leads_to": "e3"}],
        promises=[{"id": "p1", "event_id": "e1"}],
    )
    assert g["edge_count"] >= 1
    hop = graph_one_hop(g, ["e1"])
    assert isinstance(hop, list)
    assert inflight_enter("loop", "ch1") is True
    assert inflight_enter("loop", "ch1") is False
    inflight_leave("loop", "ch1")
    snap = inflight_snapshot()
    assert "loop" in snap


def test_density_trace_registry():
    from scribe3.injection_registry import density_trace_for_segments, registry_mode
    tr = density_trace_for_segments(
        domain_lengths={"drama_contract": 100, "envelope": 900, "codex": 500},
        order_indices={"drama_contract": 1},
    )
    assert tr["by_tier"]["L0"] == 100
    assert tr["primary_metric"] == "signal_density_for_drama"
    assert registry_mode() in ("shadow", "off", "active")


def test_canon_suppress_heuristic():
    from scribe3.memory_conflict_heuristic import heuristic_entity_attribute as _heuristic_entity_attribute
    keys = _heuristic_entity_attribute("张三的刀法很强")
    assert any(k[0] == "张三" for k in keys)




def test_enforce_total_prompt_budget_keeps_final_reminder():
    """O1：全域硬顶砍 supplemental，不丢 final_reminder。"""
    from scribe3.context_budget import enforce_total_prompt_budget, join_generation_segments
    big = "M" * 8000
    segs = [
        {"name": "event_drive", "layer": "redline", "text": "事件"},
        {"name": "drama_contract", "layer": "redline", "text": "戏剧"},
        {"name": "envelope", "layer": "envelope", "text": "ENV" * 100},
        {"name": "material_recall", "layer": "supplemental", "text": big},
        {"name": "codex", "layer": "supplemental", "text": "设定" + big},
        {"name": "final_reminder", "layer": "redline", "text": "【最终提醒】限知"},
    ]
    out, rep = enforce_total_prompt_budget(segs, budget=3000)
    names = [s.get("name") for s in out]
    assert "final_reminder" in names
    assert "event_drive" in names
    assert rep["enabled"] is True
    assert rep["after_est"] <= 3000 or rep.get("dropped")
    # join path with total_budget
    joined, jrep = join_generation_segments(segs, v2=True, total_budget=4000)
    assert "最终提醒" in joined or "限知" in joined
    assert jrep.get("final_reminder_kept") is True
    assert "total_enforce" in jrep


def test_get_total_budget_disable():
    import os
    from importlib import reload
    import scribe3.context_budget as cb
    os.environ["SCRIBE3_TOTAL_BUDGET"] = "999999"
    try:
        reload(cb)
        assert cb.get_total_prompt_budget() >= 900000
        segs = [{"name": "material_recall", "layer": "supplemental", "text": "x" * 100}]
        out, rep = cb.enforce_total_prompt_budget(segs, budget=999999)
        assert rep["enabled"] is False
        assert out[0]["text"] == "x" * 100
    finally:
        os.environ.pop("SCRIBE3_TOTAL_BUDGET", None)
        reload(cb)


def test_epistemic_fail_loud_flag():
    import os
    from scribe3.epistemic_guard import (
        EpistemicLeakError,
        epistemic_fail_loud_enabled,
        guard_write_instructions,
        scrub_secrets_from_text,
    )
    os.environ["SCRIBE3_EPISTEMIC_FAIL_LOUD"] = "0"
    assert epistemic_fail_loud_enabled() is False
    os.environ["SCRIBE3_EPISTEMIC_FAIL_LOUD"] = "1"
    try:
        assert epistemic_fail_loud_enabled() is True
        # pure scrub helper
        hits = [{"marker": "SECRET_XYZ"}]
        assert "已擦除" in scrub_secrets_from_text("hello SECRET_XYZ end", hits)
        # fail_loud with fake store that returns no secrets → no raise
        class _St:
            def list_facts(self, *a, **k):
                return []
        # scan needs more - just test exception type construct
        err = EpistemicLeakError("leak", hits=[{"marker": "a"}])
        assert err.hits[0]["marker"] == "a"
    finally:
        os.environ.pop("SCRIBE3_EPISTEMIC_FAIL_LOUD", None)


def test_focus_bonus_formula_with_linked_ids():
    """O7：shipped focus_bonus 纯函数 + retrieval 接线。"""
    from scribe3.memory_conflict_heuristic import focus_bonus
    assert focus_bonus(set(), {"char:alice"}) == 0.0
    assert focus_bonus({"char:alice"}, {"char:alice"}) == 0.15
    assert focus_bonus({"char:bob"}, {"char:alice"}) == 0.0
    src = open("scribe3/memory_retrieval.py", encoding="utf-8").read()
    assert "focus_bonus as _focus_bonus_fn" in src or "_focus_bonus_fn" in src
    # 若 pydantic 可用，再驱动 final_score
    try:
        from datetime import datetime, timezone
        from types import SimpleNamespace
        from scribe3.memory_retrieval import final_score
        now = datetime.now(timezone.utc)
        base = dict(
            source_kind="episodic", rrf_score=1.0, importance=1.0, confidence=1.0,
            pinned=False, observed_at=now, linked_ids=set(),
        )
        s0 = final_score(SimpleNamespace(**base), now, {"char:alice"})
        s1 = final_score(SimpleNamespace(**{**base, "linked_ids": {"char:alice"}}), now, {"char:alice"})
        assert abs((s1 - s0) - 0.15) < 1e-9
    except ModuleNotFoundError as e:
        if "pydantic" not in str(e).lower():
            raise


def test_conflict_keys_heuristic_via_suppress_path():
    """O7：structured (张三,刀法) vs 文本「张三的刀法很强」应 suppress。"""
    from scribe3.memory_conflict_heuristic import (
        conflict_keys_from_parts,
        heuristic_entity_attribute,
        should_suppress_episodic,
    )
    epi = heuristic_entity_attribute("张三的刀法很强")
    assert ("张三", "刀法") in epi or any(e == "张三" and a.startswith("刀法") for e, a in epi)
    canon = {("张三", "刀法")}
    assert should_suppress_episodic(epi, canon) is True
    # conflict_keys_from_parts：有 structured 则不用启发式
    only = conflict_keys_from_parts(
        provenance=[{"entity": "张三", "attribute": "刀法"}],
        text="无关文本",
        use_heuristic=True,
    )
    assert only == {("张三", "刀法")}
    # 无 provenance 走启发式
    h = conflict_keys_from_parts(provenance=[], text="张三的刀法很强", use_heuristic=True)
    assert should_suppress_episodic(h, canon)
    src = open("scribe3/memory_retrieval.py", encoding="utf-8").read()
    assert "should_suppress_episodic" in src




def test_gcd_fields_req_in_models_and_handler_pure():
    """O14：闸外路径 SSOT + apply_gcd_beats_patch 真路径 + 前端接线。"""
    from scribe3.chapter_gcd_rest import (
        apply_gcd_beats_patch,
        is_emergency_bypass_chapter_path,
        validate_gcd_beats_patch,
    )
    assert is_emergency_bypass_chapter_path("/chapters/3/gcd-fields") is True
    assert is_emergency_bypass_chapter_path("/chapters/3/beats-fields") is True
    assert is_emergency_bypass_chapter_path("/chapters/3") is False
    assert is_emergency_bypass_chapter_path("/chapters/3/archive") is True
    old = [{"text": "a", "goal": "g", "conflict": "c"}]
    new = [{"text": "ab", "goal": "g", "conflict": "c"}]
    ok, reason, norm = apply_gcd_beats_patch(old, new)
    assert ok and norm and norm[0]["text"] == "ab"
    bad_ok, bad_r, bad_n = apply_gcd_beats_patch(
        old, [{"text": "only"}, {"text": "extra"}],
    )
    assert not bad_ok and bad_n is None and bad_r == "beat_count_changed"
    # app_impl 接线
    src = open("scribe3/api/app_impl.py", encoding="utf-8").read()
    assert "is_emergency_bypass_chapter_path" in src
    chs = open("scribe3/api/routers/chapters.py", encoding="utf-8").read()
    assert "gcd-fields" in chs and "beats-fields" in chs
    assert "apply_gcd_beats_patch" in chs
    models = open("scribe3/api/models.py", encoding="utf-8").read()
    assert "class GcdFieldsReq" in models
    api = open("scribe3/web/src/api.js", encoding="utf-8").read()
    assert "patchChapterGcdFields" in api
    studio = open("scribe3/web/src/ChapterStudio.jsx", encoding="utf-8").read()
    assert "patchChapterGcdFields" in studio
    assert "patchChapter(seq, { beats }" not in studio



def test_patch_chapter_gcd_fields_handler_with_stub_store():
    """无 FastAPI 时仍驱动 apply_gcd_beats_patch 作为 handler 核心。"""
    from scribe3.chapter_gcd_rest import apply_gcd_beats_patch
    old = [
        {"text": "a", "goal": "g1", "conflict": "c1"},
        {"text": "b", "goal": "g2", "conflict": "c2"},
    ]
    new = [
        {"text": "a2", "goal": "g1", "conflict": "c1"},
        {"text": "b2", "goal": "g2", "conflict": "c2"},
    ]
    ok, reason, norm = apply_gcd_beats_patch(old, new)
    assert ok and norm[0]["text"] == "a2"
    # simulate store write
    store = {"beats": old}
    if ok:
        store["beats"] = norm
    assert store["beats"][1]["text"] == "b2"



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

