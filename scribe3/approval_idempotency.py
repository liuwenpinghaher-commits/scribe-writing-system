"""审批幂等指纹（O13 · 进程内缓存，可换 store 背书）。"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

_lock = threading.Lock()
# fingerprint -> {result, ts, tool}
_CACHE: dict[str, dict[str, Any]] = {}
_TTL_SEC = 24 * 3600
_MAX_SIZE = 1024  # P1-14：进程内缓存上限，防无限膨胀


def _prune_expired_unlocked(now: float | None = None) -> None:
    """持锁调用：剔 TTL 过期项；若仍超 maxsize 按最旧 ts 裁剪。"""
    t = time.time() if now is None else float(now)
    expired = [
        k for k, row in _CACHE.items()
        if t - float(row.get("ts") or 0) > _TTL_SEC
    ]
    for k in expired:
        _CACHE.pop(k, None)
    if len(_CACHE) <= _MAX_SIZE:
        return
    # 最旧优先
    ordered = sorted(_CACHE.items(), key=lambda kv: float(kv[1].get("ts") or 0))
    overflow = len(_CACHE) - _MAX_SIZE
    for k, _ in ordered[:overflow]:
        _CACHE.pop(k, None)


def compute_approval_fingerprint(tool_name: str, args: dict | None) -> str:
    """工具名 + 稳定序列化参数 → 16 hex 指纹。"""
    key_args = {k: v for k, v in sorted((args or {}).items()) if k != "timestamp"}
    try:
        payload = f"{tool_name}:{json.dumps(key_args, sort_keys=True, default=str, ensure_ascii=False)}"
    except Exception:
        payload = f"{tool_name}:{sorted(key_args.items())!r}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def lookup_approved(fingerprint: str) -> Any | None:
    """命中且未过期则返回首次 result。"""
    fp = str(fingerprint or "")
    if not fp:
        return None
    with _lock:
        row = _CACHE.get(fp)
        if not row:
            return None
        if time.time() - float(row.get("ts") or 0) > _TTL_SEC:
            _CACHE.pop(fp, None)
            return None
        return row.get("result")


def record_approved(fingerprint: str, tool_name: str, result: Any) -> None:
    fp = str(fingerprint or "")
    if not fp:
        return
    with _lock:
        _CACHE[fp] = {
            "tool": tool_name,
            "result": result,
            "ts": time.time(),
        }
        if len(_CACHE) > _MAX_SIZE:
            _prune_expired_unlocked()


def clear_approval_cache() -> None:
    with _lock:
        _CACHE.clear()


def approval_cache_size() -> int:
    with _lock:
        return len(_CACHE)
