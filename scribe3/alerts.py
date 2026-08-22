"""SYS-05：关键事件可推 webhook（没配地址就只记日志）。"""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

_log = logging.getLogger("scribe3.alerts")


def emit_alert(kind: str, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"kind": kind, "message": message, **(extra or {})}
    url = ""
    try:
        from scribe3.feature_flags import get_flag
        url = (get_flag("SCRIBE3_ALERT_WEBHOOK") or "").strip()
    except Exception:
        url = ""
    if not url:
        _log.warning("alert kind=%s msg=%s (no webhook)", kind, message)
        return {"ok": True, "delivered": False, "reason": "no_webhook", "payload": payload}
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return {"ok": True, "delivered": True, "status": getattr(resp, "status", 0)}
    except Exception as e:
        _log.warning("alert webhook fail kind=%s: %s", kind, e)
        return {"ok": False, "delivered": False, "error": type(e).__name__}
