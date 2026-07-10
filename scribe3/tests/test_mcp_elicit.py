"""S2 写路径 · elicitation 端到端(MCP 协议级,确定性,不靠人手点)。

用内存 MCP client↔server 会话 + 注入 elicitation 回调,真协议跑通:
  accept → 写工具落库(store 有该角色)
  decline → fail-closed,不落库(store 无)
比手动交互更严格、可回归。验证 _ask→ctx.elicit→commit_if_approved→store 单点 全链。
"""
import asyncio

from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import ElicitResult

import scribe3.mcp as M


class _AcceptCtx:
    async def elicit(self, *args, **kwargs):
        return ElicitResult(action="accept", content={"confirm": True})


def _drive(store, action: str):
    """以 elicitation 回调=action 跑一次 s3_add_character。"""
    M.set_store(store)

    async def cb(context, params):
        return ElicitResult(action=action, content={"confirm": True})

    async def run():
        async with create_connected_server_and_client_session(
                M.mcp._mcp_server, elicitation_callback=cb) as client:
            await client.call_tool("s3_add_character", {"oid": "role:测试君", "name": "测试君"})

    asyncio.run(run())


def test_elicit_accept_writes(store):
    _drive(store, "accept")
    e = store.entity("role:测试君")
    assert e is not None and e.name == "测试君", "批准→写工具落库 NS=scribe3"


def test_elicit_decline_blocks(store):
    _drive(store, "decline")
    assert store.entity("role:测试君") is None, "拒绝→fail-closed 不落库"


def test_work_scoped_read_uses_requested_book(store):
    from scribe3.store import SurrealStore

    other = SurrealStore(url=store.url, ns="scribe3", db="book_b")
    other.apply_schema()
    try:
        store.save_chapter(1, "主库正文。", title="主库章")
        other.save_chapter(1, "乙库正文。", title="乙库章")
        M.set_store(store)
        M.set_store(other, work="book_b")

        assert M.s3_get_chapter(1)["title"] == "主库章"
        assert M.s3_get_chapter(1, work="book_b")["title"] == "乙库章"
    finally:
        other.close()


def test_protocol_read_accepts_work_parameter(store):
    from scribe3.store import SurrealStore

    other = SurrealStore(url=store.url, ns="scribe3", db="book_b")
    other.apply_schema()
    try:
        store.save_chapter(1, "主库正文。", title="主库章")
        other.save_chapter(1, "乙库正文。", title="乙库章")
        M.set_store(store)
        M.set_store(other, work="book_b")

        async def run():
            async with create_connected_server_and_client_session(M.mcp._mcp_server) as client:
                return await client.call_tool("s3_get_chapter", {"seq": 1, "work": "book_b"})

        result = asyncio.run(run())
        blob = str(result)
        assert "乙库章" in blob
        assert "主库章" not in blob
    finally:
        other.close()


def test_work_scoped_write_only_touches_requested_book(store):
    from scribe3.store import SurrealStore

    other = SurrealStore(url=store.url, ns="scribe3", db="book_b")
    other.apply_schema()
    try:
        M.set_store(store)
        M.set_store(other, work="book_b")

        asyncio.run(M.s3_add_character(_AcceptCtx(), "role:乙库人", "乙库人", work="book_b"))

        assert other.entity("role:乙库人") is not None
        assert store.entity("role:乙库人") is None
    finally:
        other.close()
