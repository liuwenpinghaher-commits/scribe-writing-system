"""MCP 设定写面与 Codex 注册表保持一致的回归门禁。"""
from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

import yaml

import pytest

import scribe3.mcp as M
from scribe3.codex_schema import all_storage_keys
from scribe3.ontology import Entity


CREATE_TOOLS = {
    "character": M.s3_add_character,
    "faction": M.s3_add_faction,
    "item": M.s3_add_item,
    "term": M.s3_add_term,
    "world_rule": M.s3_add_world_rule,
}


class _AcceptCtx:
    async def elicit(self, *args, **kwargs):
        return type("_R", (), {"action": "accept"})()


@pytest.mark.parametrize("kind", sorted(CREATE_TOOLS))
def test_mcp_codex_create_tool_exposes_every_registered_storage_field(kind):
    """新建设定表单交给主编后，主编工具必须实际接收每个非废弃字段。"""
    params = set(inspect.signature(CREATE_TOOLS[kind]).parameters)
    missing = set(all_storage_keys(kind)) - params
    assert not missing, f"s3_add_{kind} 缺少注册字段: {sorted(missing)}"


def test_mcp_generic_codex_patch_accepts_registry_driven_fields():
    """完整档案的任意注册字段必须能经同一待批写工具送到正确的领域存储。"""
    tool = getattr(M, "s3_patch_codex")
    assert {"kind", "name", "fields"} <= set(inspect.signature(tool).parameters)


def test_hermes_author_profile_exposes_generic_codex_patch_tool():
    """工具已注册但未进入 Hermes 写 profile 等同于作者在真实 UI 中仍不可用。"""
    config = Path(__file__).parents[1] / "deploy" / "hermes" / "mcp_servers.yaml"
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    include = data["scribe3_write"]["tools"]["include"]
    assert "s3_patch_codex" in include


def test_mcp_add_character_persists_complete_registered_profile(store):
    """角色新建时，主编不可只写姓名而丢弃作者在表单中已填的档案字段。"""
    M.set_store(store)
    result = asyncio.run(M.s3_add_character(
        _AcceptCtx(), "role:林雾", "林雾",
        aliases=["阿雾"], appearance="雨衣袖口磨白", personality_detail="谨慎却不肯放弃",
        personality_tags=["谨慎", "倔强"], backstory="曾在盐场失踪三日", backstory_secret=True,
        surface_goal="找回姐姐", deep_need="承认自己也需要帮助", fear="再次被遗弃",
        internal_conflict="要独自冒险还是求援", abilities=["辨认潮声"], weaknesses=["怕深水"],
        importance="主角", first_appearance=1,
    ))
    assert result["status"] == "written"
    character = next(row for row in store.characters() if row.name == "林雾")
    assert character.traits == {
        "backstory": "曾在盐场失踪三日", "backstory_secret": True,
        "aliases": ["阿雾"], "personality_tags": ["谨慎", "倔强"], "importance": "protagonist",
        "appearance": "雨衣袖口磨白", "personality_detail": "谨慎却不肯放弃",
        "abilities": ["辨认潮声"], "weaknesses": ["怕深水"], "first_appearance": 1,
        "surface_goal": "找回姐姐", "deep_need": "承认自己也需要帮助",
        "internal_conflict": "要独自冒险还是求援", "fear": "再次被遗弃",
    }


@pytest.mark.parametrize(("kind", "name", "initial", "fields", "readback"), [
    ("character", "林雾", lambda s: s.add_entity(Entity("role:林雾", "character", "林雾")),
     {"aliases": ["阿雾"], "abilities": ["辨认潮声"], "backstory": "盐场来客", "backstory_secret": True},
     lambda s: next(x for x in s.characters() if x.name == "林雾").traits),
    ("faction", "潮汐会", lambda s: s.add_faction("潮汐会"),
     {"origin": "港口旧案", "origin_secret": True, "rituals": "月末点灯"},
     lambda s: s.get_faction("潮汐会")),
    ("item", "潮痕钥", lambda s: s.add_item("潮痕钥"),
     {"special_properties": ["遇盐发热"], "first_chapter": 2},
     lambda s: s.get_item("潮痕钥")),
    ("term", "潮痕", lambda s: s.add_term("潮痕"),
     {"aliases": ["盐纹"], "first_mention_chapter": 2},
     lambda s: s.get_term("潮痕")),
    ("world_rule", "潮誓", lambda s: s.add_world_rule("潮誓", "magic"),
     {"capabilities": ["感应誓言"], "limitations": ["满月失效"], "established_chapter": 2},
     lambda s: s.get_world_rule("潮誓")),
])
def test_mcp_generic_codex_patch_persists_extended_registry_fields(
        store, kind, name, initial, fields, readback):
    """具体 patch 工具未列出的扩展字段也必须写入对应正典对象，且仍经过审批。"""
    initial(store)
    M.set_store(store)
    result = asyncio.run(M.s3_patch_codex(_AcceptCtx(), kind, name, fields))
    assert result["status"] == "written"
    row = readback(store)
    for key, value in fields.items():
        assert row[key] == value
