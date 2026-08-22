#!/usr/bin/env python3
"""幂等写入万界 term/item。走 store.add_term / add_item，禁止 add_entity(kind=term)。

用法（demo 容器内）:
  python3 scripts/seed_wanjie_catalog.py --work <slug>
本机无 Surreal 时只打印清单。
"""
from __future__ import annotations

import argparse
import sys

from scribe3.wanjie_catalog import WANJIE_ITEMS as ITEMS
from scribe3.wanjie_catalog import WANJIE_TERMS as TERMS
from scribe3.wanjie_catalog import ensure_wanjie_catalog as seed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    if args.dry:
        print("terms", [t[0] for t in TERMS])
        print("items", [i[0] for i in ITEMS])
        return 0
    try:
        from scribe3.store import SurrealStore
    except Exception as e:
        print("no store:", e, file=sys.stderr)
        return 2
    st = SurrealStore(args.work)
    got = seed(st)
    print("seeded", args.work, got)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
