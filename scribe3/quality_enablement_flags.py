"""第一原则质量使能 · 旗读点（get_setting → env → 默认）。

避免各模块手抄 os.environ 与 REGISTRY 双默认漂移。
"""
from __future__ import annotations

from typing import Any


def _get(key: str, default: Any = None) -> Any:
    try:
        from scribe3.settings import get_setting
        return get_setting(key)
    except Exception:
        from scribe3.feature_flags import get_flag
        raw = get_flag(key)
        if raw is None or raw == "":
            return default
        if isinstance(default, bool):
            return str(raw).strip().lower() in ("1", "true", "yes", "on")
        return raw


def _as_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def provenance_in_prompt_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_PROVENANCE_IN_PROMPT", False), False)


def create_mode() -> str:
    raw = str(_get("SCRIBE3_CREATE_MODE", "standard") or "standard").strip().lower()
    return "explore" if raw == "explore" else "standard"


def explore_soft_save_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_EXPLORE_SOFT_SAVE", True), True)


def explore_ingest_hold_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_EXPLORE_INGEST_HOLD", True), True)


def craft_finalize_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_CRAFT_FINALIZE", True), True)


def structure_diversity_inject_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_STRUCTURE_DIVERSITY_INJECT", True), True)


def ending_formula_blocking() -> bool:
    return _as_bool(_get("SCRIBE3_ENDING_FORMULA_BLOCKING", False), False)


def volume_intro_compact_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_VOLUME_INTRO_COMPACT", True), True)


def phase_role_dedup_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_PHASE_ROLE_DEDUP", True), True)


def avoid_merge_antislop_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_AVOID_MERGE_ANTISLOP", True), True)


def pressure_diff_only_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_PRESSURE_DIFF_ONLY", True), True)


def director_creative_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_DIRECTOR_CREATIVE", True), True)


def graph_co_present_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_GRAPH_CO_PRESENT", False), False)


def outline_after_drama_enabled() -> bool:
    return _as_bool(_get("SCRIBE3_OUTLINE_AFTER_DRAMA", True), True)
