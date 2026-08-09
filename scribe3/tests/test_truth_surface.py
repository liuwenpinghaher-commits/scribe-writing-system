"""PR-UX1 + PR-4：世界真相树滤噪与 classify_bucket（纯逻辑，无 DB）。"""
from scribe3.truth_surface import (
    BRIDGE_SOURCE,
    WORLD_TRUTH_LABEL,
    classify_bucket,
    format_fact_as_codex_title,
    tree_hide_must,
)


def test_classify_bucket_table():
    assert classify_bucket("codex_bridge", "origin") == "bridge"
    assert classify_bucket("ingest", "状态") == "ingest_noise"
    assert classify_bucket(None, "获知") == "ingest_noise"
    assert classify_bucket(None, "行动") == "ingest_noise"
    assert classify_bucket("author", "获知") == "author"  # 手写不藏
    assert classify_bucket("canon", "anything") == "author"
    assert classify_bucket(None, "state") == "state"
    assert classify_bucket(None, "状态") == "state"
    assert classify_bucket(None, "外貌") == "author"


def test_hide_noise_attrs():
    # null source + 噪音 attr → hide
    assert tree_hide_must("获知") is True
    assert tree_hide_must("行动") is True
    assert tree_hide_must("from_knowledge") is True
    assert tree_hide_must("状态") is False
    assert tree_hide_must("origin") is False


def test_hide_bridge_only_by_source():
    assert tree_hide_must("origin", BRIDGE_SOURCE) is True
    assert tree_hide_must("origin", "codex_bridge") is True
    assert tree_hide_must("origin", None) is False
    assert tree_hide_must("origin", "author") is False
    # PR-4 / UX1b：source=author 的「获知」不藏
    assert tree_hide_must("获知", "author") is False


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


def test_ingest_source_via_fact_dataclass():
    """PR-7: Fact.source=ingest 与 classify_bucket 对齐。"""
    from scribe3.ontology import Fact
    from scribe3.truth_surface import classify_bucket
    f = Fact("fact:x", "role:a", "行动", "跑", 1, source="ingest")
    assert classify_bucket(f.source, f.attribute) == "ingest_noise"


def test_backfill_predicate_matches_noise_only():
    """M2c 回填谓词：仅噪音 attr + 空 source 应匹配（纯逻辑对齐）。"""
    from scribe3.truth_surface import NOISE_ATTRS, classify_bucket, tree_hide_must
    assert "获知" in NOISE_ATTRS and "行动" in NOISE_ATTRS
    # 回填后 bucket 与树隐藏一致
    assert classify_bucket("ingest", "获知") == "ingest_noise"
    assert tree_hide_must("获知", "ingest") is True
    # 手写 author 获知仍不藏
    assert tree_hide_must("获知", "author") is False


def test_fact_item_bucket_and_source():
    from types import SimpleNamespace
    from scribe3.api.services.misc_helpers import _fact_item

    f = SimpleNamespace(
        id="fact:ab",
        entity_id="role:焦三",
        attribute="状态",
        value="烫疤",
        secret=False,
        valid_from=1,
        valid_to=None,
        leak_markers=[],
        source="author",
    )
    item = _fact_item(f)
    assert item["source"] == "author"
    assert item["bucket"] == "state"
    assert item["value"] == "烫疤"

    secret_f = SimpleNamespace(
        id="fact:sc", entity_id="role:焦三", attribute="底细", value="真身",
        secret=True, valid_from=1, valid_to=None, leak_markers=["破绽"], source=None,
    )
    hid = _fact_item(secret_f, reveal_secret=False)
    assert hid["value"] is None
    assert hid["leak_markers"] == []
    assert hid["bucket"] == "author"

