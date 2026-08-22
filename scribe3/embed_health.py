"""SYS-06：嵌入服务探活。"""
from __future__ import annotations


def embedding_health() -> dict:
    try:
        import fastembed  # noqa: F401
        from scribe3 import embed as E
        return {
            "ok": True,
            "fastembed": True,
            "loaded": getattr(E, "_model", None) is not None,
            "model": getattr(E, "_MODEL_NAME", ""),
        }
    except Exception as e:
        return {"ok": False, "fastembed": False, "error": type(e).__name__}
