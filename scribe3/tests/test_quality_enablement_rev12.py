"""第一原则质量使能 rev.1.2 · 低内存单测（驱动 shipped 模块，无 Surreal）。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

# 强制 craft 门在本模块测中开启（conftest 可能钉 0）
@pytest.fixture(autouse=True)
def _craft_on(monkeypatch):
    monkeypatch.setenv("SCRIBE3_CRAFT_GATE", "1")
    monkeypatch.setenv("SCRIBE3_CRAFT_FINALIZE", "1")
    monkeypatch.setenv("SCRIBE3_FINALIZE_GATE", "1")
    monkeypatch.setenv("SCRIBE3_PROVENANCE_IN_PROMPT", "0")
    monkeypatch.setenv("SCRIBE3_CREATE_MODE", "standard")
    monkeypatch.setenv("SCRIBE3_EXPLORE_SOFT_SAVE", "1")
    monkeypatch.setenv("SCRIBE3_EXPLORE_INGEST_HOLD", "1")
    monkeypatch.setenv("SCRIBE3_DIRECTOR_CREATIVE", "1")
    monkeypatch.setenv("SCRIBE3_STRUCTURE_DIVERSITY_INJECT", "1")
    yield


# ── G1 budget tables ─────────────────────────────────────────────

def test_all_gen_budget_tables_provenance_zero():
    from scribe3.context_budget import (
        BLOCK_BUDGETS_V1,
        BLOCK_BUDGETS_V2,
        BLOCK_BUDGETS_NOVEL,
        BLOCK_BUDGETS_LITERARY,
        BLOCK_BUDGETS_EPIC,
        SCENE_BUDGET_PROFILES,
        SCENE_BUDGET_PROFILES_NOVEL,
        DEFAULT_ENVELOPE_TOKEN_BUDGET_V1,
        DEFAULT_ENVELOPE_TOKEN_BUDGET_V2,
        NOVEL_ENVELOPE_TOKEN_BUDGET,
    )
    tables = [
        ("V1", BLOCK_BUDGETS_V1, DEFAULT_ENVELOPE_TOKEN_BUDGET_V1),
        ("V2", BLOCK_BUDGETS_V2, DEFAULT_ENVELOPE_TOKEN_BUDGET_V2),
        ("NOVEL", BLOCK_BUDGETS_NOVEL, NOVEL_ENVELOPE_TOKEN_BUDGET),
        ("LIT", BLOCK_BUDGETS_LITERARY, sum(BLOCK_BUDGETS_LITERARY.values())),
        ("EPIC", BLOCK_BUDGETS_EPIC, sum(BLOCK_BUDGETS_EPIC.values())),
    ]
    for name, tbl, total in tables:
        assert tbl["provenance"] == 0, name
        assert sum(tbl.values()) == total, name
    for k, tbl in SCENE_BUDGET_PROFILES.items():
        assert tbl["provenance"] == 0, f"SCENE {k}"
        assert sum(tbl.values()) == 18_000
    for k, tbl in SCENE_BUDGET_PROFILES_NOVEL.items():
        assert tbl["provenance"] == 0, f"SCENE_N {k}"
        assert sum(tbl.values()) == NOVEL_ENVELOPE_TOKEN_BUDGET


def test_get_block_budgets_scene_dialogue_provenance_zero(monkeypatch):
    monkeypatch.setenv("SCRIBE3_SCENE_BUDGET_PROFILE", "dialogue_heavy")
    monkeypatch.setenv("SCRIBE3_ENVELOPE_NOVEL", "1")
    monkeypatch.setenv("SCRIBE3_ENVELOPE_V2_ENABLE", "1")
    from scribe3.context_budget import get_block_budgets, scene_budget_profile
    assert scene_budget_profile() == "dialogue_heavy"
    bb = get_block_budgets()
    assert bb.get("provenance") == 0
    assert "## 溯源" not in str(bb)


def test_density_provenance_hard_field_zero():
    from scribe3.injection_registry import density_trace_for_segments
    d = density_trace_for_segments(
        domain_lengths={
            "drama_contract": 100,
            "outline": 80,
            "phase_role": 20,
            "envelope": 500,
        },
        envelope_block_lengths={
            "canonical": 200,
            "recent": 100,
            "provenance": 0,
        },
        provenance_trace_items=12,
        provenance_in_prompt_chars=0,
    )
    assert d["provenance_in_prompt_tokens"] == 0
    assert d["provenance_in_prompt"] is False
    assert d["provenance_trace_items"] == 12
    assert "audit_meta_share" in d
    assert d["audit_share"] == d["audit_meta_share"]
    assert d["drama_core_share"] > 0


def test_outline_is_segment_l1():
    from scribe3.injection_registry import SEGMENT_REGISTRY
    m = {s.name: s for s in SEGMENT_REGISTRY}
    assert m["outline"].tier == "L1"


def test_overcap_drops_material_before_outline():
    from scribe3.context_budget import apply_l2_trim, GEN_SEGMENT_PROTECTED

    long = "甲" * 4000
    segs = [
        {"name": "event_drive", "layer": "redline", "text": "钉"},
        {"name": "envelope", "layer": "envelope", "text": "封" * 100},
        {"name": "material_recall", "layer": "supplemental", "text": long},
        {"name": "reference_craft", "layer": "supplemental", "text": long},
        {"name": "outline", "layer": "supplemental", "text": "大纲节拍：冲突与转折"},
        {"name": "brief_must", "layer": "supplemental", "text": "伏笔必达"},
        {"name": "voice_anchor", "layer": "supplemental", "text": "声口锚"},
    ]
    joined, rep = apply_l2_trim(
        segs, supplemental_hard=500, prompt_hard=800, l0_est=10, l1_est=50,
    )
    dropped = " ".join(rep.get("dropped") or [])
    # material / reference 应先被裁；outline 保护集在 GEN_SEGMENT_PROTECTED
    assert "outline" in GEN_SEGMENT_PROTECTED
    # 若有 drop，material 应先于 outline 出现在 dropped，或 outline 仍在 joined
    if "outline" in dropped:
        # 仅当 material 也已裁尽才允许
        assert "material_recall" in dropped or "reference_craft" in dropped
    assert "大纲节拍" in joined or "outline" not in dropped


# ── compact ──────────────────────────────────────────────────────

def test_volume_intro_compact_skips_when_synopsis_has_title():
    from scribe3.injection_compact import compact_volume_intro
    out = compact_volume_intro(
        "很长的卷纲" * 20,
        synopsis="第一卷 铜炉余烬 开篇",
        outline_text="",
        volume_title="铜炉余烬",
        volume_goal="找回铜匙",
    )
    assert out.startswith("卷钩：")
    assert len(out) <= 120


def test_volume_intro_compact_keeps_when_novel_volume():
    from scribe3.injection_compact import compact_volume_intro
    raw = "本卷独有氛围：雨夜码头与陌生铜腥。" * 5
    out = compact_volume_intro(
        raw,
        synopsis="另一条线",
        outline_text="节拍 A",
        volume_title="陌生卷名XYZ",
        volume_goal="从未出现过的目标句",
    )
    assert "雨夜码头" in out
    assert len(out) <= 400


def test_pressure_diff_omits_when_drama_covers_fork():
    from scribe3.injection_compact import pressure_diff_keys
    p = {"fork": "去或不去", "progress": "推进", "role": "主"}
    d = {"conflict": "去或不去", "progress": "推进", "role": "主"}
    emit = pressure_diff_keys(p, d)
    assert emit is not None
    assert "fork" not in emit
    # progress/role covered → empty emit → omit whole
    assert len(emit) == 0


def test_pressure_diff_keeps_full_when_drama_text_only():
    from scribe3.injection_compact import pressure_diff_keys
    p = {"fork": "x", "progress": "y"}
    assert pressure_diff_keys(p, None) is None


def test_phase_role_dedup_omits_when_overlap():
    from scribe3.injection_compact import dedup_phase_role
    craft = "禁 AI 腔与段末升华金句，身体先于标签写情绪。"
    pr = "禁 AI 腔与段末升华金句。"
    out = dedup_phase_role(pr, craft_text=craft, anti_slop_text="")
    assert out == ""


def test_avoid_merge_flag_default_on():
    from scribe3.injection_compact import should_omit_avoid_domain
    assert should_omit_avoid_domain() is True


# ── structure ────────────────────────────────────────────────────

def test_paragraph_isomorphism_fixture_hit():
    from scribe3.structure_style import find_paragraph_isomorphism
    # 三段：环境两句 + 无对白 + 开首同两字「夜色」
    p = (
        "夜色压在巷口。风从瓦缝里挤进来。\n\n"
        "夜色沉在井台。远处有狗叫了一声。\n\n"
        "夜色贴着墙根。铜腥味还没散尽。"
    )
    runs = find_paragraph_isomorphism(p, min_run=3)
    assert runs and runs[0]["count"] >= 3


def test_paragraph_isomorphism_fixture_miss():
    from scribe3.structure_style import find_paragraph_isomorphism
    # 三指纹必须不同：对白主导 / 长叙述 / 短动作
    p = (
        "「你来了？」\n「嗯。」\n「坐。」\n\n"
        + ("巷子里湿气贴着墙根往上爬，铜腥味混着雨水从石缝渗出来，"
           "远处更夫敲过二更，他仍站在门槛内数自己的呼吸，"
           "一、二、三，直到炉灰凉透。")
        + "\n\n他跑。雨砸在铁皮上。"
    )
    runs = find_paragraph_isomorphism(p, min_run=3)
    assert not runs


def test_ending_formula_fixture_hit():
    from scribe3.structure_style import detect_ending_formula, evaluate_structure_style
    # 「铜匙」在前 80% 出现 ≥2 次（2 字窗），末行短句意象回扣
    body = (
        "铜匙在怀里发烫。他摸了摸铜匙的齿边。"
        "雨还在下。铜匙又硌了一下。炉灰还温着。\n"
        "铜匙凉了。"
    )
    r = detect_ending_formula(body)
    assert r["hit"] is True, r
    rep = evaluate_structure_style(body)
    assert rep["ending_formula_hit"] is True
    assert rep["blocks_finalize"] is False  # default advisory


# ── craft explore + finalize ─────────────────────────────────────

class _EmptyStore:
    """最小 store：GATE-A/B 全缺。"""
    db_name = "test_explore"

    def get_intent(self):
        return {}

    def list_characters(self):
        return []

    def characters(self):
        return []

    def list_motifs(self):
        return []

    def list_promises(self):
        return []

    def open_promises(self):
        return []

    def effective_open_promises(self):
        return []

    def list_relations(self):
        return []

    def list_facts(self):
        return []

    def list_rules(self):
        return []

    def list_chapters(self):
        return [{"seq": 1}]

    def get_chapter(self, seq):
        return {"seq": seq, "prose": "", "synopsis": "", "beats": []}


def test_explore_soft_save_allows_incomplete_gate_a(monkeypatch):
    from scribe3.verify_craft_compliance import evaluate_save_craft_gate
    monkeypatch.setenv("SCRIBE3_CREATE_MODE", "explore")
    st = _EmptyStore()
    prose = "甲" * 100
    r = evaluate_save_craft_gate(st, 1, prose, create_mode="explore")
    assert r["allowed"] is True
    assert r.get("warnings") or r["code"] in ("ok", "ok_explore_soft")
    # 不得因 WARN-BUDGET 再 hard
    ga = (r.get("reports") or {}).get("gate_a") or {}
    blocking = ga.get("blocking") or []
    assert "A-WARN-BUDGET" not in blocking
    assert ga.get("ok") is not False or not blocking


def test_finalize_craft_hard_rejects_incomplete():
    from scribe3.verify_craft_compliance import evaluate_craft_finalize_gate
    st = _EmptyStore()
    r = evaluate_craft_finalize_gate(st, 1)
    assert r["allowed"] is False
    assert r["code"] == "craft_finalize"
    assert r.get("blocking")


def test_check_persist_gates_blocks_before_final(monkeypatch):
    from scribe3.finalize_gate import check_persist_gates
    st = _EmptyStore()
    r = check_persist_gates(st, 1, "甲" * 100, danger_draft=True)
    # danger 不旁路 craft
    assert r["allowed"] is False
    assert r["code"] == "craft_finalize"


def test_danger_draft_bypasses_qc_not_craft(monkeypatch):
    """质控可 bypass，但 craft 仍拦。"""
    from scribe3.finalize_gate import evaluate_finalize_gate, check_persist_gates
    # QC alone with danger
    qc = evaluate_finalize_gate(
        {"leaks": [], "issues": [], "degraded_stages": [], "visible_chars": 10},
        danger_draft=True,
    )
    assert qc["allowed"] is True
    # Combined
    st = _EmptyStore()
    r = check_persist_gates(st, 1, "甲" * 100, danger_draft=True)
    assert r["allowed"] is False


def test_explore_ingest_hold(monkeypatch):
    from scribe3.ingest_policy import decide_ingest, GateSnapshot
    monkeypatch.setenv("SCRIBE3_CREATE_MODE", "explore")
    monkeypatch.setenv("SCRIBE3_INGEST_POLICY", "auto_if_pass")
    st = _EmptyStore()
    d = decide_ingest(
        st, "book_explore_smoke", 1,
        gate=GateSnapshot(
            path="save", craft_allowed=True, finalize_verdict="pass",
            create_mode="explore",
        ),
        prose="乙" * 100,
    )
    assert d.action == "hold"
    assert d.hold_reason == "explore_draft"


# ── director ─────────────────────────────────────────────────────

def test_director_creative_suggestions_from_store():
    from scribe3.director import build_creative_suggestions

    class S:
        def effective_open_promises(self):
            return [
                {"id": "p1", "text": "铜匙齿边缺口", "status": "open"},
                {"id": "p2", "text": "灰狸不知钥匙", "status": "open"},
            ]

        def get_chapter(self, seq):
            return {"synopsis": "", "beats": []}

        def characters(self):
            return [{"id": "c1", "name": "覃灰七", "traits": {}}]

    sug = build_creative_suggestions(S(), work="main", seq=3, limit=3)
    assert len(sug) >= 1
    kinds = {s["kind"] for s in sug}
    assert "open_promise" in kinds or "drama_gap" in kinds or "char_pressure" in kinds


# ── DROP tier SSOT ───────────────────────────────────────────────

def test_l2_drop_tier_single_source():
    from scribe3.context_budget import (
        L2_DROP_TIER, L2_DROP_PRIORITY, GEN_SEGMENT_PROTECTED, _build_l2_drop_priority,
    )
    rebuilt = _build_l2_drop_priority()
    assert rebuilt == L2_DROP_PRIORITY
    # T3 > T2 > T1 > protected
    assert L2_DROP_PRIORITY["material_recall"] > L2_DROP_PRIORITY["craft"]
    assert L2_DROP_PRIORITY["craft"] > L2_DROP_PRIORITY["codex"]
    assert L2_DROP_PRIORITY["outline"] <= 10
    assert "outline" in GEN_SEGMENT_PROTECTED
    # 四档键齐全
    assert set(L2_DROP_TIER) == {"T3", "T2", "T1"}


def test_generation_forbidden_includes_provenance(monkeypatch):
    monkeypatch.setenv("SCRIBE3_PROVENANCE_IN_PROMPT", "0")
    from scribe3.api.services.write_assemble import (
        generation_forbidden_source_kinds,
        provenance_in_prompt_enabled,
    )
    assert provenance_in_prompt_enabled() is False
    assert "provenance" in generation_forbidden_source_kinds()
    monkeypatch.setenv("SCRIBE3_PROVENANCE_IN_PROMPT", "1")
    # re-import not needed — functions read env live
    assert "provenance" not in generation_forbidden_source_kinds() or provenance_in_prompt_enabled()


def test_entity_link_absent_from_graph_recall_sql():
    """静态：graph_recall 的 SELECT 不读 entity_link 列。"""
    import inspect
    from scribe3.store import recall as recall_mod
    src = inspect.getsource(recall_mod.RecallMixin.graph_recall)
    assert "entity_link.name" not in src
    assert "entity_link AS" not in src


def test_assembler_forbidden_provenance_no_header_in_text():
    """Assembler + forbidden 后 render 不含溯源标题。"""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from scribe3.context_assembler import ContextAssembler, render_envelope_text
    from scribe3.context_models import ContextFocus, ContextSnapshot

    st = MagicMock()
    st.db_name = "t"
    st.get_intent.return_value = {}
    st.list_chapters.return_value = []
    st.list_characters.return_value = []
    st.characters.return_value = []
    st.list_promises.return_value = []
    st.open_promises.return_value = []
    st.list_facts.return_value = []
    st.facts_at.return_value = []
    st.list_volumes.return_value = []
    st.get_chapter.return_value = {}
    st.list_events.return_value = []
    st.list_motifs.return_value = []
    st.list_relations.return_value = []
    st.list_rules.return_value = []

    snap = ContextSnapshot(
        session_id="s1",
        work="t",
        revision=1,
        thread_id="th1",
        entry="write",
        directory_path=(),
        focus=ContextFocus(type="chapter", id="1", label="ch1"),
        detail_route="",
        chapter=1,
        phase="draft",
        focalizer=None,
        previous_revision=None,
        navigation_id="n1",
        captured_at=datetime.now(timezone.utc),
        context_hash="h1",
    )
    asm = ContextAssembler(st, retriever=None, token_budget=10000)
    env = asm.assemble(
        snap, "写一章", mode="write",
        forbidden_source_kinds=("provenance",),
    )
    text = render_envelope_text(env)
    assert "## 溯源清单" not in text
    for b in env.blocks:
        if b.name == "provenance":
            assert not (b.text or "").strip()
