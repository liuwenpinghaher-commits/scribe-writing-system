"""记忆质量 D4：注入面实体投影与互斥消解（纯逻辑，无 DB）。

根因：collapse 只认 (entity, attribute)；变更常另开 attribute 或把旧态嵌进 value，
导致 must-link 并列「完整无缺」与「缺口」。业界时态 KG 要求同一槽位 supersede +
读路径只暴露当下真（见 docs/plans/2026-08-09-memory-quality-rootcause-plan.md）。
"""
from __future__ import annotations

from typing import Any

# 状态类槽：写入时互相 supersede（同一 entity 只保留一个开放状态槽）
STATE_SLOT_ATTRS: frozenset[str] = frozenset({
    "state", "condition", "status", "外观状态", "状态",
})

# 描述槽若 value 含状态对立词，也参与互斥消解与写入时连带关闭
DESCRIPTIVE_STATE_ATTRS: frozenset[str] = frozenset({
    "artifact", "description", "note", "外观", "描述",
})

# 互斥短语对（子串命中即冲突；较新 valid_from 胜）
EXCLUSION_PAIRS: tuple[tuple[str, str], ...] = (
    ("完整无缺", "缺口"),
    ("完整无缺", "残缺"),
    ("完好无损", "缺口"),
    ("完好", "损坏"),
    ("完好", "破碎"),
    ("未损", "缺口"),
    ("活着", "已死"),
    ("未冷", "冷死"),
    ("尚温", "冷死"),
)


def _get(f: Any, key: str, default=None):
    if isinstance(f, dict):
        return f.get(key, default)
    return getattr(f, key, default)


def fact_entity(f: Any) -> str:
    return str(_get(f, "entity_id") or "") or ""


def fact_attr(f: Any) -> str:
    return str(_get(f, "attribute") or "") or ""


def fact_value(f: Any) -> str:
    v = _get(f, "value")
    return "" if v is None else str(v)


def fact_valid_from(f: Any) -> int:
    vf = _get(f, "valid_from")
    try:
        return int(vf) if vf is not None else 0
    except (TypeError, ValueError):
        return 0


def values_mutually_exclusive(a: str, b: str) -> bool:
    """两 value 是否语义互斥（子串对立）。"""
    if not a or not b or a == b:
        return False
    for x, y in EXCLUSION_PAIRS:
        if (x in a and y in b) or (y in a and x in b):
            return True
    return False


def is_state_slot_attr(attr: str) -> bool:
    return (attr or "") in STATE_SLOT_ATTRS


def looks_like_state_value(value: str) -> bool:
    """描述性 value 是否携带可变状态（用于 artifact 长串嵌旧态）。"""
    v = value or ""
    markers = (
        "完整无缺", "缺口", "残缺", "损坏", "破碎", "完好", "断裂",
        "冷死", "未冷", "尚温", "已死", "活着",
    )
    return any(m in v for m in markers)


def should_cross_supersede_attr(attr: str, value: str) -> bool:
    """写入该 attr/value 时是否应关闭同 entity 其它状态槽。"""
    if is_state_slot_attr(attr):
        return True
    if (attr or "") in DESCRIPTIVE_STATE_ATTRS and looks_like_state_value(value):
        return True
    return False


def normalize_state_attribute(attr: str, value: str) -> str:
    """状态类写入规范到 state；纯描述 artifact 不改。"""
    a = (attr or "note").strip() or "note"
    if is_state_slot_attr(a):
        return "state"
    if a in DESCRIPTIVE_STATE_ATTRS and looks_like_state_value(value or ""):
        # 长串描述里嵌状态 → 仍保留原 attr 供兼容，但写入路径应拆 state
        return a
    return a


def collapse_facts_single_truth(facts: list) -> list:
    """同一 (entity_id, attribute) 只保留 valid_from 最新一条（纯函数）。"""
    best: dict[tuple[str, str], object] = {}
    for f in facts or []:
        eid = fact_entity(f)
        attr = fact_attr(f)
        if not eid or not attr:
            key = (str(id(f)), "")
        else:
            key = (str(eid), str(attr))
        prev = best.get(key)
        if prev is None:
            best[key] = f
            continue
        if fact_valid_from(f) >= fact_valid_from(prev):
            best[key] = f
    return list(best.values())


def resolve_injection_facts(facts: list) -> list:
    """读/注入安全网：同键折叠后，再消解同 entity 上互斥 value。

    保留 valid_from 更新者；被消解行不进入 must-link / prefetch 表面。
    无互斥时多 attribute 仍可并存（如 location + rule）。
    """
    kept, _dropped = resolve_injection_facts_with_stats(facts)
    return kept


def resolve_injection_facts_with_stats(facts: list) -> tuple[list, int]:
    """同 resolve_injection_facts，并返回因互斥被丢弃的条数（供 usage_digest）。"""
    raw_n = len(list(facts or []))
    collapsed = collapse_facts_single_truth(list(facts or []))
    if len(collapsed) <= 1:
        # 同键折叠也可能丢条
        return collapsed, max(0, raw_n - len(collapsed))

    # 按 entity 分组
    by_e: dict[str, list] = {}
    orphan: list = []
    for f in collapsed:
        eid = fact_entity(f)
        if not eid:
            orphan.append(f)
            continue
        by_e.setdefault(eid, []).append(f)

    out: list = list(orphan)
    for _eid, rows in by_e.items():
        if len(rows) == 1:
            out.extend(rows)
            continue
        # 标记被较新互斥行击败的下标
        drop: set[int] = set()
        n = len(rows)
        for i in range(n):
            if i in drop:
                continue
            for j in range(i + 1, n):
                if j in drop:
                    continue
                vi, vj = fact_value(rows[i]), fact_value(rows[j])
                if not values_mutually_exclusive(vi, vj):
                    continue
                # 较新 valid_from 胜；并列保留列表后者
                fi, fj = fact_valid_from(rows[i]), fact_valid_from(rows[j])
                if fj > fi:
                    drop.add(i)
                elif fi > fj:
                    drop.add(j)
                else:
                    drop.add(i)  # 并列丢前者
        for i, f in enumerate(rows):
            if i not in drop:
                out.append(f)
    return out, max(0, raw_n - len(out))


def cross_supersede_attributes_for(attr: str, value: str) -> list[str]:
    """写入时应一并关闭的 attribute 列表（含自身）。"""
    if not should_cross_supersede_attr(attr, value):
        return [attr] if attr else []
    attrs = set(STATE_SLOT_ATTRS)
    attrs.add(attr)
    # 描述槽若带状态词，关闭时也扫 artifact/description
    if looks_like_state_value(value):
        attrs |= set(DESCRIPTIVE_STATE_ATTRS)
    return sorted(attrs)
