#!/usr/bin/env python3
"""craft-loop SSOT 机算助手（禁止 if gate_*.ok → green）。

用法示例:
  export API_BASE=https://tonglu.qing.blue
  export SCRIBE3_COOKIE_JAR=/path/to/cj.txt
  python3 scripts/craft_loop_ssot.py --work book_qe_live5 --seq 2 --out /tmp/cl-ssot.json

仅只读 GET；写路径请走合法 SPA/orch/save-chapter。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import http.cookiejar
from pathlib import Path


def cn_len(s: str) -> int:
    return len(re.sub(r"\s+", "", (s or "").strip()))


def main() -> int:
    ap = argparse.ArgumentParser(description="craft-loop SSOT counters (not gate_*.ok)")
    ap.add_argument("--work", required=True)
    ap.add_argument("--seq", type=int, default=1)
    ap.add_argument("--base", default=os.environ.get("API_BASE", "https://tonglu.qing.blue"))
    ap.add_argument("--cookie-jar", default=os.environ.get("SCRIBE3_COOKIE_JAR", ""))
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    if not args.cookie_jar:
        print("need --cookie-jar or SCRIBE3_COOKIE_JAR", file=sys.stderr)
        return 2
    cj = http.cookiejar.MozillaCookieJar(args.cookie_jar)
    cj.load(ignore_discard=True, ignore_expires=True)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(path: str):
        url = base + path
        with opener.open(urllib.request.Request(url), timeout=60) as r:
            return json.loads(r.read().decode())

    w = args.work
    seq = args.seq
    intent = get(f"/api/intent?work={w}")
    ch = get(f"/api/chapter?seq={seq}&work={w}")
    gates = get(f"/api/craft-gates?work={w}&seq={seq}")
    promises = get(f"/api/promises?work={w}")
    entities = get(f"/api/entities?work={w}")

    syn = cn_len(ch.get("synopsis") or "")
    st = cn_len(ch.get("scene_truth") or "")
    prose = cn_len(ch.get("prose") or "")
    beats = ch.get("beats") or []
    open_p = [p for p in (promises or []) if (p.get("status") or "") == "open"]

    # craft-loop hard 机算子集（非 gate.ok）
    cl = {
        "CL-B0-H1": cn_len(intent.get("reader_feeling") or "") >= 10,
        "CL-B0-H4": isinstance(intent.get("total_word_goal"), int)
        and 40000 <= int(intent["total_word_goal"]) <= 60000,
        "CL-B2-H1": syn >= 80,
        "CL-B3-H1": len(beats) >= 3,
        "CL-B4-H1": st >= 80,
        "CL-B5-H1": prose >= 1500,
        "CL-B5-H3_focalizer": bool(ch.get("focalizer")),
        "CL-B6-H1": len(open_p) >= 1,
    }
    out = {
        "work": w,
        "seq": seq,
        "disclaimer": "gate_a/b/c.ok 不得单独等于 craft-loop green",
        "cn_len": {
            "reader_feeling": cn_len(intent.get("reader_feeling") or ""),
            "synopsis": syn,
            "scene_truth": st,
            "prose": prose,
        },
        "total_word_goal": intent.get("total_word_goal"),
        "beats_count": len(beats),
        "focalizer": ch.get("focalizer"),
        "open_promises": len(open_p),
        "characters": len(entities or []),
        "craft_loop_machine_hard": cl,
        "gate_snapshot_ok_only": {
            "gate_a": (gates.get("gate_a") or {}).get("ok"),
            "gate_b": (gates.get("gate_b") or {}).get("ok"),
            "gate_c_det": (gates.get("gate_c_det") or gates.get("gate_c") or {}).get("ok"),
        },
        "note": "human hard rows (H2/H3/H6/H9 等) 须人写 PASS/FAIL，本脚本不代签",
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
