"""Surreal LIVE → SSE 的连接生命周期回归。"""
import asyncio

import scribe3.api.app_impl as A
import scribe3.live as L


def test_live_stream_closes_connection_cancelled_during_signin(monkeypatch):
    """页面在 LIVE 登录中断开时，已创建的客户端也必须关闭。

    删除 watch 内的 finally 会让这个测试失败：客户端尚未 append 到 conns，
    外层清理无法看见它，recv/keepalive 线程会永久残留。
    """
    created = []
    entered_signin = asyncio.Event()
    release = asyncio.Event()

    class FakeAsyncSurreal:
        def __init__(self, _url):
            self.closed = False
            created.append(self)

        async def signin(self, _credentials):
            entered_signin.set()
            await release.wait()

        async def use(self, _ns, _db):
            raise AssertionError("取消前不应继续 use")

        async def close(self):
            self.closed = True

    monkeypatch.setattr(L, "AsyncSurreal", FakeAsyncSurreal)

    async def scenario():
        stream = L.live_stream("ws://test", "scribe3", "book", ["chapter"])
        await anext(stream)  # 先得到 SSE 初始化帧，随后 watch 任务进入 signin。
        await asyncio.wait_for(entered_signin.wait(), timeout=1)
        await stream.aclose()
        assert len(created) == 1
        assert created[0].closed is True

    asyncio.run(scenario())


def test_live_connection_quota_remains_held_until_stream_closes(monkeypatch):
    """LIVE 配额的释放时机必须是 SSE 流关闭，而非路由返回响应对象。"""
    A._live_count.clear()

    async def fake_live_stream(*_args, **_kwargs):
        yield "data: init\n\n"
        await asyncio.Event().wait()

    monkeypatch.setattr(A, "live_stream", fake_live_stream)

    async def scenario():
        response = await A.live(work="quota-work")
        assert A._live_count["quota-work"] == 1
        await anext(response.body_iterator)
        await response.body_iterator.aclose()
        assert A._live_count["quota-work"] == 0

    asyncio.run(scenario())
