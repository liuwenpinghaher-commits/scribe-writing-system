"""DED-05：从 target+field+正文自动抽出破绽词，不靠人手填。"""
from __future__ import annotations

import re

_CJK = re.compile(r"[\u4e00-\u9fff]{2,6}")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{1,23}")


def auto_generate_leak_markers(
    target: str,
    field: str,
    value: str,
    *,
    max_n: int = 8,
) -> list[str]:
    """非空、去重、保序。至少含实体名与字段名（够长时）。"""
    out: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        t = " ".join(str(token or "").split()).strip()
        if len(t) < 2 or t in seen:
            return
        seen.add(t)
        out.append(t)

    name = str(target or "").split(":")[-1].strip()
    add(name)
    add(str(field or "").strip())
    text = str(value or "")
    for m in _CJK.findall(text):
        add(m)
        if len(out) >= max_n:
            return out[:max_n]
    for m in _WORD.findall(text):
        add(m)
        if len(out) >= max_n:
            return out[:max_n]
    return out[:max_n]
