"""SurrealDB LIVE → SSE:把 NS=scribe3 各表的变更推给前端(改一处处处同步)。

不把 DB 凭证暴露给浏览器:后端订阅 LIVE,经 SSE 把"哪张表变了"推给前端,前端据此重取视图。
LIVE 仅单节点(研究结论);每表一条连接避免单连接多订阅的不确定性。

凭证与 store 连接同源:SCRIBE3_SURREAL_USER / SCRIBE3_SURREAL_PASS(及 settings 热读),
禁止写死 root/root(生产可换非 root)。
"""
from __future__ import annotations

import asyncio
import json
import os

from surrealdb import AsyncSurreal


def _live_credentials() -> tuple[str, str]:
    """与 SurrealStore 一致:env → 设置中心 → 开发默认 root。"""
    user = os.environ.get("SCRIBE3_SURREAL_USER")
    password = os.environ.get("SCRIBE3_SURREAL_PASS")
    if user is not None and password is not None and user != "" and password != "":
        return user, password
    try:
        from scribe3.settings import get_setting
        if not user:
            user = str(get_setting("SCRIBE3_SURREAL_USER") or "root")
        if not password:
            password = str(get_setting("SCRIBE3_SURREAL_PASS") or "root")
    except Exception:
        user = user or "root"
        password = password or "root"
    return user or "root", password or "root"


async def live_stream(url: str, ns: str, db: str, tables: list[str]):
    """异步生成器:产出 SSE 行。任一表 CREATE/UPDATE/DELETE → 推 {"table": 名}。"""
    q: asyncio.Queue = asyncio.Queue()
    conns: list = []
    tasks: list = []
    user, password = _live_credentials()

    async def watch(table: str):
        c = AsyncSurreal(url)
        await c.signin({"username": user, "password": password})
        await c.use(ns, db)
        conns.append(c)
        quuid = await c.live(table)
        gen = await c.subscribe_live(quuid)
        async for _note in gen:
            await q.put(table)

    for t in tables:
        tasks.append(asyncio.create_task(watch(t)))

    try:
        yield "retry: 3000\ndata: {\"table\": \"_init\"}\n\n"
        while True:
            try:
                table = await asyncio.wait_for(q.get(), timeout=15)
                yield f"data: {json.dumps({'table': table})}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"          # SSE 注释行保活
    finally:
        for t in tasks:
            t.cancel()
        for c in conns:
            try:
                await c.close()
            except Exception:
                pass
