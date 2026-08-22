#!/usr/bin/env python3
"""把已有角色/势力摘要同步成 digest 命题。不灌正文。"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--work", default="main")
    args = p.parse_args(argv)
    from scribe3.codex_digest import sync_entity_digests
    from scribe3.store.surreal import get_store
    st = get_store(args.work)
    n = 0
    chars = st.list_characters() if hasattr(st, "list_characters") else []
    for row in chars or []:
        name = str((row or {}).get("name") or "")
        if not name:
            continue
        sync_entity_digests(st, "character", f"role:{name}", row)
        n += 1
    factions = st.list_factions() if hasattr(st, "list_factions") else []
    for row in factions or []:
        name = str((row or {}).get("name") or "")
        if not name:
            continue
        sync_entity_digests(st, "faction", f"faction:{name}", row)
        n += 1
    print(f"digest backfill entities={n} work={args.work}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
