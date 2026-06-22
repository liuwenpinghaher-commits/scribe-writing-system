"""scribe3 领域 MCP server(FastMCP,名 "scribe3")。

读工具放行(readOnlyHint);写工具经 Hermes elicitation 待批,批准后才走 store 单点落库。
工具名带 s3_ 前缀(隔离标准:与 scribe2 同挂也不撞名)。
可测核心 = commit_if_approved 门控;elicitation 是生产侧(ctx.elicit,fail-closed)。
"""
from __future__ import annotations

from typing import Callable

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from scribe3.knowledge import project_frame
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge
from scribe3.render import render
from scribe3.verify import causal_complete, find_leaks

mcp = FastMCP("scribe3")
_store = None


def set_store(s) -> None:
    global _store
    _store = s


# ===== 写门控 =====
WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge"}


def requires_approval(name: str) -> bool:
    return name in WRITE_GATED


def commit_if_approved(name: str, accepted: bool, do_write: Callable[[], None]) -> dict:
    """写门控单一落库点:WRITE_GATED 的工具须 accepted=True 才执行 do_write
    (do_write 内部走 store.execute_write 单点)。拒绝=fail-closed 不写。"""
    if name in WRITE_GATED and not accepted:
        return {"status": "declined", "tool": name}
    do_write()
    return {"status": "written", "tool": name}


class _Approve(BaseModel):
    confirm: bool = True


async def _ask(ctx: Context, summary: str) -> bool:
    """Hermes elicitation:写前向用户征求批准。异常/超时 → fail-closed(不写)。"""
    try:
        res = await ctx.elicit(message=f"批准写入?{summary}", schema=_Approve)
        return getattr(res, "action", None) == "accept"
    except Exception:
        return False


_RO = ToolAnnotations(readOnlyHint=True)
_RW = ToolAnnotations(readOnlyHint=False)


# ===== 读工具(放行)=====
@mcp.tool(annotations=_RO)
def s3_project_frame(focalizer: str, chapter: int) -> list[dict]:
    """投影 focalizer 截至某章的知识帧(限知渲染的输入;帧外私密不在内)。"""
    fr = project_frame(_store, focalizer, chapter)
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute, "value": f.value}
            for f in fr.facts]


@mcp.tool(annotations=_RO)
def s3_render_scene(focalizer: str, chapter: int) -> str:
    """以 focalizer 限知视角渲染本章 sjuzhet(只读:生成,不改世界)。"""
    return render(_store, chapter, focalizer)


@mcp.tool(annotations=_RO)
def s3_find_leaks(prose: str, focalizer: str, chapter: int) -> list[dict]:
    """兜底 POV 判官:扫散文里冒出的帧外私密破绽词。"""
    return [{"fact_id": x.fact_id, "marker": x.marker}
            for x in find_leaks(prose, _store, focalizer, chapter)]


@mcp.tool(annotations=_RO)
def s3_causal_complete(chapter: int) -> list[dict]:
    """连贯性查询:每事件须因果入边+目标。返回违规列表(空=干净)。"""
    return [{"event": v.event_id, "reason": v.reason} for v in causal_complete(_store, chapter)]


# ===== 写工具(elicitation 待批 → store 单点)=====
@mcp.tool(annotations=_RW)
async def s3_add_character(ctx: Context, oid: str, name: str) -> dict:
    """新增角色(写,待批)。"""
    ok = await _ask(ctx, f"新增角色 {oid}={name}")
    return commit_if_approved("s3_add_character", ok,
                              lambda: _store.add_entity(Entity(oid, "character", name)))


@mcp.tool(annotations=_RW)
async def s3_add_fact(ctx: Context, oid: str, entity: str, attribute: str, value: str,
                      valid_from: int, secret: bool = False) -> dict:
    """新增事实/状态@章(写,待批)。secret=True 标私密(泄露=穿帮)。"""
    ok = await _ask(ctx, f"新增事实 {oid}:{entity}·{attribute}={value}")
    return commit_if_approved("s3_add_fact", ok,
                              lambda: _store.add_fact(Fact(oid, entity, attribute, value,
                                                           valid_from, secret=secret)))


@mcp.tool(annotations=_RW)
async def s3_add_event(ctx: Context, oid: str, etype: str, valid_from: int,
                       motivated_by_goal: str | None = None) -> dict:
    """新增事件(写,待批)。"""
    ok = await _ask(ctx, f"新增事件 {oid}:{etype}")
    return commit_if_approved("s3_add_event", ok,
                              lambda: _store.add_event(Event(oid, etype, story_time=valid_from,
                                                             motivated_by_goal=motivated_by_goal)))


@mcp.tool(annotations=_RW)
async def s3_record_knowledge(ctx: Context, knower: str, proposition: str,
                              since_chapter: int, acquired_via: str = "saw") -> dict:
    """记知识边:某角色某章获知某命题(写,待批)。"""
    ok = await _ask(ctx, f"记知识 {knower} 知道 {proposition}(章{since_chapter})")
    return commit_if_approved("s3_record_knowledge", ok,
                              lambda: _store.add_knowledge(KnowledgeEdge(knower, proposition,
                                                                         since_chapter=since_chapter,
                                                                         acquired_via=acquired_via)))
