"""Run 卡纯函数：期望×实际×红绿。禁止本机 Surreal。"""
from __future__ import annotations

from scribe3.injection_registry import SEGMENT_REGISTRY
from scribe3.run_card import (
    build_gate_run_card,
    build_run_card,
    card_row_names,
    classify_actual,
    expected_for,
    make_facts,
    public_card,
    row_verdict,
    skip_reason_for,
    summarize_verdict,
)


def _row(card: dict, name: str) -> dict:
    for r in card["rows"]:
        if r["name"] == name:
            return r
    raise AssertionError(f"missing row {name}")


def test_registry_len_36():
    assert len(SEGMENT_REGISTRY) == 36
    names = card_row_names()
    assert "prefix" in names
    assert "benchmark_advisory" in names
    assert "identity" in names


def test_sample_1_story_move_flag_off_green():
    facts = make_facts(move_library=False, move_plan_approved=False)
    exp, reason = expected_for("story_move", facts)
    assert exp is False
    assert reason == "flag_off_or_plan_missing"
    card = build_run_card(facts=facts, attempted_names=set(), request_id="a" * 32)
    row = _row(card, "story_move")
    assert row["expected"] is False
    assert row["actual"] == "absent"
    assert row["verdict"] == "green"


def test_sample_2_drama_vacuum_has_goal_or_conflict_green():
    facts = make_facts(
        drama_vacuum_flag=True,
        beats_has_goal=True,
        beats_has_conflict=False,
        should_drama_vacuum=False,
    )
    exp, _ = expected_for("drama_vacuum", facts)
    assert exp is False
    card = build_run_card(facts=facts, attempted_names=set(), request_id="b" * 32)
    assert _row(card, "drama_vacuum")["verdict"] == "green"


def test_sample_3_chapter_one_no_ember_no_causal():
    facts = make_facts(chapter=1, has_prev_chapter=False, prev_end_hook=False)
    assert expected_for("story_ember", facts)[0] is False
    assert expected_for("story_causal", facts)[0] is False
    card = build_run_card(facts=facts, attempted_names=set(), request_id="c" * 32)
    assert _row(card, "story_ember")["verdict"] == "green"
    assert _row(card, "story_causal")["verdict"] == "green"


def test_sample_4_ch2_no_end_hook_ember_green_causal_expected():
    facts = make_facts(chapter=2, has_prev_chapter=True, prev_end_hook=False)
    assert expected_for("story_ember", facts) == (False, "no_end_hook")
    assert expected_for("story_causal", facts) == (True, "has_prev_chapter")
    card = build_run_card(
        facts=facts,
        attempted_names={"story_causal"},
        bud_rep={"story_causal_skip_reason": "empty_story_causal", "domain_lengths": {}},
        request_id="d" * 32,
    )
    ember = _row(card, "story_ember")
    causal = _row(card, "story_causal")
    assert ember["expected"] is False
    assert ember["verdict"] == "green"
    assert causal["expected"] is True
    assert causal["actual"] == "empty"
    assert causal["verdict"] == "red"
    assert causal["actual_reason"] == "empty_story_causal"


def test_sample_5_deduce_scene_truth_only():
    facts = make_facts(
        phase="deduce",
        has_scene_truth=True,
        has_deduction=True,
        has_materials=True,
    )
    assert expected_for("scene_truth_proj", facts) == (True, "phase_deduce")
    assert expected_for("deduction_final", facts)[0] is False
    assert expected_for("material_recall", facts)[0] is False
    card = build_run_card(
        facts=facts,
        attempted_names={"scene_truth_proj"},
        bud_rep={"domain_lengths": {"scene_truth_proj": 40}},
        request_id="e" * 32,
    )
    assert _row(card, "scene_truth_proj")["verdict"] == "green"
    assert _row(card, "deduction_final")["expected"] is False


def test_sample_6_draft_no_focalizer_revelation_not_expected():
    facts = make_facts(phase="draft", has_focalizer=False, has_unpublished_markers=True)
    assert expected_for("revelation_discipline", facts) == (False, "no_focalizer")
    card = build_run_card(facts=facts, attempted_names=set(), request_id="f" * 32)
    assert _row(card, "revelation_discipline")["verdict"] == "green"


def test_sample_7_empty_secret_guard_not_expected():
    facts = make_facts(secret_guard_nonempty=False)
    assert expected_for("secret_guard", facts) == (False, "secret_guard_empty")
    card = build_run_card(facts=facts, attempted_names=set(), request_id="g" * 32)
    assert _row(card, "secret_guard")["expected"] is False
    assert _row(card, "secret_guard")["verdict"] == "green"


def test_sample_8_benchmark_advisory_registered():
    facts = make_facts(phase="draft", benchmark_inject=True)
    exp, reason = expected_for("benchmark_advisory", facts)
    assert exp is True
    assert reason == "bench_on"
    card = build_run_card(
        facts=facts,
        attempted_names={"benchmark_advisory"},
        bud_rep={"domain_lengths": {"benchmark_advisory": 20}},
        request_id="h" * 32,
    )
    row = _row(card, "benchmark_advisory")
    assert row["expected_reason"] != "unregistered"
    assert row["verdict"] == "green"


def test_sample_9_reveal_only_secret_guard_expected_true():
    facts = make_facts(secret_guard_nonempty=True, has_unpublished_markers=False)
    assert expected_for("secret_guard", facts) == (True, "secret_guard_nonempty")
    card = build_run_card(
        facts=facts,
        attempted_names={"secret_guard"},
        bud_rep={"domain_lengths": {"secret_guard": 80}},
        request_id="i" * 32,
    )
    row = _row(card, "secret_guard")
    assert row["expected"] is True
    assert row["actual"] == "present"
    assert row["verdict"] == "green"
    assert row["quality"].get("reveal_only") is True
    assert "secret_guard" not in (card["summary"].get("unexpected_present") or [])


def test_o1_total_drop_expected_is_red():
    facts = make_facts(chapter=2, has_prev_chapter=True, prev_end_hook=True)
    card = build_run_card(
        facts=facts,
        attempted_names={"story_causal", "story_ember", "story_recall"},
        bud_rep={
            "domain_lengths": {"story_ember": 100, "story_recall": 200},
            "l2": {"dropped": []},
            "total_enforce": {"dropped": ["story_causal:total_drop"]},
        },
        request_id="j" * 32,
    )
    causal = _row(card, "story_causal")
    assert causal["expected"] is True
    assert causal["actual"] == "dropped"
    assert causal["actual_reason"] == "story_causal:total_drop"
    assert causal["verdict"] == "red"


def test_slogan_only_quality_not_row_red():
    facts = make_facts(
        contract_has_scene=True,
        contract_slogan_fields=("desire",),
        trace_count=1,
    )
    card = build_run_card(
        facts=facts,
        attempted_names={"narrative_contract"},
        bud_rep={"domain_lengths": {"narrative_contract": 120}},
        request_id="k" * 32,
    )
    row = _row(card, "narrative_contract")
    assert row["actual"] == "present"
    assert row["verdict"] == "green"
    assert "contract_slogan" in card["quality"]["flags"]
    assert row["quality"].get("slogan") is True


def test_rows_have_no_prompt_keys():
    facts = make_facts(secret_guard_nonempty=True, contract_has_scene=True)
    card = build_run_card(
        facts=facts,
        attempted_names={"secret_guard", "narrative_contract"},
        bud_rep={"domain_lengths": {"secret_guard": 40, "narrative_contract": 90}},
        texts={"narrative_contract": "【本章必须发生的场面】欲望：去侧门"},
        request_id="m" * 32,
    )
    pub = public_card(card)
    assert pub is not None
    assert "instructions" not in pub
    for row in pub["rows"]:
        assert "text" not in row
        assert "instructions" not in row
        assert "markers" not in row
    assert ":" not in card["run_id"]
    assert all(c in "0123456789abcdef" for c in card["run_id"])


def test_half_cut_stays_green():
    facts = make_facts(has_seed_words=True)
    kind, reason = classify_actual(
        "seed_words",
        domain_lengths={"seed_words": 40},
        skip_reason=None,
        dropped=["seed_words:tail_half"],
        attempted_names={"seed_words"},
    )
    assert kind == "present"
    assert reason == "half_cut"
    assert row_verdict(True, kind) == "green"


def test_skip_reason_for_nested_and_revelation_key():
    bud = {
        "revelation_skip_reason": "revelation_skip_no_focalizer",
        "story_move": {"skip_reason": "plan_missing"},
        "story_ember_skip_reason": "empty_story_ember",
    }
    assert skip_reason_for("revelation_discipline", bud) == "revelation_skip_no_focalizer"
    assert skip_reason_for("story_move", bud) == "plan_missing"
    assert skip_reason_for("story_ember", bud) == "empty_story_ember"


def test_emit_flag_off_skips_persist():
    import os
    from scribe3.run_card_store import emit_write_run_card

    class Boom:
        def create_only_write_run_card(self, *a, **k):
            raise AssertionError("flag off must not persist")

    os.environ["SCRIBE3_RUN_CARD"] = "0"
    try:
        out = emit_write_run_card(
            st=Boom(), work="main", chapter=1, facts=make_facts(), request_id="x",
        )
        assert out is None
    finally:
        os.environ.pop("SCRIBE3_RUN_CARD", None)


def test_write_layout_has_no_run_card_table():
    from pathlib import Path
    src = (
        Path(__file__).resolve().parents[1] / "web/src/WriteLayout.jsx"
    ).read_text(encoding="utf-8")
    assert "run-card-line" in src
    assert "rows.map" not in src
    assert "run_card.rows" not in src


def test_gate_card_same_shape():
    card = build_gate_run_card(
        work="main",
        chapter=3,
        kind="save",
        request_id="n" * 32,
        assemble_ok=False,
        gate_rows=[
            {"name": "craft_gate", "expected": True, "actual": "failed", "actual_reason": "craft_gate"},
            {"name": "persist_chapter", "expected": True, "actual": "absent", "actual_reason": "not_reached"},
        ],
    )
    assert card["kind"] == "save"
    assert card["verdict"] == "red"
    names = {r["name"] for r in card["rows"]}
    assert names == {"craft_gate", "persist_chapter"}
    assert "text" not in card["rows"][0]
    assert all(c in "0123456789abcdef" for c in card["run_id"])
