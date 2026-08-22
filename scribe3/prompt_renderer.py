"""统一渲染：XML 主干 + 【】子节。旗关时不改现网组装。"""
from __future__ import annotations

from typing import Any, Mapping


def render_slots(slots: Mapping[str, str] | None, *, trunk: str = "prompt") -> str:
    """把命名槽收成一段。空槽不占位。"""
    parts: list[str] = [f"<{trunk}>"]
    for name, body in (slots or {}).items():
        text = str(body or "").strip()
        if not text:
            continue
        parts.append(f"【{name}】")
        parts.append(text)
    parts.append(f"</{trunk}>")
    if len(parts) <= 2:
        return ""
    return "\n".join(parts)


def shadow_equal(legacy: str, rendered: str) -> bool:
    def _n(s: str) -> str:
        return " ".join(str(s or "").split())
    return _n(legacy) == _n(rendered)
