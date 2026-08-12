"""GAP-13：双链审批统一观察面（canon ChangePack 与 MCP commit 共用结构）。"""
from __future__ import annotations

import threading
import time
from typing import Any

_LOCK = threading.Lock()
_EVENTS: list[dict[str, Any]] = []
_MAX = 500


def record_approval_event(
    *,
    chain: str,
    action: str,
    work: str = "main",
    tool_or_pack: str = "",
    status: str = "",
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """chain: mcp | canon | rest。"""
    row = {
        "ts": time.time(),
        "chain": chain,
        "action": action,
        "work": work,
        "tool_or_pack": tool_or_pack,
        "status": status,
        "detail": detail or {},
    }
    with _LOCK:
        _EVENTS.append(row)
        if len(_EVENTS) > _MAX:
            del _EVENTS[: len(_EVENTS) - _MAX]
    return dict(row)


def list_approval_events(*, work: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    lim = max(1, min(200, int(limit or 50)))
    with _LOCK:
        rows = list(_EVENTS)
    if work:
        rows = [r for r in rows if r.get("work") == work]
    return list(reversed(rows[-lim:]))


def clear_for_tests() -> None:
    with _LOCK:
        _EVENTS.clear()
