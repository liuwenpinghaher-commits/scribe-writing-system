# scribe3/novel_quality_flags.py
"""小说质量第一 · 特征旗读辅助与观测字段名（PR-0）。

真源设计：
  ``docs/plans/2026-08-10-novel-quality-first-pipeline-optimization.md``

约定
----
- **代码默认** = 现网可达（与 v6.3.3 连载 soft-pass / synopsis fallback 兼容）。
- **质量模式** = demo ``.env`` 显式翻转；不在此模块 silent break 主路径。
- **本模块提供读点与字段名**；行为接线按 PR 推进：
  PR-2 已接 ``BEATS_V2`` / ``BEATS_SYNOPSIS_FALLBACK``（``expand_beats``）；
  PR-3 已接 ``DRAMA_GATE`` / ``DRAMA_GATE_COMPAT``（写前 advisory park + gaps）；
  PR-4 已接草稿 ``_drama_block`` / brief 戏剧段 / ``length_steer`` soft；
  PR-5 已接 ``CRAFT_NOVEL``（``craft.build_craft_block`` 选择表）；
  PR-6a 已接 ``PARK_STROLL_BLOCKING``（``pressure_metrics`` severity + ``park_stroll`` + triage buckets）；
  PR-6b 已接 ``PILOT_SOFT_PRESSURE`` / ``PILOT_SOFT_AI_GRADE``（``full_check`` 动态 soft 集合）；
  PR-6c 已接 deliver ``pilot_card.buckets``（redline/story/style 计数；full_check 暂存 + UI 交付卡）。
  叙事引擎（rev.2.3 引导优先）：``NARRATIVE_ENGINE`` ensure+注入默认开；
  ``EVENT_DRIVE_GATE`` 硬拦仍默认关；``EVENT_LED_DETECT`` / opener soft 默认开。
- 设置 UI：已接线旗改值立即影响对应路径；未接线旗改值暂无运行时效果。

读取路径：``settings.get_setting``（DB 覆盖 → env → REGISTRY 默认）。
代码默认真源：``settings.REGISTRY``（``CODE_DEFAULTS`` 由其派生，禁止手抄第二份）。
"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("scribe3.novel_quality_flags")

# ── 旗名常量（与 settings.REGISTRY / 设计真值表逐字一致）────────────────

FLAG_BEATS_V2 = "SCRIBE3_BEATS_V2"
FLAG_DRAMA_GATE = "SCRIBE3_DRAMA_GATE"
FLAG_DRAMA_GATE_COMPAT = "SCRIBE3_DRAMA_GATE_COMPAT"
FLAG_BEATS_SYNOPSIS_FALLBACK = "SCRIBE3_BEATS_SYNOPSIS_FALLBACK"
FLAG_CRAFT_NOVEL = "SCRIBE3_CRAFT_NOVEL"
FLAG_PILOT_SOFT_PRESSURE = "SCRIBE3_PILOT_SOFT_PRESSURE"
FLAG_PILOT_SOFT_AI_GRADE = "SCRIBE3_PILOT_SOFT_AI_GRADE"
FLAG_PARK_STROLL_BLOCKING = "SCRIBE3_PARK_STROLL_BLOCKING"
FLAG_DRAMA_HARD_PRESSURE = "SCRIBE3_DRAMA_HARD_PRESSURE"
# 叙事引擎 · 冲突/事件驱动（引导优先；代码默认全关）
FLAG_NARRATIVE_ENGINE = "SCRIBE3_NARRATIVE_ENGINE"
FLAG_EVENT_DRIVE_GATE = "SCRIBE3_EVENT_DRIVE_GATE"
FLAG_EVENT_LED_DETECT = "SCRIBE3_EVENT_LED_DETECT"
FLAG_OPENER_SOFT_TRACE = "SCRIBE3_OPENER_SOFT_TRACE"
FLAG_METAPHOR_SOFT_PER_1K = "SCRIBE3_METAPHOR_SOFT_PER_1K"
# 执行合同层（代码默认关）
FLAG_DEFAULT_DRAMA_STEER = "SCRIBE3_DEFAULT_DRAMA_STEER"
FLAG_SOFT_FULFILL = "SCRIBE3_SOFT_FULFILL"
FLAG_DRIVE_PROSE_DRIFT = "SCRIBE3_DRIVE_PROSE_DRIFT"
FLAG_SOFT_FULFILL_RESTEER = "SCRIBE3_SOFT_FULFILL_RESTEER"

# REGISTRY 内 novel-quality 旗键序（派生 CODE_DEFAULTS / 对齐检查用）
NQ_FLAG_KEYS: tuple[str, ...] = (
    FLAG_BEATS_V2,
    FLAG_DRAMA_GATE,
    FLAG_DRAMA_GATE_COMPAT,
    FLAG_BEATS_SYNOPSIS_FALLBACK,
    FLAG_CRAFT_NOVEL,
    FLAG_PILOT_SOFT_PRESSURE,
    FLAG_PILOT_SOFT_AI_GRADE,
    FLAG_PARK_STROLL_BLOCKING,
    FLAG_DRAMA_HARD_PRESSURE,
    FLAG_NARRATIVE_ENGINE,
    FLAG_EVENT_DRIVE_GATE,
    FLAG_EVENT_LED_DETECT,
    FLAG_OPENER_SOFT_TRACE,
    FLAG_METAPHOR_SOFT_PER_1K,
    FLAG_DEFAULT_DRAMA_STEER,
    FLAG_SOFT_FULFILL,
    FLAG_DRIVE_PROSE_DRIFT,
    FLAG_SOFT_FULFILL_RESTEER,
)


def _code_defaults_from_registry() -> dict[str, object]:
    """从 settings.REGISTRY 派生代码默认；单一真源，避免与 Setting.default 双份漂移。"""
    from scribe3.settings import _BY_KEY
    return {k: _BY_KEY[k].default for k in NQ_FLAG_KEYS}


# 导入时绑定一次；测试若 monkeypatch REGISTRY.default 可再调 _code_defaults_from_registry()
CODE_DEFAULTS: dict[str, object] = _code_defaults_from_registry()

# 产品目标 · 质量模式（demo env 推荐；非代码默认；手维与设计 Rollout 表对齐）
QUALITY_MODE_TARGETS: dict[str, object] = {
    FLAG_BEATS_V2: True,
    FLAG_DRAMA_GATE: True,
    FLAG_DRAMA_GATE_COMPAT: False,
    FLAG_BEATS_SYNOPSIS_FALLBACK: False,
    FLAG_CRAFT_NOVEL: True,
    FLAG_PILOT_SOFT_PRESSURE: False,
    FLAG_PILOT_SOFT_AI_GRADE: True,
    FLAG_PARK_STROLL_BLOCKING: True,
    FLAG_DRAMA_HARD_PRESSURE: 4,
    # 引导优先：质量模式开 ENGINE 注入；GATE/DETECT 硬拦仍可选（rev.2.3 默认不跟刑典）
    FLAG_NARRATIVE_ENGINE: True,
    FLAG_EVENT_DRIVE_GATE: False,
    FLAG_EVENT_LED_DETECT: True,
    FLAG_OPENER_SOFT_TRACE: True,
    FLAG_METAPHOR_SOFT_PER_1K: 6,
    # 执行合同：质量模式推荐开 STEER/FULFILL/DRIFT；RESTEER 仍关（KD-EC-4/11）
    FLAG_DEFAULT_DRAMA_STEER: True,
    FLAG_SOFT_FULFILL: True,
    FLAG_DRIVE_PROSE_DRIFT: True,
    FLAG_SOFT_FULFILL_RESTEER: False,
}

# 质量模式完整 env 另需的 PDC 半边（未进本 REGISTRY；os.environ 直读，见 pressure_drive）
# 仅对照 QUALITY_MODE_TARGETS 会漏这些键；demo 片段见设计文档 Rollout。
QUALITY_MODE_EXTERNAL_ENV: dict[str, object] = {
    "SCRIBE3_PDC": True,           # 压力驱动合同注入
    "SCRIBE3_PDC_BLOCKING": True,  # 后验 progress 可 blocking（与 PARK_STROLL 二选一即可执法）
    # SCRIBE3_PDC_GATE 可选；质量模式 demo 片段未强制
}


def assert_code_defaults_aligned() -> None:
    """轻量不变量：CODE_DEFAULTS 与当前 REGISTRY.default 一致（供单测/启动自检）。"""
    live = _code_defaults_from_registry()
    if live != CODE_DEFAULTS:
        raise AssertionError(
            f"CODE_DEFAULTS 与 REGISTRY 漂移: {CODE_DEFAULTS!r} vs {live!r}"
        )


# ── 观测 / 日志字段名（稳定合同；后续 PR 写 journal/warning 时复用）──────
# 设计 Observability 节 + soft-pass 扩展 soft_p / soft_ai。
#
# soft-pass 三套标识（PR-6b 已接）：
# - LOG_FIELD_SOFT_PASS：structured / journal 推荐键（本模块合同）
# - LEGACY_SOFT_PASS_KIND：现网 full_check `_pilot_quality_warn.kind`
# - LEGACY_SOFT_PASS_LOG_MSG：现网 warning 自然语言文案前缀（非 structured key）
# structured 字段用 LOG_FIELD_*；kind 可保留 LEGACY 作别名兼容；message 可继续自然语言。

LOG_FIELD_DRAMA_VALIDATION_OK = "drama_validation.ok"
LOG_FIELD_DRAMA_WEAK = "drama_weak"
LOG_FIELD_BEATS_SOURCE = "beats_source"
LOG_FIELD_PILOT_PARK = "pilot_park"
LOG_FIELD_PARK_STROLL = "park_stroll"
LOG_FIELD_SOFT_PASS = "pilot_full_check_soft_pass"
LEGACY_SOFT_PASS_KIND = "pilot_full_check_soft_nonblocking"
LEGACY_SOFT_PASS_LOG_MSG = "pilot full_check soft-pass"
LOG_FIELD_SOFT_P = "soft_p"  # pressure soft 是否生效（扩展字段）
LOG_FIELD_SOFT_AI = "soft_ai"  # AI-grade soft 是否生效（扩展字段）
LOG_FIELD_PURPLE_DENSITY = "purple_density"
LOG_FIELD_QUALITY_ENFORCEMENT = "quality_enforcement"

# 结构化日志 / journal note 推荐键集合（文档化；非强制 schema）
OBSERVABILITY_FIELDS: tuple[str, ...] = (
    LOG_FIELD_DRAMA_VALIDATION_OK,
    LOG_FIELD_DRAMA_WEAK,
    LOG_FIELD_BEATS_SOURCE,
    LOG_FIELD_PILOT_PARK,
    LOG_FIELD_PARK_STROLL,
    LOG_FIELD_SOFT_PASS,
    LOG_FIELD_SOFT_P,
    LOG_FIELD_SOFT_AI,
    LOG_FIELD_PURPLE_DENSITY,
    LOG_FIELD_QUALITY_ENFORCEMENT,
)


def _bool(key: str) -> bool:
    from scribe3.settings import get_setting
    return bool(get_setting(key))


def beats_v2_enabled() -> bool:
    """节拍 v2 生成可写 GCD 字段。代码默认 True。"""
    return _bool(FLAG_BEATS_V2)


def drama_gate_enabled() -> bool:
    """写前戏剧门（expand_beats advisory park）。代码默认 False（不 park）。"""
    return _bool(FLAG_DRAMA_GATE)


def drama_gate_compat_enabled() -> bool:
    """v1 仅 text → drama_weak 弱通过（validate 内）。代码默认 True。"""
    return _bool(FLAG_DRAMA_GATE_COMPAT)


def beats_synopsis_fallback_enabled() -> bool:
    """已废：接地失败不得切句充数。恒 False（保留读点以免旧测试 import 炸）。"""
    return False


def craft_novel_enabled() -> bool:
    """小说优先 craft 包。代码默认 False。"""
    return _bool(FLAG_CRAFT_NOVEL)


def pilot_soft_pressure_enabled() -> bool:
    """full_check 对 pressure/park_stroll soft-pass。代码默认 True。"""
    return _bool(FLAG_PILOT_SOFT_PRESSURE)


def pilot_soft_ai_grade_enabled() -> bool:
    """full_check 对 aggregate_ai_grade soft-pass。代码默认 True。"""
    return _bool(FLAG_PILOT_SOFT_AI_GRADE)


# full_check soft-pass 检测器名（与 loop.triage 投影一致；park_stroll 预留）
SOFT_DETS_PRESSURE: frozenset[str] = frozenset({"pressure_metrics", "park_stroll"})
SOFT_DETS_AI_GRADE: frozenset[str] = frozenset({"aggregate_ai_grade"})


def soft_pass_detectors_for(
    soft_pressure: bool,
    soft_ai: bool,
) -> frozenset[str]:
    """按双旗构建 full_check soft 集合（纯函数 · PR-6b / KD-NQ-11）。

    - ``soft_pressure`` → ``pressure_metrics`` / ``park_stroll``
    - ``soft_ai`` → ``aggregate_ai_grade``
    - 禁止单旗绑死 AI+pressure
    """
    soft: set[str] = set()
    if soft_pressure:
        soft |= SOFT_DETS_PRESSURE
    if soft_ai:
        soft |= SOFT_DETS_AI_GRADE
    return frozenset(soft)


def full_check_soft_detectors() -> frozenset[str]:
    """当前生效旗下的 soft-pass 检测器集合（读 settings）。"""
    return soft_pass_detectors_for(
        pilot_soft_pressure_enabled(),
        pilot_soft_ai_grade_enabled(),
    )


def full_check_blocking_is_only_soft(
    blocking: list[dict] | list,
    soft_dets: frozenset[str] | set[str],
) -> bool:
    """blocking 列表是否全部属于 soft 集合（非空且仅 soft → soft-pass）。"""
    if not blocking:
        return False
    if not soft_dets:
        return False
    return all((b.get("detector") or "") in soft_dets for b in blocking)


def soft_pass_category_flags(blocking: list[dict] | list) -> dict[str, bool]:
    """当次 soft-pass 涉及的类别（扩展字段 soft_p / soft_ai）。"""
    dets = {(b.get("detector") or "") for b in blocking}
    return {
        LOG_FIELD_SOFT_P: bool(dets & SOFT_DETS_PRESSURE),
        LOG_FIELD_SOFT_AI: bool(dets & SOFT_DETS_AI_GRADE),
    }


def park_stroll_blocking_enabled() -> bool:
    """park_stroll / spatial 在高压章可升 blocking（PR-6a）。代码默认 False。"""
    return _bool(FLAG_PARK_STROLL_BLOCKING)


def drama_hard_pressure() -> int:
    """高压门槛（默认 4；可用 env 覆盖试 3）。

    信任 ``get_setting``：int 型经 ``_coerce`` 后为 int；坏 env fail-soft 已回落 REGISTRY.default。
    """
    from scribe3.settings import get_setting
    return int(get_setting(FLAG_DRAMA_HARD_PRESSURE))


def narrative_engine_enabled() -> bool:
    """冲突/事件驱动引导（ensure + 注入）。代码默认 False。"""
    return _bool(FLAG_NARRATIVE_ENGINE)


def event_drive_gate_enabled() -> bool:
    """高压 drive/align 硬 park。代码默认 False（引导优先）。"""
    return _bool(FLAG_EVENT_DRIVE_GATE)


def event_led_detect_enabled() -> bool:
    """写后 event_drive 检测。代码默认 False。"""
    return _bool(FLAG_EVENT_LED_DETECT)


def opener_soft_trace_enabled() -> bool:
    """开篇外力 soft 日志。代码默认 False。永不 blocking。"""
    return _bool(FLAG_OPENER_SOFT_TRACE)


def metaphor_soft_per_1k() -> float:
    """比喻 soft 阈值（每千字）；0=关。"""
    from scribe3.settings import get_setting
    try:
        return float(get_setting(FLAG_METAPHOR_SOFT_PER_1K) or 0)
    except (TypeError, ValueError):
        return 0.0


def default_drama_steer_enabled() -> bool:
    """默认首写戏剧执行合同。代码默认 False。"""
    return _bool(FLAG_DEFAULT_DRAMA_STEER)


def soft_fulfill_enabled() -> bool:
    """写后 soft 履约。代码默认 False。永不 blocking。"""
    return _bool(FLAG_SOFT_FULFILL)


def drive_prose_drift_enabled() -> bool:
    """Drive–Prose 漂移 soft。代码默认 False。"""
    return _bool(FLAG_DRIVE_PROSE_DRIFT)


def soft_fulfill_resteer_enabled() -> bool:
    """路径 D 可选扩写清稿。代码默认 False（危险）。"""
    return _bool(FLAG_SOFT_FULFILL_RESTEER)


def quality_enforcement_on() -> bool:
    """质量执法复合条件（设计真值表）。

    ``SOFT_PRESSURE=0`` **且**（``PDC_BLOCKING=1`` **或** ``PARK_STROLL_BLOCKING=1``）。

    注意：``SCRIBE3_PDC_BLOCKING`` 仍走既有 ``pressure_drive.pdc_blocking_env_enabled``
    （尚未迁入本 REGISTRY）。finding severity 升档看 ``park_stroll_blocking_enabled`` /
    ``pdc_blocking``；本复合条件供质量模式观测与 PR-6b soft-pass 对齐。
    """
    if pilot_soft_pressure_enabled():
        return False
    pdc_blocking = False
    try:
        from scribe3.pressure_drive import pdc_blocking_env_enabled
        pdc_blocking = bool(pdc_blocking_env_enabled())
    except (ImportError, AttributeError) as e:
        # 收窄：仅导入/符号缺失回落 False；其它异常上抛以免执法静默变弱
        _log.warning("pdc_blocking_env_enabled 不可用，按 False 回落: %s", e)
        pdc_blocking = False
    return pdc_blocking or park_stroll_blocking_enabled()


def novel_quality_flags_snapshot() -> dict[str, Any]:
    """当前生效旗快照（观测/调试；不改变行为）。"""
    return {
        FLAG_BEATS_V2: beats_v2_enabled(),
        FLAG_DRAMA_GATE: drama_gate_enabled(),
        FLAG_DRAMA_GATE_COMPAT: drama_gate_compat_enabled(),
        FLAG_BEATS_SYNOPSIS_FALLBACK: beats_synopsis_fallback_enabled(),
        FLAG_CRAFT_NOVEL: craft_novel_enabled(),
        FLAG_PILOT_SOFT_PRESSURE: pilot_soft_pressure_enabled(),
        FLAG_PILOT_SOFT_AI_GRADE: pilot_soft_ai_grade_enabled(),
        FLAG_PARK_STROLL_BLOCKING: park_stroll_blocking_enabled(),
        FLAG_DRAMA_HARD_PRESSURE: drama_hard_pressure(),
        FLAG_NARRATIVE_ENGINE: narrative_engine_enabled(),
        FLAG_EVENT_DRIVE_GATE: event_drive_gate_enabled(),
        FLAG_EVENT_LED_DETECT: event_led_detect_enabled(),
        FLAG_OPENER_SOFT_TRACE: opener_soft_trace_enabled(),
        FLAG_METAPHOR_SOFT_PER_1K: metaphor_soft_per_1k(),
        FLAG_DEFAULT_DRAMA_STEER: default_drama_steer_enabled(),
        FLAG_SOFT_FULFILL: soft_fulfill_enabled(),
        FLAG_DRIVE_PROSE_DRIFT: drive_prose_drift_enabled(),
        FLAG_SOFT_FULFILL_RESTEER: soft_fulfill_resteer_enabled(),
        LOG_FIELD_QUALITY_ENFORCEMENT: quality_enforcement_on(),
    }
