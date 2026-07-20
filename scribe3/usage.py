"""H-10 全系统 LLM 预算:跨进程共享日帽台账。

原日帽是进程内计数(llm.py `_daily`)——app(:3321)与 MCP stdio 进程
(run_mcp.sh)各持一份,系统真实调用数 = 各进程之和,"剩余额度"失真。
本模块用单文件 SQLite 台账共享计数:两进程同记一本账,日帽成为真正的
系统级成本保险丝。

- 台账路径:env `SCRIBE3_LLM_LEDGER`,缺省 `~/.scribe2-surreal/scribe3_llm_ledger.sqlite3`
  (与 SurrealDB 生产数据同目录,备份/迁移一起走)。
- 并发:BEGIN IMMEDIATE + busy timeout,app 与 MCP 两写方安全。
- fail-open:SQLite 任何故障回退进程内计数并 warning 一次——帽是保险丝
  不是账本,台账挂了绝不能阻断写作主链路。
- 帽语义:计"发起的 LLM 调用笔数",非 token;token 真实用量见
  store.usage_summary()(聚合 Hermes 返回的 usage)。
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS llm_calls (day TEXT PRIMARY KEY, n INTEGER NOT NULL)")
    return conn


def _warn_once(e: Exception) -> None:
    global _warned_ledger_error
    if not _warned_ledger_error:
        _warned_ledger_error = True
        _log.warning("共享日帽台账不可用,回退进程内计数(fail-open): %s", e)


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
