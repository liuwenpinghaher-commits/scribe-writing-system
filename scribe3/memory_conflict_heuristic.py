"""正典压制用 entity/attribute 弱推断（无 pydantic）。"""
from __future__ import annotations

import re


def heuristic_entity_attribute(text: str) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    s = (text or "").strip()
    if not s:
        return keys
    for m in re.finditer(
        r"([\u4e00-\u9fffA-Za-z0-9_]{2,24})的([\u4e00-\u9fffA-Za-z0-9_]{2,16})", s
    ):
        keys.add((m.group(1), m.group(2)))
        if len(keys) >= 4:
            break
    for m in re.finditer(
        r"([\u4e00-\u9fffA-Za-z0-9_]{2,24})[:：]([\u4e00-\u9fffA-Za-z0-9_]{2,16})", s
    ):
        keys.add((m.group(1), m.group(2)))
        if len(keys) >= 6:
            break
    return keys
