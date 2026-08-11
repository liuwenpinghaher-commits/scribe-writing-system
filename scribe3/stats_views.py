"""S-6: 读取聚合视图表（stats_*）。flag 关或视图不存在时回退 ad-hoc count。"""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("scribe3.stats_views")


def stats_view_enabled() -> bool:
    try:
        from scribe3.surreal_flags import stats_view_read
        return stats_view_read()
    except Exception:
        return False


def read_chapter_count(store: Any) -> int:
    """章计数：优先 stats_chapter_count 视图。"""
    if stats_view_enabled():
        try:
            rows = store._query("SELECT n FROM stats_chapter_count;") or []
            if rows and isinstance(rows[0], dict) and rows[0].get("n") is not None:
                return int(rows[0]["n"])
        except Exception as e:
            _log.debug("stats_chapter_count fallback: %s", e)
    try:
        rows = store._query("SELECT count() AS n FROM chapter GROUP ALL;") or []
        if rows and isinstance(rows[0], dict):
            return int(rows[0].get("n") or 0)
    except Exception:
        pass
    try:
        return len(store.chapters_lite() or [])
    except Exception:
        return 0


def read_open_promise_count(store: Any) -> int:
    if stats_view_enabled():
        try:
            rows = store._query("SELECT n FROM stats_open_promises;") or []
            if rows and isinstance(rows[0], dict) and rows[0].get("n") is not None:
                return int(rows[0]["n"])
        except Exception as e:
            _log.debug("stats_open_promises fallback: %s", e)
    try:
        rows = store._query(
            "SELECT count() AS n FROM promise WHERE status = 'open' GROUP ALL;"
        ) or []
        if rows and isinstance(rows[0], dict):
            return int(rows[0].get("n") or 0)
    except Exception:
        return 0
    return 0
