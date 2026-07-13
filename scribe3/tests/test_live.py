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


def test_codex_tables_all_in_live_tables(store):
    """U-002 回归门禁:设定库树里的每个分类,其底层表必须在 _LIVE_TABLES 里。

    病史(2026-07-13):world_rule/faction/item/term 四张表漏出订阅清单 → 主编经审批
    写入 15 条世界规则 + 6 个势力后,前端项目树收不到 live 事件、不重拉,设定库看着
    还是空的(数据其实已落库),作者误以为写入失败。
    前端 BinderLayout 对任何 live 事件都重建整棵树,故只要表在清单里就会刷新。
    """
    import scribe3.app as A
    # project_tree 的 codex 分类 ref 与其 SurrealDB 表名同名(见 store.project_tree 的 _cat 调用)
    tree = store.project_tree()
    codex_cats = [c["ref"] for c in (tree.get("codex") or {}).get("children", [])]
    assert codex_cats, "设定库应有分类(测试前提)"
    missing = [c for c in codex_cats if c not in A._LIVE_TABLES]
    assert not missing, (
        f"设定库分类的表未进 _LIVE_TABLES,写入后前端不会自动刷新: {missing}")
