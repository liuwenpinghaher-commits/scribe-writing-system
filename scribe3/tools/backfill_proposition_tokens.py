"""A1: 存量命题 tokens 回填（jieba；不重算 embedding）。

用法（在 backend 容器或已配 SCRIBE3_SURREAL_* 的环境）::

  python -m scribe3.tools.backfill_proposition_tokens --db book_xxx --dry-run
  python -m scribe3.tools.backfill_proposition_tokens --db book_xxx --limit 200

默认 --dry-run；加 --commit 才真写。
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Backfill proposition.tokens")
    p.add_argument("--db", default=os.environ.get("SCRIBE3_DEFAULT_WORK") or "main")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--commit", action="store_true", help="真写库（关闭 dry-run）")
    args = p.parse_args(argv)
    dry = not bool(args.commit)
    from scribe3.store import SurrealStore, backfill_proposition_tokens

    st = SurrealStore(ns="scribe3", db=args.db)
    try:
        res = backfill_proposition_tokens(st, limit=args.limit, dry_run=dry)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if int(res.get("errors") or 0) == 0 else 2
    finally:
        try:
            st.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
