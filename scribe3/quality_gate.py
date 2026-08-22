"""统一判定出口形状。旗关时调用方仍走旧层。"""
from __future__ import annotations

from typing import Any, Mapping


def gate_result(*, ok: bool, code: str = "", message: str = "", hits: list | None = None) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "code": str(code or ("ok" if ok else "reject")),
        "message": str(message or ""),
        "hits": list(hits or []),
    }


def from_existing(out: Mapping[str, Any] | None) -> dict[str, Any]:
    src = dict(out or {})
    if "ok" in src and "code" in src and "message" in src and "hits" in src:
        return gate_result(ok=src["ok"], code=src["code"], message=src["message"], hits=src.get("hits"))
    ok = src.get("ok")
    if ok is None:
        ok = not bool(src.get("error") or src.get("blocked"))
    return gate_result(
        ok=bool(ok),
        code=str(src.get("code") or ("ok" if ok else "reject")),
        message=str(src.get("message") or src.get("error") or ""),
        hits=list(src.get("hits") or src.get("issues") or []),
    )
