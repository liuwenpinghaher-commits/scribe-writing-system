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

from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge
from scribe3.render import render
from scribe3.verify import causal_complete, find_leaks

mcp = FastMCP("scribe3")
_store = None


def set_store(s) -> None:
    global _store
    _store = s


# ===== 写门控 =====
WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
               "s3_plant_promise", "s3_advance_promise",
               "s3_craft_rule_add", "s3_craft_rule_remove"}


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


@mcp.tool(annotations=_RO)
def s3_semantic_recall(query: str, k: int = 5) -> list[dict]:
    """语义召回最相关的设定/命题(向量 RAG,非字面匹配;头部工具仍多用字面,这是差异化)。"""
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute, "value": f.value}
            for f in _store.semantic_recall(query, k)]


@mcp.tool(annotations=_RO)
def s3_dramatic_irony(focalizer: str, chapter: int) -> list[dict]:
    """戏剧反讽点:读者已知、而视角角色不知的事实(KNOWS(reader,F)∧¬KNOWS(focal,F))。
    渲染该视角时据此写"角色安心、读者揪心"的张力(但角色台词只能用其帧内信息)。"""
    return [{"id": f.id, "value": f.value} for f in dramatic_irony(_store, focalizer, chapter)]


@mcp.tool(annotations=_RO)
def s3_list_promises() -> list[dict]:
    """列伏笔(open/closed + 埋/收章)。"""
    return _store.list_promises()


@mcp.tool(annotations=_RO)
def s3_list_motifs() -> list[dict]:
    """列母题(名/绑定主题/物质回声/隐喻展开)——参照不透支。"""
    return _store.list_motifs()


@mcp.tool(annotations=_RO)
def s3_get_chapter(seq: int) -> dict:
    """读某章正文(manuscript)。"""
    return _store.get_chapter(seq) or {}


@mcp.tool(annotations=_RO)
def s3_qc_chapter(seq: int) -> dict:
    """对某章正文跑确定性 QC(复读/排比/升华/AI腔)——渲染层兜底。
    升华检测叠加本书题材正则(craft_rule purple_regex)。"""
    from scribe3.critique import quality_flags
    ch = _store.get_chapter(seq)
    if not ch:
        return {}
    extra = _store.purple_patterns() if hasattr(_store, "purple_patterns") else None
    return quality_flags(ch["prose"], extra_patterns=extra)


@mcp.tool(annotations=_RO)
def s3_emotion_palette(emotion: str = "") -> list | dict:
    """情感词典(引擎层,题材无关):空参返回15种情感名;带参返回该情感的身体信号/内部感觉。
    渲染某情感时查取 2-3 个身体信号编织进叙述(show 不 tell 的命门)。"""
    from scribe3.craft import PALETTE
    if not emotion:
        return list(PALETTE)
    return PALETTE.get(emotion, {})


@mcp.tool(annotations=_RO)
def s3_craft_rule_list() -> list[dict]:
    """列本书题材层 craft 规则(升华正则/法器写法/角色覆盖动作)。"""
    return _store.list_craft_rules()


@mcp.tool(annotations=_RO)
def s3_discipline_check(seq: int, brief: str = "") -> dict:
    """LLM 纪律判官(走 Hermes):判本章 双高潮/声音崩/解说倾泻(确定性检测的盲区)。
    返回 {ok, violations, cut_after, changed, text(若可截)};不自动写,作者/主编决定是否应用。"""
    from scribe3.critique import discipline_truncate
    from scribe3.llm import hermes_complete
    ch = _store.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"ok": True, "violations": []}
    return discipline_truncate(ch["prose"], brief, hermes_complete)


# ===== manuscript 写(草稿,直接写,不待批——非世界状态)=====
@mcp.tool(annotations=_RW)
def s3_save_chapter(seq: int, prose: str, title: str = "", focalizer: str | None = None) -> dict:
    """落/覆盖某章正文(作者草稿,不经 elicitation;manuscript 非世界状态)。"""
    _store.save_chapter(seq, prose, title=title, focalizer=focalizer)
    return {"status": "saved", "seq": seq}


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

    def _write():
        _store.add_fact(Fact(oid, entity, attribute, value, valid_from, secret=secret))
        _store.semantic_index(oid, value)   # 写时建语义索引(设定即写即可召回)
    return commit_if_approved("s3_add_fact", ok, _write)


@mcp.tool(annotations=_RW)
async def s3_add_event(ctx: Context, oid: str, etype: str, valid_from: int,
                       motivated_by_goal: str | None = None) -> dict:
    """新增事件(写,待批)。"""
    ok = await _ask(ctx, f"新增事件 {oid}:{etype}")
    return commit_if_approved("s3_add_event", ok,
                              lambda: _store.add_event(Event(oid, etype, story_time=valid_from,
                                                             motivated_by_goal=motivated_by_goal)))


@mcp.tool(annotations=_RW)
async def s3_plant_promise(ctx: Context, text: str, setup_chapter: int,
                           kind: str = "promise") -> dict:
    """埋伏笔(写,待批)。kind=promise/red_herring。"""
    ok = await _ask(ctx, f"埋伏笔(第{setup_chapter}章):{text}")
    return commit_if_approved("s3_plant_promise", ok,
                              lambda: _store.plant_promise(text, setup_chapter, kind=kind))


@mcp.tool(annotations=_RW)
async def s3_advance_promise(ctx: Context, pid: str, payoff_chapter: int) -> dict:
    """回收伏笔(写,待批)。"""
    ok = await _ask(ctx, f"回收伏笔 {pid}(第{payoff_chapter}章)")
    return commit_if_approved("s3_advance_promise", ok,
                              lambda: _store.advance_promise(pid, payoff_chapter))


@mcp.tool(annotations=_RW)
def s3_ingest_chapter(seq: int) -> dict:
    """章节回写(客观回写,不待批):读定稿抽"谁新知道什么/做了什么"→更新知识账本。
    非创作虚构(add_fact/add_event 那些经 elicitation);ingest 反映已定稿正文,
    后端 save-chapter 也会自动后台跑同一逻辑。"""
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    return ingest_chapter(_store, seq, hermes_complete)


@mcp.tool(annotations=_RW)
async def s3_record_knowledge(ctx: Context, knower: str, proposition: str,
                              since_chapter: int, acquired_via: str = "saw") -> dict:
    """记知识边:某角色某章获知某命题(写,待批)。"""
    ok = await _ask(ctx, f"记知识 {knower} 知道 {proposition}(章{since_chapter})")
    return commit_if_approved("s3_record_knowledge", ok,
                              lambda: _store.add_knowledge(KnowledgeEdge(knower, proposition,
                                                                         since_chapter=since_chapter,
                                                                         acquired_via=acquired_via)))


@mcp.tool(annotations=_RW)
async def s3_craft_rule_add(ctx: Context, kind: str, pattern: str, note: str = "") -> dict:
    """加一条本书题材 craft 规则(写,待批)。kind=purple_regex|artifact_craft|cover_action。"""
    ok = await _ask(ctx, f"加题材规则 [{kind}] {pattern}")
    return commit_if_approved("s3_craft_rule_add", ok,
                              lambda: _store.add_craft_rule(kind, pattern, note))


@mcp.tool(annotations=_RW)
async def s3_craft_rule_remove(ctx: Context, rule_id: str) -> dict:
    """删一条本书题材 craft 规则(写,待批)。"""
    ok = await _ask(ctx, f"删题材规则 {rule_id}")
    return commit_if_approved("s3_craft_rule_remove", ok,
                              lambda: _store.delete_craft_rule(rule_id))


# ===== stdio 入口(供 Hermes 以 `python -m scribe3.mcp` 挂载)=====
def setup_store(ns: str = "scribe3", db: str = "main"):
    """连 NS=scribe3(与 scribe2 的 NS=scribe 隔离)+ 幂等建 schema,挂上。"""
    from scribe3.store import SurrealStore
    store = SurrealStore(ns=ns, db=db)
    store.apply_schema()
    set_store(store)
    return store


def main() -> None:
    setup_store()
    mcp.run()


if __name__ == "__main__":
    main()
