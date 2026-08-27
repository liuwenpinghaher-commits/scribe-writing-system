"""MCP shared state."""
from __future__ import annotations

"""scribe3 领域 MCP server(FastMCP,名 "scribe3")。

读工具放行(readOnlyHint);写工具经 Hermes elicitation 待批,批准后才走 store 单点落库。
工具名带 s3_ 前缀(隔离标准:与 scribe2 同挂也不撞名)。
可测核心 = commit_if_approved 门控;elicitation 是生产侧(ctx.elicit,fail-closed)。
"""

import logging
import os
from collections import OrderedDict
from typing import Any, Callable

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from scribe3.codex_schema import all_storage_keys, secret_capable_keys, secret_flag_key
from scribe3.codex_secret_bridge import sync_faction_secrets
from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge
from scribe3.verify import causal_complete, find_leaks_for_chapter

mcp = FastMCP("scribe3")
_store = None
_stores: OrderedDict[str, object] = OrderedDict()
_STORE_CACHE_MAX = 8










# ===== 写门控 =====
WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
                "s3_register_purpose",   # 北极星任务6:目的合同登记(草单待批,蓝图 §3-④)
                "s3_set_intent",         # G-001:书级北极星 intent 结构化写入
                "s3_patch_character",    # G-004:角色字段更正(对话审批落库)
                "s3_patch_codex",        # 注册表驱动的完整设定档案更正
                "s3_plant_promise", "s3_advance_promise", "s3_craft_rule_add",
                "s3_craft_rule_remove", "s3_add_character_relation",
                "s3_add_world_rule", "s3_patch_world_rule", "s3_add_faction",
                "s3_patch_faction", "s3_add_char_state",
                "s3_add_arc_beat", "s3_delete_arc_beat",  # 弧光里程碑
                "s3_set_voice_profile", "s3_add_item", "s3_patch_item",
                "s3_add_term", "s3_patch_term",
                "s3_supersede_fact", "s3_forget_knowledge",
                "s3_evolve_relation", "s3_resolve_voice_flag",
                "s3_fold_voice_flags", "s3_add_clue",
                "s3_mark_herring", "s3_touch_promise", "s3_abandon_promise",
                "s3_add_entity_relation",  # CX-Task 5:通用实体关系表写工具
                "s3_author_pref_add",      # 跨书作者偏好(USER.md)待批写入
                # Task 3–6:结构写(卷/章 meta/章 plan/弧光锚)
                "s3_add_volume", "s3_patch_volume",
                "s3_plan_volumes", "s3_plan_chapter_accounts",
                "s3_refine_volume_outline", "s3_batch_stage",
                "s3_add_arc_unit", "s3_expand_arc_window", "s3_settle_arc_event",
                "s3_add_chapter", "s3_patch_chapter_meta", "s3_refreeze_chapter",
                "s3_refreeze_volume",
                "s3_patch_play", "s3_patch_contract",
                "s3_generate_stage", "s3_save_chapter_draft",
                "s3_set_char_anchors",
                # P0:结构运维 + 母题(默认 emergency REST 关时的作者主路径)
                "s3_reorder_chapters", "s3_delete_volume",
                "s3_add_motif", "s3_patch_motif", "s3_patch_promise",
                # 设定库生命周期(archive/delete,与 objects/* 同口径)
                "s3_delete_codex",
                "s3_generate_codex",
                "s3_generate_codex_batch",
                # 素材转正典：新开审批，不改素材行
                "s3_promote_material",
                }










_RO = ToolAnnotations(readOnlyHint=True)
_RW = ToolAnnotations(readOnlyHint=False)


# ===== 读工具(放行)=====






_SECRET_MASK = "🔒 私密"
























































































# ===== manuscript 写(草稿,直接写,不待批——非世界状态)=====


# ===== 写工具(elicitation 待批 → store 单点)=====
_CHARACTER_IMPORTANCE_ALIASES = {
    "主角": "protagonist", "主要角色": "major", "重要配角": "major",
    "配角": "minor", "背景角色": "background", "龙套": "background",
}




























_MCP_UNSET = object()  # 未传哨兵(与 store._UNSET 同一思路,模块内自洽即可,两侧不必共享
                       # 同一对象):区分"调用方未传该关键字实参" vs "显式传值(含 None)"。
                       # 若不做这区分,每次调用都会把没提到的字段清空——已实测复现:旧实现
                       # 对全部字段一律用具体默认值(None/"active"/False)而非哨兵,第二次
                       # 只想改 leader 却把 ideology 等静默清空,known_members 甚至因写 NONE
                       # 进非 optional 的 array 字段直接 500(见 test_codex_faction.py 回归测试)。










# ===== CX-Task 5:通用实体关系表(双向认知 + 主编独知 truth + 时态)=====
# 与 s3_add_character_relation/s3_relations_at(锁死 character↔character)是两套独立
# 工具,互不影响。entity_relation 的 a/b 不锁实体类型,不做存在性校验。




















































# ===== 结构写:卷 / 章 meta / 章 plan / 弧光锚(Task 3–6)=====











































# ===== stdio 入口(供 Hermes 以 `python -m scribe3.mcp` 挂载)=====




if __name__ == "__main__":
    main()

__all__ = ['Any', 'BaseModel', 'Callable', 'Context', 'Entity', 'Event', 'Fact', 'FastMCP', 'Field', 'FieldInfo', 'KnowledgeEdge', 'OrderedDict', 'ToolAnnotations', 'WRITE_GATED', '_CHARACTER_IMPORTANCE_ALIASES', '_MCP_UNSET', '_RO', '_RW', '_SECRET_MASK', '_STORE_CACHE_MAX', '_store', '_stores', 'all_storage_keys', 'annotations', 'causal_complete', 'dramatic_irony', 'find_leaks_for_chapter', 'logging', 'mcp', 'os', 'project_frame', 'secret_capable_keys', 'secret_flag_key', 'sync_faction_secrets']
