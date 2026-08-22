"""GAP-12：讨论/写路径 LLM 必须经 Hermes 审计约定。

生产 chat 组装走 HermesRuntime；本模块提供可测断言与旁路检测。
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import os
from typing import Any


def hermes_only_enforced() -> bool:
    raw = (get_flag("SCRIBE3_HERMES_ONLY_LLM") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def is_hermes_complete_fn(fn: Any) -> bool:
    if fn is None:
        return False
    name = getattr(fn, "__name__", "") or ""
    mod = getattr(fn, "__module__", "") or ""
    return "hermes" in name.lower() or "hermes" in mod.lower()


def assert_llm_path_ok(fn: Any, *, path: str = "discuss") -> dict[str, Any]:
    """返回检查结果；enforced 时非 Hermes 标记 bypass=True。"""
    ok = is_hermes_complete_fn(fn) or fn is None  # None = 无 LLM 调用
    bypass = hermes_only_enforced() and fn is not None and not is_hermes_complete_fn(fn)
    return {
        "path": path,
        "ok": ok and not bypass,
        "bypass": bypass,
        "fn": getattr(fn, "__name__", repr(fn))[:80],
    }
