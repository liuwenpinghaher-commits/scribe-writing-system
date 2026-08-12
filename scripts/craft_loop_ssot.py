#!/usr/bin/env python3
"""craft-loop SSOT 机算助手（禁止 if gate_*.ok → green）。

导出双公式字段：mvp scaffold vs readable claims。
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

    prose = ch.get("prose") or ""
    syn = cn_len(ch.get("synopsis") or "")
    st_len = cn_len(ch.get("scene_truth") or "")
    prose_n = cn_len(prose)
    beats = ch.get("beats") or []
    open_p = [p for p in (promises or []) if (p.get("status") or "") == "open"]

    # dual-lamp local (same functions as shipped)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scribe3.reader_ready import build_reader_ready

    rr = build_reader_ready(
        prose,
        beats=beats,
        require_scene_cover=True,
        load_ack=False,
        scaffold_ok=(gates.get("gate_b") or {}).get("ok"),
    )

    scaffold = {
        "CL-B0-H1": cn_len(intent.get("reader_feeling") or "") >= 10,
        "CL-B0-H4": isinstance(intent.get("total_word_goal"), int)
        and 40000 <= int(intent["total_word_goal"]) <= 60000,
        "CL-B2-H1": syn >= 80,
        "CL-B3-H1": len(beats) >= 3,
        "CL-B4-H1": st_len >= 80,
        "CL-B5-H1_cover": rr.get("scene_cover", {}).get("ok") is True,
        "CL-B5-H1_length_soft": prose_n,  # not hard green alone
        "CL-B5-H1m_anti_meta": bool(rr.get("anti_meta", {}).get("ok_for_claim")),
        "CL-B5-H3_focalizer": bool(ch.get("focalizer")),
        "CL-B6-H1": len(open_p) >= 1,
    }
    claims = (rr.get("claims") or {})
    out = {
        "work": w,
        "seq": seq,
        "disclaimer": [
            "gate_a/b/c.ok 不得单独等于 craft-loop green",
            "mvp_pass 不含灯 R；readable 另计",
            "prose>=1500 不是充分绿",
        ],
        "cn_len": {
            "reader_feeling": cn_len(intent.get("reader_feeling") or ""),
            "synopsis": syn,
            "scene_truth": st_len,
            "prose": prose_n,
        },
        "craft_loop_machine_hard_scaffold": scaffold,
        "reader_ready": {
            "machine_reader_ok": rr.get("machine_reader_ok"),
            "phase": (rr.get("lamps") or {}).get("reader", {}).get("phase"),
            "anti_meta": rr.get("anti_meta"),
            "scene_cover": rr.get("scene_cover"),
            "length_policy": rr.get("length_policy"),
            "claims": claims,
        },
        "mvp_pass_hint": "scaffold 块序 + hard 人签；默认不含 may_claim_readable",
        "craft_loop_readable_pass_hint": "mvp 路径 ∧ may_claim_readable ∧ H9",
        "H9_gate": {
            "rule": "H9=PASS ⇒ claims.may_claim_readable must be true after ack",
            "may_claim_readable": claims.get("may_claim_readable"),
        },
        "gate_snapshot_ok_only": {
            "gate_a": (gates.get("gate_a") or {}).get("ok"),
            "gate_b": (gates.get("gate_b") or {}).get("ok"),
        },
        "characters": len(entities or []),
        "open_promises": len(open_p),
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
