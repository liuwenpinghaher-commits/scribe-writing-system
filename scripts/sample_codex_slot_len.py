#!/usr/bin/env python3
"""抽生产对照里的 legacy_len。不当创作放行。"""
from __future__ import annotations

import json
import sys


def main() -> int:
    from scribe3.api import app_impl as core
    work = (sys.argv[1] if len(sys.argv) > 1 else "main")
    st = core._store_for(work)
    rows = st.list_pipeline_events(work=work, tag="recall_shadow", limit=500) or []
    lens = []
    for r in rows:
        p = r.get("payload") or {}
        if p.get("legacy_len") is None:
            continue
        try:
            lens.append(int(p["legacy_len"]))
        except (TypeError, ValueError):
            pass
    lens.sort()
    n = len(lens)
    out = {"work": work, "n": n}
    if n:
        out["min"] = lens[0]
        out["p50"] = lens[n // 2]
        out["p95"] = lens[min(n - 1, int(n * 0.95))]
        out["max"] = lens[-1]
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
