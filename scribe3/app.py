"""scribe3 后端 API(FastAPI,端口 3321)· 多书(一书一 DB)。

每端点按 ?work=<slug> 路由到对应书的 DB(NS=scribe3 / db=slug),store 按书缓存。
/works 列表/新建。读端点直查;写作走主编对话(/chat/write),不经 /render 直渲。生成走 Hermes。
与 scribe2 后端 3320 隔离(3321)。

写授权契约(P02):
- REST 写端点 = 作者可信通道(全权,含 secret)。作者直编,不经待批。
- MCP 写工具 = agent 受限通道(经 elicitation 待批,commit_if_approved)。
- 新增写端点必须显式登记在 _check_write_paths 白名单,测试守护不漂移。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections import OrderedDict

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.live import live_stream
from scribe3.ontology import Entity, Fact
from scribe3.store import (
    SurrealStore, _overdue_flag, create_work, delete_work, list_works, rename_work,
)
from scribe3.verify import causal_complete

app = FastAPI(title="scribe3")
_CORS = os.environ.get("SCRIBE3_CORS_ORIGINS", "http://127.0.0.1:3311,http://localhost:3311")

# P3-e1 Fix 1: overdue 阈值单源——模块常量(前端从 /quality 消费,不重算)
OVERDUE_SLACK = 3
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _CORS.split(",") if o.strip()],
                   allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])

# P01: 可选 bearer token 认证(本地不设 env=放行;暴露=设 SCRIBE3_API_TOKEN 强制)
_API_TOKEN = os.environ.get("SCRIBE3_API_TOKEN")


@app.middleware("http")
async def _auth_middleware(request, call_next):
    if _API_TOKEN and not request.url.path.startswith("/health"):
        auth = request.headers.get("authorization", "")
        import hmac
        if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:].strip(), _API_TOKEN):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "invalid token"})
    return await call_next(request)

_STORE_CACHE_MAX = 8
_stores: OrderedDict[str, SurrealStore] = OrderedDict()
_complete_fn = None

# P28: LLM调用限流(并发上限 + 日调用上限)
_MAX_CONCURRENT = int(os.environ.get("SCRIBE3_MAX_CONCURRENT", "3"))
_DAILY_CALL_CAP = int(os.environ.get("SCRIBE3_DAILY_CALL_CAP", "500"))
_sema = asyncio.Semaphore(_MAX_CONCURRENT)
_day = (time.strftime("%Y-%m-%d"), 0)

def _check_daily():
    global _day
    today = time.strftime("%Y-%m-%d")
    d, n = _day
    if d != today:
        _day = (today, 0)
        d, n = today, 0
    if n >= _DAILY_CALL_CAP:
        raise HTTPException(status_code=429, detail="daily LLM budget exhausted")
    _day = (today, n + 1)


def set_store(store, work: str = "main") -> None:
    """测试注入某书的 store。"""
    _stores[work] = store


def set_complete_fn(fn) -> None:
    global _complete_fn
    _complete_fn = fn


def _store_for(work: str) -> SurrealStore:
    if work not in _stores:
        st = SurrealStore(ns="scribe3", db=work)
        st.apply_schema()
        _stores[work] = st
        while len(_stores) > _STORE_CACHE_MAX:
            _, old = _stores.popitem(last=False)
            old.close()
    else:
        _stores.move_to_end(work)
    return _stores[work]


def _facts(fs, reveal_secret: bool = False):
    def _item(f):
        d = {"id": f.id, "entity": f.entity_id, "attribute": f.attribute,
             "is_secret": f.secret}
        if f.secret and not reveal_secret:
            d["value"] = None   # 私密 value 屏蔽,前端只知"此处有私密"
        else:
            d["value"] = f.value
        return d
    return [_item(f) for f in fs]


def _mask_field(row: dict, field: str, secret_field: str, reveal: bool) -> dict:
    """若 row[secret_field] 为 True 且未解锁,将 row[field] 替换为锁占位符。"""
    if row.get(secret_field) and not reveal:
        row = {**row, field: "🔒 私密"}
    return row


# ===== 书 =====
@app.get("/health")
def health():
    return {"ok": True, "ns": "scribe3"}


@app.get("/works")
def works():
    out = []
    for w in list_works():
        try:
            store = _store_for(w["slug"])
            st = store.stats()
            intent = store.get_intent()
            # 携带 total_word_goal 供书卡进度条使用;None 时前端回退 100000
            if intent.get("total_word_goal") is not None:
                st["total_word_goal"] = intent["total_word_goal"]
        except Exception:
            st = {"chapter_count": 0, "word_count": 0}
        out.append({**w, **st})
    return out


class WorkIn(BaseModel):
    title: str


@app.post("/works")
def make_work(w: WorkIn):
    return create_work(w.title)


@app.patch("/works/{slug}")
def rename(slug: str, w: WorkIn):
    rename_work(slug, w.title)
    return {"ok": True}


@app.delete("/works/{slug}")
def remove_work(slug: str):
    delete_work(slug)
    _stores.pop(slug, None)
    return {"ok": True}


# ===== 读(按书)=====
@app.get("/entities")
def entities(work: str = "main", reveal_secret: bool = False):
    def _entity_dict(e):
        t = e.traits or {}
        row = {
            "id": e.id, "kind": e.kind, "name": e.name,
            "backstory": t.get("backstory"),
            "backstory_secret": t.get("backstory_secret", False),
            "importance": t.get("importance"),
            "appearance": t.get("appearance"),
            "personality_tags": t.get("personality_tags"),
            "aliases": t.get("aliases") or [],
            "personality_detail": t.get("personality_detail"),
            "abilities": t.get("abilities"),
            "weaknesses": t.get("weaknesses"),
            "first_appearance": t.get("first_appearance"),
            "surface_goal": t.get("surface_goal"),
            "deep_need": t.get("deep_need"),
            "internal_conflict": t.get("internal_conflict"),
            "fear": t.get("fear"),
        }
        if e.kind == "character":
            row = _mask_field(row, "backstory", "backstory_secret", reveal_secret)
        return row
    return [_entity_dict(e) for e in _store_for(work).all_entities()]


@app.get("/facts")
def facts(chapter: int = Query(ge=1), work: str = "main"):
    return _facts(_store_for(work).facts_at(chapter))


@app.get("/events")
def events(chapter: int = Query(ge=1), work: str = "main"):
    return [{"id": ev.id, "type": ev.type, "chapter": ev.story_time, "goal": ev.motivated_by_goal}
            for ev in _store_for(work).events_at(chapter)]


@app.get("/timeline")
def timeline(ch_from: int = Query(default=1, ge=1),
             ch_to: int | None = Query(default=None, ge=1),
             work: str = "main"):
    """时间线工艺视图(F-02):返回 [ch_from, ch_to] 区间内按章排序的事件条目。
    作者全知视图,无限知门控。MVP 仅含 events 泳道。"""
    st = _store_for(work)
    items = st.timeline(ch_from, ch_to)
    max_ch = st.max_chapter()
    return {
        "from": ch_from,
        "to": ch_to if ch_to is not None else max_ch,
        "max_chapter": max_ch,
        "items": items,
    }


@app.get("/frame")
def frame(focalizer: str, chapter: int = Query(ge=1), work: str = "main"):
    return _facts(project_frame(_store_for(work), focalizer, chapter).facts)


@app.get("/irony")
def irony(focalizer: str, chapter: int = Query(ge=1), work: str = "main"):
    return _facts(dramatic_irony(_store_for(work), focalizer, chapter))


@app.get("/causal")
def causal(chapter: int = Query(ge=1), work: str = "main"):
    return [{"event": v.event_id, "reason": v.reason} for v in causal_complete(_store_for(work), chapter)]


@app.get("/recall")
def recall(q: str, k: int = Query(default=5, ge=1, le=50), work: str = "main"):
    return _facts(_store_for(work).semantic_recall(q, k))


@app.get("/promises")
def promises(work: str = "main"):
    """P3-e1 Fix 1: 每条 promise 携带 overdue 字段(backend 单源,前端直读)。"""
    st = _store_for(work)
    proms = st.list_promises()
    mc = st.max_chapter()
    intent = st.get_intent()
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    for p in proms:
        p["overdue"] = _overdue_flag(p, mc, slack)
    return proms


@app.get("/promises/ledger")
def promises_ledger(work: str = "main"):
    """作者工具 F-03 伏笔台账(单源):三栏(open/closed/red_herring)+ 每条
    setup/payoff/overdue/跨度 + open/close bracket 完整性审计。
    overdue 阈值同 /promises、/quality(_overdue_flag 单源)。"""
    st = _store_for(work)
    intent = st.get_intent()
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    return st.promise_ledger(slack)


@app.get("/motifs")
def motifs(work: str = "main"):
    return _store_for(work).list_motifs()


# ===== 设定库 增删改(作者直编,不经 elicitation;非世界状态级别的 agent 写)=====
class CharIn(BaseModel):
    name: str
    backstory: str | None = None
    backstory_secret: bool = False
    importance: str | None = None
    appearance: str | None = None
    personality_detail: str | None = None
    personality_tags: list[str] = []
    aliases: list[str] = []
    abilities: str | None = None
    weaknesses: list = []
    surface_goal: str | None = None
    deep_need: str | None = None
    internal_conflict: str | None = None
    fear: str | None = None
    first_appearance: int | None = None


@app.post("/characters")
def add_char(c: CharIn, work: str = "main"):
    _store_for(work).add_entity(Entity(
        f"role:{c.name}", "character", c.name,
        traits={"backstory": c.backstory, "backstory_secret": c.backstory_secret,
                "personality_tags": c.personality_tags, "aliases": c.aliases}))
    return {"ok": True, "oid": f"role:{c.name}"}


@app.patch("/characters/{local}")
def edit_char(local: str, c: CharIn, work: str = "main"):
    st = _store_for(work)
    fields = {"name": c.name, "backstory": c.backstory, "backstory_secret": c.backstory_secret,
              "importance": c.importance,
              "appearance": c.appearance, "personality_detail": c.personality_detail,
              "abilities": c.abilities, "weaknesses": c.weaknesses,
              "surface_goal": c.surface_goal, "deep_need": c.deep_need,
              "internal_conflict": c.internal_conflict, "fear": c.fear,
              "first_appearance": c.first_appearance}
    st.update_record(f"role:{local}", {k: v for k, v in fields.items() if v is not None})
    return {"ok": True}


@app.delete("/characters/{local}")
def del_char(local: str, work: str = "main"):
    _store_for(work).delete_record(f"role:{local}")
    return {"ok": True}


class FactIn(BaseModel):
    entity: str
    attribute: str
    value: str
    valid_from: int = 1
    valid_to: int | None = None
    secret: bool = False
    leak_markers: list[str] = []


@app.post("/facts")
def add_fact_ep(f: FactIn, work: str = "main"):
    import uuid
    oid = f"fact:{uuid.uuid4().hex[:8]}"
    _store_for(work).add_fact(Fact(oid, f.entity, f.attribute, f.value, f.valid_from,
                                   valid_to=f.valid_to, secret=f.secret,
                                   leak_markers=f.leak_markers))
    return {"ok": True, "oid": oid}


@app.patch("/facts/{local}")
def edit_fact(local: str, f: FactIn, work: str = "main"):
    st = _store_for(work)
    st.update_record(f"fact:{local}", {
        "entity_id": f.entity,
        "attribute": f.attribute,
        "value": f.value,
        "valid_from": f.valid_from,
        "valid_to": f.valid_to,
        "secret": f.secret,
        "leak_markers": f.leak_markers,
    })
    # value 变更后重建 embedding,保持语义召回向量与当前值对齐
    try:
        st.semantic_index(f"fact:{local}", f.value)
    except Exception as _e:
        logging.getLogger("scribe3.app").warning(
            "edit_fact: 重建 embedding 失败,命题 fact:%s 将指向旧向量: %s", local, _e)
    return {"ok": True}


@app.delete("/facts/{local}")
def del_fact(local: str, work: str = "main"):
    _store_for(work).delete_record(f"fact:{local}")
    return {"ok": True}


class SupersedeIn(BaseModel):
    entity_id: str
    attribute: str
    value: str
    since_chapter: int
    secret: bool = False


@app.post("/facts/supersede")
def supersede_fact_ep(s: SupersedeIn, work: str = "main"):
    new_oid = _store_for(work).supersede_fact(
        s.entity_id, s.attribute, s.value, s.since_chapter, secret=s.secret)
    return {"ok": True, "oid": new_oid}


class ForgetIn(BaseModel):
    knower_id: str
    proposition_id: str
    until_chapter: int


@app.post("/knowledge/forget")
def forget_knowledge_ep(f: ForgetIn, work: str = "main"):
    _store_for(work).forget_knowledge(f.knower_id, f.proposition_id, f.until_chapter)
    return {"ok": True}


class PromIn(BaseModel):
    text: str
    setup_chapter: int = 1
    promise_kind: str = "promise"


@app.post("/promises-new")
def add_prom(p: PromIn, work: str = "main"):
    _store_for(work).plant_promise(p.text, p.setup_chapter, kind=p.promise_kind)
    return {"ok": True}


@app.patch("/promises/{pid}")
def edit_prom(pid: str, p: PromIn, work: str = "main"):
    _store_for(work).update_promise(pid, {"text": p.text, "setup_chapter": p.setup_chapter, "kind": p.promise_kind})
    return {"ok": True}


@app.delete("/promises/{pid}")
def del_prom(pid: str, work: str = "main"):
    _store_for(work).delete_promise(pid)
    return {"ok": True}


class AdvanceIn(BaseModel):
    payoff_chapter: int


@app.post("/promises/{pid}/advance")
def advance_prom(pid: str, body: AdvanceIn, work: str = "main"):
    """回收伏笔(作者直编):标 closed + payoff_chapter。payoff≥setup 校验。"""
    try:
        _store_for(work).advance_promise(pid, body.payoff_chapter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.post("/promises/{pid}/mark-herring")
def mark_herring(pid: str, work: str = "main"):
    """将伏笔标记为障眼法(red_herring)。"""
    try:
        _store_for(work).mark_promise_herring(pid)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


class ClueIn(BaseModel):
    note: str
    chapter: int


@app.post("/promises/{pid}/clues")
def add_promise_clue(pid: str, body: ClueIn, work: str = "main"):
    """追加草蛇灰线中途线索到某条伏笔。body:{note, chapter}。"""
    try:
        _store_for(work).add_promise_clue(pid, body.note, body.chapter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


@app.delete("/promises/{pid}/clues/{idx}")
def remove_promise_clue(pid: str, idx: int, work: str = "main"):
    """按下标(0-based)删除某条伏笔的线索。"""
    try:
        _store_for(work).remove_promise_clue(pid, idx)
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


# ===== 世界规则 + 势力(设定完整性)=====
class RuleIn(BaseModel):
    name: str
    category: str = "magic"
    source: str | None = None
    capabilities: list = []
    cost: str | None = None
    limitations: list = []
    exceptions: list = []
    scope: str = "global"
    established_chapter: int | None = None
    note: str | None = None


@app.get("/world-rules")
def list_rules(category: str | None = None, work: str = "main"):
    return _store_for(work).list_world_rules(category)


@app.post("/world-rules")
def add_rule(r: RuleIn, work: str = "main"):
    _store_for(work).add_world_rule(r.name, r.category, r.source, r.capabilities, r.cost,
                                     r.limitations, r.exceptions, r.scope,
                                     r.established_chapter, r.note)
    return {"ok": True}


@app.delete("/world-rules")
def del_rule(name: str, work: str = "main"):
    _store_for(work).delete_world_rule(name)
    return {"ok": True}


class FactionIn(BaseModel):
    name: str
    status: str = "active"
    ideology: str | None = None
    leader: str | None = None
    known_members: list = []
    public_face: str | None = None
    private_operation: str | None = None
    private_operation_secret: bool = False
    first_mention_chapter: int | None = None


@app.get("/factions")
def list_factions(work: str = "main", reveal_secret: bool = False):
    rows = _store_for(work).list_factions()
    return [_mask_field(dict(r), "private_operation", "private_operation_secret", reveal_secret)
            for r in rows]


@app.post("/factions")
def add_faction_ep(fc: FactionIn, work: str = "main"):
    _store_for(work).add_faction(fc.name, fc.ideology, fc.status, fc.leader,
                                  fc.known_members, fc.public_face,
                                  fc.private_operation, fc.first_mention_chapter,
                                  fc.private_operation_secret)
    return {"ok": True}


@app.delete("/factions")
def del_faction(name: str, work: str = "main"):
    _store_for(work).delete_faction(name)
    return {"ok": True}


@app.get("/setting-completeness")
def setting_completeness(work: str = "main"):
    return _store_for(work).setting_completeness()


# ===== 物品/道具 + 术语(设置完整性)=====
@app.get("/items")
def list_items_endpoint(state: str | None = None, work: str = "main"):
    return _store_for(work).list_items(state)


@app.post("/items")
def add_item_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_item(req.get("name",""), category=req.get("category"),
                description=req.get("description"), current_owner=req.get("current_owner"),
                symbolic_state=req.get("symbolic_state","active"),
                special_properties=req.get("special_properties"),
                first_chapter=req.get("first_chapter"))
    return {"ok": True}


@app.delete("/items")
def delete_item_endpoint(name: str, work: str = "main"):
    _store_for(work).delete_item(name)
    return {"ok": True}


@app.get("/terms")
def list_terms_endpoint(work: str = "main"):
    return _store_for(work).list_terms()


@app.post("/terms")
def add_term_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_term(req.get("name",""), category=req.get("category"),
                definition=req.get("definition"), aliases=req.get("aliases"),
                first_mention_chapter=req.get("first_mention_chapter"))
    return {"ok": True}


@app.delete("/terms")
def delete_term_endpoint(name: str, work: str = "main"):
    _store_for(work).delete_term(name)
    return {"ok": True}


@app.get("/character-relations")
def character_relations(chapter: int | None = None, work: str = "main"):
    st = _store_for(work)
    if chapter:
        return st.relations_at(chapter)
    return st.relations_at(9999)


@app.post("/character-relations")
def add_character_relation_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_character_relation(req["src"], req["dst"], req["relation"],
                              req["since_chapter"], req.get("note"))
    return {"ok": True}


@app.post("/character-relations/evolve")
def evolve_relation_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.evolve_relation(req["src"], req["dst"], req["relation"],
                       req["since_chapter"], req.get("note"))
    return {"ok": True}


@app.post("/character-relations/end")
def end_relation_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.end_relation(req["src"], req["dst"], req["until_chapter"])
    return {"ok": True}


@app.get("/char-states")
def char_states(character_id: str, work: str = "main"):
    return _store_for(work).list_char_states(character_id)


@app.post("/char-states")
def add_char_state_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_char_state(req["character_id"], req["chapter"], req["change_type"],
                      req["summary"],
                      before_state=req.get("before_state"),
                      after_state=req.get("after_state"),
                      trigger_event=req.get("trigger_event"),
                      arc_phase=req.get("arc_phase"),
                      affects_voice=req.get("affects_voice"),
                      confidence=req.get("confidence", "confirmed"))
    return {"ok": True}


@app.get("/char-state-at")
def char_state_at(character_id: str, chapter: int, work: str = "main"):
    """查询角色在某章时刻的完整状态快照(时点查询,设计文档 §3.6)。
    返回该章时刻的能力/关系/性格/弧光阶段。"""
    return _store_for(work).char_state_at(character_id, chapter)



class MotifIn(BaseModel):
    name: str
    theme: str = ""
    echoes: str = ""
    unfolding: str = ""


@app.post("/motifs-new")
def add_motif_ep(m: MotifIn, work: str = "main"):
    _store_for(work).add_motif(m.name, m.theme, m.echoes, m.unfolding)
    return {"ok": True}


@app.patch("/motifs/{mid}")
def edit_motif(mid: str, m: MotifIn, work: str = "main"):
    _store_for(work).update_motif(mid, {"name": m.name, "theme": m.theme, "echoes": m.echoes,
                                        "unfolding": m.unfolding})
    return {"ok": True}


@app.delete("/motifs/{mid}")
def del_motif(mid: str, work: str = "main"):
    _store_for(work).delete_motif(mid)
    return {"ok": True}


@app.get("/voice-flags")
def voice_flags(work: str = "main"):
    return _store_for(work).list_voice_flags("open")


@app.post("/voice-flags/{fid}/resolve")
def resolve_voice_flag_endpoint(fid: str, work: str = "main"):
    """关闭声音演变 flag(status: open → done)。"""
    _store_for(work).resolve_voice_flag(fid)
    return {"ok": True}


@app.post("/voice-flags/fold")
def fold_voice_flags_endpoint(body: dict, work: str = "main"):
    """半自动声音演变折叠:把角色的 open voice_evolution_flag 折叠进 voice_profile(LLM 演变)。
    body: {"character_id": "role:xxx"}
    返回: {"folded": n, "profile": {...}} 或 {"folded": 0, "degraded": true}
    """
    character_id = body.get("character_id", "")
    if not character_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="character_id 必填")
    from scribe3.llm import hermes_complete
    return _store_for(work).fold_voice_flags(character_id, hermes_complete)


@app.get("/graph")
def graph(chapter: int | None = None, work: str = "main"):
    """知识图谱:角色/命题节点 + knows 边(Atlas 视图)。"""
    return _store_for(work).graph(chapter)


@app.get("/quality")
def quality(work: str = "main"):
    """质量仪表盘聚合:每章 字数/双层QC问题/因果违规 + 伏笔状态。
    P3-e1 Fix 1: 使用 OVERDUE_SLACK 模块常量(唯一真源),支持 intent.overdue_threshold 覆盖;
    foreshadow.promises 含每条 promise 的 overdue 字段,前端直读,不重算。"""
    from scribe3.critique import quality_flags
    st = _store_for(work)
    per = []
    for c in st.list_chapters():
        full = st.get_chapter(c["seq"]) or {}
        prose = full.get("prose", "")
        qf = quality_flags(prose)
        per.append({
            "seq": c["seq"], "title": c["title"],
            "word_count": len("".join(prose.split())),
            "qc_issues": (len(qf["repetition"]) + len(qf["structural"]) + len(qf["purple"])
                          + len(qf["ai_tics"]) + len(qf["oversaturation"])),
            "qc_breakdown": {
                "repetition": len(qf["repetition"]),
                "structural": len(qf["structural"]),
                "purple": len(qf["purple"]),
                "ai_tics": len(qf["ai_tics"]),
                "oversaturation": len(qf["oversaturation"]),
            },
            "causal": len(causal_complete(st, c["seq"])),
        })
    proms = st.list_promises()
    mc = st.max_chapter()
    # 单源阈值:intent 可覆盖 OVERDUE_SLACK(per-work 配置)
    intent = st.get_intent()
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    prom_list = []
    for p in proms:
        is_overdue = _overdue_flag(p, mc, slack)
        prom_list.append({
            "id": p.get("id"), "text": p.get("text", ""),
            "setup_chapter": p.get("setup_chapter"), "status": p["status"],
            "kind": p.get("kind"), "overdue": is_overdue,
        })
    fore = {
        "open": sum(1 for p in proms if p["status"] == "open"),
        "closed": sum(1 for p in proms if p["status"] == "closed"),
        "overdue": sum(1 for p in prom_list if p["overdue"]),
        "promises": prom_list,
    }
    return {"chapters": per, "foreshadow": fore, "total_words": sum(c["word_count"] for c in per)}


@app.get("/intent")
def get_intent(work: str = "main"):
    return _store_for(work).get_intent()


class IntentIn(BaseModel):
    reader_feeling: str = ""
    emotional_arc: str = ""
    red_lines: str = ""
    overdue_threshold: int | None = None
    total_word_goal: int | None = None   # 整稿目标字数;None → 前端回退默认 100000
    daily_word_goal: int | None = None   # 每日目标字数;None → 不显示每日进度


@app.put("/intent")
def put_intent(i: IntentIn, work: str = "main"):
    _store_for(work).set_intent(i.model_dump())
    return {"ok": True}


@app.get("/progress")
def get_progress(work: str = "main"):
    """日字数序列 + 累计曲线 + streak + 目标完成度(只读,数据源 daily_progress 表)。"""
    return _store_for(work).progress()


def _editor_system(st) -> str:
    """主编对话的系统提示:注入本书北极星 + 角色 + 已确立设定(主编全知,含私密)。"""
    intent = st.get_intent()
    chars = st.characters()
    facts = st.facts_at(99999)
    ctx_chars = "、".join(c.name for c in chars[:14]) or "(尚无角色)"
    lines = [f"- {f.entity_id} · {f.attribute}:{f.value}" + ("(私密/伏线)" if f.secret else "")
             for f in facts[:28]]
    ctx_set = "\n".join(lines) or "(尚无设定)"
    # 开着的伏笔:预注入强提醒(易忘项;母题/事件等详情留主编按需调工具查)
    promises = st.open_promises() if hasattr(st, "open_promises") else []
    rem = ""
    if promises:
        items = "；".join(
            f"第{p.get('setup_chapter')}章埋:{(p.get('text') or '')[:30]}" for p in promises[:6])
        rem = f"\n【⚠ 开着的承诺线·勿忘(适时推进/回收,别让它凭空消失)】{items}"
    return (
        "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
        f"【北极星·作品意图】读者感受:{intent['reader_feeling'] or '—'};"
        f"情感弧:{intent['emotional_arc'] or '—'};绝不背叛的红线:{intent['red_lines'] or '—'}\n"
        f"【主要角色】{ctx_chars}\n【已确立设定(你全知,含私密伏线)】\n{ctx_set}\n\n"
        "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;紧扣上面的世界观与北极星,"
        "不空泛、不正确的废话;给剧情/人物建议时给出 2-3 个选项与各自代价;护住限知叙事(别让角色知道其知识帧外的私密)。"
    ) + rem


@app.get("/chat/stream")
def chat_stream(msg: str, work: str = "main"):
    """主编对话(SSE 流式)。注入本书设定上下文,经 Hermes 逐字回流。"""
    from scribe3.llm import hermes_complete_stream
    sysmsg = _editor_system(_store_for(work))

    def gen():
        try:
            for delta in hermes_complete_stream(msg, system=sysmsg):
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:  # 失败如实回流,不静默
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")


_responses_events = None  # 测试可 monkeypatch


@app.get("/chat/agentic-stream")
def chat_agentic_stream(msg: str, work: str = "main"):
    """主编 agentic 对话(SSE):经 scribe3 网关 /v1/responses,主编自调 s3_ 工具查 SurrealDB 真实数据。
    事件:tool(工具调用提示)/delta(回复片段)/done。注:MCP 连 db=main,agentic 当前以主参照库为准。"""
    from scribe3.llm import hermes_responses_events
    fn = _responses_events or hermes_responses_events
    instructions = _editor_system(_store_for(work)) + (
        "\n\n你能调用 s3_ 工具实时查询/操作这部书的 SurrealDB(知识帧 s3_project_frame、反讽 s3_dramatic_irony、"
        "伏笔 s3_list_promises、母题 s3_list_motifs、章节 s3_get_chapter、确定性QC s3_qc_chapter、纪律判官 "
        "s3_discipline_check、语义召回 s3_semantic_recall、因果 s3_causal_complete 等)。"
        "回答前先用只读工具核实真实数据,不臆测;引用数据时说明来自哪个工具。"
        "写操作(加角色/事实/伏笔等)会进入待批,不会立即生效。"
    )

    def gen():
        try:
            for ev in fn(msg, instructions):
                t = ev.get("type", "")
                if t == "response.output_text.delta":
                    d = ev.get("delta", "")
                    if d:
                        yield f"data: {json.dumps({'delta': d}, ensure_ascii=False)}\n\n"
                elif t == "response.output_item.added":
                    item = ev.get("item", {}) or {}
                    if item.get("type") == "function_call":
                        yield f"data: {json.dumps({'tool': item.get('name', ''), 'tool_args': item.get('arguments', '')}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")


def _editor_write_system(st) -> str:
    return _editor_system(st) + (
        "\n\n你是这部小说的主编,以**作者视角**帮作者写/改这本书的手稿——作者在写一本书,"
        "不是从某个角色的受限视角做渲染。\n\n"
        "## 核心判断:讨论 vs 动稿\n"
        "- 若作者只是讨论/提问/点评/分析/给意见 → **纯文字回复,绝对禁止输出 ⟦PROPOSAL⟧ 围栏**。\n"
        "- **仅当**作者明确使用「写/改/续写/帮我写/重写/把这段…/本章这样展开」等写作动词,\n"
        "  或作者提供了角色演绎草稿请求成文时 → 先简短说一句你的处理思路,"
        "然后把**书的本章正文**放进围栏:\n"
        "  (scope 取 chapter=整章 / selection=改选中段 / append=续写接在后面)\n"
        "  ⟦PROPOSAL scope=chapter⟧\n  （书的正文，作者笔调，纯散文，不要解说）\n  ⟦/PROPOSAL⟧\n"
        "- **多候选**:当作者对某段改写要求「2-3 个候选/几个版本/不同侧重」时,**连续输出 2-3 个独立的**\n"
        "  ⟦PROPOSAL scope=selection⟧…⟦/PROPOSAL⟧ 围栏,每个是对同一段的不同改法(如:一个收紧、"
        "一个加潜台词、一个换感官切入),围栏之间可不写解说。其余情况只出一个围栏。\n\n"
        "## 写作规则\n"
        "- 若作者给了某角色的「演绎草稿」(那角色这一场的限知体验)作为素材,把它**织进**书的叙事。\n"
        "- 尊重已确立设定/伏笔/北极星意图。默认作者视角(可全知);仅当作者明确指定本章跟某焦点者的"
        "限知走时,叙事才贴该视角、不写他不知道的私密。\n\n"
        "## 文风基准:贴《乱世铜炉》(志怪笔记体)——两条硬要求\n"
        "1. **古白话语体**:句子要带旧白话的筋骨与风物实词,少用现代抽象/翻译腔。多用'端的、岂料、怎禁得、"
        "却原来、一径、约莫'这类词;状物用具体名物(花脚毛驴、青骡子、喜糕、水酒)而非笼统形容。"
        "**禁**'像散了一地的骨头''张牙舞爪'这类用力过猛的现代文学比喻——冷笔、素描,信物自身说话。\n"
        "2. **世界密度(乱世铜炉的命门)**:每章须织入与主线无关、却让世界活起来的市井风物侧笔——"
        "婚丧社戏的张罗、乡邻帮衬、打更人讨水酒、行当忌讳、节庆吃食。别一上来直奔情节;让村镇先有烟火气,"
        "妖异方有依附。范例语感(仅供体感,勿照抄字句):\n"
        "  「" + _LUANSHI_EXEMPLAR + "」\n"
        "  ——注意它如何用一整段写婚宴的杀猪宰羊、姑嫂蒸糕、打更人讨酒,世界先活,事件才落地。"
    )


_LUANSHI_EXEMPLAR = (
    "看着贺客如潮，满日不绝，韩诤喜不自禁，顾不得年迈体衰，趁着兴头，频频把盏敬客，岂料同村几个毛头小伙"
    "喝发了兴，见主人尽欢，也都意气风发起来，一再持酒相劝。眼看着月儿西移，打更的刘时喜在门口来回好几遭了，"
    "讨了好几杯水酒喝。"
)


_WRITE_VERB_RE = re.compile(
    r"写|改|续写|帮我写|重写|把这段|本章|展开|写出来|写一段|续到"
)

_FALLBACK_MIN_CHARS = 120  # 兜底散文最短字数阈值(更短的视为讨论)


def _is_write_intent(msg) -> bool:
    """检测用户消息是否含写作动词(镜像 _editor_write_system 的围栏触发规则)。
    msg 可以是 str 或 list(含图片的 content 块)。"""
    if isinstance(msg, str):
        text = msg
    elif isinstance(msg, list):
        text = " ".join(
            block.get("text", "") if isinstance(block, dict) else ""
            for block in msg
        )
    else:
        text = str(msg)
    return bool(_WRITE_VERB_RE.search(text))


def _stream_write(message, instructions: str, expect_proposal: bool = False):
    """共用的写作 SSE 流生成器(GET/POST 复用,P20 DRY)。
    message: str(纯文本) 或 list(含图片附件)。
    expect_proposal: 若为 True 且模型未输出围栏但散文足够长,在流末尾追加兜底 proposal 事件。"""
    import json as _j
    from scribe3.llm import hermes_responses_events
    from scribe3.proposal import ProposalParser
    fn = _responses_events or hermes_responses_events
    parser = ProposalParser()
    prop = {"scope": None, "prose": []}

    # 兜底追踪状态
    saw_proposal = False
    delta_acc: list[str] = []   # 累积全部 delta 文本,用于兜底长散文

    def drain(events):
        nonlocal saw_proposal
        for kind, val in events:
            if kind == "delta":
                delta_acc.append(val)
                yield f"data: {_j.dumps({'delta': val}, ensure_ascii=False)}\n\n"
            elif kind == "proposal_open":
                saw_proposal = True
                prop["scope"] = val
                yield f"data: {_j.dumps({'proposal_start': {'scope': val}}, ensure_ascii=False)}\n\n"
            elif kind == "proposal_delta":
                prop["prose"].append(val)
                yield f"data: {_j.dumps({'proposal_chunk': {'text': val}}, ensure_ascii=False)}\n\n"
            elif kind == "proposal_close":
                yield f"data: {_j.dumps({'proposal': {'scope': prop['scope'], 'prose': ''.join(prop['prose'])}}, ensure_ascii=False)}\n\n"
                prop["scope"] = None
                prop["prose"] = []

    try:
        for ev in fn(message, instructions):
            t = ev.get("type", "")
            if t == "response.output_text.delta":
                yield from drain(parser.feed(ev.get("delta", "")))
            elif t == "response.output_item.added":
                item = ev.get("item", {}) or {}
                if item.get("type") == "function_call":
                    yield f"data: {_j.dumps({'tool': item.get('name', '')}, ensure_ascii=False)}\n\n"
        yield from drain(parser.flush())
        # 兜底:模型忘写围栏 → 把累积散文包成 chapter 提案末尾推送
        if expect_proposal and not saw_proposal:
            accumulated = "".join(delta_acc)
            if len(accumulated.strip()) >= _FALLBACK_MIN_CHARS:
                yield (
                    f"data: {_j.dumps({'proposal': {'scope': 'chapter', 'prose': accumulated, 'fallback': True}}, ensure_ascii=False)}\n\n"
                )
    except Exception as e:
        yield f"data: {_j.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
    yield 'data: {"done": true}\n\n'


def _avoid_directive(st, chapter: int, lookback: int = 3, top: int = 40) -> str:
    """前 lookback 章独特措辞 → '本章避免逐字复用'系统指令(服务端确定性防跨章复读)。

    根因:单遍长程生成的"复读病"——模型跨章逐字复用自己偏爱的措辞/动作句(实测 10 章共 106 处
    跨章逐字搬运,逐章 QC 全查不到)。把前文招式喂进【系统指令】,生成时就避开,而非事后删。

    lookback=8 覆盖到全书绝大多数前文(此前 =3 时第 7-10 章看不到前段招式→复读回升);
    刻意母题/专名(奈何谷/镇煞钉/大元炼真经…)经 motif_terms 白名单排除,不进 avoid——
    它们本应复现,逼模型回避反而伤质感(乱世铜炉正以母题手法见长)。
    """
    try:
        from scribe3.critique import distinctive_phrases
        allow = st.motif_terms() if hasattr(st, "motif_terms") else None
        avoid, seen = [], set()
        for c in st.recent_proses(chapter, k=lookback):
            for ph in distinctive_phrases(c.get("prose", ""), n=8, top=40, allow=allow):
                if ph not in seen and not ph.startswith("#"):
                    seen.add(ph)
                    avoid.append(ph)
        if not avoid:
            return ""
        return ("\n\n【防跨章复读·硬约束】前文已用过下列 ≥8 字措辞/动作句,本章**严禁逐字复用**——"
                "同一个意思换感官/换喻体/换节奏另写(专有名词与刻意母题可保留,忌的是动作描写与句式的偷懒重打):\n"
                + "、".join(f"「{a}」" for a in avoid[:top]))
    except Exception:
        return ""


def _arc_state_block(st, focalizer: str, chapter: int) -> str:
    """构建焦点者弧光状态块:将角色在当前章节的能力/关系/性格/阶段快照注入续写 prompt。"""
    if not focalizer:
        return ""
    snap = st.char_state_at(focalizer, chapter)
    if not snap:
        return ""
    parts = []
    abilities = snap.get("abilities") or {}
    if abilities:
        parts.append("能力:" + "、".join(f"{k}={v}" for k, v in abilities.items()))
    relations = snap.get("relations") or {}
    if relations:
        parts.append("关系:" + "、".join(f"{k}={v}" for k, v in relations.items()))
    personality = snap.get("personality") or ""
    if personality:
        parts.append("性格:" + str(personality))
    phases = snap.get("arc_phases") or []
    if phases:
        parts.append("当前阶段:" + str(phases[-1].get("phase", "")))
    if not parts:
        return ""
    return (f"\n\n## 本章焦点者弧光状态(写作须贴合)\n"
            f"{focalizer}:" + ";".join(parts))


def _voice_anchor_block(st, focalizer: str = "") -> str:
    """构建声音锚注入块:焦点者完整 voice_profile(含3节死字段) + 所有角色对白声音速记。
    用于 /chat/write 的 instructions 末尾,让生成时已在声而非事后 check_ooc。"""
    parts = []

    # 焦点者声音锚(叙述/内心独白贴这个声音)
    if focalizer:
        vp = st.get_voice_profile(focalizer)
        if vp and vp.get("style_summary"):
            line = (f"\n\n## 本章焦点者声音锚\n"
                    f"叙述与内心独白贴「{focalizer}」的声音:{vp['style_summary']}")
            cp = vp.get("catchphrases")
            if cp and isinstance(cp, list):
                line += f" 口头禅:{'、'.join(str(x) for x in cp if x)}。"
            tr = vp.get("tone_rules")
            if tr and isinstance(tr, list):
                line += f" 语气规则:{'；'.join(str(x) for x in tr if x)}。"
            # P3-d: 注入3个此前未用的声音节点
            im = vp.get("internal_monologue_style")
            if im:
                line += f" 内心独白风格:{im}。"
            sp = vp.get("sentence_patterns")
            if sp and isinstance(sp, dict):
                sp_str = "、".join(f"{k}={v}" for k, v in sp.items() if v)
                if sp_str:
                    line += f" 句式:{sp_str}。"
            voc = vp.get("vocabulary_profile")
            if voc and isinstance(voc, dict):
                voc_str = "、".join(str(v) for v in voc.values() if v)
                if voc_str:
                    line += f" 词汇倾向:{voc_str}。"
            rl = vp.get("reference_lines")
            # P3-e1 Fix 2: reference_lines schema 是 object 但消费时须兼容 dict/list 两种形状
            if rl:
                if isinstance(rl, dict):
                    rl_items = list(rl.values())[:2]
                elif isinstance(rl, list):
                    rl_items = rl[:2]
                else:
                    rl_items = []
                if rl_items:
                    line += f" 参考语感:{'｜'.join(str(x) for x in rl_items if x)}"
            # 声音待演变提示:该角色有 open voice_evolution_flag 时附加
            try:
                flags = st.list_voice_flags("open") or []
                focal_flags = [f for f in flags if f.get("character") == focalizer]
                if focal_flags:
                    reasons = "、".join(
                        str(f.get("reason") or f.get("trigger_chapter") or "")
                        for f in focal_flags if f.get("reason") or f.get("trigger_chapter")
                    )
                    if reasons:
                        line += (f"\n\n## 声音待演变提示\n"
                                 f"{focalizer} 因下列情节声音正在转变,行文可体现这种变化:{reasons}")
            except Exception:
                pass
            parts.append(line)

    # 对白声音速记——所有有 profile 的角色,各自对白在声,别串味
    profiles = st.list_voice_profiles() or []
    digests = []
    for p in profiles[:6]:
        cid = p.get("character_id") or ""
        ss = (p.get("style_summary") or "").strip()
        if cid and ss:
            digests.append(f"{cid}—{ss[:30]}")
    if digests:
        parts.append("\n\n## 登场角色对白声音(各自在声,别串味)\n" + "；".join(digests))

    return "".join(parts)


def _motif_block(st) -> str:
    """构建母题注入块:列出贯穿母题(name/theme/echoes),供生成时主动编织。
    空母题表 → 返回空串。上限 5 条,保持 prompt 紧凑。"""
    motifs = st.list_motifs() or []
    if not motifs:
        return ""
    lines = ["## 贯穿母题(可主动编织)"]
    for m in motifs[:5]:
        name = m.get("name") or ""
        theme = m.get("theme") or ""
        echoes = m.get("echoes") or ""
        if not name:
            continue
        entry = name
        if theme:
            entry += f":{theme}"
        if echoes:
            entry += f"（回声:{echoes}）"
        lines.append(entry)
    if len(lines) <= 1:
        return ""
    return "\n\n" + "\n".join(lines)


def _frame_block(st, focalizer: str, chapter: int) -> str:
    """限知帧注入块:将 focalizer 截至本章确知的事实喂进 prompt(私密 value 屏蔽)。
    物理隔断:帧外的事情物理上进不了这段 prompt,生成时无从写他不知道的内容。"""
    if not focalizer:
        return ""
    try:
        from scribe3.knowledge import project_frame
        frame = project_frame(st, focalizer, chapter)
        masked = _facts(frame.facts, reveal_secret=False)   # secret value → None
        # 仅保留 value 不为 None 的条目(secret=True 且未解锁的被屏蔽掉)
        visible = [f for f in masked if f.get("value") is not None]
        if not visible:
            return ""
        lines = [
            f"- {f.get('entity') or ''}|{f.get('attribute', '')}|{f.get('value', '')}"
            for f in visible[:40]
        ]
        return (
            f"\n\n## 本章焦点者【此刻确知】的事实(限知硬边界)\n"
            f"以下是 {focalizer} 截至第 {chapter} 章所知的全部。"
            "**只能据这些写他的所见所想,严禁写他不知道的事**:\n"
            + "\n".join(lines)
        )
    except Exception:
        return ""


def _recap_block(st, chapter: int) -> str:
    """前情注入块:上一章结尾文字 + 关键事件摘要,让主编接着写时不失忆。"""
    if chapter <= 1:
        return ""
    try:
        parts = []
        prev = st.recent_proses(chapter, k=1)   # seq < chapter 最近1章
        if prev:
            tail = (prev[0].get("prose") or "")[-300:]
            if tail:
                parts.append("上一章结尾:\n" + tail)
        evs = st.events_at(chapter - 1) or []
        if evs:
            ev_summ = "；".join(
                str(e.type or e.motivated_by_goal or "")
                for e in evs[:6] if e
            )
            if ev_summ:
                parts.append("上一章关键事件:" + ev_summ)
        if not parts:
            return ""
        return "\n\n## 前情(接着往下写,别重复已发生的)\n" + "\n\n".join(parts)
    except Exception:
        return ""


def _current_tail_block(st, chapter: int) -> str:
    """续写衔接块:当前章已写部分的末段(~400字),让 append 续写自然接上,不另起炉灶。
    若当前章无 prose(全新章)则返回空串,不干扰全新章的生成。"""
    try:
        ch = st.get_chapter(chapter)
        if not ch:
            return ""
        prose = ch.get("prose") or ""
        tail = prose[-400:].strip()
        if not tail:
            return ""
        return (
            "\n\n## 本章已写到这里(若续写,从此处自然接上,别另起炉灶/别重复)\n" + tail
        )
    except Exception:
        return ""


@app.get("/chat/write")
def chat_write(msg: str, chapter: int = 1, focalizer: str = "", work: str = "main"):
    """对话驱动写作(SSE):主编自判讨论 vs 动稿;动稿用 ⟦PROPOSAL⟧ 围栏回传新散文。
    事件:delta(对话,进右轨)/ tool(工具调用)/ proposal(草稿,进中区)/ done。"""
    from scribe3.craft import build_craft_block
    st = _store_for(work)
    instructions = _editor_write_system(st)
    instructions += f"\n当前第 {chapter} 章。"
    if focalizer:
        instructions += f"作者指定本章跟随焦点者 {focalizer} 的限知视角:贴该角色所知所感写,别写他不知道的私密。"
    else:
        instructions += "本章未指定限知焦点者 → 作者视角(可全知)。"
    instructions += _avoid_directive(st, chapter)
    instructions += _voice_anchor_block(st, focalizer)
    instructions += _arc_state_block(st, focalizer, chapter)
    instructions += _motif_block(st)
    instructions += _frame_block(st, focalizer, chapter)
    instructions += _recap_block(st, chapter)
    instructions += _current_tail_block(st, chapter)
    craft = build_craft_block(st.list_craft_rules() or None)
    if craft:
        instructions += "\n\n" + craft
    instructions += _final_reminder()
    return StreamingResponse(
        _stream_write(msg, instructions, expect_proposal=_is_write_intent(msg)),
        media_type="text/event-stream",
    )


_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGES = 6
_MAX_IMG_BYTES = 5 * 1024 * 1024


class ImageModel(BaseModel):
    data: str
    type: str

    @field_validator("type")
    @classmethod
    def _mime_ok(cls, v: str) -> str:
        if v not in _ALLOWED_MIME:
            raise ValueError(f"unsupported mime: {v}")
        return v

    @field_validator("data")
    @classmethod
    def _size_ok(cls, v: str) -> str:
        import base64
        try:
            raw = base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("invalid base64")
        if len(raw) > _MAX_IMG_BYTES:
            raise ValueError("image too large")
        return v


class ChatWriteReq(BaseModel):
    msg: str
    chapter: int = 1
    focalizer: str = ""
    images: list[ImageModel] = []
    seed_words: list[str] = []   # 浸泡产出的情绪种子词(由前端可选传入),注入写作 prompt

    @field_validator("images")
    @classmethod
    def _count_ok(cls, v: list) -> list:
        if len(v) > _MAX_IMAGES:
            raise ValueError(f"too many images (max {_MAX_IMAGES})")
        return v


def _soak_block(seed_words: list[str]) -> str:
    """浸泡种子词注入块:仅当 seed_words 非空时注入,否则返回空串(不发 LLM,pure-cheap)。
    soak() 需要 LLM 调用,不在写作热路径中自动触发;前端可预先调用 soak 后把 seed_words 传进来。"""
    if not seed_words:
        return ""
    return "\n\n## 情绪种子词(浸泡得出,贴此情绪写)\n" + "、".join(str(w) for w in seed_words)


def _final_reminder() -> str:
    """末尾强化提醒(recency 效应):把两条非谈判性约束放在 instructions 最后,
    对抗多块拼接后关键规则被稀释的注意力漂移。不含新信息,仅复述最高优先级约束。"""
    return (
        "\n\n（再次强调:① 动稿必须用 ⟦PROPOSAL scope=...⟧ 围栏包正文;"
        "② 文风贴乱世铜炉志怪笔记体——古白话、冷笔、世界密度,忌现代翻译腔与用力比喻。）"
    )


@app.post("/chat/write")
def chat_write_post(req: ChatWriteReq, work: str = "main"):
    """POST 版写作对话(支持图片附件):前端用 fetch 流式读取。"""
    from scribe3.craft import build_craft_block
    st = _store_for(work)
    instructions = _editor_write_system(st)
    instructions += f"\n当前第 {req.chapter} 章。"
    if req.focalizer:
        instructions += f"作者指定本章跟随焦点者 {req.focalizer} 的限知视角:贴该角色所知所感写,别写他不知道的私密。"
    else:
        instructions += "本章未指定限知焦点者 → 作者视角(可全知)。"
    instructions += _avoid_directive(st, req.chapter)
    instructions += _voice_anchor_block(st, req.focalizer)
    instructions += _arc_state_block(st, req.focalizer, req.chapter)
    instructions += _motif_block(st)
    instructions += _frame_block(st, req.focalizer, req.chapter)
    instructions += _recap_block(st, req.chapter)
    instructions += _current_tail_block(st, req.chapter)
    instructions += _soak_block(req.seed_words)
    craft = build_craft_block(st.list_craft_rules() or None)
    if craft:
        instructions += "\n\n" + craft
    instructions += _final_reminder()

    if req.images:
        content = [{"type": "input_text", "text": req.msg}]
        for img in req.images:
            content.append({"type": "input_image", "image_url": f"data:{img.get('type','image/jpeg')};base64,{img.get('data','')}"})
        message = [{"role": "user", "content": content}]
    else:
        message = req.msg

    return StreamingResponse(
        _stream_write(message, instructions, expect_proposal=_is_write_intent(req.msg)),
        media_type="text/event-stream",
    )


@app.get("/chapters")
def chapters(work: str = "main"):
    return _store_for(work).list_chapters()


# ===== 大纲/卷章树(手稿支数据层,作者工具 F-01 后端)=====

@app.get("/outline")
def get_outline(work: str = "main"):
    """聚合大纲:卷 + 章(梗概/字数/QC/视角/sort_order/label + 场景数)。
    章按 sort_order 升序;sort_order=NONE 时回退 seq。不回正文全文。"""
    return _store_for(work).outline()


@app.get("/project-tree")
def get_project_tree(work: str = "main"):
    """混合 Binder 项目树(作者工具 F-06):手稿支(卷→章→场景)+ 素材支(分类→条目)
    + 横切视图清单。只读统一投影,只回身份+角标,详情按 ref 懒加载。"""
    return _store_for(work).project_tree()


class ReorderReq(BaseModel):
    volume: str | None = None   # 目标卷裸 id;None = 未分卷区
    order: list[int]            # 该卷内章 seq 的新顺序(全量)


@app.post("/chapters/reorder")
def reorder_chapters(req: ReorderReq, work: str = "main"):
    """拖拽重排:改 sort_order(及 volume),绝不动 seq(故事时间轴主键)。"""
    count = _store_for(work).reorder_chapters(req.volume, req.order)
    return {"status": "reordered", "volume": req.volume, "count": count}


class ChapterMetaReq(BaseModel):
    synopsis: str | None = None
    volume: str | None = None   # 卷裸 id 或 None(置未分卷)
    label: str | None = None
    title: str | None = None


@app.patch("/chapters/{seq}")
def patch_chapter(seq: int, req: ChapterMetaReq, work: str = "main"):
    """改章梗概/卷归属/标签/标题,不碰正文/embedding/qc。"""
    fields = req.model_dump(exclude_none=True)
    ok = _store_for(work).update_chapter_meta(seq, fields)
    if not ok:
        raise HTTPException(status_code=404, detail=f"chapter {seq} not found")
    return {"status": "updated", "seq": seq}


# == 卷 CRUD ==

class VolumeReq(BaseModel):
    title: str = ""
    sort_order: int = 0
    intro: str | None = None
    color: str | None = None


@app.get("/volumes")
def list_volumes(work: str = "main"):
    return _store_for(work).list_volumes()


@app.post("/volumes")
def add_volume(req: VolumeReq, work: str = "main"):
    vid = _store_for(work).add_volume(
        title=req.title, sort_order=req.sort_order,
        intro=req.intro, color=req.color)
    return {"status": "created", "id": vid}


class VolumePatchReq(BaseModel):
    title: str | None = None
    sort_order: int | None = None
    intro: str | None = None
    color: str | None = None


@app.patch("/volumes/{vid}")
def update_volume(vid: str, req: VolumePatchReq, work: str = "main"):
    fields = req.model_dump(exclude_none=True)
    _store_for(work).update_volume(vid, fields)
    return {"status": "updated", "id": vid}


@app.delete("/volumes/{vid}")
def delete_volume(vid: str, work: str = "main"):
    """删卷:该卷下的章 volume 置 NONE(章不删),再删卷记录。"""
    _store_for(work).delete_volume(vid)
    return {"status": "deleted", "id": vid}


@app.get("/chapter")
def get_chapter(seq: int, work: str = "main"):
    return _store_for(work).get_chapter(seq) or {}


@app.get("/qc")
def qc(seq: int, work: str = "main"):
    from scribe3.critique import quality_flags
    ch = _store_for(work).get_chapter(seq)
    return quality_flags(ch["prose"]) if ch else {}


@app.get("/discipline")
def discipline(seq: int, brief: str = "", work: str = "main"):
    from scribe3.critique import discipline_truncate
    from scribe3.llm import hermes_complete
    ch = _store_for(work).get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"ok": True, "violations": []}
    return discipline_truncate(ch["prose"], brief, hermes_complete)


# ===== 写 =====
class SaveChapterReq(BaseModel):
    seq: int
    prose: str
    title: str = ""
    focalizer: str | None = None


class CheckpointReq(BaseModel):
    prose: str
    label: str = ""
    kind: str = "checkpoint"   # checkpoint | final
    qc: dict = {}


class CheckReq(BaseModel):
    prose: str
    focalizer: str = ""


def _bg_ingest(work: str, seq: int) -> None:
    """后台客观回写:开独立 store 连接跑 ingest_chapter。异常只记日志,不影响存稿。"""
    import logging
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    try:
        st = _store_for(work)
        r = ingest_chapter(st, seq, hermes_complete)
        if r.get("parse_failed"):
            logging.getLogger("scribe3").warning(
                "后台 ingest %s 第%s章: LLM 回复解析失败,既有知识已保留(未 purge)", work, seq)
    except Exception as e:
        logging.getLogger("scribe3").warning("后台 ingest %s 第%s章失败: %s", work, seq, e)


@app.post("/save-chapter")
def save_chapter(req: SaveChapterReq, background: BackgroundTasks, work: str = "main"):
    st = _store_for(work)
    st.save_chapter(req.seq, req.prose, title=req.title, focalizer=req.focalizer)
    # 软校验(确定性、快、不打 LLM):QC + 限知泄露。回写走独立 /ingest(前端接受后再调)。
    from scribe3.critique import quality_flags, find_cross_chapter_repetitions
    qf = quality_flags(req.prose)
    # 跨章复读:逐章 QC 查不到的"单遍长程生成典型病"(模型跨章复用偏爱措辞)。
    # 比对前文最近 5 章逐字 ≥8 字重叠——把"重复"从'事后逐章删'升级为'跨章可度量'。
    cross_rep: list[dict] = []
    try:
        priors = [c["prose"] for c in st.recent_proses(req.seq, k=8) if c.get("prose")]
        allow = st.motif_terms() if hasattr(st, "motif_terms") else None
        cross_rep = find_cross_chapter_repetitions(req.prose, priors, n=8, allow=allow)
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning("cross_repetition 失败 work=%s seq=%s: %s", work, req.seq, e)
    leaks, leak_error = None, None
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks
            leaks = len(find_leaks(req.prose, st, req.focalizer, req.seq))
        except Exception as e:
            import logging
            logging.getLogger("scribe3").warning("find_leaks 失败 work=%s seq=%s: %s", work, req.seq, e)
            leak_error = str(e)[:160]
    background.add_task(_bg_ingest, work, req.seq)
    return {"status": "saved", "seq": req.seq,
            "qc": {"repetition": len(qf["repetition"]), "structural": len(qf["structural"]),
                   "purple": len(qf["purple"]), "cross_repetition": len(cross_rep)},
            "cross_repetition_phrases": [h["phrase"] for h in cross_rep[:12]],
            "leaks": leaks, "leak_error": leak_error, "ingesting": True}


@app.post("/dedup-chapter")
def dedup_chapter(seq: int, work: str = "main"):
    """确定性事后跨章改写(QC 的'治'层):定位本章含跨章逐字复读的句子→定向 LLM 改写→存回。

    比'prompt 预防'可靠(实测最严重章跨章复读 30→8,↓73%),契合本系统'确定性扫描+定向改'的纪律。
    幂等:无复读则原样返回、不调 LLM。"""
    st = _store_for(work)
    ch = st.get_chapter(seq)
    if not ch or not ch.get("prose"):
        raise HTTPException(status_code=404, detail="chapter not found")
    from scribe3.critique import rewrite_cross_repetitions
    from scribe3.llm import hermes_complete
    priors = [c["prose"] for c in st.recent_proses(seq, k=8) if c.get("prose")]
    allow = st.motif_terms() if hasattr(st, "motif_terms") else None
    res = rewrite_cross_repetitions(ch["prose"], priors, hermes_complete, n=8, allow=allow)
    if res["rewritten"] > 0:
        st.save_chapter(seq, res["prose"], title=ch.get("title", ""), focalizer=ch.get("focalizer"))
    return {"seq": seq, "rewritten": res["rewritten"],
            "cross_repetition_before": res["before"], "cross_repetition_after": res["after"]}


@app.post("/check")
def check_prose(req: CheckReq, seq: int, work: str = "main"):
    """护栏轻检查:QC + 限知泄露,不落库(改造③ 停笔静默刷新用)。
    F-05: 新增顶层 issues 列表(带 range),兼容旧 qc/leaks 计数字段。"""
    st = _store_for(work)
    from scribe3.critique import quality_flags, quality_issues
    qf = quality_flags(req.prose)
    leaks = []
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks
            leaks = [{"fact_id": lk.fact_id, "marker": lk.marker, "subject": lk.subject,
                      "range": list(lk.range) if lk.range else None}
                     for lk in find_leaks(req.prose, st, req.focalizer, seq)]
        except Exception as e:
            import logging
            logging.getLogger("scribe3").warning("check find_leaks 失败: %s", e)

    # F-05: 组装带 range 的 issues(白送类 QC + leaks)
    issues: list[dict] = []
    try:
        extra = st.purple_patterns() if hasattr(st, "purple_patterns") else None
        issues = quality_issues(req.prose, extra)
    except Exception as e:
        import logging
        logging.getLogger("scribe3").warning("check quality_issues 失败: %s", e)
    # 追加 leak issues
    for lk in leaks:
        issues.append({
            "type": "leak",
            "message": f"限知泄露:视角角色不该知道「{lk['marker']}」",
            "text": lk["marker"],
            "range": lk["range"],
            "meta": {"fact_id": lk["fact_id"], "subject": lk["subject"]},
        })

    return {"qc": {"repetition": len(qf["repetition"]),
                   "structural": len(qf["structural"]),
                   "purple": len(qf["purple"]),
                   "ai_tics": len(qf["ai_tics"]),
                   "oversaturation": len(qf["oversaturation"])},
            "leaks": leaks,
            "issues": issues}


class PostCheckReq(BaseModel):
    prose: str
    focalizer: str = ""
    brief: str = ""


@app.post("/post-check")
def post_check(req: PostCheckReq, seq: int, work: str = "main"):
    """生成后全量体检:五类确定性 QC + 限知泄露 + LLM 语义纪律判(fail-open)。
    不落库。注册为 read-only POST(见 KNOWN_REST_WRITE_ROUTES)。
    F-05: 新增顶层 issues 列表(带 range),兼容旧 quality/leaks 字段。"""
    import logging
    from scribe3.critique import quality_flags, quality_issues, discipline_truncate
    st = _store_for(work)

    # 1. 确定性五类 QC
    qf = quality_flags(req.prose)
    qc_breakdown = {
        "repetition": len(qf["repetition"]),
        "structural": len(qf["structural"]),
        "purple": len(qf["purple"]),
        "ai_tics": len(qf["ai_tics"]),
        "oversaturation": len(qf["oversaturation"]),
    }
    qc_total = sum(qc_breakdown.values())

    # 2. 限知泄露(有 focalizer 才跑)
    leaks: list[dict] = []
    if req.focalizer:
        try:
            from scribe3.verify import find_leaks
            leaks = [{"fact_id": lk.fact_id, "marker": lk.marker, "subject": lk.subject,
                      "range": list(lk.range) if lk.range else None}
                     for lk in find_leaks(req.prose, st, req.focalizer, seq)]
        except Exception as e:
            logging.getLogger("scribe3").warning("post_check find_leaks 失败: %s", e)

    # 3. LLM 语义纪律判(fail-open)
    discipline: dict = {}
    degraded = False
    try:
        # 优先用测试注入的 _complete_fn,否则走真实 hermes_complete
        complete_fn = _complete_fn
        if complete_fn is None:
            from scribe3.llm import hermes_complete
            complete_fn = hermes_complete
        discipline = discipline_truncate(req.prose, req.brief, complete_fn)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check discipline 失败: %s", e)
        degraded = True

    # 4. 设定校验:物品状态/OOC/世界规则/命名一致性(fail-soft)
    setting: list[dict] = []
    try:
        setting = st.validate_setting(seq, req.prose)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check validate_setting 失败: %s", e)

    # F-05: 组装带 range 的顶层 issues(白送类 QC + leaks + discipline.cut_after)
    issues: list[dict] = []
    try:
        extra = st.purple_patterns() if hasattr(st, "purple_patterns") else None
        issues = quality_issues(req.prose, extra)
    except Exception as e:
        logging.getLogger("scribe3").warning("post_check quality_issues 失败: %s", e)
    # leak issues
    for lk in leaks:
        issues.append({
            "type": "leak",
            "message": f"限知泄露:视角角色不该知道「{lk['marker']}」",
            "text": lk["marker"],
            "range": lk["range"],
            "meta": {"fact_id": lk["fact_id"], "subject": lk["subject"]},
        })
    # discipline.cut_after issue(纪律违规起点句)
    if discipline.get("cut_after"):
        cut = discipline["cut_after"]
        idx = req.prose.find(cut)
        rng = [idx, idx + len(cut)] if idx >= 0 else None
        issues.append({
            "type": "discipline",
            "message": f"纪律违规:{'、'.join(discipline.get('violations', []))}",
            "text": cut,
            "range": rng,
            "meta": {"violations": discipline.get("violations", [])},
        })
    # setting issues
    for hint in setting:
        evidence = hint.get("evidence") or ""
        idx = req.prose.find(evidence) if evidence else -1
        rng = [idx, idx + len(evidence)] if idx >= 0 and evidence else None
        issues.append({
            "type": "setting",
            "message": hint.get("description", "设定校验问题"),
            "text": evidence,
            "range": rng,
            "meta": {"entity": hint.get("entity"), "severity": hint.get("severity")},
        })

    return {
        "quality": {**qc_breakdown, "total": qc_total},
        "leaks": leaks,
        "discipline": discipline,
        "degraded": degraded,
        "setting": setting,
        "issues": issues,
    }


@app.post("/checkpoint")
def checkpoint(req: CheckpointReq, seq: int, background: BackgroundTasks, work: str = "main"):
    st = _store_for(work)
    vid = st.add_chapter_version(seq, req.prose, label=req.label,
                                 kind=req.kind, qc=req.qc)
    # kind=final → 这是正式定稿,知识图谱应同步更新(非 final 的草稿快照不 ingest)
    if req.kind == "final":
        background.add_task(_bg_ingest, work, seq)
    return {"status": "saved", "id": vid, "seq": seq, "kind": req.kind}


@app.get("/chapter-versions")
def chapter_versions(seq: int, work: str = "main"):
    return _store_for(work).list_chapter_versions(seq)


@app.get("/chapter-version/{vid}")
def chapter_version(vid: str, work: str = "main"):
    v = _store_for(work).get_chapter_version(vid)
    if not v:
        raise HTTPException(status_code=404, detail="version not found")
    return v


@app.post("/ingest")
def ingest(seq: int, work: str = "main"):
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    return ingest_chapter(_store_for(work), seq, hermes_complete)


@app.get("/ingest-unverified")
def ingest_unverified(status: str = "pending", work: str = "main"):
    return _store_for(work).list_unverified(status)


@app.post("/ingest-unverified/{uid}/accept")
def accept_unverified_ep(uid: str, work: str = "main"):
    from scribe3.llm import hermes_complete
    return _store_for(work).accept_unverified(uid, complete_fn=hermes_complete)


@app.post("/ingest-unverified/{uid}/ignore")
def ignore_unverified_ep(uid: str, work: str = "main"):
    _store_for(work).ignore_unverified(uid)
    return {"ok": True}


_LIVE_TABLES = ["character", "place", "proposition", "event", "knows", "reader_knows",
                "promise", "motif", "chapter"]


_LIVE_MAX = int(os.environ.get("SCRIBE3_LIVE_MAX", "5"))
_live_count: dict[str, int] = {}


@app.get("/live")
async def live(work: str = "main"):
    if _live_count.get(work, 0) >= _LIVE_MAX:
        raise HTTPException(status_code=429, detail=f"too many live connections for {work}")
    _live_count[work] = _live_count.get(work, 0) + 1
    url = os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")
    try:
        return StreamingResponse(live_stream(url, "scribe3", work, _LIVE_TABLES),
                                 media_type="text/event-stream")
    finally:
        _live_count[work] = max(0, _live_count.get(work, 0) - 1)


def main() -> None:
    import uvicorn
    list_works()   # 确保 main 已登记
    uvicorn.run(app, host="127.0.0.1", port=3321)


if __name__ == "__main__":
    main()
