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
    Flag("SCRIBE3_STORYLINE_UI", "1", "（deprecated）故事线 Gantt/情绪 UI；产品面已并入故事线注入", "storyline", "safe"),
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
        "（deprecated）写章设计时检查这一章是否还接得上这本书。现无独立实现，保留以免旧环境报未知旗。",
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
        "SCRIBE3_RECALL_SHADOW_VECTOR",
        "1",
        "影子对照纳入向量/混合通道（默认开）",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_RECALL_SHADOW_VECTOR_SYNC",
        "0",
        "向量对照同步跑（默认关，写章不等待；单测开）",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_RECALL_PLAYBOOK",
        "1",
        "写章设定槽走统一召回（默认开；关=紧急退回旧子串+字母序凑数）",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_RECALL_DISCUSS",
        "1",
        "对话设定槽走统一召回（默认开；关=只退对话路，写章不动）",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_BEATS_WRITE_LEGACY",
        "0",
        "过渡：仍往 chapter.beats/deductions/scene_truth 写（147 已删这些列）",
        "store",
        "danger",
    ),
    Flag(
        "SCRIBE3_HTTP_ERRORS_UNIFIED",
        "1",
        "HTTP 错误统一 {code,message}（默认开；关=旧 detail 原样）",
        "api",
        "caution",
    ),
    Flag(
        "SCRIBE3_PROMPT_RENDERER",
        "1",
        "PromptRenderer 统一组装（默认开；关=紧急回退旧拼接）",
        "prompt",
        "caution",
    ),
    Flag(
        "SCRIBE3_QUALITY_GATE_UNIFIED",
        "1",
        "QualityGate 统一判定出口（默认开；关=紧急回退旧形状）",
        "quality",
        "caution",
    ),
    Flag(
        "SCRIBE3_EPISTEMIC_ORACLE",
        "1",
        "限知 visible_to 单入口（默认开）",
        "epistemic",
        "caution",
    ),
    Flag(
        "SCRIBE3_SECRET_BRIDGE_ROLES",
        "1",
        "角色类 secret 字段同步进限知命题（默认开；关则只走势力桥）",
        "recall",
        "caution",
    ),
    Flag(
        "SCRIBE3_OUTLINE_STATUS_GATE",
        "1",
        "纲改过未核对时拦演绎/草稿（缺字段不拦）",
        "structure",
        "caution",
    ),
    Flag(
        "SCRIBE3_IRON_RULES_DUAL_ANCHOR",
        "1",
        "写章嘱咐开头结尾各钉一次今晚不能拆穿的事（七条责任）",
        "playbook",
        "safe",
    ),
    Flag(
        "SCRIBE3_HINT_NO_ACCUM",
        "1",
        "质量环改稿提示只留上一轮；过三轮换角度看",
        "playbook",
        "safe",
    ),
    Flag("SCRIBE3_PDC", "0", "闲笔偏科 craft 切面", "craft", "caution"),
    Flag("SCRIBE3_QUALITY_DIM_ADVISORY", "1", "十维质量分 advisory 注入", "quality", "safe"),
    Flag("SCRIBE3_HERMES_SOUL_LAYERS", "1", "Hermes SOUL 三层", "hermes_runtime", "safe"),
    Flag(
        "SCRIBE3_HERMES_SYSTEM",
        "You are Scribe3 writing runtime. Obey epistemic and craft gates.",
        "Hermes system 层文案",
        "hermes_runtime",
        "safe",
    ),
    Flag(
        "SCRIBE3_HERMES_PERSONALITY",
        "冷静、可审计的小说主编；不编造未批准正典。",
        "Hermes personality 层文案",
        "hermes_runtime",
        "safe",
    ),
    Flag("SCRIBE3_REVIEW_LLM", "0", "章评 L1 限知 LLM 审计", "review", "caution"),
    Flag("SCRIBE3_INGEST_POLICY", "auto_if_pass", "ingest 策略 auto_if_pass|confirm_all|off", "ingest", "caution"),
    Flag("SCRIBE3_CHAPTER_REVIEW_PERSIST", "0", "章评快照落表", "review", "safe"),
    Flag("SCRIBE3_CODEX_INJECT_CAP", "", "点名包软顶覆盖（空=按信封档）", "iceberg", "caution"),
    Flag("SCRIBE3_ICEBERG_WRITE", "1", "冰山注入截断", "iceberg", "safe"),
    Flag("SCRIBE3_CODEX_THICKEN_GATE", "1", "设定加厚门", "iceberg", "safe"),
    Flag("SCRIBE3_LIVE_MAX", "5", "LIVE 连接上限", "live", "caution"),
    Flag("SCRIBE3_ALLOW_FACT_EDIT", "0", "允许直接改命题", "codex", "danger"),
    Flag("SCRIBE3_EVENT_LED_LLM", "0", "事件抽取走 LLM", "narrative", "caution"),
    Flag("SCRIBE3_CANON_DEBT_BLOCK_HIGH", "0", "高债挡定稿", "canon", "caution"),
    Flag("SCRIBE3_WORKS_LIST_STATS_CAP", "24", "书列表统计条数", "works", "safe"),
    Flag("SCRIBE3_STRICT_GATEWAY_GUARD", "0", "网关守卫加严", "hermes", "caution"),
    Flag("SCRIBE3_PROSE_STYLE", "", "正文文风覆盖", "prompt", "safe"),
    Flag("SCRIBE3_INJECT_FLOOR", "1", "注入地板", "inject", "safe"),
    Flag("SCRIBE3_PROVENANCE_IN_PROMPT", "0", "出处进嘱咐", "prompt", "caution"),
    Flag("SCRIBE3_VOLUME_INTRO_INJECT", "1", "卷纲进嘱咐", "prompt", "safe"),
    Flag("SCRIBE3_AUDIT_TTL_DAYS", "30", "审计保留天数", "audit", "safe"),
    Flag("SCRIBE3_LEGACY_OWNER", "admin", "无主书归属", "auth", "caution"),
    Flag("SCRIBE3_BENCHMARK_INJECT", "0", "benchmark 注入", "benchmark", "caution"),
    Flag("SCRIBE3_CANON_EXTRACT_MODE", "llm", "正典抽取模式", "canon", "caution"),
    Flag("SCRIBE3_CHANGEFEED_INTERVAL", "", "changefeed 轮询间隔", "changefeed", "caution"),
    Flag("SCRIBE3_CHANGEFEED_LEADER_ELECTION", "0", "changefeed 选主", "changefeed", "caution"),
    Flag("SCRIBE3_UNIFIED_CHAPTER_ANALYSIS", "1", "统一章分析", "chapter_analysis", "safe"),
    Flag("SCRIBE3_TENSION_CACHE", "1", "张力缓存", "chapter_analysis", "safe"),
    Flag("SCRIBE3_DISCIPLINE_CACHE", "1", "纪律缓存", "chapter_analysis", "safe"),
    Flag("SCRIBE3_ENVELOPE_TOKEN_BUDGET", "", "信封 token 预算覆盖", "context_budget", "caution"),
    Flag("SCRIBE3_PROMPT_HARD", "", "prompt 硬顶覆盖", "context_budget", "caution"),
    Flag("SCRIBE3_SUPPLEMENTAL_HARD", "", "补充硬顶", "context_budget", "caution"),
    Flag("SCRIBE3_SUPPLEMENTAL_SOFT", "", "补充软顶", "context_budget", "caution"),
    Flag("SCRIBE3_OUTLINE_AFTER_DRAMA", "1", "戏剧后大纲", "context_budget", "safe"),
    Flag("SCRIBE3_EVENT_GRAPH_K", "2", "事件图跳数", "event_graph", "caution"),
    Flag("SCRIBE3_DIRECTOR_CREATIVE", "1", "导演创意层", "director", "safe"),
    Flag("SCRIBE3_DRAMA_HARD_PRESSURE", "", "戏剧硬压力覆盖", "drama", "caution"),
    Flag("SCRIBE3_DRAMA_GATE_COMPAT", "", "戏剧门兼容", "drama", "caution"),
    Flag("SCRIBE3_EMOTION_MODE", "lexicon", "情绪标尺模式", "emotion", "safe"),
    Flag("SCRIBE3_EPISTEMIC_DISCUSS_GUARD", "1", "讨论限知守卫", "epistemic", "caution"),
    Flag("SCRIBE3_FINALIZE_GATE", "1", "定稿门", "finalize", "caution"),
    Flag("SCRIBE3_FINALIZE_USE_REVIEW_SNAPSHOT", "0", "定稿用章评快照", "finalize", "caution"),
    Flag("SCRIBE3_HERMES_ONLY_LLM", "1", "只走 Hermes 模型", "llm", "caution"),
    Flag("SCRIBE3_CREATE_MODE", "standard", "创作模式 standard|explore", "ingest", "caution"),
    Flag("SCRIBE3_MEMORY_IRON_IN_ABLATION", "keep", "消融时铁律记忆", "memory", "caution"),
    Flag("SCRIBE3_MEMORY_STEER_MODE", "minimal", "记忆转向档", "memory", "caution"),
    Flag("SCRIBE3_MUST_LINK_LIMIT", "", "必链条数上限", "memory", "caution"),
    Flag("SCRIBE3_PARALLEL_DEDUCE_LLM", "1", "并行演绎走模型", "deduce", "caution"),
    Flag("SCRIBE3_PARALLEL_DEDUCE_MAX", "2", "并行演绎路数", "deduce", "caution"),
    Flag("SCRIBE3_DISTILL_MODE", "heuristic", "蒸馏模式", "distill", "safe"),
    Flag("SCRIBE3_SCHEMA_SOFT", "0", "schema 失败不阻断启动", "store", "danger"),
    Flag("SCRIBE3_ARCHIVE_RETENTION_DAYS", "30", "废弃书保留天数", "works", "safe"),
    Flag("SCRIBE3_GRAPH_CO_PRESENT", "0", "共现进关系图", "recall", "caution"),
    Flag("SCRIBE3_TRUTH_UI", "entity_first", "真相面板口径", "structure", "safe"),
    Flag("SCRIBE3_RUN_CARD_TTL_DAYS", "7", "run card 保留天数", "run_card", "safe"),
    Flag("SCRIBE3_PREFETCH_PREFS_TEXT", "", "预取作者偏好文案", "hermes", "safe"),
    Flag("SCRIBE3_STRUCTURE_DIVERSITY_INJECT", "1", "结构多样性注入", "structure_style", "safe"),
    Flag("SCRIBE3_ENDING_FORMULA_BLOCKING", "0", "结尾套话硬拦", "structure_style", "caution"),
    Flag("SCRIBE3_JOURNEY_PRECHECK", "1", "开写前检查作品意图/母题", "journey", "caution"),
    Flag("SCRIBE3_DUTY_SUMMARY_LOOKBACK", "3", "近几章责任摘要回看章数", "playbook", "safe"),
    Flag("SCRIBE3_DEFAULT_WORK", "main", "默认书名（changefeed/未指定 work）", "works", "safe"),
    Flag("SCRIBE3_ALERT_WEBHOOK", "", "关键事件 webhook", "ops", "caution"),
    Flag(
        "SCRIBE3_CHENGSE_CRAFT",
        "1",
        "成色：拆古白话贴铜炉；日子/办事/假破真进生成与审判；关=回旧文案",
        "playbook",
        "caution",
    ),
)


def _coerce_override(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bool):
        return "1" if raw else "0"
    text = str(raw).strip()
    if not text:
        return ""
    if text[0] in "[{tfnTFN\"0123456789-":
        try:
            import json
            val = json.loads(text)
            if isinstance(val, bool):
                return "1" if val else "0"
            return str(val).strip()
        except Exception:
            pass
    return text


def get_flag(name: str) -> str:
    """读旗：SQLite 台账 > env > FLAG_REGISTRY 默认。台账故障 fail-soft。"""
    try:
        from scribe3.settings_store import get_override
        ov = get_override(name)
        if ov is not None:
            coerced = _coerce_override(ov)
            return coerced
    except Exception:
        pass
    env = os.environ.get(name)
    if env is not None and env != "":
        return env
    entry = next((f for f in FLAG_REGISTRY if f.name == name), None)
    if entry is None:
        return ""
    return entry.default or ""


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
