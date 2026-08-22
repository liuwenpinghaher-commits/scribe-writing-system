"""Surreal LIVE → SSE 的连接生命周期回归。"""
import asyncio
import json

import scribe3.app  # noqa: F401  — 把 /live 绑回 app_impl，A.live 才存在
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


def test_live_sse_three_event_shapes_chapter_approval_pilot(monkeypatch):
    """DIR-04：/live 至少吐出 chapter_update / approval / pilot_state 三种事件形状。"""
    A._live_count.clear()
    frames = [
        {"table": "chapter", "action": "UPDATE", "id": "chapter:1"},
        {"table": "idea", "action": "CREATE", "id": "approval:run-1"},
        {"table": "chapter", "action": "UPDATE", "id": "chapter:3",
         "fields": {"pilot_state": "drafting"}},
    ]

    async def fake_live_stream(*_args, **_kwargs):
        for payload in frames:
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    monkeypatch.setattr(A, "live_stream", fake_live_stream)

    async def scenario():
        response = await A.live(work="shape-work")
        chunks: list[str] = []
        async for line in response.body_iterator:
            chunks.append(line if isinstance(line, str) else line.decode())
        await response.body_iterator.aclose()
        text = "".join(chunks)
        assert '"table": "chapter"' in text and "UPDATE" in text
        assert "approval:run-1" in text
        assert "pilot_state" in text
        assert A._live_count.get("shape-work", 0) == 0

    asyncio.run(scenario())
    ch = L._normalize_live_note("chapter", {"action": "UPDATE", "id": "chapter:1"})
    ap = L._normalize_live_note("idea", {"action": "CREATE", "id": "approval:run-1"})
    ps = L._normalize_live_note(
        "chapter",
        {"action": "UPDATE", "id": "chapter:3", "result": {"pilot_state": "drafting"}},
    )
    assert ch.get("action") == "UPDATE" and ch.get("table") == "chapter"
    assert ap.get("action") == "CREATE" and "approval" in ap.get("id", "")
    assert ps.get("fields", {}).get("pilot_state") == "drafting"
