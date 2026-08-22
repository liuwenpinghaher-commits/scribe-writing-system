"""Surreal 深度利用 feature flags（S-1…S-8）。质量/一致性默认开。"""
from __future__ import annotations

from scribe3.feature_flags import flag_truthy

_TRUE = {"1", "true", "yes", "on"}


def _env_bool(key: str, default: bool = True) -> bool:
    try:
        return flag_truthy(key)
    except Exception:
        return default


def hybrid_search_native() -> bool:
    return _env_bool("SCRIBE3_HYBRID_SEARCH_NATIVE", True)


def changefeed_cache() -> bool:
    return _env_bool("SCRIBE3_CHANGEFEED_CACHE", True)


def db_inflight_lock() -> bool:
    return _env_bool("SCRIBE3_DB_INFLIGHT_LOCK", True)


def db_knowledge_frame() -> bool:
    return _env_bool("SCRIBE3_DB_KNOWLEDGE_FRAME", True)


def stats_view_read() -> bool:
    return _env_bool("SCRIBE3_STATS_VIEW", True)


def live_granular() -> bool:
    """S-8 默认开：多带 action/id，兼容只读 table 的旧客户端。"""
    return _env_bool("SCRIBE3_LIVE_GRANULAR", True)
