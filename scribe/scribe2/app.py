from __future__ import annotations
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from .conn import connect, domain_from
from .domain import Domain
from .generate import generate_continue, ingest_chapter
from .llm import hermes_complete
from .critique import build_critique_prompt, parse_critique, critique_revise
from .consistency import check_chapter

app = FastAPI(title="Scribe (SurrealDB)")
_complete = hermes_complete  # 生成走 Hermes;测试可 monkeypatch scribe2.app._complete
_singleton: dict = {"d": None}

def get_domain() -> Domain:
    if _singleton["d"] is None:
        _singleton["d"] = domain_from(connect())
    return _singleton["d"]

def owner(x: str | None) -> str:
    if not x:
        raise HTTPException(401, "缺少 X-Owner-Id")
    return x

class WorkIn(BaseModel):
    title: str; genre: str = ""
class ChapterIn(BaseModel):
    seq: int; title: str = ""
class ProseIn(BaseModel):
    content: str; lock: bool = False
class SettingIn(BaseModel):
    name: str; desc: str = ""
class SearchIn(BaseModel):
    query: str; k: int = 6

@app.post("/works")
def create_work(b: WorkIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    return {"work_id": d.create_work(b.title, b.genre, owner(x_owner_id))}

@app.get("/works")
def list_works(x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    return d.list_works(owner(x_owner_id))

@app.put("/works/{w}/chapters")
def add_chapter(w: str, b: ChapterIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"chapter_id": d.add_chapter(w, b.seq, b.title)}

@app.get("/works/{w}/chapters")
def list_chapters(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_chapters(w)

@app.post("/works/{w}/chapters/{c}/prose")
def save_prose(w: str, c: str, b: ProseIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"snapshot_id": d.save_prose(w, c, b.content, b.lock)}

@app.post("/works/{w}/settings")
def add_setting(w: str, b: SettingIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"setting_id": d.add_setting(w, b.name, b.desc)}

@app.post("/works/{w}/search")
def search(w: str, b: SearchIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.search(w, b.query, b.k)

# ==== 写作面:圣经 CRUD + 生成 + 自动章记忆 ====
class IntentIn(BaseModel):
    reader_feeling: str = ""; core_emotional_arc: str = ""; why_write: str = ""
    central_promise: str = ""; red_lines: list[str] = []
class CharacterIn(BaseModel):
    name: str; motivation: str = ""; voice: str = ""
class ForeshadowIn(BaseModel):
    summary: str; chapter: int; importance: str = "normal"
class ActionIn(BaseModel):
    instruction: str = ""; target_chars: int = 850; prev: str = ""


@app.put("/works/{w}/author-intent")
def set_intent(w: str, b: IntentIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    d.set_intent(w, b.reader_feeling, b.core_emotional_arc, b.why_write, b.central_promise, b.red_lines)
    return {"ok": True}

@app.get("/works/{w}/author-intent")
def get_intent(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.get_intent(w) or {}

@app.post("/works/{w}/characters")
def add_character(w: str, b: CharacterIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"character_id": d.add_character(w, b.name, b.motivation, b.voice)}

@app.get("/works/{w}/characters")
def list_characters(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_characters(w)

@app.post("/works/{w}/foreshadows")
def plant_foreshadow(w: str, b: ForeshadowIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"foreshadow_id": d.plant_foreshadow(w, b.summary, b.chapter, b.importance)}

@app.get("/works/{w}/foreshadows")
def list_foreshadows(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_open_foreshadows(w)

@app.post("/works/{w}/foreshadows/{fid}/{action}")
def advance_foreshadow(w: str, fid: str, action: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    mp = {"trigger": "triggered", "pay": "paid", "abandon": "abandoned"}
    if action not in mp:
        raise HTTPException(400, "action 必须是 trigger/pay/abandon")
    d.advance_foreshadow(fid, mp[action]); return {"state": mp[action]}

@app.post("/works/{w}/chapters/{seq}/actions/continue")
def gen_continue(w: str, seq: int, b: ActionIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """生成第 seq 章一节正文(_writing_context 注入 + 走 Hermes)。不落库,接受才存稿。"""
    owner(x_owner_id)
    content = generate_continue(d, w, seq, b.instruction, _complete, b.target_chars, b.prev)
    return {"content": content}

@app.post("/works/{w}/chapters/{seq}/ingest")
def ingest(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """定稿后建章记忆 + 确定性 rollup(跨章连贯)。"""
    owner(x_owner_id); return {"summary": ingest_chapter(d, w, seq, _complete)}

@app.get("/works/{w}/memory")
def memory(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return {"global": d.get_global_memory(w), "chapters": d.list_chapter_memories(w)}


# ==== 评改 + 一致性 ====
class CritiqueIn(BaseModel):
    content: str = ""; revise: bool = False

def _chapter_prose(d: Domain, w: str, seq: int) -> str:
    ch = next((c for c in d.list_chapters(w) if c.get("seq") == seq), None)
    return d.latest_prose(d._idpart(ch["id"])) if ch else ""

@app.post("/works/{w}/chapters/{seq}/critique")
def critique_ep(w: str, seq: int, b: CritiqueIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """8 维评改:revise=False 仅评分;True 则不达标定向重写。"""
    owner(x_owner_id)
    text = b.content.strip() or _chapter_prose(d, w, seq)
    if not text:
        raise HTTPException(400, "无正文可评改")
    rf = (d.get_intent(w) or {}).get("reader_feeling", "")
    if not b.revise:
        return {"critique": parse_critique(_complete(build_critique_prompt(text, rf))),
                "improved": False, "final": text}
    return critique_revise(text, rf, _complete, max_rounds=1)

@app.post("/works/{w}/chapters/{seq}/check")
def check_ep(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """对照角色/设定/主线找本章矛盾,落 consistency_flag。"""
    owner(x_owner_id); return {"flags": check_chapter(d, w, seq, _complete)}

@app.get("/works/{w}/consistency-flags")
def flags_ep(w: str, status: str = "open", x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_consistency_flags(w, status)


@app.get("/health")
def health():
    return {"ok": True}
