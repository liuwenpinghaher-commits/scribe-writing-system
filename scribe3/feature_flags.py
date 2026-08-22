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
    Flag("SCRIBE3_FINAL_REMINDER_CORE", "1", "final_reminder 短核（默认开）", "prompt_blocks", "safe"),
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
    # 话语层 Week-1（方案 E · advisory only；永不 finalize blocking）
    Flag("SCRIBE3_DISCOURSE_ADVISORY", "1", "话语层 soft + post-check 顶键总开关", "discourse", "safe"),
    Flag("SCRIBE3_DISCOURSE_MESO", "1", "discourse_soft meso 子块（W2；W1 无段无影响）", "discourse", "caution"),
    Flag("SCRIBE3_DISCOURSE_SERIAL", "1", "discourse_soft serial 子块（W2）", "discourse", "safe"),
    Flag("SCRIBE3_DISCOURSE_INFO_DELTA", "1", "信息增量 info_delta 检测", "discourse", "safe"),
    Flag("SCRIBE3_DISCOURSE_STAKES", "1", "stakes_on_page 检测（展示级）", "discourse", "safe"),
    Flag(
        "SCRIBE3_DISCOURSE_BLOCKING",
        "0",
        "仅改 discourse 展示 severity；finalize/is_blocking_issue 不读",
        "discourse",
        "danger",
    ),
    # dual-lamp · 工程验收 vs 读者可读
    Flag("SCRIBE3_ANTI_META", "1", "反元叙事检测进 post/collect 顶键", "anti_meta", "safe"),
    Flag(
        "SCRIBE3_ANTI_META_BLOCK_CLAIM",
        "1",
        "宣称可读路径 assert_reader_claim 生效",
        "anti_meta",
        "caution",
    ),
    Flag(
        "SCRIBE3_ANTI_META_BLOCK_SAVE",
        "0",
        "存草稿也因验收腔 409（默认关）",
        "anti_meta",
        "danger",
    ),
    Flag(
        "SCRIBE3_ANTI_META_ON_STAMP",
        "0",
        "kind=final stamp 前可读宣称检查（默认关）",
        "anti_meta",
        "caution",
    ),
    Flag("SCRIBE3_DISCOURSE_RASHOMON", "0", "罗生门多版本工具预留（默认关）", "discourse", "caution"),
    Flag("SCRIBE3_MOVE_LIBRARY", "0", "故事招式库：检索/注入/MCP/章计划", "story_move", "caution"),
    Flag("SCRIBE3_NOVEL_WIDE", "", "96k：空=窗够大自动开；1=强制（须窗）；0=强制 48k", "context_budget", "caution"),
    Flag("SCRIBE3_NOVEL_PROMPT_HARD", "", "只接受空或 96000；其它 fail-loud", "context_budget", "caution"),
    Flag("SCRIBE3_MODEL_CONTEXT_WINDOW", "", "供应商 token 窗。≥192000 时产品默认 96k", "context_budget", "caution"),
    Flag("SCRIBE3_NOVEL_WIDE_WORKS", "", "升窗书白名单；非空则未传 work 走窄档", "context_budget", "caution"),
    Flag("SCRIBE3_RUN_CARD", "1", "是否派生对照摘要 contrast_summary；0=不算对照", "observability", "safe"),
    Flag("SCRIBE3_RUN_CARD_PERSIST", "0", "是否 CREATE write_run_card；P3b 默认 0", "observability", "safe"),
    Flag("SCRIBE3_PIPELINE_TRACE", "1", "写路径 chain+span 主账；0=零 I/O 不挡写", "observability", "safe"),
    Flag("SCRIBE3_PIPELINE_TRACE_PREVIEW", "0", "步骤片段预览（默认关，不回默认 API）", "observability", "caution"),
    Flag("SCRIBE3_PIPELINE_TRACE_TTL_DAYS", "7", "pipeline_chain/span TTL 天", "observability", "safe"),
    Flag(
        "SCRIBE3_DESIGN_BOOK",
        "on",
        "写章设计时检查这一章是否还接得上这本书（人、地、线、简介）。off=只检查表格填没填满。",
        "chapter_design",
        "caution",
    ),
    Flag("SCRIBE3_PIPELINE_RECORDER", "1", "飞行记录仪事件+工件；默认开", "observability", "caution"),
    Flag("SCRIBE3_PIPELINE_ARTIFACT_CAP", "16384", "单工件 Unicode 字帽", "observability", "safe"),
    Flag(
        "SCRIBE3_VOLUME_LEDGER",
        "1",
        "写章时注入本卷台账近窗（今晚/已办/还没办）；0/false/off=关",
        "playbook",
        "safe",
    ),
    Flag(
        "SCRIBE3_CODEX_DIGEST_SYNC",
        "1",
        "实体摘要同步为 codex_digest 命题；0=不同步",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_GRAPH_RELATION_RECALL",
        "1",
        "人物/实体关系 ≤2 跳进召回图通道",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_RECALL_SHADOW",
        "1",
        "RecallService 影子：并行计算只记 diff，写章输出不变",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_RECALL_PLAYBOOK",
        "0",
        "写章设定槽改走 RecallService（翻主；默认关）",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_SECRET_BRIDGE_ROLES",
        "0",
        "角色类 secret 字段同步进限知命题（默认关，势力桥不受影响）",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_OUTLINE_STATUS_GATE",
        "0",
        "纲改过未核对时拦演绎/草稿（默认关；旧书缺字段不拦）",
        "structure",
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
