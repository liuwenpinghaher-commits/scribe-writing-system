#!/usr/bin/env python3
"""可选：对若干章正文抽样 structure_style 指标（非 CI gate · 不宣称文学分）。

用法（在有 store 的环境）::

  PYTHONPATH=. python3 -m scribe3.tools.sample_structure_metrics --work main --seqs 1,2,3

或纯文本 stdin。
"""
from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    p = argparse.ArgumentParser(description="sample structure_style metrics")
    p.add_argument("--work", default="")
    p.add_argument("--seqs", default="", help="comma seqs when using store")
    p.add_argument("--stdin", action="store_true")
    args = p.parse_args()
    from scribe3.structure_style import evaluate_structure_style

    rows = []
    if args.stdin or not args.work:
        text = sys.stdin.read()
        r = evaluate_structure_style(text)
        rows.append({"source": "stdin", **{k: r.get(k) for k in (
            "ending_formula_hit", "isomorphism_hit", "simile_like_per_1k",
        )}})
    else:
        # optional store path — fail soft
        try:
            from scribe3.store import SurrealStore
            st = SurrealStore(ns="scribe3", db=args.work or "main")
            seqs = [int(x) for x in args.seqs.split(",") if x.strip()]
            for s in seqs:
                ch = st.get_chapter(s) or {}
                r = evaluate_structure_style(ch.get("prose") or "")
                rows.append({
                    "seq": s,
                    "ending_formula_hit": r.get("ending_formula_hit"),
                    "isomorphism_hit": r.get("isomorphism_hit"),
                    "simile_like_per_1k": r.get("simile_like_per_1k"),
                })
        except Exception as e:
            print(json.dumps({"error": str(e)[:200]}, ensure_ascii=False), file=sys.stderr)
            return 1
    print(json.dumps({"rows": rows, "note": "advisory only; not a literary score"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
