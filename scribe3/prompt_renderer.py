"""统一渲染：XML 主干 + 【】子节。旗关时不改现网组装。"""
from __future__ import annotations

import re
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
    """语义等价：空白折叠后相同；渲染器加的 XML 主干和槽名标头不计入。"""
    def _n(s: str) -> str:
        return " ".join(str(s or "").split())

    raw_l, raw_r = _n(legacy), _n(rendered)
    if raw_l == raw_r:
        return True
    stripped = re.sub(r"</?[A-Za-z_][\w.-]*>", " ", rendered or "")
    stripped = re.sub(r"【[A-Za-z_][\w.-]*】", " ", stripped)
    if raw_l == _n(stripped):
        return True
    compact = lambda s: re.sub(r"\s+", "", s or "")
    return compact(legacy) == compact(stripped)
