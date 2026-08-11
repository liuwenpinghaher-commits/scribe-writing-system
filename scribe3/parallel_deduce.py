"""并行多视角演绎计划（O22 · 默认 dry-run · 不 fork Hermes）。"""
from __future__ import annotations

import os
from typing import Any


def parallel_deduce_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_PARALLEL_DEDUCE") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def build_parallel_deduce_plan(
    chapter: int,
    focalizers: list[str] | None = None,
    *,
    max_parallel: int = 2,
    work: str = "main",
) -> dict[str, Any]:
    """生成 N 路 deduce run 计划（profile=scribe3_deduce）。

    不发起 LLM；execute 由调用方旗控。
    """
    focals = [str(f).strip() for f in (focalizers or []) if str(f).strip()]
    if not focals:
        focals = ["_default"]
    cap = max(1, min(6, int(max_parallel or 2)))
    runs = []
    for i, f in enumerate(focals[:cap]):
        runs.append({
            "index": i,
            "focalizer": f if f != "_default" else "",
            "profile": "scribe3_deduce",
            "api_env": "HERMES_DEDUCE_RUNS_API",
            "run_scope": f"chapter:{int(chapter)}:deduce",
            "work": work or "main",
            "chapter": int(chapter),
        })
    return {
        "chapter": int(chapter),
        "work": work or "main",
        "runs": runs,
        "max_parallel": cap,
        "dry_run": True,
        "execute": False,
        "enabled_flag": parallel_deduce_enabled(),
        "lock_kind": "run",
        "surface": "parallel_deduce.plan",
        "note": "execute 须显式二次确认；默认只返回 plan",
    }
