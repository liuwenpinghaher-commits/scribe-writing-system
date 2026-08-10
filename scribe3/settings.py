# scribe3/settings.py
"""统一设置中心:声明式配置注册表 + 三级优先读取(DB 覆盖 → env → 代码默认)。

- 热生效(effect='hot'):读点每次调 get_setting();写入即失效进程内缓存,
  跨进程靠 2s TTL 自然收敛。
- 重启生效(effect='restart'):读点不改(仍读 env);进程启动最早期调
  apply_restart_overrides() 把 DB 覆盖灌进 os.environ,再走原读取路径。
- secret:DB 存真值(内部可用),settings_snapshot()/审计对外一律掩码。
- env 只对全大写既有键生效;点分新键(craft.* / llm.* / memory.*)只认 DB→默认。
- 门禁:tests/test_settings_gate.py 保证代码里新增的 SCRIBE3_*/HERMES_* env
  读取必须登记本注册表。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass

from scribe3 import settings_store

_TRUE = {"1", "true", "yes", "on"}   # 与 context_cache._TRUE 逐字一致

_log = logging.getLogger("scribe3.settings")
_warned_keys: set[str] = set()   # 坏值告警按 key 只发一次,防日志风暴


def _warn_once(key: str, where: str, e: Exception) -> None:
    if key not in _warned_keys:
        _warned_keys.add(key)
        _log.warning("设置 %s 的值无效(%s),按 fail-soft 回落: %s", key, where, e)


@dataclass(frozen=True)
class Setting:
    key: str
    category: str          # connection | llm | craft | flags | gateway
    type: str              # 'int' | 'float' | 'str' | 'bool' | 'secret'
    default: object
    effect: str            # 'hot' | 'restart'
    label: str
    desc: str = ""
    min: float | None = None
    max: float | None = None
    danger: bool = False   # 前端二次确认


REGISTRY: tuple[Setting, ...] = (
    # ── connection(连接与服务)──
    Setting("SCRIBE3_SURREAL_URL", "connection", "str", "ws://127.0.0.1:8001/rpc", "restart", "SurrealDB 地址"),
    Setting("SCRIBE3_SURREAL_USER", "connection", "str", "root", "restart", "SurrealDB 用户名"),
    Setting("SCRIBE3_SURREAL_PASS", "connection", "secret", "root", "restart", "SurrealDB 密码"),
    Setting("SCRIBE3_CORS_ORIGINS", "connection", "str", "http://127.0.0.1:3311,http://localhost:3311", "restart", "CORS 白名单", "逗号分隔"),
    Setting("SCRIBE3_API_TOKEN", "connection", "secret", "", "restart", "机器/CLI API token(次要)",
            "浏览器主路径用会话登录;空且未开 SCRIBE3_AUTH_ENABLED=不鉴权"),
    Setting("SCRIBE3_AUTH_ENABLED", "connection", "bool", False, "restart", "L1 会话门禁",
            "1=公网会话登录+作品归属隔离;见 docs/L1-AUTH-ISOLATION.md"),
    Setting("SCRIBE3_SESSION_SECRET", "connection", "secret", "", "restart", "会话 Cookie 签名密钥",
            "启用 SCRIBE3_AUTH_ENABLED 时必填"),
    Setting("SCRIBE3_BOOTSTRAP_USERS", "connection", "secret", "", "restart", "首次灌库用户",
            "格式 user:pass,user2:pass2;仅用户表为空时写入"),
    Setting("SCRIBE3_LEGACY_OWNER", "connection", "str", "admin", "restart", "无 owner 历史书归属",
            "L1 effective_owner 回落用户名"),
    Setting("SCRIBE3_LIVE_MAX", "connection", "int", 5, "restart", "SSE /live 并发配额", min=1, max=64),
    Setting("SCRIBE3_WORK", "connection", "str", "main", "restart", "默认书 slug"),
    Setting("SCRIBE3_LOOP_JOURNAL_DIR", "connection", "str", "", "restart", "循环日志目录", "空 = ~/.scribe3-loop-journals"),
    Setting("SCRIBE3_IMPORT_JOURNAL_DIR", "connection", "str", "", "restart", "导入日志目录", "空 = 系统临时目录"),
    Setting("SCRIBE3_LLM_LEDGER", "connection", "str", "", "restart", "日帽台账路径", "空 = ~/.scribe2-surreal/scribe3_llm_ledger.sqlite3"),
    Setting("SCRIBE3_READ_MCP_LABEL", "connection", "str", "scribe3_read", "restart", "只读 MCP 工具集标签"),
    # ── llm(LLM 与用量;全热)──
    Setting("llm.model", "llm", "str", "deepseek-v4-flash-0731", "hot", "补全模型名"),
    # 与写网关 agent.gateway_timeout=1800 对齐(H1 2026-08-08)；客户端须 ≥ 最长动稿。
    Setting("llm.timeout_seconds", "llm", "float", 1800.0, "hot", "LLM 请求超时(秒)", min=30, max=3600),
    Setting("llm.max_retries", "llm", "int", 3, "hot", "瞬时错误重试次数", min=0, max=10),
    Setting("SCRIBE3_DAILY_CALL_CAP", "llm", "int", 0, "hot", "每日 LLM 调用日帽", "0=无限，正整数=成本保险丝", min=0, max=100000, danger=True),
    # ── craft(工艺阈值;全热,对应 critique.py 常量)──
    Setting("craft.banned_density_per_k", "craft", "float", 3.0, "hot", "禁词密度/千字", min=0, max=50),
    Setting("craft.banned_min_sents", "craft", "int", 3, "hot", "禁词判定最少句数", min=1, max=20),
    Setting("craft.contextual_per_k", "craft", "float", 1.5, "hot", "语境禁词密度/千字", min=0, max=50),
    Setting("craft.contextual_min_hits", "craft", "int", 2, "hot", "语境禁词最少命中", min=1, max=20),
    Setting("craft.wandai_block_hits", "craft", "int", 2, "hot", "顽固禁词阻断命中数", min=1, max=20),
    Setting("craft.max_negative_span", "craft", "int", 80, "hot", "负向情绪连续跨度上限", min=10, max=500),
    Setting("craft.max_positive_span", "craft", "int", 80, "hot", "正向情绪连续跨度上限", min=10, max=500),
    Setting("craft.oversaturation_per_k", "craft", "float", 3.0, "hot", "直说情绪密度/千字(留白)", min=0, max=50),
    Setting("craft.adverb_per_k_max", "craft", "float", 3.0, "hot", "副词密度上限/千字", min=0, max=50),
    Setting("craft.rule_of_three_item_max", "craft", "int", 6, "hot", "三段式条目上限", min=2, max=20),
    Setting("craft.rule_of_three_gate_per_k", "craft", "float", 2.0, "hot", "三段式密度门槛/千字", min=0, max=50),
    Setting("craft.near_dup_sim", "craft", "float", 0.7, "hot", "近似重复段落相似度阈值", min=0.3, max=1.0),
    Setting("craft.near_dup_min_len", "craft", "int", 25, "hot", "近似重复最短段长", min=10, max=500),
    # ── craft:记忆检索(memory_retrieval.py 常量)──
    Setting("memory.weight_structured", "craft", "float", 2.0, "hot", "检索权重:正典直查", min=0, max=10),
    Setting("memory.weight_bm25", "craft", "float", 1.0, "hot", "检索权重:BM25", min=0, max=10),
    Setting("memory.weight_vector", "craft", "float", 1.0, "hot", "检索权重:向量", min=0, max=10),
    Setting("memory.weight_graph", "craft", "float", 1.2, "hot", "检索权重:图", min=0, max=10),
    Setting("memory.weight_recency", "craft", "float", 0.8, "hot", "检索权重:recency(预留)", min=0, max=10),
    Setting("memory.half_life_working", "craft", "int", 3, "hot", "半衰期(天):working", min=1, max=3650),
    Setting("memory.half_life_episodic", "craft", "int", 30, "hot", "半衰期(天):episodic", min=1, max=3650),
    Setting("memory.half_life_procedural", "craft", "int", 180, "hot", "半衰期(天):procedural", min=1, max=3650),
    Setting("memory.half_life_reference", "craft", "int", 90, "hot", "半衰期(天):reference", min=1, max=3650),
    Setting("memory.half_life_uncertainty", "craft", "int", 14, "hot", "半衰期(天):uncertainty", min=1, max=3650),
    # ── flags(运行时开关;全热)──
    # 上下文产品三件套默认**开**(非灰度休眠);仅显式 env/DB 覆盖可关(测试/运维隔离)。
    Setting("SCRIBE3_CONTEXT_SNAPSHOT_V1", "flags", "bool", True, "hot", "统一上下文快照 v1",
            "默认开;关=前端可降级本地投影", danger=True),
    Setting("SCRIBE3_EDITORIAL_THREAD_V1", "flags", "bool", False, "hot", "主编讨论线程 v1",
            "可选增强,默认关", danger=True),
    Setting("SCRIBE3_MEMORY_FABRIC_V1", "flags", "bool", True, "hot", "记忆织网检索 v1",
            "默认开:写路径检索+捕获+/memory/*;显式关仅用于隔离", danger=True),
    Setting("SCRIBE3_MEMORY_ABLATION", "flags", "str", "none", "hot",
            "记忆消融模式（质量对照）",
            "none=正常; no_must=禁 must-link; no_must_facts=禁 must+正典 fact 注入（轨2 B 组，fabric 可仍开）",
            danger=True),
    Setting("SCRIBE3_MUST_LINK_LIMIT", "flags", "int", 10, "hot",
            "must-link 压力锚条数上限",
            "防注入清单过长稀释主角/状态（默认 10，范围 3–24）",
            min=3, max=24, danger=False),
    Setting("SCRIBE3_MEMORY_STEER_MODE", "flags", "str", "minimal", "hot",
            "写章 steer 模式",
            "minimal=质量默认（少喂靠记忆）；full=允许长指令/粘贴设定模式",
            danger=False),
    Setting("SCRIBE3_MEMORY_IRON_IN_ABLATION", "flags", "str", "keep", "hot",
            "消融时铁律注入",
            "keep=产品默认仍注入铁律；strip=B2/B3 评测剥全部 red_lines 注入点（不进作者主 UI）",
            danger=True),
    Setting("SCRIBE3_CONTEXT_INSPECTOR_V1", "flags", "bool", True, "hot", "上下文检查器 v1",
            "默认开:主编区 ContextInspector 可见", danger=True),
    Setting("SCRIBE3_EMERGENCY_REST_WRITE", "flags", "bool", False, "hot",
            "紧急 REST 世界写", "默认关；仅自动化测试/紧急运维显式开启", danger=True),
    Setting("SCRIBE3_CRAFT_GATE", "flags", "bool", True, "hot",
            "工艺门闩", "默认开:save_chapter 等写路径需脚手架齐套;测试 conftest 钉 0", danger=True),
    Setting("SCRIBE3_CANON_DEBT_BLOCK_HIGH", "flags", "bool", False, "hot",
            "高风险设定债挡 pilot 推进",
            "开=有 risk=high 的 pending 设定债时禁止 pilot/step（须先收件箱处理）；默认关",
            danger=True),
    Setting("SCRIBE3_CANON_EXTRACT_MODE", "flags", "str", "llm", "hot",
            "正文设定抽取模式",
            "llm=标记+模型(默认,禁启发式); hybrid=标记+模型+规则; heuristic=标记+规则; marker=仅标记",
            danger=False),
    Setting("SCRIBE3_UNIFIED_CHAPTER_ANALYSIS", "flags", "bool", True, "hot",
            "章后统一模型分析",
            "开=定稿/ingest 一次 LLM 同时出设定增量+知识账本(缓存复用); 关=分路旧逻辑",
            danger=False),
    Setting("SCRIBE3_DISCIPLINE_CACHE", "flags", "bool", True, "hot",
            "纪律判结果写章后缓存",
            "开=/post-check 与终选可复用同正文指纹的纪律结果，免重复调模型",
            danger=False),
    Setting("SCRIBE3_FINALIZE_RUN_DISCIPLINE", "flags", "bool", False, "hot",
            "终选时顺带跑纪律判",
            "开=finalize 多一次 LLM 但 post-check 可命中缓存；默认关以免拖慢终选",
            danger=False),
    Setting("SCRIBE3_TENSION_CACHE", "flags", "bool", True, "hot",
            "张力盲评结果写章后缓存",
            "开=/tension-check 同正文指纹可复用 rubric，免重复调模型",
            danger=False),
    # ── novel-quality 戏剧/节拍/压力旗(PR-0 登记;代码默认=现网可达;质量模式见 demo env)──
    # 读点：scribe3.novel_quality_flags；已接线：BEATS_* / DRAMA_GATE* / CRAFT_NOVEL /
    # PARK_STROLL_BLOCKING(PR-6a severity) / PILOT_SOFT_*(PR-6b full_check 动态 soft)。
    # 真源：docs/plans/2026-08-10-novel-quality-first-pipeline-optimization.md
    Setting("SCRIBE3_BEATS_V2", "flags", "bool", True, "hot",
            "节拍 v2 生成(GCD 字段)",
            "开=expand_beats 写 goal/conflict/turn/cost/hook 等 GCD；关=仅 text 行(v1)。代码默认开。",
            danger=False),
    Setting("SCRIBE3_DRAMA_GATE", "flags", "bool", False, "hot",
            "写前戏剧门",
            "开=expand_beats 后高压章 validate_drama_beats 失败 → pilot_park drama_incomplete"
            "（advisory：可补字段继续，不擦 beats；缺口在 beats_meta.drama_validation.gaps）；"
            "关=不因戏剧弱 park（代码默认）。质量模式 demo 开。",
            danger=True),
    Setting("SCRIBE3_DRAMA_GATE_COMPAT", "flags", "bool", True, "hot",
            "戏剧门 v1 弱通过兼容",
            "开=仅 text 节拍 drama_weak 警告且 ok 弱通过（代码默认，配合 DRAMA_GATE 时不因 v1 硬 park）；"
            "关=v1 高压可进 errors。质量模式关。",
            danger=False),
    Setting("SCRIBE3_BEATS_SYNOPSIS_FALLBACK", "flags", "bool", True, "hot",
            "节拍大纲切句充数",
            "开=接地失败用 synopsis 切句充数并标 beats_source=synopsis_segments(代码默认兼容)；"
            "关=接地失败 park 且不写 beats（质量模式推荐关）。",
            danger=True),
    Setting("SCRIBE3_CRAFT_NOVEL", "flags", "bool", False, "hot",
            "小说优先 craft 包",
            "开=craft 小说优先选择表(比喻无「2-4」、不双注入) + draft_loop length_steer 强化冲突/行动优先；"
            "代码默认关以免 silent 改声口",
            danger=False),
    Setting("SCRIBE3_PILOT_SOFT_PRESSURE", "flags", "bool", True, "hot",
            "pilot full_check 压力 soft-pass",
            "已接线·full_check。开=pressure_metrics/park_stroll 不硬停(代码默认可达)；"
            "关=压力类可硬停(质量模式)；与 SOFT_AI_GRADE 双旗拆分 KD-NQ-11",
            danger=True),
    Setting("SCRIBE3_PILOT_SOFT_AI_GRADE", "flags", "bool", True, "hot",
            "pilot full_check AI 味 soft-pass",
            "已接线·full_check。开=aggregate_ai_grade 不硬停(代码/质量模式均默认可达)；"
            "关=AI 味可硬停；与 SOFT_PRESSURE 双旗拆分 KD-NQ-11",
            danger=True),
    Setting("SCRIBE3_PARK_STROLL_BLOCKING", "flags", "bool", False, "hot",
            "公园散步检测升 blocking",
            "开=高压章 spatial_inventory/park_stroll 可 meta.severity=blocking，loop.triage 进 blocking 桶；"
            "代码默认关=一律 advisory。full_check soft-pass 由 SOFT_PRESSURE 控制(已接线 PR-6b)。",
            danger=True),
    Setting("SCRIBE3_DRAMA_HARD_PRESSURE", "flags", "int", 4, "hot",
            "高压章压力门槛",
            "chapter_pressure>=本值或 role 高压/推进视为高压（drama 门 + park_stroll）；默认 4(KD-NQ-15)；可 env 试 3",
            min=1, max=5, danger=False),
    # ── gateway(Hermes 网关;地址类 restart)──
    Setting("HERMES_API", "gateway", "str", "http://127.0.0.1:8642/v1", "restart", "速答网关(default)"),
    Setting("HERMES_RESPONSES_API", "gateway", "str", "http://127.0.0.1:8643/v1", "restart", "agentic 读网关"),
    Setting("HERMES_RESPONSES_PROFILE", "gateway", "str", "scribe3", "restart", "读网关 profile"),
    Setting("HERMES_RUNS_API", "gateway", "str", "http://127.0.0.1:8644/v1", "restart", "写入 Runs 网关"),
    Setting("HERMES_RUNS_PROFILE", "gateway", "str", "scribe3_write", "restart", "写网关 profile"),
    Setting("HERMES_DEDUCE_RUNS_API", "gateway", "str", "http://127.0.0.1:8645/v1", "restart", "章节演绎受限 Runs 网关"),
    Setting("HERMES_DEDUCE_PREVIEW_RUNS_API", "gateway", "str", "http://127.0.0.1:8646/v1", "restart", "章节演绎只读预览 Runs 网关"),
    Setting("HERMES_HOME", "gateway", "str", "", "restart", "Hermes 根目录", "空 = ~/.hermes"),
    Setting("DEEPSEEK_API_KEY", "gateway", "secret", "", "hot", "Qwen API 密钥（兼容键）",
            "旧键名为兼容现有本机设置；无工具补全/纪律审校直连 Qwen 官方服务；本地受限权限设置存储；审计掩码；当前不宣称静态加密"),
    Setting("SCRIBE3_STRICT_GATEWAY_GUARD", "gateway", "bool", False, "restart", "网关安全守卫 fail-fast",
            "开=启动时网关安全不变量违规(默认网关有工具面/挂 *_reveal)直接拒绝启动;关=只 CRITICAL 日志(U-007)"),
    Setting("gateway.hermes_bin", "gateway", "str", "~/.local/bin/hermes", "restart", "hermes CLI 路径", "一键重启用"),
    Setting("gateway.dashboard_url", "gateway", "str", "http://127.0.0.1:9119", "hot", "Dashboard 地址", "官方管理台,hermes dashboard 默认端口"),
)
_BY_KEY: dict[str, Setting] = {s.key: s for s in REGISTRY}

_cache_lock = threading.Lock()
_cache: dict = {"ts": 0.0, "overrides": None}
_CACHE_TTL = 2.0   # 跨进程收敛窗口:另一进程写入后本进程最迟 2s 见到


def invalidate_cache() -> None:
    with _cache_lock:
        _cache["ts"] = 0.0
        _cache["overrides"] = None


def _overrides() -> dict[str, str]:
    with _cache_lock:
        if _cache["overrides"] is None or time.monotonic() - _cache["ts"] > _CACHE_TTL:
            _cache["overrides"] = settings_store.get_all_overrides()
            _cache["ts"] = time.monotonic()
        return _cache["overrides"]


def _coerce(s: Setting, value):
    """类型归一 + 校验;非法抛 ValueError。env 字符串与 JSON 原生值都走这里。"""
    if s.type == "bool":
        if isinstance(value, str):
            value = value.strip().lower() in _TRUE
        value = bool(value)
    elif s.type == "int":
        # 非整数 float 不许静默截断(bool 是 int 子类,int(True)=1 无损,不受影响)
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"{s.key} 需要整数,收到 {value!r}")
        try:
            value = int(value)
        except (TypeError, ValueError) as e:   # None 等不可转值统一包成 ValueError
            raise ValueError(f"{s.key} 无法转换为 int: {value!r}") from e
    elif s.type == "float":
        try:
            value = float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{s.key} 无法转换为 float: {value!r}") from e
    else:   # str / secret
        value = str(value)
    if s.min is not None and isinstance(value, (int, float)) and value < s.min:
        raise ValueError(f"{s.key} 低于下限 {s.min}")
    if s.max is not None and isinstance(value, (int, float)) and value > s.max:
        raise ValueError(f"{s.key} 高于上限 {s.max}")
    return value


def get_setting(key: str):
    s = _BY_KEY[key]
    raw = _overrides().get(key)
    if raw is not None:
        try:
            return _coerce(s, json.loads(raw))
        except Exception as e:
            _warn_once(key, "DB 覆盖", e)   # 台账里的坏值不炸系统:回落 env/默认
    if key.isupper():   # env 只对全大写既有键生效
        env = os.environ.get(key)
        if env is not None and env != "":
            try:
                return _coerce(s, env)
            except Exception as e:
                _warn_once(key, "env", e)
    return s.default


def is_explicitly_configured(key: str) -> bool:
    """secret 的 env/DB 记录是否存在；不读取值，也不声称语法有效或可用。"""
    setting = _BY_KEY[key]
    if setting.type != "secret":
        raise ValueError(f"{key} 不是 secret 设置")
    if key in os.environ:
        return True
    return settings_store.has_override(key)


def get_public_setting(key: str):
    """窄读取单个非 secret 设置；不触发全量覆盖值缓存。"""
    setting = _BY_KEY[key]
    if setting.type == "secret":
        raise ValueError(f"{key} 是 secret 设置")
    raw = settings_store.get_override(key)
    if raw is not None:
        try:
            return _coerce(setting, json.loads(raw))
        except Exception as e:
            _warn_once(key, "DB 覆盖", e)
    if key.isupper() and key in os.environ and os.environ[key] != "":
        try:
            return _coerce(setting, os.environ[key])
        except Exception as e:
            _warn_once(key, "env", e)
    return setting.default


def put_setting(key: str, value) -> dict:
    s = _BY_KEY[key]   # 未登记 → KeyError,调用方转 404
    coerced = _coerce(s, value)
    settings_store.set_override(key, json.dumps(coerced, ensure_ascii=False),
                                mask=(s.type == "secret"))
    invalidate_cache()
    return {"key": key, "value": None if s.type == "secret" else coerced, "effect": s.effect}


def reset_setting(key: str) -> None:
    s = _BY_KEY[key]
    settings_store.delete_override(key, mask=(s.type == "secret"))
    invalidate_cache()


def _source(s: Setting) -> str:
    if s.key in _overrides():
        return "db"
    if s.key.isupper() and os.environ.get(s.key):
        return "env"
    return "default"


def _pending_restart(s: Setting) -> bool:
    """restart 项:DB 已存值 ≠ 当前进程 env 生效值 → 待重启。"""
    if s.effect != "restart" or s.key not in _overrides():
        return False
    try:
        db_val = _coerce(s, json.loads(_overrides()[s.key]))
    except Exception as e:
        _warn_once(s.key, "pending_restart", e)
        return False
    env = os.environ.get(s.key)
    cur = _coerce(s, env) if env not in (None, "") else s.default
    return db_val != cur


def settings_snapshot() -> list[dict]:
    """GET /settings 的序列化:secret 掩码(value=None + is_set),永不回显明文。"""
    out = []
    for s in REGISTRY:
        val = get_setting(s.key)
        secret = s.type == "secret"
        out.append({
            "key": s.key, "category": s.category, "type": s.type,
            "label": s.label, "desc": s.desc, "effect": s.effect, "danger": s.danger,
            "default": None if secret else s.default,
            "value": None if secret else val,
            "is_set": (_source(s) != "default") if secret else None,
            "source": _source(s), "min": s.min, "max": s.max,
            "pending_restart": _pending_restart(s),
        })
    return out


def apply_restart_overrides() -> None:
    """进程启动最早期调用(app.py / mcp.py 顶部):把 restart 项的 DB 覆盖灌进
    os.environ,后续模块按原 env 路径读取。DB 是持久层,env 是进程生效层。"""
    ov = settings_store.get_all_overrides()
    for s in REGISTRY:
        if s.effect != "restart" or s.key not in ov or not s.key.isupper():
            continue
        try:
            v = _coerce(s, json.loads(ov[s.key]))
        except Exception as e:
            _warn_once(s.key, "restart 灌注", e)
            continue
        os.environ[s.key] = str(v).lower() if s.type == "bool" else str(v)
