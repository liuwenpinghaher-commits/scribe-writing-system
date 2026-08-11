"""Novel-first 薄产品表面（P0–P2 residual · 无 Surreal 依赖）。

供 HTTP / 写路径 / 单测共用：soft precheck、文学蒸馏、事件图一跳。
"""
from __future__ import annotations

from typing import Any


def soft_precheck_surface(payload: Any) -> dict[str, Any]:
    """驱动 shipped soft_precheck_plan（advisory · 不 hard-park）。"""
    from scribe3.soft_precheck import soft_precheck_plan
    out = soft_precheck_plan(payload)
    out["surface"] = "novel_first.soft_precheck"
    return out


def literary_distill_surface(
    recap: str = "",
    *,
    max_bullets: int = 12,
    text: str | None = None,
) -> dict[str, Any]:
    """驱动 shipped literary_distill；text 别名兼容 body.text。"""
    from scribe3.literary_distill import literary_distill
    raw = recap if recap else (text or "")
    out = literary_distill(raw, max_bullets=max_bullets)
    out["surface"] = "novel_first.literary_distill"
    return out


def event_graph_surface(
    events: list[dict[str, Any]] | None = None,
    promises: list[dict[str, Any]] | None = None,
    *,
    seed_id: str | None = None,
) -> dict[str, Any]:
    """写/检索共享：邻接 + 一跳 + 可选 linked_pair 样例。"""
    from scribe3.event_graph import (
        build_event_adjacency,
        graph_linked_pair,
        graph_one_hop,
    )
    g = build_event_adjacency(events=events, promises=promises)
    nodes = list(g.get("nodes") or [])
    seed = seed_id or (nodes[0] if nodes else "")
    hop: list[str] = graph_one_hop(g, [seed]) if seed else []
    pair: dict[str, Any] | None = None
    # 找一对 leads_to 边作诚实样例
    adj = g.get("adjacency") or {}
    for a, node in adj.items():
        if not isinstance(node, dict):
            continue
        for b in node.get("leads_to") or []:
            pair = graph_linked_pair(g, str(a), str(b))
            break
        if pair:
            break
    if pair is None and len(nodes) >= 2:
        pair = graph_linked_pair(g, nodes[0], nodes[1])
    return {
        "graph": g,
        "seed": seed,
        "one_hop": hop,
        "sample_pair": pair,
        "surface": "novel_first.event_graph",
        "version": g.get("version") or "event_graph.v0",
    }


def event_graph_from_store_chapter(store: Any, chapter: int) -> dict[str, Any]:
    """从 store 抽本章事件/伏笔 → event_graph_surface（fail-soft 空图）。"""
    events: list[dict[str, Any]] = []
    promises: list[dict[str, Any]] = []
    try:
        if hasattr(store, "list_events"):
            raw = store.list_events(int(chapter)) or []
            for e in raw:
                if isinstance(e, dict):
                    events.append(e)
                else:
                    events.append({
                        "id": getattr(e, "id", None) or getattr(e, "oid", None),
                        "leads_to": getattr(e, "leads_to", None),
                        "enables": getattr(e, "enables", None),
                    })
    except Exception:
        events = []
    try:
        if hasattr(store, "list_promises"):
            raw_p = store.list_promises() or []
            for p in raw_p:
                if isinstance(p, dict):
                    promises.append(p)
                else:
                    promises.append({
                        "id": getattr(p, "id", None) or getattr(p, "oid", None),
                        "event_id": getattr(p, "event_id", None),
                        "related_event": getattr(p, "related_event", None),
                    })
    except Exception:
        promises = []
    # 章内兜底：chapter.plan / meta 无事件时仍可空图
    try:
        ch = store.get_chapter(int(chapter)) or {}
        for e in ch.get("events") or []:
            if isinstance(e, dict) and e not in events:
                events.append(e)
    except Exception:
        pass
    return event_graph_surface(events=events, promises=promises)


def is_chapter_op_busy(kind: str, work: str | None, seq: int | str) -> bool:
    """只读：chapter_lock / concurrency_lock 是否占坑（遗留 set 另查）。"""
    try:
        from scribe3.chapter_lock import chapter_target
        from scribe3.concurrency_lock import lock_snapshot
        t = chapter_target(work, seq)
        snap = lock_snapshot() or {}
        bucket = snap.get(str(kind or "loop")) or {}
        return t in bucket
    except Exception:
        return False
