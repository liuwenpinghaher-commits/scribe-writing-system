"""章设计中间稿：每一整份生成留一档。过审看整份，不拼半成品。"""
from __future__ import annotations

from typing import Any


def record_attempt(
    n: int,
    parsed: dict[str, Any] | None,
    dens,
    *,
    raw: str = "",
) -> dict[str, Any]:
    src = parsed if isinstance(parsed, dict) else {}
    errors = list(getattr(dens, "errors", None) or [])
    if not src.get("ok"):
        code = str(src.get("code") or "unparsed")
        if code and code not in errors:
            errors = [code] + errors
    return {
        "n": int(n),
        "struct_ok": bool(src.get("ok")),
        "exam_ok": bool(dens is not None and getattr(dens, "ok", False)),
        "errors": errors,
        "chapter_spine": src.get("chapter_spine") if isinstance(src.get("chapter_spine"), dict) else {},
        "beats": src.get("beats") if isinstance(src.get("beats"), list) else [],
        "clock": src.get("clock") if isinstance(src.get("clock"), dict) else {},
        "place": src.get("place") if isinstance(src.get("place"), dict) else {},
        "designated_beat": src.get("designated_beat"),
        "synopsis": src.get("synopsis") or "",
        "raw_cn": int(src.get("cn") or 0),
        "raw_head": (raw or "")[:240],
    }


def first_passed(attempts: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """历史+本轮多份一块看：哪一整份过了，就用哪一份。不拼格子。"""
    for row in attempts or []:
        if row.get("struct_ok") and row.get("exam_ok"):
            return row
    return None


def slim_attempts(attempts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out = []
    for row in attempts or []:
        out.append({
            "n": row.get("n"),
            "ok": bool(row.get("struct_ok") and row.get("exam_ok")),
            "errors": list(row.get("errors") or []),
        })
    return out
