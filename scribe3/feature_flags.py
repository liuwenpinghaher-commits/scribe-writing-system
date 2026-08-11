"""统一实验/安全旗标注册表（O27 · 无 I/O 外读 env）。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Flag:
    name: str
    default: str  # "0"/"1"/"" 等字符串默认
    description: str
    module: str
    risk_level: str  # safe | caution | danger


FLAG_REGISTRY: tuple[Flag, ...] = (
    Flag("SCRIBE3_ENVELOPE_V2_ENABLE", "0", "18k envelope + V2 物理序/L2", "context_budget", "caution"),
    Flag("SCRIBE3_CONTEXT_FIDELITY", "compat", "compat|v2|literary|epic|novel", "context_budget", "caution"),
    Flag("SCRIBE3_ADAPTIVE_BUDGET", "0", "按 beat_type 场景预算重配", "context_budget", "safe"),
    Flag("SCRIBE3_SCENE_BUDGET_PROFILE", "", "显式场景 profile 名", "context_budget", "safe"),
    Flag("SCRIBE3_TOTAL_BUDGET", "", "全域 prompt 硬顶（空=PROMPT_HARD）", "context_budget", "caution"),
    Flag("SCRIBE3_INJECTION_REGISTRY", "", "off|shadow|active 段注册表", "injection_registry", "caution"),
    Flag("SCRIBE3_DENSITY_TRACE", "1", "密度观测", "injection_registry", "safe"),
    Flag("SCRIBE3_INJECT_DEDUP", "1", "must-link / inject 指纹去重", "inject_dedup", "safe"),
    Flag("SCRIBE3_CANON_SUPPRESS_HEURISTIC", "1", "正典压制文本弱推断", "memory_retrieval", "safe"),
    Flag("SCRIBE3_EPISTEMIC_FAIL_LOUD", "0", "限知出口 fail-loud", "epistemic_guard", "caution"),
    Flag("SCRIBE3_DRAMA_VACUUM_WARN", "1", "无 GCD 戏剧真空警告", "drama_beats", "safe"),
    Flag("SCRIBE3_FINAL_REMINDER_CORE", "0", "final_reminder 短核", "prompt_blocks", "safe"),
    Flag("SCRIBE3_EMERGENCY_REST_WRITE", "0", "REST 世界写闸全开", "app_impl", "danger"),
    Flag("SCRIBE3_DISTRIBUTED_LOCK", "0", "store 背书并发锁", "concurrency_lock", "caution"),
    Flag("SCRIBE3_MEMORY_ACCESS_DECAY", "1", "访问频率衰减加成", "memory_score", "safe"),
)


def get_flag(name: str) -> str:
    entry = next((f for f in FLAG_REGISTRY if f.name == name), None)
    if entry is None:
        return (os.environ.get(name) or "").strip()
    return (os.environ.get(name) if os.environ.get(name) is not None else entry.default) or entry.default


def flag_truthy(name: str) -> bool:
    raw = get_flag(name).strip().lower()
    return raw in ("1", "true", "yes", "on")


def get_all_flags() -> dict[str, Any]:
    """全部旗标当前值（供 GET /debug/flags 或纯查询）。"""
    out: dict[str, Any] = {}
    for f in FLAG_REGISTRY:
        val = get_flag(f.name)
        out[f.name] = {
            "value": val,
            "default": f.default,
            "description": f.description,
            "module": f.module,
            "risk": f.risk_level,
            "truthy": val.strip().lower() in ("1", "true", "yes", "on") if val else False,
        }
    return out
