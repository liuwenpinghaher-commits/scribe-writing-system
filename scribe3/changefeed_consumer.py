"""S-2: Changefeed 驱动缓存失效（可选）。

flag SCRIBE3_CHANGEFEED_CACHE 开时轮询 SHOW CHANGES，对变更表调用
context_cache.emit_invalidation / invalidate_by_table。
默认关；与手动 emit 可双跑。
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable

_log = logging.getLogger("scribe3.changefeed")

_TRUE = {"1", "true", "yes", "on"}
# 旁路 cache_watch（带 CHANGEFEED）为主；直接表 SHOW CHANGES 作补充（常为空直至 DDL）
_WATCH = ("cache_watch", "proposition", "memory_item", "material", "chapter", "character")


def changefeed_cache_enabled() -> bool:
    try:
        from scribe3.settings import get_setting
        v = get_setting("SCRIBE3_CHANGEFEED_CACHE")
        if v is not None:
            return bool(v)
    except Exception:
        pass
    return (os.environ.get("SCRIBE3_CHANGEFEED_CACHE") or "").strip().lower() in _TRUE


def apply_changes_to_cache(changes: list[dict], work: str | None = None) -> set[str]:
    """将 changefeed 行应用到缓存失效。返回触及的表名集合。

    支持：
    - cache_watch 行：value.table_name / table_name
    - 其它表：id 前缀
    不向 cache_watch 再双写（避免环）。
    """
    from scribe3.context_cache import emit_invalidation

    touched: set[str] = set()

    def _touch(table: str, w: str | None = None) -> None:
        t = (table or "").strip()
        if not t or t == "cache_watch":
            return
        emit_invalidation(t, w if w is not None else work)
        touched.add(t)

    for ch in changes or []:
        if not isinstance(ch, dict):
            continue
        # Surreal SHOW CHANGES 形态：{ changes: [...], versionstamp: ... }
        if "changes" in ch:
            for inner in ch.get("changes") or []:
                if not isinstance(inner, dict):
                    continue
                # create/update payload
                val = inner.get("value") or inner.get("after") or inner
                if isinstance(val, dict):
                    tn = val.get("table_name") or val.get("table")
                    ww = val.get("work")
                    if tn:
                        _touch(str(tn), str(ww) if ww else work)
                        continue
                vid = inner.get("id") or (val.get("id") if isinstance(val, dict) else None)
                if vid is not None:
                    s = str(vid)
                    if ":" in s:
                        _touch(s.split(":", 1)[0], work)
            continue
        table = ch.get("table") or ch.get("tb") or ch.get("table_name")
        if table:
            _touch(str(table), work)
    return touched


def poll_table_changes(store: Any, table: str, since: str | int | None = None) -> list:
    """SHOW CHANGES FOR TABLE … — 返回原始行列表。

    Surreal 3.2 要求 ``SINCE``（不可仅 LIMIT）；无 cursor 时用 ``SINCE 0``。
    """
    try:
        if since is None or since == "" :
            since = 0
        # 语法：SHOW CHANGES FOR TABLE name SINCE <versionstamp|0> [LIMIT n]
        q = f"SHOW CHANGES FOR TABLE {table} SINCE $since LIMIT 50;"
        return store._query(q, {"since": since}) or []
    except Exception as e:
        _log.debug("poll %s: %s", table, e)
        return []


class ChangefeedCacheWorker:
    """后台线程：轮询关键表 changefeed 并失效缓存。"""

    def __init__(self, store_factory: Callable[[], Any], work: str = "main", interval: float = 2.0):
        self._factory = store_factory
        self._work = work
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cursors: dict[str, Any] = {}

    def start(self) -> None:
        if not changefeed_cache_enabled():
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="s3-changefeed-cache", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                st = self._factory()
                for table in _WATCH:
                    rows = poll_table_changes(st, table, self._cursors.get(table))
                    if not rows:
                        continue
                    # 更新 cursor
                    last = rows[-1]
                    if isinstance(last, dict) and "versionstamp" in last:
                        self._cursors[table] = last["versionstamp"]
                    apply_changes_to_cache(rows if isinstance(rows, list) else [rows], self._work)
            except Exception as e:
                _log.debug("changefeed loop: %s", e)
            self._stop.wait(self._interval)
