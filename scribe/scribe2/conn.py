from __future__ import annotations
import os
from surrealdb import Surreal
from .store import Store
from .domain import Domain

SURREAL_URL = os.environ.get("SURREAL_URL", "ws://127.0.0.1:8001/rpc")  # scribe2 专属库(:8000 是别的项目)
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")
SURREAL_NS = os.environ.get("SURREAL_NS", "scribe")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")


def _is_conn_error(e: Exception) -> bool:
    """判定是否 WS 连接掉线类错误(SurrealDB 长连接 idle 后会掉)。"""
    s = f"{type(e).__name__} {e}".lower()
    return any(k in s for k in ("connectionclosed", "no close frame", "not connected",
                                "connection is closed", "websocket", "broken pipe"))


class _ResilientDB:
    """包 Surreal 客户端:任意操作遇连接掉线时自动重连并重试一次。
    根治"WS idle 掉线后整库 500、必须重启进程"的韧性坑。"""

    def __init__(self, factory):
        self._factory = factory
        self._db = factory()

    def __getattr__(self, name):
        # _factory/_db 是实例属性,不会进这里;其余(create/select/query/merge/delete/use…)走包装
        attr = getattr(self._db, name)
        if not callable(attr):
            return attr

        def wrapped(*a, **kw):
            try:
                return getattr(self._db, name)(*a, **kw)
            except Exception as e:
                if _is_conn_error(e):
                    self._db = self._factory()  # 重连
                    return getattr(self._db, name)(*a, **kw)  # 重试一次
                raise
        return wrapped


def _raw_connect() -> Surreal:
    d = Surreal(SURREAL_URL)
    d.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
    d.use(SURREAL_NS, SURREAL_DB)
    return d


def connect():
    """返回带自动重连的 SurrealDB 客户端(WS 掉线不再整库 500)。"""
    return _ResilientDB(_raw_connect)


def domain_from(db) -> Domain:
    return Domain(Store(db))
