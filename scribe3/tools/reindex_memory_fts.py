#!/usr/bin/env python3
"""按 tokenize_for_fts 重算 memory_item.tokens（不改 text/embedding）。

  python -m scribe3.tools.reindex_memory_fts --work main
  python -m scribe3.tools.reindex_memory_fts --work perf_s32 --limit 500
"""
from __future__ import annotations

import argparse
import json
import sys

from scribe3.text_tokens import tokenize_for_fts


def reindex(work: str, limit: int = 2000) -> dict:
    from scribe3.store import SurrealStore

    st = SurrealStore(db=work)
    rows = st._query(
        "SELECT meta::id(id) AS id, text, tokens FROM memory_item "
        "WHERE work=$w LIMIT $lim",
        {"w": work, "lim": int(limit)},
    ) or []
    updated = 0
    for r in rows:
        mid = r.get("id")
        text = r.get("text") or ""
        new_toks = tokenize_for_fts(text)
        if new_toks == (r.get("tokens") or ""):
            continue
        st._execute_write(
            "UPDATE type::record('memory_item', $id) SET tokens=$t, updated_at=time::now()",
            {"id": mid, "t": new_toks},
        )
        updated += 1
    return {"work": work, "scanned": len(rows), "updated": updated}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--work", default="main")
    p.add_argument("--limit", type=int, default=2000)
    args = p.parse_args(argv)
    print(json.dumps(reindex(args.work, args.limit), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
