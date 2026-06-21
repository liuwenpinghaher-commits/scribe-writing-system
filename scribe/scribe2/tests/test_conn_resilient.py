"""SurrealDB 连接韧性:WS 掉线时自动重连并重试一次(防整库 500)。"""
from scribe2.conn import _ResilientDB, _is_conn_error


def test_is_conn_error():
    assert _is_conn_error(Exception("ConnectionClosedError: no close frame received or sent"))
    assert _is_conn_error(Exception("websocket connection is closed"))
    assert not _is_conn_error(ValueError("bad work id"))


def test_resilient_db_reconnects_and_retries():
    state = {"n": 0}

    class FakeDB:
        def __init__(self, idx):
            self.idx = idx
        def query(self, q):
            if self.idx == 0:  # 第一个连接:模拟 WS 掉线
                raise Exception("ConnectionClosedError: no close frame received or sent")
            return [{"ok": True}]

    def factory():
        db = FakeDB(state["n"]); state["n"] += 1; return db

    rdb = _ResilientDB(factory)            # 初始连接=db0(会抛)
    assert rdb.query("SELECT 1") == [{"ok": True}]  # 掉线→重连db1→重试成功
    assert state["n"] == 2                 # 初始 + 重连各一次


def test_resilient_db_non_conn_error_propagates():
    class FakeDB:
        def query(self, q):
            raise ValueError("真实业务错误,不该被吞")
    rdb = _ResilientDB(lambda: FakeDB())
    try:
        rdb.query("x"); assert False, "应抛出"
    except ValueError:
        pass
