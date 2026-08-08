#!/usr/bin/env python3
"""Surreal 3.2.4 热路径计时 + EXPLAIN 探针（在已部署 backend 内跑）。

  python -m scribe3.tools.probe_s32_hotpath
  python -m scribe3.tools.probe_s32_hotpath --work perf_s32
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from typing import Any


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


def _explain(st, surql: str, vars: dict | None = None) -> str:
    """返回 EXPLAIN 文本摘要。"""
    try:
        rows = st._query(f"EXPLAIN {surql}", vars or {})
        return str(rows)[:500]
    except Exception as e:
        return f"EXPLAIN_ERR {type(e).__name__}: {e}"


def _plan_hint(explain_text: str) -> str:
    t = explain_text.lower()
    if "knnscan" in t or "hnsw" in t:
        return "HNSW/KnnScan"
    if "tablescan" in t and "knn" in t:
        return "KNN+TableScan?"
    if "tablescan" in t:
        return "TableScan"
    if "iterateindex" in t or "index" in t:
        return "Index"
    return "unknown"


def probe(work: str, rounds: int = 3) -> dict[str, Any]:
    from scribe3.store import SurrealStore

    st = SurrealStore(db=work)
    out: dict[str, Any] = {"work": work, "paths": {}, "explain": {}}

    def time_path(name: str, fn, *, warm: bool = True):
        if warm:
            try:
                fn()
            except Exception:
                pass
        samples = []
        last_err = None
        last_n = None
        for _ in range(rounds):
            t0 = time.perf_counter()
            try:
                r = fn()
                samples.append(_ms(t0))
                last_n = len(r) if hasattr(r, "__len__") else None
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                samples.append(None)
        ok = [s for s in samples if s is not None]
        out["paths"][name] = {
            "samples_ms": samples,
            "p50_ms": sorted(ok)[len(ok) // 2] if ok else None,
            "n": last_n,
            "error": last_err,
        }

    time_path("list_characters", lambda: st._query(
        "SELECT meta::id(id) AS id, name FROM character LIMIT 200"))
    time_path("list_chapters", lambda: st._query(
        "SELECT seq, title FROM chapter ORDER BY seq LIMIT 200"))
    time_path("list_propositions", lambda: st._query(
        "SELECT meta::id(id) AS id, attribute FROM proposition LIMIT 200"))
    time_path("memory_items_active", lambda: st._query(
        "SELECT meta::id(id) AS id FROM memory_item WHERE status='active' LIMIT 100"))

    # semantic / memory (need embed)
    try:
        time_path("semantic_recall", lambda: st.semantic_recall("血玉铜炉 密室 玉佩", k=5, chapter=5))
    except Exception as e:
        out["paths"]["semantic_recall"] = {"error": str(e)}
    try:
        time_path("memory_vector", lambda: st.memory_vector(work, "密室机关 铜炉", k=5, chapter=5))
    except Exception as e:
        out["paths"]["memory_vector"] = {"error": str(e)}
    try:
        time_path("memory_bm25", lambda: st.memory_bm25(work, "密室 铜炉", k=5, chapter=5))
    except Exception as e:
        out["paths"]["memory_bm25"] = {"error": str(e)}
    try:
        time_path("hybrid_recall", lambda: st.hybrid_recall("铜炉 玉佩", chapter=5, k=5))
    except Exception as e:
        out["paths"]["hybrid_recall"] = {"error": str(e)}

    # EXPLAIN KNN form used in production
    from scribe3.embed import embed
    qv = embed(["探针查询 铜炉"])[0]
    knn_sql = (
        "SELECT meta::id(id) AS local, vector::distance::knn() AS dist "
        "FROM proposition WHERE embedding <|5,40|> $qv ORDER BY dist"
    )
    exp = _explain(st, knn_sql, {"qv": qv})
    out["explain"]["proposition_knn"] = {
        "sql": knn_sql,
        "plan_hint": _plan_hint(exp),
        "raw": exp,
    }
    mem_sql = (
        "SELECT meta::id(id) AS id, vector::distance::knn() AS dist "
        "FROM memory_item WHERE embedding <|5,40|> $qv AND work=$w AND status='active' "
        "ORDER BY dist"
    )
    exp2 = _explain(st, mem_sql, {"qv": qv, "w": work})
    out["explain"]["memory_knn"] = {
        "sql": mem_sql,
        "plan_hint": _plan_hint(exp2),
        "raw": exp2,
    }
    # FTS explain
    exp3 = _explain(
        st,
        "SELECT meta::id(id) AS id FROM memory_item "
        "WHERE work=$w AND status='active' AND tokens @1@ $q LIMIT 5",
        {"w": work, "q": "密室 铜炉"},
    )
    out["explain"]["memory_bm25"] = {
        "plan_hint": _plan_hint(exp3),
        "raw": exp3,
    }
    exp4 = _explain(st, "SELECT seq, title FROM chapter ORDER BY seq LIMIT 50")
    out["explain"]["chapter_order"] = {
        "plan_hint": _plan_hint(exp4),
        "raw": exp4,
    }

    # recommendation stubs
    recs = []
    for key, block in out["explain"].items():
        hint = block.get("plan_hint") or ""
        if "TableScan" in hint and "knn" in key.lower():
            recs.append(f"{key}: KNN may not use HNSW — review <|K,EF|> syntax on 3.2.4")
        if key == "chapter_order" and "TableScan" in hint:
            recs.append(
                "chapter ORDER BY seq is TableScan — consider INDEX on chapter.seq if p95 high"
            )
    out["recommendations"] = recs
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--work", default="perf_s32")
    p.add_argument("--rounds", type=int, default=3)
    args = p.parse_args(argv)
    result = probe(args.work, rounds=args.rounds)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
