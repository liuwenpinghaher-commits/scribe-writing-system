"""Agent cron 产品目录（O23 · 读 crons.yaml + settings 覆盖）。"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
# name -> enabled bool override
_OVERRIDES: dict[str, bool] = {}


def agent_cron_ui_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_AGENT_CRON_UI") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def default_crons_yaml_path() -> Path:
    env = (os.environ.get("SCRIBE3_CRONS_YAML") or "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve().parent
    return here / "deploy" / "hermes" / "crons.yaml"


def parse_crons_yaml(text: str) -> list[dict[str, Any]]:
    """极简 YAML 子集解析（jobs 列表）；无 PyYAML 依赖时可用。"""
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if isinstance(jobs, list):
            return [j for j in jobs if isinstance(j, dict)]
    except Exception:
        pass
    # fallback：按 name/schedule 行扫描
    jobs: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- name:"):
            if cur:
                jobs.append(cur)
            cur = {"name": s.split(":", 1)[1].strip().strip('"').strip("'")}
        elif cur is not None and s.startswith("schedule:"):
            cur["schedule"] = s.split(":", 1)[1].strip().strip('"').strip("'")
        elif cur is not None and s.startswith("script:"):
            cur["script"] = s.split(":", 1)[1].strip()
        elif cur is not None and s.startswith("no_agent:"):
            cur["no_agent"] = "true" in s.lower()
    if cur:
        jobs.append(cur)
    return jobs


def load_cron_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or default_crons_yaml_path()
    text = ""
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        text = ""
    jobs = parse_crons_yaml(text) if text else []
    with _LOCK:
        out = []
        for j in jobs:
            name = str(j.get("name") or "")
            en = _OVERRIDES.get(name, True)
            row = dict(j)
            row["enabled"] = en
            row["source"] = str(p)
            out.append(row)
        return out


def set_cron_enabled(name: str, enabled: bool) -> dict[str, Any]:
    n = str(name or "").strip()
    with _LOCK:
        _OVERRIDES[n] = bool(enabled)
    return {"name": n, "enabled": bool(enabled), "persisted": "process"}


def clear_cron_overrides_for_tests() -> None:
    with _LOCK:
        _OVERRIDES.clear()
