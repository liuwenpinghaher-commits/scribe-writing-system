"""S5-LIVE · 去风险:验证 surrealdb-py 2.0 + SurrealDB 3.1.5 的 LIVE 订阅可用。

LIVE SELECT 仅单节点(研究结论)——临时内存库正合。订阅 character 表,另一连接写入,
应收到 CREATE 通知。这是"改一处处处同步"多视图的底层。
"""
import asyncio

from surrealdb import AsyncSurreal

from scribe3.ontology import Entity


def test_live_notifies_on_create(store):
    async def run():
        sub = AsyncSurreal(store.url)
        await sub.signin({"username": "root", "password": "root"})
        await sub.use("scribe3", "test")
        quuid = await sub.live("character")

        async def consume():
            gen = await sub.subscribe_live(quuid)
            async for note in gen:
                return note

        task = asyncio.create_task(consume())
        await asyncio.sleep(0.3)                       # 让订阅起来
        store.add_entity(Entity("role:小试", "character", "小试"))   # 另一连接写入
        try:
            return await asyncio.wait_for(task, timeout=8)
        finally:
            await sub.kill(quuid)
            await sub.close()

    note = asyncio.run(run())
    assert note, "应收到 LIVE 通知(改一处→订阅方收到)"
