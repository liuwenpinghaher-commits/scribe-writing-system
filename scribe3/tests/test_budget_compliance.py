"""预算协调器合规断言：profile 完整性 + 运行时预算帽守卫。"""
import pytest
from scribe3.context_budget import (
    BLOCK_BUDGETS_V1, DEFAULT_ENVELOPE_TOKEN_BUDGET_V1,
    BLOCK_BUDGETS_V2, DEFAULT_ENVELOPE_TOKEN_BUDGET_V2,
    BLOCK_BUDGETS_NOVEL, NOVEL_ENVELOPE_TOKEN_BUDGET,
    BLOCK_BUDGETS_LITERARY, LITERARY_ENVELOPE_TOKEN_BUDGET,
    BLOCK_BUDGETS_EPIC, EPIC_ENVELOPE_TOKEN_BUDGET,
    SCENE_BUDGET_PROFILES,
    get_block_budgets, get_envelope_token_budget,
)
from scribe3.recall_service import _BUDGET_BY_TAG, budget_for

_ALL_PROFILES = {
    "V1": (BLOCK_BUDGETS_V1, DEFAULT_ENVELOPE_TOKEN_BUDGET_V1),
    "V2": (BLOCK_BUDGETS_V2, DEFAULT_ENVELOPE_TOKEN_BUDGET_V2),
    "NOVEL": (BLOCK_BUDGETS_NOVEL, NOVEL_ENVELOPE_TOKEN_BUDGET),
    "LITERARY": (BLOCK_BUDGETS_LITERARY, LITERARY_ENVELOPE_TOKEN_BUDGET),
    "EPIC": (BLOCK_BUDGETS_EPIC, EPIC_ENVELOPE_TOKEN_BUDGET),
}
_CANONICAL_KEYS = {
    "focus", "global", "canonical", "recent",
    "procedural", "reference", "uncertainty", "provenance",
}


@pytest.mark.parametrize("name,tbl_total", list(_ALL_PROFILES.items()))
def test_profile_sum_equals_declared_total(name, tbl_total):
    tbl, total = tbl_total
    assert sum(tbl.values()) == total, f"{name} 块合≠声明总额"


@pytest.mark.parametrize("name,tbl_total", list(_ALL_PROFILES.items()))
def test_profile_has_canonical_keys(name, tbl_total):
    tbl, _ = tbl_total
    assert set(tbl.keys()) == _CANONICAL_KEYS, f"{name} 键集不完整"


def test_scene_profiles_sum_to_v2():
    for pname, p in SCENE_BUDGET_PROFILES.items():
        assert sum(p.values()) == DEFAULT_ENVELOPE_TOKEN_BUDGET_V2, f"scene {pname} 总额偏离 V2"
        assert set(p.keys()) == _CANONICAL_KEYS


def test_budget_tag_covers_all_consumption_sites():
    required = {"playbook_codex", "discuss_codex", "canonical", "volume_intro", "ledger"}
    assert required <= set(_BUDGET_BY_TAG.keys())
    assert budget_for("playbook_codex") == 800


def test_runtime_envelope_consistent():
    assert get_envelope_token_budget() == sum(get_block_budgets().values())
