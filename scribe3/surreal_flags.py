"""Surreal 深度利用 feature flags（S-1…S-8）。默认关，探活绿后再开。"""
from __future__ import annotations

import os

_TRUE = {"1", "true", "yes", "on"}


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        try:
            from scribe3.settings import get_setting
            v = get_setting(key)
            if v is not None:
                return bool(v)
        except Exception:
            pass
        return default
    return raw.strip().lower() in _TRUE


def hybrid_search_native() -> bool:
    return _env_bool("SCRIBE3_HYBRID_SEARCH_NATIVE", False)


def changefeed_cache() -> bool:
    return _env_bool("SCRIBE3_CHANGEFEED_CACHE", False)


def db_inflight_lock() -> bool:
    return _env_bool("SCRIBE3_DB_INFLIGHT_LOCK", False)


def db_knowledge_frame() -> bool:
    return _env_bool("SCRIBE3_DB_KNOWLEDGE_FRAME", False)


def stats_view_read() -> bool:
    return _env_bool("SCRIBE3_STATS_VIEW", False)


def live_granular() -> bool:
    """S-8 默认开：多带 action/id，兼容只读 table 的旧客户端。"""
    return _env_bool("SCRIBE3_LIVE_GRANULAR", True)
