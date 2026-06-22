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
