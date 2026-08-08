#!/usr/bin/env python3
"""D4 质量地板探针：同键 supersede 后 facts/prefetch 不得把旧值当真相。

用法（demo）:
  export API_BASE=https://www.qing.blue
  export SCRIBE3_BOOTSTRAP_USERS=admin:xxx
  python3 scripts/probe_d4_single_truth.py --work book_xxx

退出码 0=地板通过（旧值不在当章真相表面）；1=失败。
注意：这是通/绿地板，不是质量 9.5 人评。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE = os.environ.get("API_BASE", "https://www.qing.blue")
JAR = os.environ.get("COOKIE_JAR", "/tmp/d4_probe_cookie.txt")


def curl(method, path, data=None, timeout=120, work=""):
    out = Path("/tmp/d4_probe_out.json")
    urlpath = path
    if work and "work=" not in path and not path.startswith("/api/auth"):
        urlpath += ("&" if "?" in path else "?") + "work=" + work
    cmd = [
        "curl", "-sS", "-o", str(out), "-w", "%{http_code}",
        "-b", JAR, "-c", JAR, "-X", method,
        "-H", f"Origin: {BASE}", "--max-time", str(timeout),
    ]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json",
                "-d", json.dumps(data, ensure_ascii=False)]
    cmd.append(BASE + urlpath)
    p = subprocess.run(cmd, capture_output=True, text=True)
    body = out.read_text() if out.exists() else ""
    try:
        j = json.loads(body) if body else None
    except Exception:
        j = body
    return p.stdout.strip(), j


def login():
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    u, pw = bu.split(":", 1)
    subprocess.run(["rm", "-f", JAR], check=False)
    code, _ = curl("POST", "/api/auth/login", {"username": u, "password": pw})
    if code != "200":
        raise SystemExit(f"login failed {code}")


def approve(work: str, tool: str, args: dict, summary: str):
    prop = {
        "id": f"p{int(time.time() * 1000)}",
        "status": "pending",
        "summary": summary,
        "ops": [{
            "tool": tool,
            "args": args,
            "label": tool,
            "out_of_allowlist": False,
            "status": "pending",
        }],
    }
    code, res = curl(
        "POST",
        "/api/orchestration/proposal/apply",
        {"proposal": prop, "decision": "approve", "execute": True},
        work=work,
        timeout=120,
    )
    st = ((res or {}).get("proposal") or {}).get("status") if isinstance(res, dict) else None
    print(summary, code, st, flush=True)
    if code != "200" or st not in ("applied", "partial"):
        print(json.dumps(res, ensure_ascii=False)[:800], flush=True)
        raise SystemExit(f"approve failed {summary}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    w = args.work
    login()
    entity = "world:d4_probe_匙"
    attr = "condition"
    old_v = "D4探针旧值·完整无缺"
    new_v = "D4探针新值·齿边缺口"

    approve(w, "s3_add_fact", {
        "oid": "fact:d4probe-old",
        "entity": entity,
        "attribute": attr,
        "value": old_v,
        "valid_from": 1,
    }, "d4probe seed old")
    approve(w, "s3_add_fact", {
        "oid": "fact:d4probe-new",
        "entity": entity,
        "attribute": attr,
        "value": new_v,
        "valid_from": 4,
    }, "d4probe supersede new")

    code, facts = curl("GET", "/api/facts?chapter=5", work=w)
    if code != "200" or not isinstance(facts, list):
        raise SystemExit(f"facts failed {code}")
    vals = [
        f.get("value") for f in facts
        if f.get("attribute") == attr
        and entity in str(f.get("entity") or f.get("entity_id") or "")
    ]
    # also match entity field variants
    if not vals:
        vals = [f.get("value") for f in facts if f.get("attribute") == attr and old_v in str(f.get("value")) or new_v in str(f.get("value"))]
    print("condition values @ch5:", vals, flush=True)
    if old_v in vals:
        print("FAIL old value still truth at ch5", flush=True)
        sys.exit(1)
    if new_v not in vals:
        # collapse may use entity_id field
        all_v = [f.get("value") for f in facts if f.get("attribute") == attr]
        print("all condition values", all_v, flush=True)
        if old_v in all_v:
            print("FAIL old still in any condition", flush=True)
            sys.exit(1)
        if new_v not in all_v:
            print("FAIL new missing", flush=True)
            sys.exit(1)

    code, pref = curl("POST", "/api/memory/prefetch", {
        "query": f"{entity} {attr} {old_v} {new_v}",
        "thread_id": "",
    }, work=w, timeout=90)
    ctx = (pref or {}).get("context") or "" if isinstance(pref, dict) else ""
    print("prefetch has old", old_v in ctx, "has new", new_v in ctx, flush=True)
    if old_v in ctx and new_v in ctx:
        # both mentioned in query echo is ok; fail if fact line asserts old
        for line in ctx.splitlines():
            if entity.split(":")[-1] in line or "d4_probe" in line or attr in line:
                if old_v in line and new_v not in line:
                    print("FAIL prefetch fact line still old-only:", line[:160], flush=True)
                    sys.exit(1)
    if old_v in ctx and new_v not in ctx:
        print("FAIL prefetch only old", flush=True)
        sys.exit(1)

    print("D4 floor PASS (same-key supersede; not quality 9.5)", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
