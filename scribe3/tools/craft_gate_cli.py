#!/usr/bin/env python3
"""工艺优先 GATE 命令行(API 旁路,读本地 Surreal work)。

用法:
  scribe3/.venv/bin/python -m scribe3.tools.craft_gate_cli --work book_b4e72480
  scribe3/.venv/bin/python -m scribe3.tools.craft_gate_cli --work X --seq 1 --expect-fail

环境: SURREAL_URL 默认 ws://127.0.0.1:8001/rpc
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Craft-first GATE runner")
    p.add_argument("--work", required=True, help="Surreal db / work slug")
    p.add_argument("--seq", type=int, default=None, help="章号;省略则只跑 GATE-A")
    p.add_argument("--url", default=os.environ.get("SURREAL_URL", "ws://127.0.0.1:8001/rpc"))
    p.add_argument("--expect-fail", action="store_true", help="预期整闸失败(反面对照)")
    p.add_argument("--out", default="", help="写 JSON 报告路径")
    args = p.parse_args(argv)

    from scribe3.store import SurrealStore
    from scribe3.verify_craft_compliance import (
        audit_chapter_det,
        gate_a,
        gate_b,
        gate_d,
        journey_pass,
        to_jsonable,
    )

    st = SurrealStore(url=args.url, ns="scribe3", db=args.work)
    try:
        st.apply_schema()
    except Exception:
        pass

    report: dict = {"work": args.work}
    ga = gate_a(st)
    report["gate_a"] = to_jsonable(ga)

    chapters = []
    overall_ok = ga.ok
    if args.seq is not None:
        gb = gate_b(st, args.seq)
        gc = audit_chapter_det(st, args.seq)
        gd = gate_d(st, args.seq)
        report["gate_b"] = to_jsonable(gb)
        report["gate_c_det"] = to_jsonable(gc)
        report["gate_d"] = to_jsonable(gd)
        chapters.append({
            "seq": args.seq,
            "gate_b_ok": gb.ok,
            "gate_c_ok": gc.ok,
            "gate_d_ok": gd.ok,
        })
        overall_ok = ga.ok and gb.ok and gc.ok and gd.ok
    else:
        # 全书:对 list_chapters 有 prose 的章抽样
        try:
            chs = st.list_chapters() or []
        except Exception:
            chs = []
        for row in chs:
            seq = row.get("seq")
            if seq is None:
                continue
            ch = st.get_chapter(seq) or {}
            if not (ch.get("prose") or "").strip():
                continue
            gb = gate_b(st, seq)
            gc = audit_chapter_det(st, seq)
            gd = gate_d(st, seq)
            chapters.append({
                "seq": seq,
                "gate_b_ok": gb.ok,
                "gate_c_ok": gc.ok,
                "gate_d_ok": gd.ok,
            })
        if chapters:
            jp = journey_pass(gate_a_ok=ga.ok, chapters=chapters)
            overall_ok = jp["ok"]
            report["journey"] = jp
        else:
            overall_ok = ga.ok

    report["ok"] = overall_ok
    report["chapters"] = chapters
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)

    if args.expect_fail:
        return 0 if not overall_ok else 1
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
