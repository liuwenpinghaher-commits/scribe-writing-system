#!/usr/bin/env python3
"""FTS 探针：固定查询集 × BM25 命中。

  python -m scribe3.tools.probe_fts_s32 --work main
"""
from __future__ import annotations

import argparse
import json
import sys

from scribe3.text_tokens import tokenize_for_fts

# 查询 → 期望「至少命中」的启发式（文本子串）
DEFAULT_CASES = [
    ("铜炉", "铜炉"),
    ("密室", "密室"),
    ("备忘", "备忘"),
    ("玉佩", "玉佩"),
    ("犹豫", "犹豫"),
    ("铜炉 密室", "铜炉"),
]


def probe(work: str) -> dict:
    from scribe3.store import SurrealStore

    st = SurrealStore(db=work)
    items = st._query(
        "SELECT meta::id(id) AS id, text FROM memory_item WHERE work=$w AND status='active'",
        {"w": work},
    ) or []
    results = []
    for q, needle in DEFAULT_CASES:
        ids = st.memory_bm25(work, q, k=10)
        # expected: any active item containing needle in text
        expect_ids = {r["id"] for r in items if needle in (r.get("text") or "")}
        hit = set(ids)
        results.append({
            "query": q,
            "query_tokens": tokenize_for_fts(q),
            "bm25_ids": ids,
            "expect_any_of": sorted(expect_ids)[:5],
            "expect_n": len(expect_ids),
            "hit_expect": bool(hit & expect_ids) if expect_ids else (len(ids) >= 0),
            "ok": (not expect_ids) or bool(hit & expect_ids),
        })
    ok = all(r["ok"] for r in results if r["expect_n"] > 0)
    return {
        "work": work,
        "active_items": len(items),
        "ok": ok,
        "cases": results,
        "weights_doc": {
            "memory.weight_structured": 2.0,
            "memory.weight_bm25": 1.0,
            "memory.weight_vector": 1.0,
            "memory.weight_graph": 1.2,
            "memory.weight_recency": 0.8,
            "note": "defaults from scribe3/settings.py; override via settings DB",
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--work", default="main")
    args = p.parse_args(argv)
    out = probe(args.work)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
