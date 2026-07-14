# scribe3/tests/test_codex_schema.py
"""CX-Task 1:设定字段注册表 codex_schema.py 的六条断言(先红后绿)。"""
import json

import pytest

from scribe3 import codex_schema
from scribe3.codex_schema import (
    FACTION_FIELDS,
    KINDS,
    CodexField,
    all_storage_keys,
    chief_only_keys,
    fields_for,
    prompt_keys,
    schema_for,
    secret_capable_keys,
    secret_flag_key,
)

EXPECTED_KEYS = {
    # 现有(保留)
    "name", "status", "ideology", "leader", "known_members", "public_face",
    "first_mention_chapter",
    # 拆桶三件
    "artifact_operation", "external_manipulation", "acceleration_methods",
    # 第一梯队
    "origin", "internal_factions", "structure", "key_figures", "artifacts",
    # 第二梯队
    "scale", "recruitment", "symbols", "motto", "goals", "world_rule_affinity",
    # 第三梯队
    "aliases", "timeline", "headquarters", "communication", "rituals", "secret_agenda",
    # deprecated
    "private_operation",
}

ARRAY_OBJECT_KEYS = {
    "internal_factions", "key_figures", "artifacts", "goals",
    "world_rule_affinity", "timeline",
}


def _by_key(fields, key):
    for f in fields:
        if f.key == key:
            return f
    raise AssertionError(f"字段 {key} 不存在于注册表")


def test_faction_fields_full_coverage():
    """① FACTION_FIELDS 含 spec 列出的全部字段(28 个:7+3+5+6+6+1 deprecated)。"""
    actual_keys = {f.key for f in FACTION_FIELDS}
    assert actual_keys == EXPECTED_KEYS
    assert len(FACTION_FIELDS) == len(EXPECTED_KEYS) == 28
    # KINDS 登记且 fields_for 可取
    assert KINDS["faction"] is FACTION_FIELDS
    assert fields_for("faction") is FACTION_FIELDS
    with pytest.raises(KeyError):
        fields_for("no_such_kind")


def test_secret_capable_fields_have_derived_flag_key():
    """② 每个 secret_capable 字段都有伴生 bool 键 f"{key}_secret",由 secret_flag_key() 派生。"""
    expected_secret_fields = {
        "artifact_operation", "external_manipulation", "acceleration_methods",
        "origin", "secret_agenda", "private_operation",
    }
    actual_secret_fields = set(secret_capable_keys("faction"))
    assert actual_secret_fields == expected_secret_fields

    storage_keys = set(all_storage_keys("faction"))
    for key in actual_secret_fields:
        flag_key = secret_flag_key(key)
        assert flag_key == f"{key}_secret"
        # 伴生旗标键不是手写的 CodexField,而是通过 all_storage_keys 派生登记
        assert flag_key in storage_keys
        assert flag_key not in {f.key for f in FACTION_FIELDS}   # 确认"不手写"

    # 非 secret_capable 字段不应有伴生旗标键混入
    non_secret = _by_key(FACTION_FIELDS, "name")
    assert not non_secret.secret_capable
    assert secret_flag_key("name") not in storage_keys


def test_schema_for_is_json_serializable_with_full_metadata():
    """③ schema_for('faction') 返回可 JSON 序列化的元数据,字段齐全。"""
    schema = schema_for("faction")
    dumped = json.dumps(schema, ensure_ascii=False)   # 不抛异常即证明可序列化
    reloaded = json.loads(dumped)
    assert reloaded == schema

    required_meta_keys = {"key", "label", "type", "secret_capable", "in_prompt",
                           "desc", "enum", "item_schema", "deprecated", "chief_only"}
    for entry in schema:
        assert required_meta_keys <= entry.keys()
        assert isinstance(entry["key"], str) and entry["key"]
        assert isinstance(entry["label"], str) and entry["label"]
        assert isinstance(entry["desc"], str) and entry["desc"]   # 每字段都要有说明


def test_array_object_fields_have_nonempty_item_schema():
    """④ array<object> 字段的 item_schema 非空,且每个子字段有 key/label/type。"""
    schema_by_key = {e["key"]: e for e in schema_for("faction")}
    for key in ARRAY_OBJECT_KEYS:
        field = _by_key(FACTION_FIELDS, key)
        assert field.type == "array<object>"
        assert field.item_schema and len(field.item_schema) > 0
        for sub in field.item_schema:
            assert isinstance(sub, CodexField)
            assert sub.key and sub.label and sub.type

        entry = schema_by_key[key]
        assert entry["item_schema"] and len(entry["item_schema"]) > 0
        for sub_dict in entry["item_schema"]:
            assert sub_dict["key"] and sub_dict["label"] and sub_dict["type"]


def test_enum_fields_have_nonempty_enum_list():
    """⑤ enum 字段(status/structure.type/key_figures[].status)的 enum 列表非空。"""
    status_field = _by_key(FACTION_FIELDS, "status")
    assert status_field.type == "enum"
    assert status_field.enum == ("active", "dissolved", "dormant", "reformed")

    structure_field = _by_key(FACTION_FIELDS, "structure")
    structure_type_field = _by_key(structure_field.item_schema, "type")
    assert structure_type_field.type == "enum"
    assert structure_type_field.enum == ("金字塔", "扁平", "蜂窝", "双头")

    key_figures_field = _by_key(FACTION_FIELDS, "key_figures")
    kf_status_field = _by_key(key_figures_field.item_schema, "status")
    assert kf_status_field.type == "enum"
    assert kf_status_field.enum == ("active", "dissipated", "dead")

    goals_field = _by_key(FACTION_FIELDS, "goals")
    goals_status_field = _by_key(goals_field.item_schema, "status")
    assert goals_status_field.type == "enum"
    assert goals_status_field.enum == ("planned", "ongoing", "done", "failed")


def test_deprecated_field_marked_and_excluded_from_prompt():
    """⑥ deprecated 字段标记为 deprecated=True 且 in_prompt=False(不进 prompt,不进新建表单)。"""
    legacy = _by_key(FACTION_FIELDS, "private_operation")
    assert legacy.deprecated is True
    assert legacy.in_prompt is False
    assert legacy.secret_capable is True   # 仍受限知掩码,只是不再进 prompt/新表单
    assert legacy.chief_only is False      # deprecated ≠ chief_only,两个维度互相独立

    prompt_field_keys = set(prompt_keys("faction"))
    assert "private_operation" not in prompt_field_keys

    # in_prompt=False 目前只有一类,逐一钉死(新增第二类必须显式改这里,防有人顺手关掉
    # 某字段的注入、或反过来把红线字段打开):deprecated 的旧垃圾桶字段 private_operation。
    #
    # secret_agenda 不在这里(2026-07-15 U-003 三档可见性重构,推翻上一版做法):
    # 上一版曾把它也 in_prompt=False 整个关出 prompt——结果连"仅主编可见"的"主编"都
    # 看不见它了,太钝。现在它 in_prompt=True(恢复默认,照常出现在 prompt_keys 里,
    # 会注入作者/主编对话),真正的保护改用 chief_only=True——app.py
    # `_faction_prompt_block` 据此在 for_generation=True(生成/限知续写路径)时结构性
    # 永不注入,与 in_prompt 完全独立的第二道门。见下一测试 + test_codex_prompt_adversarial.py
    # 的 test_secret_agenda_never_injected_in_generation_path_even_with_a_knows_edge。
    NOT_IN_PROMPT = {"private_operation"}
    for f in FACTION_FIELDS:
        if f.key in NOT_IN_PROMPT:
            assert f.in_prompt is False, f"{f.key} 应结构性不进 prompt"
            assert f.key not in prompt_field_keys
        else:
            assert f.in_prompt is True
            assert f.key in prompt_field_keys


def test_chief_only_field_pinned_to_secret_agenda_and_independent_of_deprecated():
    """U-003 三档可见性(2026-07-15)新增维度:chief_only 是独立于 in_prompt/deprecated
    的第三个轴,当前只钉死 secret_agenda 一个字段。private_operation 虽然也
    secret_capable 且 deprecated,但**不是** chief_only——它只是"旧垃圾桶字段不再用",
    不是"仅主编可见"这个更强的可见性档位,两码事不能混为一谈。"""
    assert chief_only_keys("faction") == ("secret_agenda",)

    agenda = _by_key(FACTION_FIELDS, "secret_agenda")
    assert agenda.chief_only is True
    assert agenda.secret_capable is True
    assert agenda.in_prompt is True    # 恢复默认:出现在作者/主编对话的 prompt 里
    assert agenda.deprecated is False
    assert "secret_agenda" in prompt_keys("faction")
    assert "secret_agenda" in secret_capable_keys("faction")

    for f in FACTION_FIELDS:
        if f.key != "secret_agenda":
            assert f.chief_only is False, f"{f.key} 不应被误标为 chief_only"

    # schema_for() 的 JSON 也要带上 chief_only,供前端渲染"仅主编可见"徽标。
    schema = {e["key"]: e for e in schema_for("faction")}
    assert schema["secret_agenda"]["chief_only"] is True
    assert schema["private_operation"]["chief_only"] is False


def test_status_enum_matches_migration_027_assert():
    """status 枚举值须与既有 migration 027 的 ASSERT 同源(回归锚点,勿改)。"""
    status_field = _by_key(FACTION_FIELDS, "status")
    assert set(status_field.enum) == {"active", "dissolved", "dormant", "reformed"}


def test_array_object_subfield_names_pinned():
    """子字段名逐字钉死(2026-07-14):这些名字来自作者原始需求,且一旦进 SCHEMAFULL migration
    就固化成 DB 列名——改名要付真实数据迁移的代价。spec 初稿曾把它们简写错,靠人工核对才发现。"""
    from scribe3.codex_schema import FACTION_FIELDS
    by_key = {f.key: f for f in FACTION_FIELDS}
    sub = lambda k: tuple(s.key for s in (by_key[k].item_schema or ()))

    assert sub("key_figures") == (
        "name", "generation", "fragment_decay_rate", "status", "known_abilities")
    assert sub("artifacts") == (
        "artifact_name", "artifact_type", "current_power_level", "decay_rate",
        "last_transfer_chapter")
    assert sub("internal_factions") == ("name", "claim", "representative", "power_share")
    assert sub("structure") == ("type", "core_size", "decision_mechanism", "succession")
    assert sub("goals") == ("phase", "target", "status")
    assert sub("world_rule_affinity") == ("rule_name", "affinity_type", "note")
    assert sub("timeline") == ("chapter", "event")
