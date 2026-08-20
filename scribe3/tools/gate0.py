"""Gate 0 硬冻结：冒烟通过后钉 SHA；跑批对不上就拒跑。"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def current_sha() -> str:
    env = (os.environ.get("SCRIBE3_GIT_SHA") or os.environ.get("GIT_SHA") or "").strip()
    if env:
        return env
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return ""


def current_gate0_tag() -> str:
    try:
        out = subprocess.check_output(
            ["git", "describe", "--exact-match", "--tags", "--match", "gate0-*", "HEAD"],
            cwd=str(ROOT),
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return ""


def expected_sha() -> str:
    env = (os.environ.get("SCRIBE3_GATE0_SHA") or "").strip()
    if env:
        return env
    for p in (ROOT / "GATE0_SHA", Path("/opt/scribe3/app/GATE0_SHA")):
        try:
            if p.is_file():
                return p.read_text(encoding="utf-8").strip().split()[0]
        except Exception:
            continue
    return ""


def _truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def check_gate0_freeze(*, require: bool | None = None) -> dict:
    """跑批窗口：HEAD 必须对上 GATE0_SHA 或本机 gate0-* tag。

    容器里常常没有 git：用环境变量 SCRIBE3_GATE0_SHA / SCRIBE3_GIT_SHA。
    require=True 或 SCRIBE3_REQUIRE_GATE0=1 时，缺钉也拒跑。
    """
    if require is None:
        require = _truthy("SCRIBE3_REQUIRE_GATE0")
    want = expected_sha()
    got = current_sha()
    tag = current_gate0_tag()
    if want:
        if got and (got.startswith(want) or want.startswith(got)):
            return {"ok": True, "sha": got, "want": want, "tag": tag}
        return {
            "ok": False,
            "code": "gate0_mismatch",
            "message": "HEAD 对不上 Gate 0 钉住的版本，拒跑",
            "want": want,
            "got": got,
        }
    if tag:
        return {"ok": True, "sha": got, "tag": tag}
    if require:
        return {
            "ok": False,
            "code": "gate0_unfrozen",
            "message": "未钉 Gate 0 版本，拒跑",
            "got": got,
        }
    return {"ok": True, "skipped": True, "sha": got}
