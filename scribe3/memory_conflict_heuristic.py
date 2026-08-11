"""正典压制用 entity/attribute 弱推断（无 pydantic）。

目标：结构化正典 ``(entity=张三, attribute=刀法)`` 与叙述句
「张三的刀法很强」能产生**可相交**键，避免 _suppress_by_canonical 静默空转。
"""
from __future__ import annotations

import re

# 的-form 后属性：取到程度/语气/句读前；并展开 2–4 字前缀键供与结构化 attribute 相交
_DE_ATTR = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9_]{2,24})的"
    r"([\u4e00-\u9fffA-Za-z0-9_]{1,16}?)"
    r"(?=很|极|太|更|不|了|着|过|是|的|，|。|！|？|；|、|：|$)",
)
_COLON_ATTR = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9_]{2,24})[:：]"
    r"([\u4e00-\u9fffA-Za-z0-9_]{2,16})",
)


def _expand_attr_keys(entity: str, attr: str) -> set[tuple[str, str]]:
    """entity 固定，attribute 本体 + 2–4 字前缀（中文属性常见 2 字）。"""
    keys: set[tuple[str, str]] = set()
    a = (attr or "").strip()
    e = (entity or "").strip()
    if not e or not a:
        return keys
    keys.add((e, a))
    for n in (2, 3, 4):
        if len(a) >= n:
            keys.add((e, a[:n]))
    return keys


def heuristic_entity_attribute(text: str) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    s = (text or "").strip()
    if not s:
        return keys
    for m in _DE_ATTR.finditer(s):
        keys |= _expand_attr_keys(m.group(1), m.group(2))
        if len(keys) >= 12:
            break
    for m in _COLON_ATTR.finditer(s):
        keys |= _expand_attr_keys(m.group(1), m.group(2))
        if len(keys) >= 16:
            break
    return keys


def entity_attr_keys_overlap(
    a: set[tuple[str, str]],
    b: set[tuple[str, str]],
) -> bool:
    """正典键与启发式键是否视为冲突（等值或同 entity 下 attribute 前缀相交）。"""
    if not a or not b:
        return False
    if a & b:
        return True
    for e1, a1 in a:
        for e2, a2 in b:
            if e1 != e2 or not a1 or not a2:
                continue
            if a1 == a2 or a1.startswith(a2) or a2.startswith(a1):
                return True
    return False


def focus_bonus(linked_ids: set | frozenset | None, focus_ids: set | frozenset | None) -> float:
    """shipped final_score 的 focus 项（0.15）；无 pydantic，可单测。"""
    if not linked_ids or not focus_ids:
        return 0.0
    return 0.15 if set(linked_ids) & set(focus_ids) else 0.0


def conflict_keys_from_parts(
    *,
    provenance: list | None = None,
    text: str = "",
    use_heuristic: bool = True,
) -> set[tuple[str, str]]:
    """从 provenance 与可选正文启发式抽取 (entity, attribute) 键集合。"""
    keys: set[tuple[str, str]] = set()
    for p in provenance or []:
        if not isinstance(p, dict):
            continue
        e, a = p.get("entity"), p.get("attribute")
        if e and a:
            keys.add((str(e), str(a)))
    if keys or not use_heuristic:
        return keys
    return heuristic_entity_attribute(text)


def should_suppress_episodic(
    episodic_keys: set[tuple[str, str]],
    canonical_keys: set[tuple[str, str]],
) -> bool:
    """正典压制是否应拒绝该 episodic（shipped _suppress_by_canonical 内核）。"""
    if not episodic_keys or not canonical_keys:
        return False
    if episodic_keys & canonical_keys:
        return True
    return entity_attr_keys_overlap(episodic_keys, canonical_keys)
