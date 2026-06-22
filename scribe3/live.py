"""SurrealDB LIVE → SSE:把 NS=scribe3 各表的变更推给前端(改一处处处同步)。

不把 DB 凭证暴露给浏览器:后端订阅 LIVE,经 SSE 把"哪张表变了"推给前端,前端据此重取视图。
LIVE 仅单节点(研究结论);每表一条连接避免单连接多订阅的不确定性。
"""
from __future__ import annotations

import asyncio
import json

from surrealdb import AsyncSurreal


async def live_stream(url: str, ns: str, db: str, tables: list[str]):
    """异步生成器:产出 SSE 行。任一表 CREATE/UPDATE/DELETE → 推 {"table": 名}。"""
    q: asyncio.Queue = asyncio.Queue()
    conns: list = []
    tasks: list = []

    async def watch(table: str):
        c = AsyncSurreal(url)
        await c.signin({"username": "root", "password": "root"})
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
