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
_WATCH = ("proposition", "memory_item", "material", "chapter", "character")


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

    纯函数侧：从 change 行提取 table，调 emit_invalidation。
    """
    from scribe3.context_cache import emit_invalidation

    touched: set[str] = set()
    for ch in changes or []:
        if not isinstance(ch, dict):
            continue
        # Surreal SHOW CHANGES 形态：{ changes: [...], versionstamp: ... } 或扁平
        table = ch.get("table") or ch.get("tb")
        if not table and "changes" in ch:
            for inner in ch.get("changes") or []:
                if isinstance(inner, dict):
                    # value may be {id: ...} define table from id
                    vid = inner.get("id") or (inner.get("value") or {}).get("id")
                    if vid is not None:
                        # id like proposition:xyz
                        s = str(vid)
                        table = s.split(":")[0] if ":" in s else None
                    if table:
                        emit_invalidation(str(table), work)
                        touched.add(str(table))
            continue
        if table:
            emit_invalidation(str(table), work)
            touched.add(str(table))
    return touched


def poll_table_changes(store: Any, table: str, since: str | int | None = None) -> list:
    """SHOW CHANGES FOR TABLE … — 返回原始行列表。"""
    try:
        if since is None or since == "" or since == 0:
            q = f"SHOW CHANGES FOR TABLE {table} LIMIT 50;"
            return store._query(q) or []
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
