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


async def live_stream(url: str, ns: str, db: str, tables: list[str]):
    """异步生成器:产出 SSE 行。

    S-8: 推送 ``{table, action?, id?, fields?}``；仅读 table 的旧前端仍可用。
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
            quuid = await c.live(table)
            gen = await c.subscribe_live(quuid)
            async for note in gen:
                await q.put(_normalize_live_note(table, note))
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
