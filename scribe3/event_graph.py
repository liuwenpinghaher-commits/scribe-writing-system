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
        if not isinstance(ev, dict):
            continue
        eid = str(ev.get("id") or ev.get("event_id") or "")
        if not eid:
            continue
        node = _node(eid)
        if prev_id:
            _node(prev_id)["leads_to"].append(eid)
        # explicit edges on this node
        for k, rel in (("leads_to", "leads_to"), ("enables", "enables"), ("caused_by", "enables")):
            raw = ev.get(k)
            if isinstance(raw, str) and raw:
                node[rel].append(raw)
            elif isinstance(raw, list):
                node[rel].extend(str(x) for x in raw if x)
        # ontology.Event.causal_in: [(src_id, ctype)] → src enables/leads_to this
        for item in ev.get("causal_in") or []:
            src, ctype = "", "enables"
            if isinstance(item, (list, tuple)) and item:
                src = str(item[0] or "")
                if len(item) > 1 and item[1]:
                    ctype = str(item[1])
            elif isinstance(item, dict):
                src = str(item.get("id") or item.get("event_id") or "")
                ctype = str(item.get("type") or item.get("ctype") or "enables")
            elif isinstance(item, str):
                src = item
            if not src:
                continue
            rel = "leads_to" if ctype in ("leads_to", "sequence", "next") else "enables"
            if eid not in _node(src)[rel]:
                _node(src)[rel].append(eid)
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


def graph_linked_pair(
    adjacency: dict[str, Any],
    a: str,
    b: str,
) -> dict[str, Any]:
    """检查 a↔b 是否经一跳邻接相连；返回结构化边描述（P2 诚实表面）。"""
    g = adjacency or {}
    adj = g.get("adjacency") if isinstance(g.get("adjacency"), dict) else g
    if not isinstance(adj, dict):
        adj = {}
    sa, sb = str(a), str(b)
    hops_a = graph_one_hop({"adjacency": adj}, [sa])
    hops_b = graph_one_hop({"adjacency": adj}, [sb])
    forward = sb in hops_a
    backward = sa in hops_b
    rels: list[str] = []
    node_a = adj.get(sa) or {}
    if isinstance(node_a, dict):
        for rel in ("leads_to", "enables", "related_promises"):
            if sb in [str(x) for x in (node_a.get(rel) or [])]:
                rels.append(rel)
    return {
        "a": sa,
        "b": sb,
        "linked": bool(forward or backward),
        "forward": forward,
        "backward": backward,
        "relations": rels,
        "one_hop_from_a": hops_a,
        "version": "event_graph.v0",
    }
