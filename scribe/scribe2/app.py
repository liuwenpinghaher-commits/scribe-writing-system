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
    return d.work_summaries(owner(x_owner_id))

@app.get("/works/{w}")
def get_work(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.get_work(w) or {}

@app.delete("/works/{w}")
def delete_work(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    for tb in ["chapter", "snapshot", "segment", "setting", "character", "foreshadow",
               "memory_entry", "author_intent", "consistency_flag", "insight",
               "option_set", "thread", "material", "imagination"]:
        d.s.delete_where(tb, "work = $w", {"w": f"work:{w}"})
    d.s.delete("work", w)
    return {"ok": True}

@app.put("/works/{w}/chapters")
def add_chapter(w: str, b: ChapterIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"chapter_id": d.add_chapter(w, b.seq, b.title)}

@app.get("/works/{w}/chapters")
def list_chapters(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_chapters(w)

@app.get("/works/{w}/chapters/{seq}")
def get_chapter(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    ch = d.get_chapter(w, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    return ch

def _cid(d: Domain, w: str, seq: int) -> str:
    ch = next((c for c in d.list_chapters(w) if c.get("seq") == seq), None)
    if not ch:
        raise HTTPException(404, "章节不存在")
    return d._idpart(ch["id"])

@app.post("/works/{w}/chapters/{seq}/prose")
def save_prose(w: str, seq: int, b: ProseIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    sid = d.save_prose(w, _cid(d, w, seq), b.content, b.lock)
    return {"snapshot_id": sid}

class StatusIn(BaseModel):
    status: str = "draft"
class FeedbackIn(BaseModel):
    nl_critique: str = ""
class BranchIn(BaseModel):
    label: str; content: str

@app.post("/works/{w}/chapters/{seq}/status")
def set_status(w: str, seq: int, b: StatusIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); d.set_chapter_status(w, seq, b.status); return {"status": b.status}

@app.post("/works/{w}/chapters/{seq}/move/{direction}")
def move_chapter(w: str, seq: int, direction: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"moved": d.move_chapter(w, seq, direction)}

@app.post("/works/{w}/chapters/{seq}/feedback")
def feedback(w: str, seq: int, b: FeedbackIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"feedback_id": d.save_feedback(w, seq, b.nl_critique)}

@app.get("/works/{w}/chapters/{seq}/segments")
def list_segments(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_segments(_cid(d, w, seq))

@app.post("/works/{w}/chapters/{seq}/segments/rebuild")
def rebuild_segments(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    cid = _cid(d, w, seq)
    return {"segments": d.save_segments(w, cid, d.latest_prose(cid))}

@app.get("/works/{w}/chapters/{seq}/branches")
def list_branches(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_branches(_cid(d, w, seq))

@app.post("/works/{w}/chapters/{seq}/branches")
def create_branch(w: str, seq: int, b: BranchIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"snapshot_id": d.create_branch(w, _cid(d, w, seq), b.label, b.content)}

@app.post("/works/{w}/chapters/{seq}/branches/{label}/merge")
def merge_branch(w: str, seq: int, label: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"merged": d.merge_branch(w, _cid(d, w, seq), label)}

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


# 前端兼容桩:外围面板端点(insights/option-sets/threads/materials… + volumes 真实)
from .compat import register as _register_compat  # noqa: E402
_register_compat(app, get_domain, owner, Depends, Domain)
