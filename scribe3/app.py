"""scribe3 后端 API(FastAPI,端口 3321)· 多书(一书一 DB)。

每端点按 ?work=<slug> 路由到对应书的 DB(NS=scribe3 / db=slug),store 按书缓存。
/works 列表/新建。读端点直查;/render 走知识帧投影(API 层也不泄露)。生成走 Hermes。
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
import time
from collections import OrderedDict

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.live import live_stream
from scribe3.ontology import Entity, Fact
from scribe3.render import render
from scribe3.store import SurrealStore, create_work, delete_work, list_works, rename_work
from scribe3.verify import causal_complete

app = FastAPI(title="scribe3")
_CORS = os.environ.get("SCRIBE3_CORS_ORIGINS", "http://127.0.0.1:3311,http://localhost:3311")
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


# ===== 书 =====
@app.get("/health")
def health():
    return {"ok": True, "ns": "scribe3"}


@app.get("/works")
def works():
    out = []
    for w in list_works():
        try:
            st = _store_for(w["slug"]).stats()
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
def entities(work: str = "main"):
    def _entity_dict(e):
        t = e.traits or {}
        return {
            "id": e.id, "kind": e.kind, "name": e.name,
            "backstory": t.get("backstory"),
            "importance": t.get("importance"),
            "appearance": t.get("appearance"),
            "personality_tags": t.get("personality_tags"),
            "personality_detail": t.get("personality_detail"),
            "abilities": t.get("abilities"),
            "weaknesses": t.get("weaknesses"),
            "first_appearance": t.get("first_appearance"),
            "surface_goal": t.get("surface_goal"),
            "deep_need": t.get("deep_need"),
            "internal_conflict": t.get("internal_conflict"),
            "fear": t.get("fear"),
        }
    return [_entity_dict(e) for e in _store_for(work).all_entities()]


@app.get("/facts")
def facts(chapter: int = Query(ge=1), work: str = "main"):
    return _facts(_store_for(work).facts_at(chapter))


@app.get("/events")
def events(chapter: int = Query(ge=1), work: str = "main"):
    return [{"id": ev.id, "type": ev.type, "chapter": ev.story_time, "goal": ev.motivated_by_goal}
            for ev in _store_for(work).events_at(chapter)]


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
    return _store_for(work).list_promises()


@app.get("/motifs")
def motifs(work: str = "main"):
    return _store_for(work).list_motifs()


# ===== 设定库 增删改(作者直编,不经 elicitation;非世界状态级别的 agent 写)=====
class CharIn(BaseModel):
    name: str
    backstory: str | None = None
    importance: str | None = None
    appearance: str | None = None
    personality_detail: str | None = None
    abilities: str | None = None
    weaknesses: list = []
    surface_goal: str | None = None
    deep_need: str | None = None
    internal_conflict: str | None = None
    fear: str | None = None
    first_appearance: int | None = None


@app.post("/characters")
def add_char(c: CharIn, work: str = "main"):
    _store_for(work).add_entity(Entity(f"role:{c.name}", "character", c.name, traits={"backstory": c.backstory}))
    return {"ok": True, "oid": f"role:{c.name}"}


@app.patch("/characters/{local}")
def edit_char(local: str, c: CharIn, work: str = "main"):
    st = _store_for(work)
    fields = {"name": c.name, "backstory": c.backstory, "importance": c.importance,
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
    secret: bool = False


@app.post("/facts")
def add_fact_ep(f: FactIn, work: str = "main"):
    import uuid
    oid = f"fact:{uuid.uuid4().hex[:8]}"
    _store_for(work).add_fact(Fact(oid, f.entity, f.attribute, f.value, f.valid_from, secret=f.secret))
    return {"ok": True, "oid": oid}


@app.patch("/facts/{local}")
def edit_fact(local: str, f: FactIn, work: str = "main"):
    _store_for(work).update_record(f"fact:{local}", {"entity": f.entity, "attribute": f.attribute,
                                                     "value": f.value, "secret": f.secret})
    return {"ok": True}


@app.delete("/facts/{local}")
def del_fact(local: str, work: str = "main"):
    _store_for(work).delete_record(f"fact:{local}")
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


# ===== 世界规则 + 势力(设定完整性)=====
class RuleIn(BaseModel):
    name: str
    category: str = "magic"
    source: str | None = None
    cost: str | None = None
    scope: str = "global"
    note: str | None = None


@app.get("/world-rules")
def list_rules(category: str | None = None, work: str = "main"):
    return _store_for(work).list_world_rules(category)


@app.post("/world-rules")
def add_rule(r: RuleIn, work: str = "main"):
    _store_for(work).add_world_rule(r.name, r.category, r.source, cost=r.cost, scope=r.scope, note=r.note)
    return {"ok": True}


@app.delete("/world-rules")
def del_rule(name: str, work: str = "main"):
    _store_for(work).delete_world_rule(name)
    return {"ok": True}


class FactionIn(BaseModel):
    name: str
    ideology: str | None = None
    leader: str | None = None
    public_face: str | None = None
    private_operation: str | None = None
    status: str = "active"


@app.get("/factions")
def list_factions(work: str = "main"):
    return _store_for(work).list_factions()


@app.post("/factions")
def add_faction(f: FactionIn, work: str = "main"):
    _store_for(work).add_faction(f.name, f.ideology, f.status, f.leader,
                                  public_face=f.public_face, private_operation=f.private_operation)
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
                special_properties=req.get("special_properties"))
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
                definition=req.get("definition"), aliases=req.get("aliases"))
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


@app.get("/char-states")
def char_states(character_id: str, work: str = "main"):
    return _store_for(work).list_char_states(character_id)


@app.post("/char-states")
def add_char_state_endpoint(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_char_state(req["character_id"], req["chapter"], req["change_type"],
                      req["summary"], arc_phase=req.get("arc_phase"))
    return {"ok": True}


@app.get("/char-state-at")
def char_state_at(character_id: str, chapter: int, work: str = "main"):
    """查询角色在某章时刻的完整状态快照(时点查询,设计文档 §3.6)。
    返回该章时刻的能力/关系/性格/弧光阶段。"""
    return _store_for(work).char_state_at(character_id, chapter)


# ===== 世界规则 + 势力(设定完整性)=====
class RuleIn(BaseModel):
    name: str
    category: str = "magic"
    source: str | None = None
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
    _store_for(work).add_world_rule(r.name, r.category, r.source, None, r.cost,
                                     r.limitations, r.exceptions, r.scope,
                                     r.established_chapter, r.note)
    return {"ok": True}


@app.delete("/world-rules")
def del_rule(name: str, work: str = "main"):
    _store_for(work).delete_world_rule(name)
    return {"ok": True}


class FactionIn(BaseModel):
    name: str
    ideology: str | None = None
    leader: str | None = None
    known_members: list = []
    public_face: str | None = None
    private_operation: str | None = None
    first_mention_chapter: int | None = None


@app.get("/factions")
def list_factions(work: str = "main"):
    return _store_for(work).list_factions()


@app.post("/factions")
def add_faction_ep(fc: FactionIn, work: str = "main"):
    _store_for(work).add_faction(fc.name, fc.ideology, "active", fc.leader,
                                  fc.known_members, fc.public_face,
                                  fc.private_operation, fc.first_mention_chapter)
    return {"ok": True}


@app.delete("/factions")
def del_faction(name: str, work: str = "main"):
    _store_for(work).delete_faction(name)
    return {"ok": True}


# ===== 世界规则 + 势力(层1 设定完整性)=====
@app.get("/world-rules")
def get_world_rules(category: str | None = None, work: str = "main"):
    return _store_for(work).list_world_rules(category)


@app.post("/world-rules")
def add_world_rule(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_world_rule(req.get("name",""), req.get("category","social"),
                      source=req.get("source"), cost=req.get("cost"),
                      limitations=req.get("limitations"), exceptions=req.get("exceptions"),
                      scope=req.get("scope","global"), note=req.get("note"))
    return {"ok": True}


@app.delete("/world-rules")
def del_world_rule(name: str, work: str = "main"):
    _store_for(work).delete_world_rule(name)
    return {"ok": True}


@app.get("/factions")
def get_factions(work: str = "main"):
    return _store_for(work).list_factions()


@app.post("/factions")
def add_faction(req: dict, work: str = "main"):
    st = _store_for(work)
    st.add_faction(req.get("name",""), ideology=req.get("ideology"),
                   leader=req.get("leader"), known_members=req.get("known_members"),
                   public_face=req.get("public_face"),
                   private_operation=req.get("private_operation"))
    return {"ok": True}


@app.delete("/factions")
def del_faction(name: str, work: str = "main"):
    _store_for(work).delete_faction(name)
    return {"ok": True}


@app.get("/setting-completeness")
def get_completeness(work: str = "main"):
    return _store_for(work).setting_completeness()


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


class VoiceIn(BaseModel):
    character: str
    voice_kind: str
    text: str
    since_chapter: int = 0


@app.post("/voice")
def add_voice(v: VoiceIn, work: str = "main"):
    _store_for(work).add_voice_sample(v.character, v.voice_kind, v.text, v.since_chapter)
    return {"ok": True}


@app.get("/voice")
def get_voice(character: str, work: str = "main"):
    return _store_for(work).list_voice_samples(character)


@app.get("/voice-flags")
def voice_flags(work: str = "main"):
    return _store_for(work).list_voice_flags("open")


@app.get("/graph")
def graph(chapter: int | None = None, work: str = "main"):
    """知识图谱:角色/命题节点 + knows 边(Atlas 视图)。"""
    return _store_for(work).graph(chapter)


@app.get("/quality")
def quality(work: str = "main"):
    """质量仪表盘聚合:每章 字数/双层QC问题/因果违规 + 伏笔状态。"""
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
            "qc_issues": len(qf["repetition"]) + len(qf["structural"]) + len(qf["purple"]),
            "causal": len(causal_complete(st, c["seq"])),
        })
    proms = st.list_promises()
    mc = st.max_chapter()
    fore = {
        "open": sum(1 for p in proms if p["status"] == "open"),
        "closed": sum(1 for p in proms if p["status"] == "closed"),
        "overdue": sum(1 for p in proms if p["status"] == "open" and p["setup_chapter"] + 3 < mc),
    }
    return {"chapters": per, "foreshadow": fore, "total_words": sum(c["word_count"] for c in per)}


@app.get("/intent")
def get_intent(work: str = "main"):
    return _store_for(work).get_intent()


class IntentIn(BaseModel):
    reader_feeling: str = ""
    emotional_arc: str = ""
    red_lines: str = ""


@app.put("/intent")
def put_intent(i: IntentIn, work: str = "main"):
    _store_for(work).set_intent(i.model_dump())
    return {"ok": True}


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
        "  ⟦PROPOSAL scope=chapter⟧\n  （书的正文，作者笔调，纯散文，不要解说）\n  ⟦/PROPOSAL⟧\n\n"
        "## 写作规则\n"
        "- 若作者给了某角色的「演绎草稿」(那角色这一场的限知体验)作为素材,把它**织进**书的叙事。\n"
        "- 尊重已确立设定/伏笔/北极星意图。默认作者视角(可全知);仅当作者明确指定本章跟某焦点者的"
        "限知走时,叙事才贴该视角、不写他不知道的私密。"
    )


def _stream_write(message, instructions: str):
    """共用的写作 SSE 流生成器(GET/POST 复用,P20 DRY)。
    message: str(纯文本) 或 list(含图片附件)。"""
    import json as _j
    from scribe3.llm import hermes_responses_events
    from scribe3.proposal import ProposalParser
    fn = _responses_events or hermes_responses_events
    parser = ProposalParser()
    prop = {"scope": None, "prose": []}

    def drain(events):
        for kind, val in events:
            if kind == "delta":
                yield f"data: {_j.dumps({'delta': val}, ensure_ascii=False)}\n\n"
            elif kind == "proposal_open":
                prop["scope"] = val
            elif kind == "proposal_delta":
                prop["prose"].append(val)
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
    except Exception as e:
        yield f"data: {_j.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
    yield 'data: {"done": true}\n\n'


@app.get("/chat/write")
def chat_write(msg: str, chapter: int = 1, focalizer: str = "", work: str = "main"):
    """对话驱动写作(SSE):主编自判讨论 vs 动稿;动稿用 ⟦PROPOSAL⟧ 围栏回传新散文。
    事件:delta(对话,进右轨)/ tool(工具调用)/ proposal(草稿,进中区)/ done。"""
    st = _store_for(work)
    instructions = _editor_write_system(st)
    instructions += f"\n当前第 {chapter} 章。"
    if focalizer:
        instructions += f"作者指定本章跟随焦点者 {focalizer} 的限知视角:贴该角色所知所感写,别写他不知道的私密。"
    else:
        instructions += "本章未指定限知焦点者 → 作者视角(可全知)。"
    return StreamingResponse(_stream_write(msg, instructions), media_type="text/event-stream")


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

    @field_validator("images")
    @classmethod
    def _count_ok(cls, v: list) -> list:
        if len(v) > _MAX_IMAGES:
            raise ValueError(f"too many images (max {_MAX_IMAGES})")
        return v


@app.post("/chat/write")
def chat_write_post(req: ChatWriteReq, work: str = "main"):
    """POST 版写作对话(支持图片附件):前端用 fetch 流式读取。"""
    st = _store_for(work)
    instructions = _editor_write_system(st)
    instructions += f"\n当前第 {req.chapter} 章。"
    if req.focalizer:
        instructions += f"作者指定本章跟随焦点者 {req.focalizer} 的限知视角:贴该角色所知所感写,别写他不知道的私密。"
    else:
        instructions += "本章未指定限知焦点者 → 作者视角(可全知)。"

    if req.images:
        content = [{"type": "input_text", "text": req.msg}]
        for img in req.images:
            content.append({"type": "input_image", "image_url": f"data:{img.get('type','image/jpeg')};base64,{img.get('data','')}"})
        message = [{"role": "user", "content": content}]
    else:
        message = req.msg

    return StreamingResponse(_stream_write(message, instructions), media_type="text/event-stream")


@app.get("/chapters")
def chapters(work: str = "main"):
    return _store_for(work).list_chapters()


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


def _bg_ingest(work: str, seq: int) -> None:
    """后台客观回写:开独立 store 连接跑 ingest_chapter。异常只记日志,不影响存稿。"""
    import logging
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    try:
        st = _store_for(work)
        ingest_chapter(st, seq, hermes_complete)
    except Exception as e:
        logging.getLogger("scribe3").warning("后台 ingest %s 第%s章失败: %s", work, seq, e)


@app.post("/save-chapter")
def save_chapter(req: SaveChapterReq, background: BackgroundTasks, work: str = "main"):
    st = _store_for(work)
    st.save_chapter(req.seq, req.prose, title=req.title, focalizer=req.focalizer)
    # 软校验(确定性、快、不打 LLM):QC + 限知泄露。回写走独立 /ingest(前端接受后再调)。
    from scribe3.critique import quality_flags
    qf = quality_flags(req.prose)
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
                   "purple": len(qf["purple"])},
            "leaks": leaks, "leak_error": leak_error, "ingesting": True}


@app.post("/ingest")
def ingest(seq: int, work: str = "main"):
    from scribe3.ingest import ingest_chapter
    from scribe3.llm import hermes_complete
    return ingest_chapter(_store_for(work), seq, hermes_complete)


class RenderReq(BaseModel):
    focalizer: str
    chapter: int


@app.post("/render")
def do_render(req: RenderReq, work: str = "main"):
    return {"prose": render(_store_for(work), req.chapter, req.focalizer, complete_fn=_complete_fn)}


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
