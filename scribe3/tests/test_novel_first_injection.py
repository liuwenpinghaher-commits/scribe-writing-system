"""Novel-first 写路径预算 / 物理序 / 脚手架 / GCD REST 纯函数与 shipped 路径。

设计：docs/plans/2026-08-11-novel-first-injection-quality-optimal.md rev.3.1
无 Surreal / 无 LLM / 无全量 pytest 依赖（可直接 python 跑本文件）。
"""
from __future__ import annotations

import os


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


def test_flag_off_keeps_v1_budget(monkeypatch=None):
    from scribe3 import context_budget as cb
    os.environ.pop("SCRIBE3_ENVELOPE_V2_ENABLE", None)
    os.environ.pop("SCRIBE3_ENVELOPE_NOVEL", None)
    assert cb.envelope_v2_enabled() is False
    assert sum(cb.get_block_budgets().values()) == 10_000
    assert cb.get_envelope_token_budget() == 10_000


def test_flag_on_v2_budget():
    from scribe3 import context_budget as cb
    os.environ["SCRIBE3_ENVELOPE_V2_ENABLE"] = "1"
    os.environ.pop("SCRIBE3_ENVELOPE_NOVEL", None)
    try:
        assert cb.envelope_v2_enabled() is True
        b = cb.get_block_budgets()
        assert sum(b.values()) == 18_000
        assert cb.get_envelope_token_budget() == 18_000
        assert b["canonical"] == 6800
        assert b["recent"] == 4000
    finally:
        os.environ.pop("SCRIBE3_ENVELOPE_V2_ENABLE", None)


def test_engine_passes_token_budget():
    """Engine/Assembler 接线：源码必传 budget；helpers 在 flag 下返回 18k/10k。"""
    eng_src = open("scribe3/context_engine.py", encoding="utf-8").read()
    assert "get_envelope_token_budget" in eng_src
    assert "get_block_budgets" in eng_src
    assert "ContextAssembler(" in eng_src
    assert "token_budget=tb" in eng_src or "token_budget=tb" in eng_src.replace(" ", "")
    asm_src = open("scribe3/context_assembler.py", encoding="utf-8").read()
    assert "block_budgets" in asm_src
    assert "self.token_budget" in asm_src

    from importlib import reload
    import scribe3.context_budget as cb

    os.environ["SCRIBE3_ENVELOPE_V2_ENABLE"] = "1"
    try:
        reload(cb)
        assert cb.get_envelope_token_budget() == 18_000
        assert sum(cb.get_block_budgets().values()) == 18_000
        assert cb.get_block_budgets()["canonical"] == 6800
    finally:
        os.environ.pop("SCRIBE3_ENVELOPE_V2_ENABLE", None)
        reload(cb)
    assert cb.get_envelope_token_budget() == 10_000
    assert sum(cb.get_block_budgets().values()) == 10_000


def test_effective_l2_cap_formula():
    from scribe3.context_budget import effective_l2_cap
    # min(18000, 42000 - 10000 - 18000) = min(18000, 14000) = 14000
    assert effective_l2_cap(10_000, 18_000, supplemental_hard=18_000, prompt_hard=42_000) == 14_000
    # novel: min(18000, 48000 - 10000 - 22000) = 16000
    assert effective_l2_cap(10_000, 22_000, supplemental_hard=18_000, prompt_hard=48_000) == 16_000


def test_apply_l2_trim_drops_material_keeps_final_reminder():
    from scribe3.context_budget import apply_l2_trim

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
    # 低优先级 material 应被裁
    assert any("material" in d for d in (rep.get("dropped") or [])) or "素材" not in joined
    # 禁止整串尾截导致 final 丢失
    assert not joined.endswith("XXXX")


def test_physical_order_names_v2():
    from scribe3.context_budget import (
        assert_physical_order_indices,
        generation_physical_order_names,
    )
    names = generation_physical_order_names(v2=True)
    idx = {n: i for i, n in enumerate(names)}
    assert_physical_order_indices({
        "event_drive": idx["event_drive"],
        "drama_contract": idx["drama_contract"],
        "envelope": idx["envelope"],
        "codex": idx["codex"],
        "final_reminder": idx["final_reminder"],
    })
    assert idx["event_drive"] < idx["drama_contract"] < idx["envelope"] < idx["codex"]
    assert idx["codex"] < idx["final_reminder"]


def test_scaffold_policy_excludes_save():
    from scribe3.run_stage_policy import (
        PLAN_SCAFFOLD_FORBIDDEN,
        resolve_run_stage_policy,
        scaffold_tools_exclude_save,
    )
    for phase in ("outline", "beats", "plan"):
        pol = resolve_run_stage_policy(f"chapter:3:{phase}")
        assert pol is not None
        assert scaffold_tools_exclude_save(pol) is True
        assert not (pol.allowed_tools & PLAN_SCAFFOLD_FORBIDDEN)
        assert "s3_patch_chapter_plan" in pol.allowed_tools
        assert "s3_save_chapter" not in pol.allowed_tools
        assert "s3_ingest_chapter" not in pol.allowed_tools


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
    # count change
    ok2, r2 = validate_gcd_beats_patch(old, new_ok[:2])
    assert not ok2 and r2 == "beat_count_changed"
    # too long
    long = [dict(x) for x in new_ok]
    long[0]["text"] = "字" * 400
    ok3, r3 = validate_gcd_beats_patch(old, long)
    assert not ok3 and "text_too_long" in r3
    # mixed meta not only-beats
    assert not is_gcd_beats_only_body({"beats": new_ok, "synopsis": "x"})


def test_cap_codex():
    from scribe3.context_budget import cap_codex_text
    s = "甲" * 10000
    out = cap_codex_text(s, 100)
    assert len(out) <= 100
    assert out.endswith("…")


def test_budget_report_no_cost_kpi():
    from scribe3.context_budget import build_budget_report
    r = build_budget_report(domain_lengths={"outline": 100}, order_indices={"codex": 4})
    assert r["primary_metric"] == "signal_density_for_drama"
    assert r["not_a_kpi"] == "tokens_saved"
    assert "envelope_token_budget" in r


def test_emergency_path_whitelist_gcd():
    """闸外路径名：gcd-fields（源码结构 + 可选 import）。"""
    src = open("scribe3/api/app_impl.py", encoding="utf-8").read()
    assert "gcd-fields" in src
    assert "beats-fields" in src
    try:
        from scribe3.api import app_impl as core
        assert core._is_rest_world_write_path("/chapters/3") is True
        assert core._is_rest_world_write_path("/chapters/3/gcd-fields") is False
        assert core._is_rest_world_write_path("/chapters/3/beats-fields") is False
    except ModuleNotFoundError:
        pass  # 宿主无 fastapi/httpx 时仅源码断言


if __name__ == "__main__":
    # lightweight runner without pytest
    import traceback
    failed = []
    for name, fn in list(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print("PASS", name)
        except TypeError:
            # monkeypatch signature skip
            try:
                fn()
                print("PASS", name)
            except Exception as e:
                print("FAIL", name, e)
                traceback.print_exc()
                failed.append(name)
        except Exception as e:
            print("FAIL", name, e)
            traceback.print_exc()
            failed.append(name)
    print("SUMMARY failed=", failed)
    raise SystemExit(1 if failed else 0)
