"""演绎纯函数:role normalize / truth revision / stale / 五层 / soft_gate。"""
from __future__ import annotations

import pytest

from scribe3.deduce_helpers import (
    DEDUCTION_HEADINGS,
    has_five_layer_headings,
    is_stale_deduction,
    missing_layer_headings,
    missing_roles,
    normalize_deductions,
    normalize_involved,
    normalize_role_id,
    prepare_deductions_for_write,
    should_bump_truth_revision,
    soft_gate_issues,
    stale_roles,
    stamp_deduction,
    truth_revision,
)


@pytest.mark.parametrize(
    "raw,want",
    [
        (None, ""),
        ("", ""),
        ("  ", ""),
        ("沈砚", "role:沈砚"),
        ("role:沈砚", "role:沈砚"),
        ("role: 沈砚 ", "role:沈砚"),
        ("ROLE:沈砚", "role:沈砚"),  # bare after colon
    ],
)
def test_normalize_role_id(raw, want):
    # ROLE:沈砚 → split → 沈砚 → role:沈砚
    assert normalize_role_id(raw) == want


def test_normalize_involved_dedupes_bare_and_prefixed():
    assert normalize_involved(["沈砚", "role:沈砚", "role:季棠", "季棠", ""]) == [
        "role:沈砚",
        "role:季棠",
    ]


def test_truth_revision_default_and_coerce():
    assert truth_revision(None) == 0
    assert truth_revision({}) == 0
    assert truth_revision({"scene_truth_revision": 3}) == 3
    assert truth_revision({"scene_truth_revision": "2"}) == 2
    assert truth_revision({"scene_truth_revision": "x"}) == 0


def test_stamp_and_stale():
    d = stamp_deduction({"character_id": "沈砚", "prose": "他看见闸。"}, 2)
    assert d["character_id"] == "role:沈砚"
    assert d["based_on_truth_rev"] == 2
    assert is_stale_deduction(d, 2) is False
    assert is_stale_deduction(d, 3) is True
    # 缺 stamp：rev>0 视为 stale
    assert is_stale_deduction({"character_id": "role:a", "prose": "x"}, 1) is True
    assert is_stale_deduction({"character_id": "role:a", "prose": "x"}, 0) is False
    # 空 prose 不算 stale
    assert is_stale_deduction({"character_id": "role:a", "prose": ""}, 5) is False


def test_missing_and_stale_roles_use_normalize():
    involved = ["沈砚", "role:季棠"]
    deds = [
        {"character_id": "role:沈砚", "prose": "投影A", "based_on_truth_rev": 1},
    ]
    assert missing_roles(involved, deds) == ["role:季棠"]
    assert stale_roles(involved, deds, 2) == ["role:沈砚"]
    assert stale_roles(involved, deds, 1) == []


def test_normalize_deductions_last_wins_and_stamp():
    raw = [
        {"character_id": "沈砚", "prose": "旧"},
        {"character_id": "role:沈砚", "prose": "新"},
        {"character_id": "role:季棠", "prose": "B"},
    ]
    out = normalize_deductions(raw, current_rev=4, stamp_missing_rev=True)
    by = {d["character_id"]: d for d in out}
    assert set(by) == {"role:沈砚", "role:季棠"}
    assert by["role:沈砚"]["prose"] == "新"
    assert by["role:沈砚"]["based_on_truth_rev"] == 4


def test_five_layer_headings():
    prose = "\n\n".join(f"### {h}\n内容" for h in DEDUCTION_HEADINGS)
    assert has_five_layer_headings(prose) is True
    assert missing_layer_headings("### 看到/听到\n仅一层") == [
        h for h in DEDUCTION_HEADINGS if h != "看到/听到"
    ]


def test_soft_gate_issues():
    ch = {
        "scene_truth": "真相",
        "scene_truth_revision": 2,
        "involved_characters": ["role:a", "role:b"],
        "deductions": [
            {"character_id": "role:a", "prose": "旧投影", "based_on_truth_rev": 1},
        ],
    }
    issues = soft_gate_issues(ch)
    assert issues["empty_truth"] is False
    assert issues["missing"] == ["role:b"]
    assert issues["stale"] == ["role:a"]
    assert issues["needs_attention"] is True
    assert soft_gate_issues({
        "scene_truth": "t",
        "scene_truth_revision": 1,
        "involved_characters": ["role:a"],
        "deductions": [{"character_id": "role:a", "prose": "ok", "based_on_truth_rev": 1}],
    })["needs_attention"] is False


def test_should_bump_truth_revision():
    assert should_bump_truth_revision("", "新真相") is True
    assert should_bump_truth_revision("同", "同") is False
    assert should_bump_truth_revision("  a  ", "a") is False


def test_prepare_deductions_does_not_stamp_unchanged_unstamped_prose():
    """全文重存不得把缺 based_on 的旧 prose stamp 成当前 rev（洗 stale）。"""
    existing = [
        {"character_id": "role:哑姑", "prose": "旧投影无 stamp"},
    ]
    incoming = [
        {"character_id": "哑姑", "prose": "旧投影无 stamp"},  # 同 prose，无 based_on
        {"character_id": "role:老范", "prose": "新角色投影"},  # 新 → 应 stamp
    ]
    out = prepare_deductions_for_write(incoming, existing, next_rev=5)
    by = {d["character_id"]: d for d in out}
    assert "based_on_truth_rev" not in by["role:哑姑"]
    assert is_stale_deduction(by["role:哑姑"], 5) is True
    assert by["role:老范"]["based_on_truth_rev"] == 5
    assert is_stale_deduction(by["role:老范"], 5) is False


def test_prepare_deductions_stamps_when_prose_changes():
    existing = [{"character_id": "role:a", "prose": "旧", "based_on_truth_rev": 1}]
    out = prepare_deductions_for_write(
        [{"character_id": "role:a", "prose": "新文"}], existing, next_rev=3)
    assert out[0]["based_on_truth_rev"] == 3


def test_prepare_inherits_existing_based_on_when_prose_unchanged():
    existing = [{"character_id": "role:a", "prose": "同", "based_on_truth_rev": 2}]
    out = prepare_deductions_for_write(
        [{"character_id": "a", "prose": "同"}], existing, next_rev=9)
    assert out[0]["based_on_truth_rev"] == 2
    assert is_stale_deduction(out[0], 9) is True


def test_inject_deduction_items_omits_stale_prose():
    from scribe3.deduce_helpers import inject_deduction_items

    ch = {
        "scene_truth_revision": 3,
        "deductions": [
            {"character_id": "role:a", "character_name": "甲",
             "prose": "新鲜全文", "based_on_truth_rev": 3},
            {"character_id": "role:b", "character_name": "乙",
             "prose": "过期全文", "based_on_truth_rev": 1},
        ],
    }
    items = inject_deduction_items(ch)
    by = {i["character_id"]: i for i in items}
    assert by["role:a"]["status"] == "fresh" and by["role:a"]["prose"] == "新鲜全文"
    assert by["role:b"]["status"] == "stale" and by["role:b"]["prose"] is None


def test_unaware_leak_markers_from_five_layers():
    from scribe3.deduce_helpers import unaware_leak_markers

    prose = "\n".join([
        "### 看到/听到", "灯灭了。",
        "### 知道", "门开着。",
        "### 以为(误读)", "以为风。",
        "### 做了/说了", "退了一步。",
        "### 没察觉的", "炉心真名已写在灰契上。借命正在发生。",
    ])
    ms = unaware_leak_markers(prose)
    assert any("炉心真名" in m for m in ms)
    assert any("借命" in m for m in ms)
