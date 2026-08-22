"""Novel-first 薄产品表面（P0–P2 residual · 无 Surreal 依赖）。

供 HTTP / 写路径 / 单测共用：soft precheck、文学蒸馏、事件图一跳。
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
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
    k: int = 1,
    max_nodes: int = 64,
) -> dict[str, Any]:
    """写/检索共享：邻接 + 一跳/多跳 + 可选 linked_pair 样例。

    k>1 且旗 SCRIBE3_MULTI_HOP_GRAPH 开时返回 multi_hop；否则强制 k=1。
    """
    import os
    from scribe3.event_graph import (
        build_event_adjacency,
        graph_k_hop,
        graph_linked_pair,
        graph_one_hop,
    )
    g = build_event_adjacency(events=events, promises=promises)
    nodes = list(g.get("nodes") or [])
    seed = seed_id or (nodes[0] if nodes else "")
    hop: list[str] = graph_one_hop(g, [seed]) if seed else []
    multi = None
    kk = max(1, int(k or 1))
    multi_flag = (get_flag("SCRIBE3_MULTI_HOP_GRAPH") or "1").strip().lower() in (
        "1", "true", "yes", "on",
    )
    if kk > 1 and not multi_flag:
        kk = 1
    if seed and kk >= 1:
        multi = graph_k_hop(g, [seed], k=kk, max_nodes=max_nodes)
    pair: dict[str, Any] | None = None
    # 找一对 leads_to / enables 边作诚实样例
    adj = g.get("adjacency") or {}
    for a, node in adj.items():
        if not isinstance(node, dict):
            continue
        for rel in ("leads_to", "enables"):
            for b in node.get(rel) or []:
                pair = graph_linked_pair(g, str(a), str(b))
                if pair and pair.get("linked"):
                    break
            if pair and pair.get("linked"):
                break
        if pair and pair.get("linked"):
            break
    if pair is None and len(nodes) >= 2:
        pair = graph_linked_pair(g, nodes[0], nodes[1])
    return {
        "graph": g,
        "seed": seed,
        "one_hop": hop,
        "multi_hop": multi,
        "k": kk,
        "sample_pair": pair,
        "surface": "novel_first.event_graph",
        "version": g.get("version") or "event_graph.v0",
    }


def event_to_graph_dict(ev: Any) -> dict[str, Any] | None:
    """ontology.Event / dict → build_event_adjacency 可消费的 dict（含 causal_in）。"""
    if ev is None:
        return None
    if isinstance(ev, dict):
        eid = str(ev.get("id") or ev.get("event_id") or "")
        if not eid:
            return None
        out = dict(ev)
        out["id"] = eid
        if "causal_in" in out and out["causal_in"] is not None:
            out["causal_in"] = list(out["causal_in"])
        return out
    eid = getattr(ev, "id", None) or getattr(ev, "oid", None)
    if not eid:
        return None
    causal_in = list(getattr(ev, "causal_in", None) or [])
    return {
        "id": str(eid),
        "type": getattr(ev, "type", None),
        "causal_in": causal_in,
        "leads_to": getattr(ev, "leads_to", None),
        "enables": getattr(ev, "enables", None),
        "caused_by": getattr(ev, "caused_by", None),
    }


def event_graph_from_store_chapter(store: Any, chapter: int) -> dict[str, Any]:
    """从 store 抽本章事件/伏笔 → event_graph_surface。

    生产入口：**events_at(chapter)**（SurrealStore / EventsMixin），
    非虚构的 list_events。Event 边在 **causal_in**，经 event_to_graph_dict 映射。
    """
    events: list[dict[str, Any]] = []
    promises: list[dict[str, Any]] = []
    ch = int(chapter)
    raw: list[Any] = []
    try:
        if hasattr(store, "events_at"):
            raw = list(store.events_at(ch) or [])
        elif hasattr(store, "list_events"):
            # 兼容旧/测试双名，生产以 events_at 为准
            raw = list(store.list_events(ch) or [])
    except Exception:
        raw = []
    for e in raw:
        d = event_to_graph_dict(e)
        if d:
            events.append(d)
    try:
        # 常见：list_promises / promises / open_promises
        for meth in ("list_promises", "promises", "open_promises"):
            if hasattr(store, meth):
                raw_p = getattr(store, meth)()
                if raw_p is None:
                    continue
                for p in raw_p or []:
                    if isinstance(p, dict):
                        promises.append(p)
                    else:
                        promises.append({
                            "id": getattr(p, "id", None) or getattr(p, "oid", None),
                            "event_id": getattr(p, "event_id", None),
                            "related_event": getattr(p, "related_event", None),
                        })
                break
    except Exception:
        promises = []
    # 章内兜底
    try:
        chd = store.get_chapter(ch) or {}
        for e in chd.get("events") or []:
            d = event_to_graph_dict(e)
            if d and d["id"] not in {x["id"] for x in events}:
                events.append(d)
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
