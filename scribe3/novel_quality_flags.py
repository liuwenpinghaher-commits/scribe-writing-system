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
  其余（DRAMA_GATE / craft / soft-pass / park_stroll）仍在 PR-3/5/6a/6b。
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
# soft-pass 三套标识（PR-6b 接线时统一）：
# - LOG_FIELD_SOFT_PASS：structured / journal 推荐键（本模块合同）
# - LEGACY_SOFT_PASS_KIND：现网 full_check `_pilot_quality_warn.kind`
# - LEGACY_SOFT_PASS_LOG_MSG：现网 warning 自然语言文案前缀（非 structured key）
# PR-6b：structured 字段用 LOG_FIELD_*；kind 可保留 LEGACY 作别名兼容；message 可继续自然语言。

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
    """写前戏剧门。代码默认 False（不 park）。"""
    return _bool(FLAG_DRAMA_GATE)


def drama_gate_compat_enabled() -> bool:
    """v1 仅 text → drama_weak 弱通过。代码默认 True。"""
    return _bool(FLAG_DRAMA_GATE_COMPAT)


def beats_synopsis_fallback_enabled() -> bool:
    """接地失败时 synopsis 切句充数。代码默认 True（兼容）。"""
    return _bool(FLAG_BEATS_SYNOPSIS_FALLBACK)


def craft_novel_enabled() -> bool:
    """小说优先 craft 包。代码默认 False。"""
    return _bool(FLAG_CRAFT_NOVEL)


def pilot_soft_pressure_enabled() -> bool:
    """full_check 对 pressure/park_stroll soft-pass。代码默认 True。"""
    return _bool(FLAG_PILOT_SOFT_PRESSURE)


def pilot_soft_ai_grade_enabled() -> bool:
    """full_check 对 aggregate_ai_grade soft-pass。代码默认 True。"""
    return _bool(FLAG_PILOT_SOFT_AI_GRADE)


def park_stroll_blocking_enabled() -> bool:
    """park_stroll 在质量执法下可升 blocking。代码默认 False。"""
    return _bool(FLAG_PARK_STROLL_BLOCKING)


def drama_hard_pressure() -> int:
    """高压门槛（默认 4；可用 env 覆盖试 3）。

    信任 ``get_setting``：int 型经 ``_coerce`` 后为 int；坏 env fail-soft 已回落 REGISTRY.default。
    """
    from scribe3.settings import get_setting
    return int(get_setting(FLAG_DRAMA_HARD_PRESSURE))


def quality_enforcement_on() -> bool:
    """质量执法复合条件（设计真值表）。

    ``SOFT_PRESSURE=0`` **且**（``PDC_BLOCKING=1`` **或** ``PARK_STROLL_BLOCKING=1``）。

    注意：``SCRIBE3_PDC_BLOCKING`` 仍走既有 ``pressure_drive.pdc_blocking_env_enabled``
    （尚未迁入本 REGISTRY）；本函数仅供后续 PR 读取，PR-0 无调用方。
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
        LOG_FIELD_QUALITY_ENFORCEMENT: quality_enforcement_on(),
    }
