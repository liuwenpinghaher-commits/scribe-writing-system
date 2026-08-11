"""事件关系图基础设施（P2 骨架 · 可扩展）。

当前：从章事件 / promises 构建一跳邻接表，供检索与观测；
不替代 memory graph 通道，仅补跨章因果节点类型。
"""
from __future__ import annotations

from typing import Any


def build_event_adjacency(
    events: list[dict[str, Any]] | None = None,
    promises: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """构建简易邻接：event_id -> {leads_to, enables, related_promises}。"""
    graph: dict[str, dict[str, list[str]]] = {}
    events = events or []
    promises = promises or []

    def _node(eid: str) -> dict[str, list[str]]:
        if eid not in graph:
            graph[eid] = {"leads_to": [], "enables": [], "related_promises": []}
        return graph[eid]

    prev_id: str | None = None
    for ev in events:
        eid = str(ev.get("id") or ev.get("event_id") or "")
        if not eid:
            continue
        node = _node(eid)
        if prev_id:
            _node(prev_id)["leads_to"].append(eid)
        # explicit edges
        for k, rel in (("leads_to", "leads_to"), ("enables", "enables"), ("caused_by", "enables")):
            raw = ev.get(k)
            if isinstance(raw, str) and raw:
                node[rel].append(raw)
            elif isinstance(raw, list):
                node[rel].extend(str(x) for x in raw if x)
        prev_id = eid

    for pr in promises:
        pid = str(pr.get("id") or pr.get("promise_id") or "")
        if not pid:
            continue
        _node(f"promise:{pid}")
        tied = pr.get("event_id") or pr.get("related_event")
        if tied:
            _node(str(tied))["related_promises"].append(pid)
            _node(f"promise:{pid}")["enables"].append(str(tied))

    return {
        "nodes": sorted(graph.keys()),
        "adjacency": graph,
        "edge_count": sum(
            len(v["leads_to"]) + len(v["enables"]) + len(v["related_promises"])
            for v in graph.values()
        ),
        "version": "event_graph.v0",
    }


def graph_one_hop(adjacency: dict[str, Any], seed_ids: list[str]) -> list[str]:
    """从种子一跳扩展（不含种子自身重复）。"""
    adj = (adjacency or {}).get("adjacency") or adjacency or {}
    out: list[str] = []
    seen = set(seed_ids)
    for sid in seed_ids:
        node = adj.get(sid) or {}
        if not isinstance(node, dict):
            continue
        for rel in ("leads_to", "enables", "related_promises"):
            for x in node.get(rel) or []:
                xs = str(x)
                if xs not in seen:
                    seen.add(xs)
                    out.append(xs)
    return out
