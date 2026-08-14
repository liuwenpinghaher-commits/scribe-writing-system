"""Service helpers extracted from app_impl (architecture split Phase B).

Runtime: ``app_impl._rebind_services()`` rebinds each public function into
``app_impl`` globals (monkeypatch / router rebind).  Do not call these for
side-effectful paths without going through ``scribe3.app`` / ``app_impl``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque
from functools import wraps
from typing import Any, Optional


# novel-first：写路径软失败计数 + 最近一次 budget_report（无 I/O · 可观测）
_WRITE_SOFT_FAIL_COUNTERS: dict[str, int] = {
    "epistemic_guard": 0,
    "empty_drama": 0,
    "empty_outline": 0,
    "continue_snapshot_skip": 0,
}
_LAST_WRITE_BUDGET_REPORT: dict[str, Any] = {}
_WRITE_OBS_LOCK = threading.Lock()


def record_write_soft_fail(kind: str) -> None:
    """递增 soft-fail 计数并打结构化日志（非成本 KPI）。"""
    key = str(kind or "unknown")
    with _WRITE_OBS_LOCK:
        _WRITE_SOFT_FAIL_COUNTERS[key] = int(_WRITE_SOFT_FAIL_COUNTERS.get(key, 0)) + 1
        count = _WRITE_SOFT_FAIL_COUNTERS[key]
    logging.getLogger("scribe3").info(
        "write_soft_fail kind=%s count=%s", key, count,
    )


def get_write_soft_fail_counters() -> dict[str, int]:
    with _WRITE_OBS_LOCK:
        return dict(_WRITE_SOFT_FAIL_COUNTERS)


def get_last_write_budget_report() -> dict[str, Any]:
    """最近一次 V1/V2 组装的 budget_report（可能为空 dict）。"""
    with _WRITE_OBS_LOCK:
        return dict(_LAST_WRITE_BUDGET_REPORT)


def _store_write_budget_report(report: dict[str, Any] | None) -> None:
    if not report:
        return
    with _WRITE_OBS_LOCK:
        _LAST_WRITE_BUDGET_REPORT.clear()
        _LAST_WRITE_BUDGET_REPORT.update(report)


# Note: function bodies resolve free names via rebound globals on app_impl.

# PR-EH-10: prompt blocks
from scribe3.api.services.write_assemble_blocks import (  # noqa: E402
    _faction_prompt_block,
    _codex_block,
    _codex_segments,
    _editor_system,
    _editor_identity_block,
    _write_protocol_block,
    _write_revision_block,
    inject_floor_env_enabled,
    _anti_slop_floor_block,
    provenance_in_prompt_enabled,
    generation_forbidden_source_kinds,
)




# PR-EH-10b: context blocks live in write_assemble_context
from scribe3.api.services.write_assemble_context import (  # noqa: E402,F401
    _editor_write_system,
    _voice_anchor_block,
    _clip_chars,
    _volume_intro_inject_enabled,
    _outline_block,
    _volume_intro_block,
    _event_drive_block,
    _drama_block,
    FOCAL_DEDUCTION_PROSE_CAP,
    _deduction_context_segments,
    _purpose_and_lessons_write_block,
    _pressure_drive_write_block,
    _brief_must_sections_write_block,
    _material_recall_block,
)


# Package C: envelope V1 + discussion in dedicated modules
from scribe3.api.services.write_assemble_v1 import (  # noqa: E402,F401
    _assemble_write_instructions_v1,
)
from scribe3.api.services.write_assemble_discuss import (  # noqa: E402,F401
    assemble_discussion_system,
)

# rebind 到 app_impl 后，v1 内 LOAD_GLOBAL 解析这些名（须列入 _rebind_services 白名单）
def _record_write_soft_fail(kind: str) -> None:
    record_write_soft_fail(kind)


# ── write_assemble 包 rebind 白名单 SSOT（app_impl._rebind_services 必须消费本表）──
WRITE_ASSEMBLE_REBIND_NAMES: tuple[str, ...] = (
    "_faction_prompt_block",
    "_codex_block",
    "_codex_segments",
    "_editor_system",
    "_editor_identity_block",
    "_write_protocol_block",
    "_write_revision_block",
    "inject_floor_env_enabled",
    "_anti_slop_floor_block",
    "generation_forbidden_source_kinds",
    "provenance_in_prompt_enabled",
    "record_write_soft_fail",
    "_record_write_soft_fail",
    "_store_write_budget_report",
    "get_last_write_budget_report",
    "get_write_soft_fail_counters",
    "_WRITE_OBS_LOCK",
    "_WRITE_SOFT_FAIL_COUNTERS",
    "_LAST_WRITE_BUDGET_REPORT",
    "_editor_write_system",
    "_voice_anchor_block",
    "_outline_block",
    "_volume_intro_block",
    "_volume_intro_inject_enabled",
    "_event_drive_block",
    "_drama_block",
    "FOCAL_DEDUCTION_PROSE_CAP",
    "_deduction_context_segments",
    "_purpose_and_lessons_write_block",
    "_brief_must_sections_write_block",
    "_pressure_drive_write_block",
    "_material_recall_block",
    "_clip_chars",
    "_assemble_write_instructions_v1",
    "_assemble_write_instructions",
)

# 跨模块但 v1 rebind 后也必须出现在 app_impl 全局的名字（由其它 rebind 表注入）
WRITE_ASSEMBLE_EXTERNAL_GLOBALS: tuple[str, ...] = (
    "_final_reminder",
    "_final_reminder_full",
    "_get_write_retriever",
    "_build_write_retrieval_query",
    "_phase_role_block",
    "_avoid_directive",
    "_author_prefs_block_safe",
    "_secret_guard_block",
    "_revelation_discipline_block",
)


def assert_write_assemble_rebind_ready(ns: dict | None = None) -> list[str]:
    """检查 rebind 后命名空间是否含写路径必需符号；返回缺失名列表（空=就绪）。"""
    g = ns if ns is not None else globals()
    missing: list[str] = []
    for name in WRITE_ASSEMBLE_REBIND_NAMES:
        if name not in g:
            missing.append(name)
    for name in WRITE_ASSEMBLE_EXTERNAL_GLOBALS:
        if name not in g:
            missing.append(f"external:{name}")
    return missing


def check_generate_reread_gate(work: str, chapter: int) -> dict:
    """供 /chat/write 等生成入口:硬续写模式未 ack 则拒。"""
    from scribe3.experience import exp_state
    from scribe3.experience.continue_rite import reread_allowed
    return reread_allowed(
        require_reread=exp_state.get_require_reread(work),
        acked=exp_state.has_reread_ack(work, chapter),
        is_generate=True,
    )


def _assemble_write_instructions(st, *, chapter: int, focalizer: str, phase: str,
                                 seed_words: list, short_mode: bool,
                                 with_tools: bool = False,
                                 work: str | None = None,
                                 envelope_trace: dict | None = None,
                                 memory_trace_ctx: dict | None = None,
                                 extra_instructions: str = "",
                                 request_text: str = "") -> str:
    """chat_write 完整组装链单源；生产无条件走 Creative Context Engine。

    统一内核是唯一生产写作路由。编译失败直接上抛，不得回退旧散点链
    伪装成“没有上下文”。"""
    return _assemble_write_instructions_v1(
        st, chapter=chapter, focalizer=focalizer, phase=phase,
        seed_words=seed_words, short_mode=short_mode,
        with_tools=with_tools, work=work, envelope_trace=envelope_trace,
        memory_trace_ctx=memory_trace_ctx,
        extra_instructions=extra_instructions, request_text=request_text,
    )


