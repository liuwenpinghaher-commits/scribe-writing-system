"""PR-UX1：世界真相树滤噪（纯逻辑，无 DB）。"""
from scribe3.truth_surface import (
    BRIDGE_SOURCE,
    WORLD_TRUTH_LABEL,
    format_fact_as_codex_title,
    tree_hide_must,
)


def test_hide_noise_attrs():
    assert tree_hide_must("获知") is True
    assert tree_hide_must("行动") is True
    assert tree_hide_must("from_knowledge") is True
    assert tree_hide_must("状态") is False
    assert tree_hide_must("origin") is False


def test_hide_bridge_only_by_source():
    # 势力字段名 + bridge source → 隐藏
    assert tree_hide_must("origin", BRIDGE_SOURCE) is True
    assert tree_hide_must("origin", "codex_bridge") is True
    # 同 attribute 但无 source / author → 不因 attribute 藏 bridge
    assert tree_hide_must("origin", None) is False
    assert tree_hide_must("origin", "author") is False
    # 禁止：attribute=获知 且 source=author 会藏（Must 接受属性滤副作用）
    assert tree_hide_must("获知", "author") is True


def test_show_engine_bypasses_all():
    assert tree_hide_must("获知", show_engine=True) is False
    assert tree_hide_must("origin", BRIDGE_SOURCE, show_engine=True) is False


def test_codex_title_secret_hides_value():
    t = format_fact_as_codex_title("role:焦三", "状态", "烫疤", secret=True)
    assert t == "焦三·状态"
    assert "烫疤" not in t


def test_codex_title_public():
    t = format_fact_as_codex_title("role:焦三", "状态", "铜炉发烫")
    assert t == "焦三·状态 = 铜炉发烫"


def test_world_truth_label_constant():
    assert WORLD_TRUTH_LABEL == "世界真相"
