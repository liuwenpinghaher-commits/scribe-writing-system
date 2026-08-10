#!/usr/bin/env python3
"""同章 AB 词表代理指标（OI-7 · 非产品功能）。

用法::
  python -m scribe3.tools.ne_oi_ab_metrics --a path/a.md --b path/b.md --out metrics.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SIM = re.compile(r"像|仿佛|宛如|好似|如同|恍若")
WALK = re.compile(r"走|巷|嗅|闻|摸|停|蹲|望|循着|路过|穿过|门槛|街|屋脊")
CONF = re.compile(r"债|不敢|钥|匙|禁|若|否则|逼|讨|抵|失|门闩|父名|炉册|代价|威胁")
QUOTE = re.compile(r'[「"“]')


def metrics(text: str) -> dict:
    t = text or ""
    cn = len(re.sub(r"\s+", "", t))
    if cn <= 0:
        return {"prose_cn": 0, "walk_per_k": 0, "conflict_per_k": 0, "simile_per_k": 0, "quotes": 0}

    def pk(n: int) -> float:
        return round(1000.0 * n / cn, 1)

    return {
        "prose_cn": cn,
        "walk_per_k": pk(len(WALK.findall(t))),
        "conflict_per_k": pk(len(CONF.findall(t))),
        "simile_per_k": pk(len(SIM.findall(t))),
        "quotes": len(QUOTE.findall(t)),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--out", default="")
    p.add_argument("--work", default="")
    p.add_argument("--seq", type=int, default=0)
    args = p.parse_args(argv)
    a = Path(args.a).read_text(encoding="utf-8", errors="replace")
    b = Path(args.b).read_text(encoding="utf-8", errors="replace")
    out = {
        "work": args.work,
        "seq": args.seq,
        "a": {"label": "baseline", **metrics(a)},
        "b": {"label": "engine_oi", **metrics(b)},
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
