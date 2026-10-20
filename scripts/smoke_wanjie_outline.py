#!/usr/bin/env python3
"""只读冒烟：万界卷一四章各有账。禁止 generate-stage。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = os.environ.get("API_BASE", "https://tonglu.example.com")
SLUG = os.environ.get("WANJIE_SLUG", "book_36177e20")
TITLES = ("华山成核", "四十二度", "金縢裂纹", "灭活边缘")


def curl(method: str, path: str, data=None, jar: str = "") -> tuple[int, object]:
    out = Path(tempfile.gettempdir()) / "wanjie_outline_out.json"
    cmd = [
        "curl", "-sS", "-o", str(out), "-w", "%{http_code}",
        "-X", method, "-H", f"Origin: {BASE}", "--max-time", "30",
    ]
    if jar:
        cmd += ["-b", jar, "-c", jar]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data, ensure_ascii=False)]
    cmd.append(BASE + path)
    raw = subprocess.check_output(cmd, text=True).strip()
    code = int(raw[-3:] if raw[-3:].isdigit() else raw or "0")
    try:
        body = json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        body = out.read_text(encoding="utf-8")[:400]
    return code, body


def main() -> int:
    jar = str(Path(tempfile.gettempdir()) / "wanjie_outline_cookie.txt")
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    user, _, pw = bu.partition(":")
    hc, health = curl("GET", "/api/health")
    if hc != 200:
        print("health", hc, health)
        return 1
    lc, login = curl("POST", "/api/auth/login", {"username": user, "password": pw}, jar=jar)
    if lc != 200:
        print("login", lc, login)
        return 1
    oc, outline = curl("GET", f"/api/outline?work={SLUG}", jar=jar)
    if oc != 200 or not isinstance(outline, dict):
        print("outline", oc, outline)
        return 1
    chs = outline.get("chapters") or []
    vols = outline.get("volumes") or []
    cage = next((v for v in vols if "囚笼" in str(v.get("title") or "")), None)
    if not cage:
        print("missing volume 囚笼")
        return 1
    vid = str(cage.get("id") or "")
    peers = [c for c in chs if str(c.get("volume") or "") == vid]
    titles = [str(c.get("title") or "") for c in peers]
    missing = [t for t in TITLES if t not in titles]
    if missing:
        print("missing titles", missing, "got", titles)
        return 1
    empty = [c.get("title") for c in peers if not str(c.get("synopsis") or "").strip()]
    if empty:
        print("empty synopsis", empty)
        return 1
    print("OK volume", cage.get("title"), "chapters", titles)
    print("OK health", hc, "outline", oc, "n", len(peers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
