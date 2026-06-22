"""scribe3 后端 API(FastAPI,端口 3321)。

前端写作台 v2 读 NS=scribe3 + 驱动渲染的桥。读端点直查 store;/render 走知识帧投影
(API 层也不泄露)。生成走 Hermes(complete_fn 可注入,测试用假)。
与 scribe2 后端 3320 隔离(3321)。
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scribe3.knowledge import dramatic_irony, project_frame
from scribe3.render import render
from scribe3.verify import causal_complete

app = FastAPI(title="scribe3")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_store = None
_complete_fn = None


def set_store(s) -> None:
    global _store
    _store = s


def set_complete_fn(fn) -> None:
    global _complete_fn
    _complete_fn = fn


def _facts(fs):
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute, "value": f.value,
             "secret": f.secret} for f in fs]


@app.get("/health")
def health():
    return {"ok": True, "ns": "scribe3"}


@app.get("/entities")
def entities():
    return [{"id": e.id, "kind": e.kind, "name": e.name} for e in _store.all_entities()]


@app.get("/facts")
def facts(chapter: int):
    return _facts(_store.facts_at(chapter))


@app.get("/events")
def events(chapter: int):
    return [{"id": ev.id, "type": ev.type, "chapter": ev.story_time,
             "goal": ev.motivated_by_goal} for ev in _store.events_at(chapter)]


@app.get("/frame")
def frame(focalizer: str, chapter: int):
    return _facts(project_frame(_store, focalizer, chapter).facts)


@app.get("/irony")
def irony(focalizer: str, chapter: int):
    return _facts(dramatic_irony(_store, focalizer, chapter))


@app.get("/causal")
def causal(chapter: int):
    return [{"event": v.event_id, "reason": v.reason} for v in causal_complete(_store, chapter)]


@app.get("/recall")
def recall(q: str, k: int = 5):
    return _facts(_store.semantic_recall(q, k))


class RenderReq(BaseModel):
    focalizer: str
    chapter: int


@app.post("/render")
def do_render(req: RenderReq):
    """以 focalizer 限知视角渲染本章 sjuzhet(走知识帧投影,帧外私密不进 prompt)。"""
    return {"prose": render(_store, req.chapter, req.focalizer, complete_fn=_complete_fn)}


def main() -> None:
    from scribe3.store import SurrealStore
    store = SurrealStore(ns="scribe3", db="main")
    store.apply_schema()
    set_store(store)
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3321)   # 与 scribe2 后端 3320 隔离


if __name__ == "__main__":
    main()
