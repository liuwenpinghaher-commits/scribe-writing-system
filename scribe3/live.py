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


def live_id_allowed(
    table: str,
    note_payload: dict,
    record_ids: dict[str, list[str]] | None,
) -> bool:
    """GAP-4 / D8：记录级过滤的**等效实现**（输出侧）。

    表级 ``c.live(table)`` + 本函数过滤 ≡ 调用方只关心目标 id 的推送语义。
    原生 ``LIVE SELECT … WHERE`` 待 Surreal SDK 稳定后切换（DEFERRED，一行级）。
    """
    id_filter = record_ids or {}
    allowed = id_filter.get(table)
    if not allowed:
        return True
    rid = str((note_payload or {}).get("id") or "")
    if not rid:
        return True
    return any(rid == a or rid.endswith(":" + a) or a in rid for a in allowed)


def _normalize_live_note(table: str, note) -> dict:
    """S-8: 从 LIVE 通知提取 action + id + 可选 fields；始终含 table（旧客户端兼容）。"""
    payload: dict = {"table": table}
    try:
        from scribe3.surreal_flags import live_granular
        granular = live_granular()
    except Exception:
        granular = True
    if not granular or note is None:
        return payload
    action = None
    rid = None
    fields = None
    if isinstance(note, dict):
        action = note.get("action") or note.get("type") or note.get("op")
        rid = note.get("id") or note.get("record") or note.get("thing")
        val = note.get("result") or note.get("value") or note.get("after")
        if isinstance(val, dict):
            fields = {k: val.get(k) for k in list(val.keys())[:12]}
            rid = rid or val.get("id")
        elif val is not None and rid is None:
            rid = str(val)
    else:
        # 部分 SDK 推 record id 字符串
        s = str(note)
        if ":" in s and len(s) < 200:
            rid = s
    if action:
        payload["action"] = str(action)
    if rid is not None:
        payload["id"] = str(rid)
    if fields:
        payload["fields"] = fields
    return payload


async def live_stream(
    url: str,
    ns: str,
    db: str,
    tables: list[str],
    *,
    record_ids: dict[str, list[str]] | None = None,
):
    """异步生成器:产出 SSE 行。

    S-8 / GAP-4: 推送 ``{table, action?, id?, fields?}``。
    ``record_ids`` 若提供：对对应表在输出侧按 id 过滤（DB 条件 LIVE 在驱动不稳时回退过滤）。
    """
    from surrealdb import AsyncSurreal

    q: asyncio.Queue = asyncio.Queue()
    tasks: list = []
    user, password = _live_credentials()
    async def watch(table: str):
        c = AsyncSurreal(url)
        try:
            await c.signin({"username": user, "password": password})
            await c.use(ns, db)
            # D8 DEFERRED：整表 live + live_id_allowed；SDK 稳后改为条件 LIVE
            quuid = await c.live(table)
            gen = await c.subscribe_live(quuid)
            async for note in gen:
                payload = _normalize_live_note(table, note)
                if isinstance(payload, dict) and not live_id_allowed(
                    table, payload, record_ids
                ):
                    continue
                await q.put(payload)
        finally:
            # 取消可能发生在 signin/use 期间；此时客户端尚未完成订阅，
            # 也不能依赖外层的已订阅连接列表兜底关闭。
            try:
                await c.close()
            except Exception:
                pass

    for t in tables:
        tasks.append(asyncio.create_task(watch(t)))

    try:
        yield "retry: 3000\ndata: {\"table\": \"_init\"}\n\n"
        while True:
            try:
                payload = await asyncio.wait_for(q.get(), timeout=15)
                if isinstance(payload, str):
                    payload = {"table": payload}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"          # SSE 注释行保活
    finally:
        for t in tasks:
            t.cancel()
        # 等待 watch 自己的 finally 实际关闭 AsyncSurreal，不能只 cancel 后返回，
        # 否则页面快速 reload 会累积 recv/keepalive 线程和套接字。
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
