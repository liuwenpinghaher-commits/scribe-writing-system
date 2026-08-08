#!/usr/bin/env python3
"""D7 地板：usage_digest 可用 + 对照协议落地说明。

质量 9.5 必须人评 A/B 成稿；本脚本验证：
  1) POST /memory/prefetch 含 usage_digest.summary
  2) POST /memory/usage-preview 返回人话摘要
  3) 打印对照协议 pass_rule

用法：
  API_BASE=https://www.qing.blue SCRIBE3_BOOTSTRAP_USERS=admin:x \\
  python3 scripts/probe_d7_memory_gain.py --work book_6340c01f
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BASE = os.environ.get("API_BASE", "https://www.qing.blue")
JAR = os.environ.get("COOKIE_JAR", "/tmp/d7_probe_cookie.txt")


def curl(method, path, data=None, timeout=90, work=""):
    out = Path("/tmp/d7_probe_out.json")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--chapter", type=int, default=4)
    args = ap.parse_args()
    w = args.work
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    u, pw = bu.split(":", 1)
    subprocess.run(["rm", "-f", JAR], check=False)
    code, _ = curl("POST", "/api/auth/login", {"username": u, "password": pw})
    if code != "200":
        raise SystemExit(f"login {code}")

    code, pref = curl("POST", "/api/memory/prefetch", {
        "query": "缺口 铜匙 本章",
        "chapter": args.chapter,
        "thread_id": "",
    }, work=w, timeout=90)
    print("prefetch", code)
    ud = (pref or {}).get("usage_digest") if isinstance(pref, dict) else None
    print("prefetch.usage_digest summary:", (ud or {}).get("summary"))
    if not (ud or {}).get("summary"):
        print("FAIL no usage_digest on prefetch")
        sys.exit(1)

    code, prev = curl("POST", "/api/memory/usage-preview", {
        "query": "缺口",
        "chapter": args.chapter,
        "focalizer": "role:覃灰七",
    }, work=w, timeout=90)
    print("usage-preview", code)
    ud2 = (prev or {}).get("usage_digest") if isinstance(prev, dict) else None
    print("preview summary:", (ud2 or {}).get("summary"))
    if code != "200" or not (ud2 or {}).get("summary"):
        print("FAIL usage-preview")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scribe3.memory_gain import comparison_protocol
    proto = comparison_protocol()
    print("A/B pass_rule:", proto["pass_rule"])
    print("D7 floor PASS (usage visible API; quality 9.5 needs human A/B)")
    sys.exit(0)


if __name__ == "__main__":
    main()
