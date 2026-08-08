#!/usr/bin/env python3
"""D6 地板：限知成稿 find_leaks + 本地 guards 自检。

质量 9.5 仍需人评「像角色在想」；本脚本只做地板。

  API_BASE=https://www.qing.blue SCRIBE3_BOOTSTRAP_USERS=admin:x \\
  python3 scripts/probe_d6_epistemic.py --work book_6340c01f --seq 3
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BASE = os.environ.get("API_BASE", "https://www.qing.blue")
JAR = os.environ.get("COOKIE_JAR", "/tmp/d6_probe_cookie.txt")


def curl(method, path, data=None, timeout=90, work=""):
    out = Path("/tmp/d6_probe_out.json")
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
    ap.add_argument("--seq", type=int, default=3)
    args = ap.parse_args()
    w, seq = args.work, args.seq
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    u, pw = bu.split(":", 1)
    subprocess.run(["rm", "-f", JAR], check=False)
    code, _ = curl("POST", "/api/auth/login", {"username": u, "password": pw})
    if code != "200":
        raise SystemExit(f"login {code}")

    code, ch = curl("GET", f"/api/chapter?seq={seq}", work=w)
    prose = (ch or {}).get("prose") or "" if isinstance(ch, dict) else ""
    foc = ((ch or {}).get("focalizer") or "") if isinstance(ch, dict) else ""
    print("chapter", seq, "focalizer", foc, "prose_len", len(prose))
    if not prose:
        print("WARN no prose; skip find_leaks API")
    else:
        # post_check style if available
        code, res = curl("POST", "/api/check", {
            "prose": prose[:20000],
            "focalizer": foc or "role:灰狸",
            "chapter": seq,
        }, work=w, timeout=120)
        print("check http", code, str(res)[:300] if res else "")
        leaks = []
        if isinstance(res, dict):
            leaks = res.get("leaks") or res.get("find_leaks") or []
        print("leaks_count", len(leaks) if isinstance(leaks, list) else leaks)

    # 本地诱导：secret 应在 guard 中被检出
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scribe3.epistemic_guard import (
        discussion_omniscient_banner,
        scan_prompt_for_off_frame_secrets,
        writing_limited_banner,
    )
    assert "作者全知" in discussion_omniscient_banner()
    assert "限知" in writing_limited_banner("role:灰狸")

    class Fake:
        def facts_at(self, ch):
            from scribe3.ontology import Fact
            return [Fact(
                "fact:s", "role:冷锅婆", "密", "炉心印能开旧库侧门",
                valid_from=1, secret=True, leak_markers=["炉心印能开"],
            )]

    import scribe3.epistemic_guard as eg
    eg.frame_known_fact_ids = lambda s, f, c: set()  # type: ignore
    hits = scan_prompt_for_off_frame_secrets(
        "正文里写：炉心印能开旧库侧门",
        Fake(), focalizer="role:灰狸", chapter=seq,
    )
    print("local_adversarial_hits", len(hits))
    if not hits:
        print("FAIL local adversarial")
        sys.exit(1)
    print("D6 floor PASS (banners + adversarial scan; not quality 9.5)")
    sys.exit(0)


if __name__ == "__main__":
    main()
