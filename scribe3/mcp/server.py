"""MCP server lifecycle / setup."""
from __future__ import annotations

from scribe3.mcp._common import *  # noqa: F403
from scribe3.mcp.gating import *  # noqa: F403
from scribe3.mcp.tools import *  # noqa: F403

def set_store(s, work: str | None = None) -> None:
    from scribe3.mcp import _common as C
    w = work or _store_work(s) or _default_work()
    C._stores[w] = s
    C._stores.move_to_end(w)
    if C._store is None or work is None or w == _default_work():
        C._store = s
        C._stores[_default_work()] = s



def setup_store(ns: str = "scribe3", db: str | None = None):
    """连 NS=scribe3 + 幂等建 schema,挂上默认书。

    work-scoped 工具可显式传 work,同一 MCP 进程会按书缓存 SurrealStore;未传 work 时保持
    旧行为,使用 SCRIBE3_WORK/main 绑定的默认书。"""
    from scribe3.store import SurrealStore
    db = db or os.environ.get("SCRIBE3_WORK", "main")
    store = SurrealStore(ns=ns, db=db)
    store.apply_schema()
    set_store(store, work=db)
    return store


def main() -> None:
    """MCP stdio entry; resolve setup_store/mcp via package so tests can monkeypatch."""
    import scribe3.mcp as pkg
    from scribe3 import settings as _settings
    _settings.apply_restart_overrides()   # restart 类 DB 覆盖灌 env(界面改的 DB 地址等对 MCP 进程同样生效)
    pkg.setup_store()
    pkg.mcp.run()


__all__ = ['set_store', 'setup_store', 'main']
