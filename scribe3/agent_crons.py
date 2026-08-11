"""Agent cron 产品目录（O23 · 读 crons.yaml + 落盘 enable 覆盖）。

与 provision_hermes / deploy/hermes/crons.yaml 关系：
- yaml 为 schedule/script 真源（本模块只读，不改 schedule 内容）
- enable 覆盖写入 SCRIBE3_CRON_OVERRIDES_PATH 或 ~/.scribe3/cron_overrides.json
- 产品 UI 开关仅影响「目录展示的 enabled 位」；真正 Hermes timer 仍以 yaml+systemd 为准
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
# name -> enabled bool override
_OVERRIDES: dict[str, bool] = {}
_LOADED = False


def agent_cron_ui_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_AGENT_CRON_UI") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def default_crons_yaml_path() -> Path:
    env = (os.environ.get("SCRIBE3_CRONS_YAML") or "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve().parent
    return here / "deploy" / "hermes" / "crons.yaml"


def default_overrides_path() -> Path:
    env = (os.environ.get("SCRIBE3_CRON_OVERRIDES_PATH") or "").strip()
    if env:
        return Path(env)
    data = (os.environ.get("SCRIBE3_DATA_DIR") or "").strip()
    if data:
        return Path(data) / "cron_overrides.json"
    return Path.home() / ".scribe3" / "cron_overrides.json"


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


def _load_overrides_disk() -> None:
    global _LOADED
    if _LOADED:
        return
    path = default_overrides_path()
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, bool):
                        _OVERRIDES[str(k)] = v
                    elif isinstance(v, dict) and "enabled" in v:
                        _OVERRIDES[str(k)] = bool(v.get("enabled"))
    except Exception:
        pass
    _LOADED = True


def _save_overrides_disk() -> None:
    path = default_overrides_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_OVERRIDES, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def load_cron_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or default_crons_yaml_path()
    text = ""
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        text = ""
    jobs = parse_crons_yaml(text) if text else []
    with _LOCK:
        _load_overrides_disk()
        out = []
        for j in jobs:
            name = str(j.get("name") or "")
            en = _OVERRIDES.get(name, True)
            row = dict(j)
            row["enabled"] = en
            row["source"] = str(p)
            row["override_path"] = str(default_overrides_path())
            out.append(row)
        return out


def set_cron_enabled(name: str, enabled: bool) -> dict[str, Any]:
    """启停覆盖：写入落盘 JSON（仅 enable 位，不改 schedule/script）。"""
    n = str(name or "").strip()
    with _LOCK:
        _load_overrides_disk()
        _OVERRIDES[n] = bool(enabled)
        _save_overrides_disk()
        persisted = "disk"
        path = str(default_overrides_path())
    return {
        "name": n,
        "enabled": bool(enabled),
        "persisted": persisted,
        "path": path,
    }


def clear_cron_overrides_for_tests() -> None:
    global _LOADED
    with _LOCK:
        _OVERRIDES.clear()
        _LOADED = False
        # 测试可选：不删用户盘文件，除非 env 指向 tmp
        path = default_overrides_path()
        try:
            if "tmp" in str(path) or "pytest" in str(path) or "test" in str(path).lower():
                if path.is_file():
                    path.unlink()
        except Exception:
            pass
