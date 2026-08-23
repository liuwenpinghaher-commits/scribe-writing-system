"""最近一次写路径组装的预算报告（无 I/O）。store 与 api 共用。"""
from __future__ import annotations

import logging
import threading
from typing import Any

_WRITE_SOFT_FAIL_COUNTERS: dict[str, int] = {
    "epistemic_guard": 0,
    "empty_drama": 0,
    "empty_outline": 0,
    "continue_snapshot_skip": 0,
}
_LAST_WRITE_BUDGET_REPORT: dict[str, Any] = {}
_WRITE_OBS_LOCK = threading.Lock()


def record_write_soft_fail(kind: str) -> None:
    key = str(kind or "unknown")
    with _WRITE_OBS_LOCK:
        _WRITE_SOFT_FAIL_COUNTERS[key] = int(_WRITE_SOFT_FAIL_COUNTERS.get(key, 0)) + 1
        count = _WRITE_SOFT_FAIL_COUNTERS[key]
    logging.getLogger("scribe3").info("write_soft_fail kind=%s count=%s", key, count)


def get_write_soft_fail_counters() -> dict[str, int]:
    with _WRITE_OBS_LOCK:
        return dict(_WRITE_SOFT_FAIL_COUNTERS)


def get_last_write_budget_report() -> dict[str, Any]:
    with _WRITE_OBS_LOCK:
        return dict(_LAST_WRITE_BUDGET_REPORT)


def _store_write_budget_report(report: dict[str, Any] | None) -> None:
    if not report:
        return
    with _WRITE_OBS_LOCK:
        _LAST_WRITE_BUDGET_REPORT.clear()
        _LAST_WRITE_BUDGET_REPORT.update(report)
