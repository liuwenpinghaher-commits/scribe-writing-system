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
    Flag("SCRIBE3_ENVELOPE_V2_ENABLE", "1", "V2 物理序/L2（质量优先默认开）", "context_budget", "caution"),
    Flag("SCRIBE3_ENVELOPE_NOVEL", "1", "novel 信封 22k + PROMPT_HARD 48k", "context_budget", "caution"),
    Flag("SCRIBE3_CONTEXT_FIDELITY", "novel", "compat|v2|literary|epic|novel", "context_budget", "caution"),
    Flag("SCRIBE3_ADAPTIVE_BUDGET", "1", "按 beat_type 场景预算重配", "context_budget", "safe"),
    Flag("SCRIBE3_SCENE_BUDGET_PROFILE", "", "显式场景 profile 名", "context_budget", "safe"),
    Flag("SCRIBE3_TOTAL_BUDGET", "", "全域 prompt 硬顶（空=PROMPT_HARD）", "context_budget", "caution"),
    Flag("SCRIBE3_INJECTION_REGISTRY", "active", "off|shadow|active 段注册表", "injection_registry", "caution"),
    Flag("SCRIBE3_DENSITY_TRACE", "1", "密度观测", "injection_registry", "safe"),
    Flag("SCRIBE3_INJECT_DEDUP", "1", "must-link / inject 指纹去重", "inject_dedup", "safe"),
    Flag("SCRIBE3_CANON_SUPPRESS_HEURISTIC", "1", "正典压制文本弱推断", "memory_retrieval", "safe"),
    Flag("SCRIBE3_EPISTEMIC_FAIL_LOUD", "0", "限知出口 fail-loud", "epistemic_guard", "caution"),
    Flag("SCRIBE3_DRAMA_VACUUM_WARN", "1", "无 GCD 戏剧真空警告", "drama_beats", "safe"),
    Flag("SCRIBE3_FINAL_REMINDER_CORE", "0", "final_reminder 短核", "prompt_blocks", "safe"),
    Flag("SCRIBE3_EMERGENCY_REST_WRITE", "0", "REST 世界写闸全开", "app_impl", "danger"),
    Flag("SCRIBE3_DISTRIBUTED_LOCK", "1", "store 背书并发锁", "concurrency_lock", "caution"),
    Flag("SCRIBE3_MEMORY_ACCESS_DECAY", "1", "访问频率衰减加成", "memory_score", "safe"),
    # Surreal 深度利用（质量/一致性默认开）
    Flag("SCRIBE3_HYBRID_SEARCH_NATIVE", "1", "混合召回单程 native", "recall", "caution"),
    Flag("SCRIBE3_CHANGEFEED_CACHE", "1", "Changefeed 驱动缓存失效", "changefeed_consumer", "caution"),
    Flag("SCRIBE3_DB_INFLIGHT_LOCK", "1", "DB inflight 章操作锁", "inflight_lock", "caution"),
    Flag("SCRIBE3_DB_KNOWLEDGE_FRAME", "1", "fn::knowledge_frame 知识帧", "knowledge", "caution"),
    Flag("SCRIBE3_STATS_VIEW", "1", "stats_* 聚合视图读", "stats_views", "safe"),
    Flag("SCRIBE3_LIVE_GRANULAR", "1", "LIVE/SSE 带 action+id", "live", "safe"),
    # 叙事/工艺 soft（硬 park 仍关）
    Flag("SCRIBE3_CRAFT_NOVEL", "1", "小说优先 craft 包", "craft", "safe"),
    Flag("SCRIBE3_NARRATIVE_ENGINE", "1", "叙事引擎引导", "narrative_drive", "caution"),
    Flag("SCRIBE3_EVENT_LED_DETECT", "1", "写后事件驱动检测 soft", "narrative_drive", "safe"),
    Flag("SCRIBE3_OPENER_SOFT_TRACE", "1", "开篇 soft 可观测", "narrative_drive", "safe"),
    Flag("SCRIBE3_FINALIZE_RUN_DISCIPLINE", "1", "终选顺带纪律判", "finalize", "caution"),
    Flag("SCRIBE3_EDITORIAL_THREAD_V1", "1", "主编讨论线程 v1", "editorial", "safe"),
    # P2 novel-first（产品 soft 默认开；硬门仍关）
    Flag("SCRIBE3_SOFT_ACTIVATION", "1", "软 lore 激活（L2/L3 可丢）", "soft_activation", "caution"),
    Flag("SCRIBE3_SOFT_PRECHECK", "1", "大纲/节拍软预检 advisory", "soft_precheck", "safe"),
    Flag("SCRIBE3_LITERARY_DISTILL", "1", "文学蒸馏原型（启发式）", "literary_distill", "safe"),
    # 延期产品 backlog（默认开 · 安全硬门仍关）
    Flag("SCRIBE3_STORYLINE_UI", "1", "故事线 Gantt/情绪 UI", "storyline", "safe"),
    Flag("SCRIBE3_MULTI_HOP_GRAPH", "1", "事件图多跳 k≥2", "event_graph", "caution"),
    Flag("SCRIBE3_STAGE_MACHINE", "1", "章节阶段机产品", "chapter_stage", "caution"),
    Flag("SCRIBE3_STAGE_MACHINE_HARD", "0", "阶段非法跳转 hard 409", "chapter_stage", "danger"),
    Flag("SCRIBE3_PARALLEL_DEDUCE", "1", "并行多视角演绎", "parallel_deduce", "caution"),
    Flag("SCRIBE3_AGENT_CRON_UI", "1", "agent cron 产品面", "agent_crons", "safe"),
    Flag("SCRIBE3_BENCHMARK_LIB", "1", "benchmark 参考库", "benchmark_lib", "safe"),
    Flag("SCRIBE3_STORYLINE_INJECT", "1", "故事线注入 polish 段", "storyline_inject", "caution"),
    Flag(
        "SCRIBE3_STORYLINE_PROMISE_HINT",
        "0",
        "故事线一行未收线伏笔计数提示（默认关；omit 正文仍是硬保证）",
        "storyline_inject",
        "caution",
    ),
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
