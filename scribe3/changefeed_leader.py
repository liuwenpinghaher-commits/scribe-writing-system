"""GAP-18：Changefeed 多 worker 去重 — 文件租约 leader election。

单 worker 生产默认：唯一进程即 leader。
多 worker：仅 leader 跑 ChangefeedCacheWorker 轮询；非 leader 跳过。
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

_LEADER_ID = uuid.uuid4().hex[:12]


def leader_election_enabled() -> bool:
    raw = (os.environ.get("SCRIBE3_CHANGEFEED_LEADER_ELECTION") or "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def leader_lease_path() -> Path:
    env = (os.environ.get("SCRIBE3_CHANGEFEED_LEADER_PATH") or "").strip()
    if env:
        return Path(env)
    data = (os.environ.get("SCRIBE3_DATA_DIR") or "").strip()
    if data:
        return Path(data) / "changefeed_leader.lease"
    return Path("/tmp/scribe3_changefeed_leader.lease")  # noqa: S108 — 可配置；非 goal scratch


def try_acquire_leader(*, ttl_seconds: int = 30) -> dict[str, Any]:
    """尝试成为 leader。返回 {is_leader, leader_id, path}。

    未启用 election 时始终 is_leader=True（单 worker 契约）。
    """
    if not leader_election_enabled():
        return {
            "is_leader": True,
            "leader_id": _LEADER_ID,
            "election": False,
            "note": "election off; single-worker default",
        }
    path = leader_lease_path()
    now = time.time()
    ttl = max(5, int(ttl_seconds))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8").strip().split("|")
                lid, ts = raw[0], float(raw[1]) if len(raw) > 1 else 0.0
                if lid == _LEADER_ID or (now - ts) > ttl:
                    path.write_text(f"{_LEADER_ID}|{now}", encoding="utf-8")
                    return {"is_leader": True, "leader_id": _LEADER_ID, "election": True, "path": str(path)}
                return {"is_leader": False, "leader_id": lid, "election": True, "path": str(path)}
            except Exception:
                pass
        path.write_text(f"{_LEADER_ID}|{now}", encoding="utf-8")
        return {"is_leader": True, "leader_id": _LEADER_ID, "election": True, "path": str(path)}
    except Exception as e:
        # 租约失败 fail-open 为 leader，避免缓存永不失效
        return {
            "is_leader": True,
            "leader_id": _LEADER_ID,
            "election": True,
            "error": str(e)[:120],
            "fail_open": True,
        }


def renew_leader(*, ttl_seconds: int = 30) -> bool:
    st = try_acquire_leader(ttl_seconds=ttl_seconds)
    return bool(st.get("is_leader"))
