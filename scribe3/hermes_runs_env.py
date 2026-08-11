"""Hermes Runs 基址映射（无 httpx · 可单测）。

``run_stage_policy.api_env`` → 进程 env 中的网关 URL。
"""
from __future__ import annotations

import os

HERMES_RUNS = os.environ.get("HERMES_RUNS_API", "http://127.0.0.1:8644/v1")
HERMES_DEDUCE_RUNS = os.environ.get("HERMES_DEDUCE_RUNS_API", "http://127.0.0.1:8645/v1")
HERMES_DEDUCE_PREVIEW_RUNS = os.environ.get(
    "HERMES_DEDUCE_PREVIEW_RUNS_API", "http://127.0.0.1:8646/v1",
)
HERMES_PLAN_RUNS = os.environ.get("HERMES_PLAN_RUNS_API", "http://127.0.0.1:8647/v1")
HERMES_DRAFT_RUNS = os.environ.get("HERMES_DRAFT_RUNS_API", "http://127.0.0.1:8648/v1")


def hermes_runs_api_base_for_env(api_env: str) -> str:
    """run_stage_policy.api_env → 已配置 Runs 基址。

    未知 env 抛 KeyError，由 ``_hermes_runs_runtime`` 转 RuntimeError。
    """
    mapping = {
        "HERMES_DEDUCE_RUNS_API": HERMES_DEDUCE_RUNS,
        "HERMES_DEDUCE_PREVIEW_RUNS_API": HERMES_DEDUCE_PREVIEW_RUNS,
        "HERMES_PLAN_RUNS_API": HERMES_PLAN_RUNS,
        "HERMES_DRAFT_RUNS_API": HERMES_DRAFT_RUNS,
        "HERMES_RUNS_API": HERMES_RUNS,
    }
    return mapping[api_env]
