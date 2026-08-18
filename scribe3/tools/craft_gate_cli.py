#!/usr/bin/env python3
"""旧工艺 GATE 已废。本命令只报退役，并可选跑定稿门。"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Craft-first GATE 已退役")
    p.add_argument("--work", required=True, help="Surreal db / work slug")
    p.add_argument("--seq", type=int, default=None, help="章号；给出则跑 finalize_gate")
    p.add_argument("--url", default=os.environ.get("SURREAL_URL", "ws://127.0.0.1:8001/rpc"))
    p.add_argument("--out", default="", help="写 JSON 报告路径")
    args = p.parse_args(argv)

    report: dict = {
        "work": args.work,
        "retired": True,
        "message": "verify_craft_compliance 已删。存正文走 finalize_gate。",
        "ok": True,
    }
    if args.seq is not None:
        from scribe3.store import SurrealStore
        from scribe3.finalize_gate import check_finalize_for_save
        st = SurrealStore(url=args.url, ns="scribe3", db=args.work)
        try:
            st.apply_schema()
        except Exception:
            pass
        ch = st.get_chapter(int(args.seq)) or {}
        fg = check_finalize_for_save(
            st, int(args.seq), ch.get("prose") or "",
            focalizer=ch.get("focalizer") or None,
        )
        report["finalize_gate"] = {
            "allowed": fg.get("allowed"),
            "code": fg.get("code"),
            "detail": fg.get("detail"),
        }
        report["ok"] = bool(fg.get("allowed"))
        report["seq"] = int(args.seq)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
