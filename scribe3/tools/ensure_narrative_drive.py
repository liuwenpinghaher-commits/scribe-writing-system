#!/usr/bin/env python3
"""批量 ensure 章级 narrative_drive（OI-2 · 灭 ch3 主路径）。

用法（在已配置 store 的环境，如 demo 容器 / 指向 demo 的 env）::

  # 默认 dry-run
  python -m scribe3.tools.ensure_narrative_drive --work book_xxx

  # 写库 + 大纲 enrich 回填（OI 上线推荐）
  python -m scribe3.tools.ensure_narrative_drive --work book_xxx --apply \\
      --recompose-if outline_enrich

  # 指定章
  python -m scribe3.tools.ensure_narrative_drive --work book_xxx --seqs 1,2,3 --apply

环境：仅 demo 已部署栈或指向该库的 store；禁止在 Grok 运行机另起 Surreal。
默认 dry-run；永不 park。
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ensure narrative_drive range (guidance-first)")
    p.add_argument("--work", required=True, help="work slug / Surreal db name")
    p.add_argument("--seqs", default="", help="comma-separated seqs; empty=auto from chapters")
    p.add_argument("--apply", action="store_true", help="write DB (default is dry-run)")
    p.add_argument("--force", action="store_true", help="force recompose (still skip author unless --include-author)")
    p.add_argument(
        "--recompose-if",
        default="",
        choices=["", "outline_enrich", "always"],
        help="outline_enrich=回填缺 enrich 观测的旧 ok drive；always=force",
    )
    p.add_argument("--include-author", action="store_true", help="allow force overwrite of author/locked (danger)")
    p.add_argument("--max-seqs", type=int, default=200)
    p.add_argument("--json", action="store_true", help="print stats as JSON")
    args = p.parse_args(argv)

    # ENGINE 须开（可用 env 覆盖）
    os.environ.setdefault("SCRIBE3_NARRATIVE_ENGINE", "1")

    from scribe3.store import SurrealStore
    from scribe3.narrative_drive import ensure_narrative_drive_range

    st = SurrealStore(db=args.work)
    seqs = None
    if (args.seqs or "").strip():
        seqs = [int(x.strip()) for x in args.seqs.split(",") if x.strip()]

    recompose = (args.recompose_if or "").strip() or None
    stats = ensure_narrative_drive_range(
        st,
        seqs=seqs,
        force=bool(args.force) or recompose == "always",
        recompose_if=recompose if recompose != "always" else None,
        dry_run=not bool(args.apply),
        max_seqs=int(args.max_seqs or 200),
        include_author=bool(args.include_author),
    )
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print(
            f"enabled={stats.get('enabled')} dry_run={stats.get('dry_run')} "
            f"total={stats.get('total')} rewritten={stats.get('rewritten')} "
            f"already_ok_skip={stats.get('already_ok_skip')} "
            f"skipped_locked={stats.get('skipped_locked')} "
            f"ensured_ok={stats.get('ensured_ok')} "
            f"empty_seed={stats.get('empty_seed')} "
            f"coverage={stats.get('coverage_ratio')} "
            f"would_write={stats.get('dry_run_would_write')}"
        )
        if stats.get("errors"):
            print("errors:", stats["errors"][:10], file=sys.stderr)
    return 0 if stats.get("enabled") else 2


if __name__ == "__main__":
    raise SystemExit(main())
