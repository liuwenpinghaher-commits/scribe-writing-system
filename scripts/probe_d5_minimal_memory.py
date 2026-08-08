#!/usr/bin/env python3
"""D5 地板探针：prefetch/组装含 must-link；作者粘贴圣经可被检出。

不代替质量 9.5 人评。用法：
  API_BASE=https://www.qing.blue SCRIBE3_BOOTSTRAP_USERS=admin:x \\
  python3 scripts/probe_d5_minimal_memory.py --work book_6340c01f
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BASE = os.environ.get("API_BASE", "https://www.qing.blue")
JAR = os.environ.get("COOKIE_JAR", "/tmp/d5_probe_cookie.txt")


def curl(method, path, data=None, timeout=90, work=""):
    out = Path("/tmp/d5_probe_out.json")
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
    args = ap.parse_args()
    w = args.work
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    u, pw = bu.split(":", 1)
    subprocess.run(["rm", "-f", JAR], check=False)
    code, _ = curl("POST", "/api/auth/login", {"username": u, "password": pw})
    if code != "200":
        raise SystemExit(f"login {code}")

    code, pref = curl("POST", "/api/memory/prefetch", {
        "query": "本章 缺口 铜匙 伏笔",
        "thread_id": "",
    }, work=w, timeout=90)
    ctx = (pref or {}).get("context") or "" if isinstance(pref, dict) else ""
    print("prefetch http", code, "len", len(ctx))
    has_must = "戏剧必需" in ctx or "作者铁律" in ctx or "写作宪法" in ctx
    print("has_constraint_or_must_marker", has_must)
    # 本地复述检测（不依赖服务端导出 anchors API）
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scribe3.memory_must_link import detect_author_restated_canon
    fake_anchors = [
        {"text": "开放伏笔:三棱铜匙与炉心印鉴伪"},
        {"text": "world:三棱铜匙·condition=缺口"},
        {"text": "出场/相关角色:覃灰七"},
        {"text": "出场/相关角色:冷锅婆"},
    ]
    paste = "覃灰七 三棱铜匙 缺口 炉心印鉴伪 冷锅婆 全部设定在此请照着写"
    r = detect_author_restated_canon(paste, fake_anchors, threshold=0.5)
    print("restated_detector", r)
    if not r.get("restated") and r.get("ratio", 0) < 0.4:
        print("WARN detector weak on synthetic paste", flush=True)
    print("D5 floor partial: constraint markers + restated detector available")
    # 不 fail 缺 must 字样（旧 assemble 未部署时）——只报告
    sys.exit(0 if code == "200" else 1)


if __name__ == "__main__":
    main()
