"""H-10 全系统 LLM 预算:跨进程共享日帽台账。

原日帽是进程内计数(llm.py `_daily`)——app(:3321)与 MCP stdio 进程
(run_mcp.sh)各持一份,系统真实调用数 = 各进程之和,"剩余额度"失真。
本模块用单文件 SQLite 台账共享计数:两进程同记一本账,日帽成为真正的
系统级成本保险丝。

- 台账路径:env `SCRIBE3_LLM_LEDGER`,缺省 `~/.scribe2-surreal/scribe3_llm_ledger.sqlite3`
  (与 SurrealDB 生产数据同目录,备份/迁移一起走)。
- 并发:BEGIN IMMEDIATE + busy timeout,app 与 MCP 两写方安全。
- fail-open/fail-soft:日帽写故障回退进程内计数；provider usage 写故障丢弃该条
  旁路证据并 warning 一次。两者都不得阻断写作主链路。
- 帽语义:计"发起的 LLM 调用笔数",非 token;token 真实用量见
  store.usage_summary()(Hermes trace)与 provider_usage_summary()(官方直连)，两者分账。
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from datetime import date, timedelta
from pathlib import Path

_log = logging.getLogger("scribe3.usage")

_lock = threading.Lock()
_proc_daily = ["", 0]   # 进程内 fallback 计数 [day, count]
_warned_ledger_error = False


def ledger_path() -> Path:
    p = os.environ.get("SCRIBE3_LLM_LEDGER")
    if p:
        return Path(p).expanduser()
    return Path.home() / ".scribe2-surreal" / "scribe3_llm_ledger.sqlite3"


def _connect() -> sqlite3.Connection:
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=2.0)
    conn.execute("PRAGMA busy_timeout=2000")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS llm_calls (day TEXT PRIMARY KEY, n INTEGER NOT NULL)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS provider_usage ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "day TEXT NOT NULL, ts TEXT NOT NULL, provider TEXT NOT NULL, "
        "model TEXT NOT NULL, transport TEXT NOT NULL, status TEXT NOT NULL, "
        "http_status INTEGER, input_tokens INTEGER NOT NULL DEFAULT 0, "
        "output_tokens INTEGER NOT NULL DEFAULT 0, total_tokens INTEGER NOT NULL DEFAULT 0, "
        "prompt_cache_hit_tokens INTEGER NOT NULL DEFAULT 0, "
        "prompt_cache_miss_tokens INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_provider_usage_day ON provider_usage(day)"
    )
    return conn


def _warn_once(e: Exception) -> None:
    global _warned_ledger_error
    if not _warned_ledger_error:
        _warned_ledger_error = True
        _log.warning(
            "共享 LLM 台账不可用,按调用类型 fail-soft/fail-open: %s",
            type(e).__name__,
        )


def _token_value(usage: dict | None, primary: str, fallback: str | None = None) -> int:
    raw = (usage or {}).get(primary)
    if raw is None and fallback is not None:
        raw = (usage or {}).get(fallback)
    try:
        value = int(raw or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def record_provider_usage(
    *,
    provider: str,
    model: str,
    transport: str,
    status: str,
    http_status: int | None = None,
    usage: dict | None = None,
) -> bool:
    """记录一次逻辑官方供应商调用；SQLite 故障返回 False，不阻断调用方。"""
    from scribe3.llm_visible import visible_usage
    usage = visible_usage(usage if isinstance(usage, dict) else usage)
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    day = now[:10]
    values = (
        day,
        now,
        str(provider),
        str(model),
        str(transport),
        str(status),
        int(http_status) if http_status is not None else None,
        _token_value(usage, "input_tokens", "prompt_tokens"),
        _token_value(usage, "output_tokens", "completion_tokens"),
        _token_value(usage, "total_tokens"),
        _token_value(usage, "prompt_cache_hit_tokens"),
        _token_value(usage, "prompt_cache_miss_tokens"),
    )
    try:
        with _lock:
            conn = _connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO provider_usage("
                    "day, ts, provider, model, transport, status, http_status, "
                    "input_tokens, output_tokens, total_tokens, "
                    "prompt_cache_hit_tokens, prompt_cache_miss_tokens"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    values,
                )
                conn.commit()
            finally:
                conn.close()
        return True
    except Exception as e:
        _warn_once(e)
        return False


def provider_usage_summary(days: int = 7) -> dict:
    """按天/供应商/模型/transport/状态聚合官方调用，不与 trace token 混算。"""
    base = {
        "days": [],
        "cost_amount": None,
        "pricing_status": "not_configured",
    }
    try:
        window = max(1, min(int(days), 3650))
    except (TypeError, ValueError):
        window = 7
    cutoff = (date.today() - timedelta(days=window - 1)).isoformat()
    try:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT day, provider, model, transport, status, http_status, "
                "COUNT(*), COALESCE(SUM(input_tokens), 0), "
                "COALESCE(SUM(output_tokens), 0), COALESCE(SUM(total_tokens), 0), "
                "COALESCE(SUM(prompt_cache_hit_tokens), 0), "
                "COALESCE(SUM(prompt_cache_miss_tokens), 0) "
                "FROM provider_usage WHERE day >= ? "
                "GROUP BY day, provider, model, transport, status, http_status "
                "ORDER BY day DESC, provider, model, transport, status, http_status",
                (cutoff,),
            ).fetchall()
        finally:
            conn.close()
    except Exception as e:
        _warn_once(e)
        return {**base, "error": "provider_usage_unavailable"}

    by_day: dict[str, list[dict]] = {}
    for row in rows:
        day_value = row[0]
        by_day.setdefault(day_value, []).append({
            "provider": row[1],
            "model": row[2],
            "transport": row[3],
            "status": row[4],
            "http_status": row[5],
            "calls": row[6],
            "input_tokens": row[7],
            "output_tokens": row[8],
            "total_tokens": row[9],
            "prompt_cache_hit_tokens": row[10],
            "prompt_cache_miss_tokens": row[11],
        })
    base["days"] = [
        {"day": day_value, "groups": groups}
        for day_value, groups in by_day.items()
    ]
    return base


def _cap_error(cap: int) -> RuntimeError:
    return RuntimeError(
        f"LLM 日调用上限已达({cap},SCRIBE3_DAILY_CALL_CAP 可调)")


def tick(cap: int) -> str:
    """记一笔今日 LLM 调用；cap=0 仅记账，cap>0 达帽时抛 RuntimeError。
    返回生效计数域:'shared'(共享台账)| 'process'(SQLite 故障回退)。"""
    today = time.strftime("%Y-%m-%d")
    with _lock:
        if _proc_daily[0] != today:
            _proc_daily[0], _proc_daily[1] = today, 0
        shared_ok = False
        try:
            conn = _connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT n FROM llm_calls WHERE day=?", (today,)).fetchone()
                if cap > 0 and (row[0] if row else 0) >= cap:
                    conn.rollback()
                    raise _cap_error(cap)
                conn.execute(
                    "INSERT INTO llm_calls(day, n) VALUES(?, 1) "
                    "ON CONFLICT(day) DO UPDATE SET n = n + 1", (today,))
                conn.commit()
                shared_ok = True
            finally:
                conn.close()
        except RuntimeError:
            raise
        except Exception as e:
            _warn_once(e)
        if not shared_ok and cap > 0 and _proc_daily[1] >= cap:
            raise _cap_error(cap)
        _proc_daily[1] += 1   # 进程内恒记(shared 故障时的下限账本)
        return "shared" if shared_ok else "process"


def used_today() -> tuple[int, str]:
    """今日已用笔数 + 计数域('shared'|'process')。只读,不计笔。"""
    today = time.strftime("%Y-%m-%d")
    try:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT n FROM llm_calls WHERE day=?", (today,)).fetchone()
            return (row[0] if row else 0), "shared"
        finally:
            conn.close()
    except Exception as e:
        _warn_once(e)
        with _lock:
            return (_proc_daily[1] if _proc_daily[0] == today else 0), "process"


def reset_today() -> None:
    """清零今日计数(共享台账 + 进程内);测试与人工重置用。"""
    today = time.strftime("%Y-%m-%d")
    with _lock:
        _proc_daily[0], _proc_daily[1] = "", 0
    try:
        conn = _connect()
        try:
            conn.execute("DELETE FROM llm_calls WHERE day=?", (today,))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        _warn_once(e)
