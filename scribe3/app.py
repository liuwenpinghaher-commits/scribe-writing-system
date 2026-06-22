"""scribe3 后端 API(FastAPI,端口 3321)· 多书(一书一 DB)。

每端点按 ?work=<slug> 路由到对应书的 DB(NS=scribe3 / db=slug),store 按书缓存。
/works 列表/新建。读端点直查;/render 走知识帧投影(API 层也不泄露)。生成走 Hermes。
与 scribe2 后端 3320 隔离(3321)。
"""
from __future__ import annotations

import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.live import live_stream
from scribe3.ontology import Entity, Fact
from scribe3.render import render
from scribe3.store import SurrealStore, create_work, delete_work, list_works, rename_work
from scribe3.verify import causal_complete

app = FastAPI(title="scribe3")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_stores: dict[str, SurrealStore] = {}
_complete_fn = None


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
    return _stores[work]


def _facts(fs):
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute, "value": f.value,
             "secret": f.secret} for f in fs]


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
    return [{"id": e.id, "kind": e.kind, "name": e.name, "backstory": e.traits.get("backstory")}
            for e in _store_for(work).all_entities()]


@app.get("/facts")
def facts(chapter: int, work: str = "main"):
    return _facts(_store_for(work).facts_at(chapter))


@app.get("/events")
def events(chapter: int, work: str = "main"):
    return [{"id": ev.id, "type": ev.type, "chapter": ev.story_time, "goal": ev.motivated_by_goal}
            for ev in _store_for(work).events_at(chapter)]


@app.get("/frame")
def frame(focalizer: str, chapter: int, work: str = "main"):
    return _facts(project_frame(_store_for(work), focalizer, chapter).facts)


@app.get("/irony")
def irony(focalizer: str, chapter: int, work: str = "main"):
    return _facts(dramatic_irony(_store_for(work), focalizer, chapter))


@app.get("/causal")
def causal(chapter: int, work: str = "main"):
    return [{"event": v.event_id, "reason": v.reason} for v in causal_complete(_store_for(work), chapter)]


@app.get("/recall")
def recall(q: str, k: int = 5, work: str = "main"):
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


@app.post("/characters")
def add_char(c: CharIn, work: str = "main"):
    _store_for(work).add_entity(Entity(f"role:{c.name}", "character", c.name, traits={"backstory": c.backstory}))
    return {"ok": True, "oid": f"role:{c.name}"}


@app.patch("/characters/{local}")
def edit_char(local: str, c: CharIn, work: str = "main"):
    _store_for(work).update_record(f"role:{local}", {"name": c.name, "backstory": c.backstory})
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
    kind: str = "promise"


@app.post("/promises-new")
def add_prom(p: PromIn, work: str = "main"):
    _store_for(work).plant_promise(p.text, p.setup_chapter, kind=p.kind)
    return {"ok": True}


@app.patch("/promises/{pid}")
def edit_prom(pid: str, p: PromIn, work: str = "main"):
    _store_for(work).update_promise(pid, {"text": p.text, "setup_chapter": p.setup_chapter, "kind": p.kind})
    return {"ok": True}


@app.delete("/promises/{pid}")
def del_prom(pid: str, work: str = "main"):
    _store_for(work).delete_promise(pid)
    return {"ok": True}


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
    return (
        "你是这部长篇小说的资深主编(责编),与作者面对面讨论创作。\n"
        f"【北极星·作品意图】读者感受:{intent['reader_feeling'] or '—'};"
        f"情感弧:{intent['emotional_arc'] or '—'};绝不背叛的红线:{intent['red_lines'] or '—'}\n"
        f"【主要角色】{ctx_chars}\n【已确立设定(你全知,含私密伏线)】\n{ctx_set}\n\n"
        "要求:用简体中文,像真正的资深文学编辑那样具体、犀利、可操作;紧扣上面的世界观与北极星,"
        "不空泛、不正确的废话;给剧情/人物建议时给出 2-3 个选项与各自代价;护住限知叙事(别让角色知道其知识帧外的私密)。"
    )


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


@app.post("/save-chapter")
def save_chapter(req: SaveChapterReq, work: str = "main"):
    _store_for(work).save_chapter(req.seq, req.prose, title=req.title, focalizer=req.focalizer)
    return {"status": "saved", "seq": req.seq}


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


@app.get("/live")
async def live(work: str = "main"):
    url = os.environ.get("SCRIBE3_SURREAL_URL", "ws://127.0.0.1:8001/rpc")
    return StreamingResponse(live_stream(url, "scribe3", work, _LIVE_TABLES),
                             media_type="text/event-stream")


def main() -> None:
    import uvicorn
    list_works()   # 确保 main 已登记
    uvicorn.run(app, host="127.0.0.1", port=3321)


if __name__ == "__main__":
    main()
