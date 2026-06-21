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


# ==== WaveB:编辑功能 CRUD ====
class MaterialIn(BaseModel):
    content: str; type: str = "snippet"; scope: str = "work"
class ImaginationIn(BaseModel):
    raw_text: str
class PrefIn(BaseModel):
    source: str; polarity: str = "+"; signal: dict | None = None
class AgentMemIn(BaseModel):
    namespace: str; key: str; value: object = ""; confidence: float = 1.0; scope: str = "owner"
class SkillIn(BaseModel):
    name: str; spec: dict | None = None

@app.get("/works/{w}/insights")
def list_insights(w: str, status: str = "new", x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_insights(w, status)

@app.post("/works/{w}/insights/{iid}/{act}")
def act_insight(w: str, iid: str, act: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); d.act_insight(iid, act); return {"ok": True}

@app.get("/works/{w}/option-sets")
def list_option_sets(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_option_sets(w)

@app.post("/works/{w}/option-sets/{oid}/choose")
def choose_option(w: str, oid: str, body: dict, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    chosen = body.get("chosen_option_id") or body.get("chosen", "")
    d.choose_option(oid, chosen)
    d.add_preference(w, source="option_choice", polarity="+", signal={"chosen": chosen})
    return {"chosen": chosen}

@app.get("/works/{w}/threads")
def list_threads(w: str, status: str | None = None, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_threads(w, status)

@app.post("/works/{w}/threads/{tid}/resolve")
def resolve_thread(w: str, tid: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); d.resolve_thread(tid); return {"ok": True}

@app.get("/works/{w}/materials")
def list_materials(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_materials(w)

@app.post("/works/{w}/materials")
def add_material(w: str, b: MaterialIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"material_id": d.add_material(w, b.content, b.type, b.scope)}

@app.delete("/works/{w}/materials/{mid}")
def delete_material(w: str, mid: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); d.delete_material(mid); return {"ok": True}

@app.get("/works/{w}/imaginations")
def list_imaginations(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_imaginations(w)

@app.post("/works/{w}/imaginations")
def capture_imagination(w: str, b: ImaginationIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"imagination_id": d.add_imagination(w, b.raw_text)}

@app.post("/works/{w}/imaginations/{iid}/status/{status}")
def set_imagination_status(w: str, iid: str, status: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); d.set_imagination_status(iid, status); return {"status": status}

@app.post("/works/{w}/preference")
def add_preference(w: str, b: PrefIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"signal_id": d.add_preference(w, b.source, b.polarity, b.signal)}

@app.get("/works/{w}/agent-memory")
def list_agent_memory(w: str, namespace: str | None = None, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    o = owner(x_owner_id); return d.list_agent_memory(o, w, namespace)

@app.post("/works/{w}/agent-memory")
def write_agent_memory(w: str, b: AgentMemIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    o = owner(x_owner_id)
    wk = w if b.scope == "work" else None
    return {"memory_id": d.write_agent_memory(o, wk, b.namespace, b.key, b.value, b.confidence), "stored": True}

@app.get("/works/{w}/agent-skills")
def list_agent_skills(w: str, status: str | None = None, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_agent_skills(w, status)

@app.post("/works/{w}/agent-skills")
def propose_skill(w: str, b: SkillIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"skill_id": d.propose_skill(w, b.name, b.spec)}

@app.post("/works/{w}/agent-skills/{sid}/{action}")
def act_skill(w: str, sid: str, action: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"status": d.act_skill(sid, action)}

@app.get("/works/{w}/relations")
def list_relations(w: str, upto: int | None = None, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_relations(w, upto)

@app.get("/works/{w}/characters/{name}/states")
def char_states(w: str, name: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_char_states(w, name)

@app.get("/works/{w}/timeline")
def timeline(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_timeline(w)

@app.post("/works/{w}/consistency-flags/{fid}/{action}")
def resolve_flag(w: str, fid: str, action: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    mp = {"confirm": "confirmed", "dismiss": "dismissed", "fix": "fixed"}
    d.resolve_consistency_flag(fid, mp.get(action, action))
    return {"status": mp.get(action, action)}

class VolumeIn(BaseModel):
    seq: int; title: str = ""; arc_goal: str = ""

@app.get("/works/{w}/volumes")
def list_volumes(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.s.list("volume", "work = $w", {"w": f"work:{w}"})

@app.post("/works/{w}/volumes")
def create_volume(w: str, b: VolumeIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"volume_id": d.create_volume(w, b.seq, b.title)}


@app.get("/health")
def health():
    return {"ok": True}


# 前端兼容桩:外围面板端点(insights/option-sets/threads/materials… + volumes 真实)
from .compat import register as _register_compat  # noqa: E402
_register_compat(app, get_domain, owner, Depends, Domain)
