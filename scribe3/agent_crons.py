"""Agent cron 产品目录（O23 · 读 crons.yaml + 落盘 enable 覆盖）。

与 provision_hermes / deploy/hermes/crons.yaml 关系：
- yaml 为 schedule/script 真源（本模块只读，不改 schedule 内容）
- enable 覆盖写入 SCRIBE3_CRON_OVERRIDES_PATH 或 ~/.scribe3/cron_overrides.json
- 产品 UI 开关仅影响「目录展示的 enabled 位」；真正 Hermes timer 仍以 yaml+systemd 为准
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
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
    raw = (get_flag("SCRIBE3_AGENT_CRON_UI") or "1").strip().lower()
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
            row["catalog_enabled"] = en
            row["hermes"] = None
            row["source"] = str(p)
            row["override_path"] = str(default_overrides_path())
            out.append(row)
        return out


_HERMES_CRON_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_HERMES_LIST_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_HERMES_CRON_TTL = 45.0


def parse_hermes_cron_list(text: str) -> dict[str, dict[str, Any]]:
    """解析 ``hermes cron list`` 文本 → name → {present, active, last_status?, job_id?}。

    兼容样例（见 test_hermes_runtime）::

        dc4bd8e87938 [active]
          Name:      scribe3-体检
          ...
          Last run:  2026-07-10T00:03:07+08:00  ok
    """
    import re
    out: dict[str, dict[str, Any]] = {}
    if not text:
        return out
    # 按 job 块切分：行首十六进制 id 或 "Name:"
    blocks: list[str] = []
    cur_lines: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*[0-9a-fA-F]{8,}\s*(\[|$)", line.strip()) and cur_lines:
            blocks.append("\n".join(cur_lines))
            cur_lines = [line]
        else:
            cur_lines.append(line)
    if cur_lines:
        blocks.append("\n".join(cur_lines))

    for block in blocks:
        name_m = re.search(r"Name:\s*(.+?)\s*$", block, re.M)
        if not name_m:
            # 行内 Name: 变体
            name_m = re.search(r"Name:\s*(.+)", block)
        if not name_m:
            continue
        name = name_m.group(1).strip()
        if not name:
            continue
        active = "[active]" in block.lower() or re.search(r"\bactive\b", block, re.I) is not None
        # paused / inactive 优先
        if re.search(r"\[paused\]|\[inactive\]|\[disabled\]", block, re.I):
            active = False
        last_status = None
        last_m = re.search(r"Last run:\s+.*?\s+([A-Za-z_ -]+)\s*(?:\n|$)", block)
        if last_m:
            last_status = last_m.group(1).strip()
        job_id = None
        id_m = re.search(r"^\s*([0-9a-fA-F]{8,})\b", block, re.M)
        if id_m:
            job_id = id_m.group(1)
        out[name] = {
            "present": True,
            "active": bool(active),
            "last_status": last_status,
            "job_id": job_id,
        }
    return out


def match_job_hermes(
    catalog_name: str,
    hermes_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """yaml name ↔ hermes list Name 模糊匹配。"""
    n = (catalog_name or "").strip()
    if not n:
        return {"present": False, "active": False, "match": None}
    if n in hermes_by_name:
        row = dict(hermes_by_name[n])
        row["match"] = "exact"
        return row
    # 子串 / 去前缀
    for hn, hv in hermes_by_name.items():
        if n in hn or hn in n:
            row = dict(hv)
            row["match"] = "fuzzy"
            row["matched_name"] = hn
            return row
    return {"present": False, "active": False, "match": None}


def fetch_hermes_cron_list_text(*, profile: str = "scribe3", timeout: float = 3.0) -> str:
    """subprocess hermes cron list；无 CLI 返回空串。"""
    import subprocess
    try:
        listing = subprocess.run(
            ["hermes", "-p", profile, "cron", "list"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (listing.stdout or "") + "\n" + (listing.stderr or "")
    except Exception:
        return ""


def load_hermes_cron_jobs(*, force: bool = False) -> dict[str, dict[str, Any]]:
    """Phase2：per-job 表；缓存 45s。"""
    import time
    now = time.time()
    if (
        not force
        and _HERMES_LIST_CACHE.get("data") is not None
        and (now - float(_HERMES_LIST_CACHE.get("ts") or 0)) < _HERMES_CRON_TTL
    ):
        return dict(_HERMES_LIST_CACHE["data"])
    text = fetch_hermes_cron_list_text()
    parsed = parse_hermes_cron_list(text)
    _HERMES_LIST_CACHE["ts"] = now
    _HERMES_LIST_CACHE["data"] = dict(parsed)
    return dict(parsed)


def load_hermes_cron_aggregate(*, force: bool = False) -> dict[str, Any]:
    """聚合 +（Phase2）附带 jobs_parsed 计数；缓存 45s；失败 checked=false 不抛。"""
    import time
    now = time.time()
    if (
        not force
        and _HERMES_CRON_CACHE.get("data") is not None
        and (now - float(_HERMES_CRON_CACHE.get("ts") or 0)) < _HERMES_CRON_TTL
    ):
        return dict(_HERMES_CRON_CACHE["data"])
    out: dict[str, Any] = {
        "checked": False,
        "gateway_running": False,
        "active_jobs": None,
        "scribe3_qc": {"present": False, "active": False, "last_status": None},
        "jobs_parsed": 0,
        "note": "aggregate + per-job match (phase2); CLI missing → checked=false",
    }
    try:
        from scribe3.api.services.hermes_status import _hermes_cron_status
        raw = _hermes_cron_status("scribe3")
        if isinstance(raw, dict):
            out.update(raw)
    except Exception as e:
        out["error"] = str(e)[:160]
        out["checked"] = False
    try:
        jobs_map = load_hermes_cron_jobs(force=force)
        out["jobs_parsed"] = len(jobs_map)
        out["note"] = "aggregate + per-job match (phase2)"
    except Exception as e:
        out.setdefault("error", str(e)[:160])
    _HERMES_CRON_CACHE["ts"] = now
    _HERMES_CRON_CACHE["data"] = dict(out)
    return dict(out)


def retry_failed_ingests_job(store: Any) -> dict[str, Any]:
    from scribe3.ingest_integrity import retry_failed_ingests
    return retry_failed_ingests(store, max_retries=3)


def retry_pending_extracts_job(complete_fn=None) -> dict[str, Any]:
    from scribe3.extract_retry import retry_pending_extracts
    return retry_pending_extracts(complete_fn)


def check_overdue_promises(store: Any) -> dict[str, Any]:
    """每日伏笔超期：2 条告警，3 条硬拦由写路径闸负责。"""
    from scribe3.alerts import emit_alert
    from scribe3.promise_overdue_gate import count_open_overdue
    n = 0
    try:
        lister = getattr(store, "open_promises", None) or getattr(store, "list_promises", None)
        rows = lister() if callable(lister) else []
        mx = getattr(store, "max_chapter", None)
        max_ch = int(mx() or 0) if callable(mx) else 0
        n = int(count_open_overdue(rows, max_ch) or 0)
    except Exception:
        n = 0
    alerted = False
    if n >= 2:
        emit_alert("promise_overdue", f"有{n}条伏笔超期未兑现", extra={"count": n})
        alerted = True
    return {"overdue": n, "alerted": alerted}


def build_agent_crons_response() -> dict[str, Any]:
    """GET /agent-crons：catalog + 聚合 + per-job hermes 匹配。"""
    jobs = load_cron_catalog()
    extras = [
        {
            "name": "check_overdue_promises",
            "schedule": "0 9 * * *",
            "script": "scribe3.agent_crons.check_overdue_promises",
            "enabled": True,
            "catalog_enabled": True,
            "note_zh": "每日 9 点：超期伏笔 ≥2 条告警",
        },
        {
            "name": "retry_failed_ingests",
            "schedule": "*/5 * * * *",
            "script": "scribe3.agent_crons.retry_failed_ingests_job",
            "enabled": True,
            "catalog_enabled": True,
            "note_zh": "每 5 分钟：知识回写失败自动再试，最多 3 次",
        },
        {
            "name": "retry_pending_extracts",
            "schedule": "*/15 * * * *",
            "script": "scribe3.agent_crons.retry_pending_extracts_job",
            "enabled": True,
            "catalog_enabled": True,
            "note_zh": "抽取失败后再试",
        },
    ]
    have = {str(j.get("name") or "") for j in jobs}
    for extra in extras:
        if extra["name"] not in have:
            jobs.append(extra)
    hermes = load_hermes_cron_aggregate()
    hermes_jobs = load_hermes_cron_jobs()
    for row in jobs:
        name = str(row.get("name") or "")
        row["hermes"] = match_job_hermes(name, hermes_jobs)
    return {
        "jobs": jobs,
        "hermes_cron": hermes,
        "enabled_flag": agent_cron_ui_enabled(),
        "note_zh": (
            "启停覆盖仅影响产品目录；真正 timer 以 crons.yaml + provision_hermes/systemd 为准。"
            "hermes 列：在册/活跃为只读匹配。"
        ),
        "mutates_hermes_timer": False,
        "surface": "agent_crons.list",
        "phase": "2",
    }


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
        "mutates_hermes_timer": False,
    }


def run_audit_cleanup(store=None) -> dict[str, Any]:
    """GAP-3 产品侧清理入口（供 cron/运维调用）。"""
    from scribe3.audit_maintenance import purge_audit_events, audit_ttl_days
    from scribe3.context_cache import purge_cache_watch
    out: dict[str, Any] = {
        "job": "audit_cleanup",
        "ttl_days": audit_ttl_days(),
    }
    if store is None:
        out["ok"] = False
        out["error"] = "store required"
        return out
    out["audit"] = purge_audit_events(store)
    out["cache_watch"] = {"purged": purge_cache_watch(store, max_age_seconds=3600)}
    out["ok"] = bool((out.get("audit") or {}).get("ok"))
    return out


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
