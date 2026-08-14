"""设定库两层 persist 闸。禁止 Surreal。"""
from __future__ import annotations

from scribe3.iceberg import (
    evaluate_codex_ready,
    persist_codex_fields_blocked,
)


def test_incremental_stub_personality_250_passes():
    assert persist_codex_fields_blocked(
        "character",
        {"personality_detail": "慎" * 250},
        mode="incremental",
    ) is None


def test_incremental_three_chars_blocked():
    hit = persist_codex_fields_blocked(
        "character",
        {"personality_detail": "沉默"},
        mode="incremental",
    )
    assert hit and hit["code"] == "codex_thin_persist"


def test_pack_800_blocked():
    hit = persist_codex_fields_blocked(
        "term",
        {"definition": "是什么。不是什么。本书用法。边界。" + ("义" * 80)},
        mode="pack",
    )
    assert hit and any(m["id"] == "pack" for m in hit["missing"])


def test_empty_definition_not_gated_incremental():
    assert persist_codex_fields_blocked("term", {"name": "炉令"}, mode="incremental") is None


def test_short_definition_incremental_blocked():
    hit = persist_codex_fields_blocked(
        "term", {"definition": "祭火口头令" + ("短" * 8)}, mode="incremental",
    )
    assert hit and hit["code"] == "codex_thin_persist"


def test_evaluate_ready_stub_thin_ready():
    stub = evaluate_codex_ready("term", {"name": "炉令"})
    assert stub["status"] == "stub" and stub["ok"] is False
    thin = evaluate_codex_ready("term", {"name": "炉令", "definition": "短义"})
    assert thin["status"] == "thin"
    fat = (
        "是什么：铜炉祭火口头契约。不是什么：不是朝廷公文。本书用法：当场应声。"
        "边界：不得隔夜。" + ("义" * 1200)
    )
    ready = evaluate_codex_ready("term", {"name": "炉令", "definition": fat})
    assert ready["ok"] is True and ready["status"] == "ready"


def test_private_operation_rejected():
    hit = persist_codex_fields_blocked(
        "faction", {"private_operation": "旧垃圾桶"}, mode="incremental",
    )
    assert hit and any(m["id"] == "private_operation" for m in hit["missing"])


def test_faction_ideology_three_chars_blocked():
    hit = persist_codex_fields_blocked(
        "faction", {"ideology": "口号党"}, mode="incremental",
    )
    assert hit and hit["code"] == "codex_thin_persist"


def test_item_short_description_blocked():
    hit = persist_codex_fields_blocked(
        "item", {"description": "一把短刀"}, mode="incremental",
    )
    assert hit and hit["code"] == "codex_thin_persist"


def test_voice_pack_needs_two_sections():
    hit = persist_codex_fields_blocked(
        "voice", {"style_summary": "声" * 80}, mode="pack",
    )
    assert hit and any(m["id"] == "voice_sections" for m in hit["missing"])
    ok = persist_codex_fields_blocked(
        "voice",
        {
            "style_summary": "声" * 80,
            "catchphrases": ["嗯"],
            "tone_rules": ["短句"],
        },
        mode="pack",
    )
    assert ok is None


def test_rest_l1_short_definition_blocked():
    from scribe3.iceberg import persist_codex_fields_blocked
    hit = persist_codex_fields_blocked(
        "term", {"definition": "祭火口头令"}, mode="incremental",
    )
    assert hit and hit["code"] == "codex_thin_persist"


def test_rest_l1_stub_name_only_passes():
    from scribe3.iceberg import persist_codex_fields_blocked
    assert persist_codex_fields_blocked("character", {}, mode="incremental") is None
    assert persist_codex_fields_blocked("term", {}, mode="incremental") is None


def test_faction_short_origin_blocked():
    hit = persist_codex_fields_blocked(
        "faction", {"origin": "短源"}, mode="incremental",
    )
    assert hit and hit["code"] == "codex_thin_persist"


def test_no_faction_400_cap_symbol():
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "api" / "app_impl.py"
    assert "_FACTION_PROMPT_CHAR_CAP" not in src.read_text(encoding="utf-8")
    from scribe3.iceberg import INJECT_CAP
    assert INJECT_CAP["faction_public"] == 2500


def test_attach_codex_ready_payload():
    from scribe3.iceberg import attach_codex_ready, codex_ready_badge
    out = attach_codex_ready("term", {"name": "炉令"})
    assert out["codex_ready"]["status"] == "stub"
    badge = codex_ready_badge("term", {"name": "炉令"})
    assert badge["kind"] == "codex_ready" and badge["value"] == "空壳"
