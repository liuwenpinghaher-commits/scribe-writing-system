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
# 最优：真表自带 CHANGEFEED（重建库后 SHOW 有数据）；cache_watch 双写作补充
_WATCH = ("proposition", "memory_item", "material", "chapter", "character", "event", "cache_watch")


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

    支持 Surreal 3.2 SHOW CHANGES 形态::
      { versionstamp, changes: [ {update: {...}} | {create: {...}} | {id: ...} ] }

    cache_watch 行：payload.table_name → 目标表；不向 cache_watch 再双写（避免环）。
    """
    from scribe3.context_cache import emit_invalidation

    touched: set[str] = set()

    def _touch(table: str, w: str | None = None) -> None:
        t = (table or "").strip()
        if not t or t == "cache_watch":
            return
        emit_invalidation(t, w if w is not None else work)
        touched.add(t)

    def _from_payload(val: dict) -> bool:
        if not isinstance(val, dict):
            return False
        # 跳过 DDL define_table 等
        if "define_table" in val or "define_field" in val:
            return False
        tn = val.get("table_name") or val.get("table")
        ww = val.get("work")
        if tn:
            _touch(str(tn), str(ww) if ww not in (None, "") else work)
            return True
        vid = val.get("id")
        if vid is not None:
            s = str(vid)
            if ":" in s:
                _touch(s.split(":", 1)[0], work)
                return True
        return False

    for ch in changes or []:
        if not isinstance(ch, dict):
            continue
        # Surreal SHOW CHANGES 形态：{ changes: [...], versionstamp: ... }
        if "changes" in ch:
            for inner in ch.get("changes") or []:
                if not isinstance(inner, dict):
                    continue
                # 3.2 常见：{"update": row} / {"create": row} / {"delete": {...}}
                handled = False
                for key in ("update", "create", "value", "after"):
                    if key in inner and isinstance(inner.get(key), dict):
                        handled = _from_payload(inner[key]) or handled
                if handled:
                    continue
                if "define_table" in inner or "define_field" in inner:
                    continue
                # 扁平 id / table_name
                if _from_payload(inner):
                    continue
                vid = inner.get("id")
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

    Surreal 3.2 要求 ``SINCE``（不可仅 LIMIT）；**不接受参数绑定** ``$since``，
    须字面 versionstamp / 0 / datetime。无 cursor 时用 ``SINCE 0``。
    """
    try:
        if since is None or since == "":
            since_lit = "0"
        elif isinstance(since, bool):
            since_lit = "0"
        elif isinstance(since, int):
            since_lit = str(int(since))
        else:
            s = str(since).strip()
            # 仅允许数字 versionstamp 或 d"…" 日期字面量，防注入
            if s.isdigit() or (s.startswith("d\"") and s.endswith("\"")):
                since_lit = s
            else:
                # 尝试纯数字 versionstamp 字符串
                try:
                    since_lit = str(int(s))
                except Exception:
                    since_lit = "0"
        # 表名白名单形态：字母数字下划线
        if not str(table).replace("_", "").isalnum():
            return []
        q = f"SHOW CHANGES FOR TABLE {table} SINCE {since_lit} LIMIT 50;"
        return store._query(q) or []
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
        self._started_at: float | None = None
        self._last_ok_at: float | None = None
        self._last_error: str | None = None
        self._poll_count: int = 0
        self._invalidate_count: int = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        if not changefeed_cache_enabled():
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._started_at = time.time()
        self._thread = threading.Thread(target=self._run, name="s3-changefeed-cache", daemon=True)
        self._thread.start()
        _log.warning("changefeed cache worker started interval=%s work=%s", self._interval, self._work)

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": changefeed_cache_enabled(),
                "alive": bool(self._thread and self._thread.is_alive()),
                "started_at": self._started_at,
                "last_ok_at": self._last_ok_at,
                "last_error": self._last_error,
                "poll_count": self._poll_count,
                "invalidate_count": self._invalidate_count,
                "cursors": dict(self._cursors),
                "work": self._work,
            }

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                st = self._factory()
                batch_touched = 0
                for table in _WATCH:
                    rows = poll_table_changes(st, table, self._cursors.get(table))
                    with self._lock:
                        self._poll_count += 1
                    if not rows:
                        continue
                    # 更新 cursor
                    last = rows[-1]
                    if isinstance(last, dict) and "versionstamp" in last:
                        self._cursors[table] = last["versionstamp"]
                    touched = apply_changes_to_cache(
                        rows if isinstance(rows, list) else [rows], self._work)
                    batch_touched += len(touched or ())
                with self._lock:
                    self._last_ok_at = time.time()
                    self._last_error = None
                    self._invalidate_count += batch_touched
            except Exception as e:
                with self._lock:
                    self._last_error = str(e)[:200]
                _log.debug("changefeed loop: %s", e)
            self._stop.wait(self._interval)
