"""设置中心的跨进程权威源:单文件 SQLite(沿用 usage.py 日帽台账范式)。

- 路径:env SCRIBE3_SETTINGS_DB,缺省 ~/.scribe2-surreal/scribe3_settings.sqlite3
  (与 SurrealDB 生产数据同目录,备份一起走)。
- 为什么不是 SurrealDB:DB 连接参数本身是设置项(自举悖论);且 app 与 MCP
  stdio 进程要共享同一份设置。
- fail-soft 边界:读故障回空(系统回落 env/默认值照常工作,告警一次);
  写故障原样抛(修改必须显式失败,不能假装成功)。
- 本地权限边界:仅本次调用新建的数据库直接父目录设为 0700；已有自定义父目录
  保持原权限，数据库文件仍收紧为 0600;
  当前不宣称静态加密。只读窄探针不创建文件、不 chmod。
- value 一律 JSON 编码字符串;secret 项审计只记 «secret»,绝不落明文。
  审计 old 值在同一事务内原子读取,不信任调用方;key 命中敏感词
  (KEY/TOKEN/PASS/SECRET)时存储层兜底强制掩码。
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from pathlib import Path

_log = logging.getLogger("scribe3.settings_store")
_warned = False
_MASKED = "«secret»"
_SENSITIVE = re.compile(r"(KEY|TOKEN|PASS|SECRET)", re.I)


def db_path() -> Path:
    p = os.environ["SCRIBE3_SETTINGS_DB"] if "SCRIBE3_SETTINGS_DB" in os.environ else None
    if p:
        return Path(p).expanduser()
    return Path.home() / ".scribe2-surreal" / "scribe3_settings.sqlite3"


def _connect() -> sqlite3.Connection:
    path = db_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        pass
    else:
        os.chmod(path.parent, 0o700)
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(path), timeout=2.0)
        os.chmod(path, 0o600)
        conn.execute("CREATE TABLE IF NOT EXISTS setting ("
                     "key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS setting_audit ("
                     "id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
                     "key TEXT NOT NULL, old TEXT, new TEXT)")
        return conn
    except Exception:
        if conn is not None:
            conn.close()
        raise


def _warn_once(e: Exception) -> None:
    global _warned
    if not _warned:
        _warned = True
        _log.warning("设置台账不可用,回落 env/默认值(fail-soft): %s", e)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _current_value(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM setting WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def get_all_overrides() -> dict[str, str]:
    """全部覆盖值 {key: json_str}。读故障回空 dict(fail-soft)。"""
    try:
        conn = _connect()
        try:
            return {k: v for k, v in conn.execute("SELECT key, value FROM setting")}
        finally:
            conn.close()
    except Exception as e:
        _warn_once(e)
        return {}


def has_override(key: str) -> bool:
    """只读检查某 key 是否存在；不创建目录/数据库/表，不加载 value。"""
    path = db_path()
    if not path.is_file():
        return False
    try:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        try:
            row = conn.execute(
                "SELECT 1 FROM setting WHERE key=? LIMIT 1",
                (key,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()
    except Exception:
        return False


def get_override(key: str) -> str | None:
    """只读返回某 key 的 JSON 值；不创建目录/数据库/表。"""
    path = db_path()
    if not path.is_file():
        return None
    try:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        try:
            row = conn.execute(
                "SELECT value FROM setting WHERE key=? LIMIT 1",
                (key,),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    except Exception:
        return None


def set_override(key: str, value_json: str, *, mask: bool = False) -> None:
    """写覆盖值 + 审计。old 在同一事务内原子读取;敏感 key 强制掩码。写故障原样抛。"""
    mask = mask or bool(_SENSITIVE.search(key))
    conn = _connect()
    try:
        with conn:  # 事务:异常自动 rollback,正常自动 commit
            old_json = _current_value(conn, key)
            conn.execute(
                "INSERT INTO setting(key, value, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, value_json, _now()))
            conn.execute(
                "INSERT INTO setting_audit(ts, key, old, new) VALUES(?,?,?,?)",
                (_now(), key, _MASKED if (mask and old_json is not None) else old_json,
                 _MASKED if mask else value_json))
    finally:
        conn.close()


def delete_override(key: str, *, mask: bool = False) -> None:
    """删覆盖值 + 审计。old 在同一事务内原子读取;敏感 key 强制掩码。写故障原样抛。"""
    mask = mask or bool(_SENSITIVE.search(key))
    conn = _connect()
    try:
        with conn:  # 事务:异常自动 rollback,正常自动 commit
            old_json = _current_value(conn, key)
            conn.execute("DELETE FROM setting WHERE key=?", (key,))
            conn.execute(
                "INSERT INTO setting_audit(ts, key, old, new) VALUES(?,?,?,?)",
                (_now(), key, _MASKED if (mask and old_json is not None) else old_json, None))
    finally:
        conn.close()


def append_audit(key: str, *, actor: str = "", payload: str = "") -> None:
    """通用审计一行（招式提议/网关改文件等）。"""
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO setting_audit(ts, key, old, new) VALUES(?,?,?,?)",
                (_now(), key, actor or None, (payload or "")[:800] or None))
    finally:
        conn.close()


def audit_rows(limit: int = 50, offset: int = 0) -> list[dict]:
    try:
        conn = _connect()
        try:
            rows = conn.execute("SELECT ts, key, old, new FROM setting_audit "
                                "ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
            return [{"ts": t, "key": k, "old": o, "new": n} for t, k, o, n in rows]
        finally:
            conn.close()
    except Exception as e:
        _warn_once(e)
        return []
