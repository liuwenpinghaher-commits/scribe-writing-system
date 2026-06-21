from __future__ import annotations
import asyncio
import json as _json
from fastapi import FastAPI, Header, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .conn import connect, domain_from
from .domain import Domain, _cjk
from .generate import generate_continue, ingest_chapter, build_chapter_prompt
from .writing import build_writing_context
from .llm import hermes_complete, hermes_complete_stream, hermes_responses_events
from .critique import build_critique_prompt, parse_critique, critique_revise
from .consistency import check_chapter
from . import editorial as _ed

app = FastAPI(title="Scribe (SurrealDB)")
# CORS:前端(:3310)跨域调本后端(:3320),放行浏览器预检。本地工具用 X-Owner-Id 头、无 cookie,
# 故 allow_origins=* + allow_credentials=False(二者不可同真)。
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
_complete = hermes_complete  # 生成走 Hermes;测试可 monkeypatch scribe2.app._complete
_complete_stream = hermes_complete_stream  # 流式;测试可 monkeypatch
_responses_events = hermes_responses_events  # 主编 agentic(调 scribe2 MCP 工具);测试可 monkeypatch

_CHIEF_SYSTEM = (
    "你是这本小说的主编,熟悉全书设定、人物、章节与伏笔。回答作者时,"
    "凡涉及书里的具体设定/人物/章节/伏笔/记忆,务必先调用 scribe2 工具查真实数据,不要凭空编造;"
    "回答简洁中肯,带文学判断。"
)
_singleton: dict = {"d": None}

def get_domain() -> Domain:
    if _singleton["d"] is None:
        d = domain_from(connect())
        try:
            d.s.init_schema()  # 启动时确保 schema(幂等)
        except Exception:
            pass
        _singleton["d"] = d
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
    name: str; type_: str = "设定"; description: str = ""; desc: str = ""
    fields: dict = {}  # Codex 2.0:力量体系 cost/limitations/trouble 等结构化字段
class MotifIn(BaseModel):
    name: str; metaphor_unfolding: str = ""; bound_theme: str = ""
    material_echoes: list = []; naming_logic: str = ""
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
    cid = _cid(d, w, seq)
    sid = d.save_prose(w, cid, b.content, b.lock)
    d.save_segments(w, cid, b.content)  # 存即分段,供「阅读/引用」视图直接展示+回填引用
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

# ==== 划词交互:批注 / 高亮 / 段级改写(锚在选中文字 quote)====
class AnnotationIn(BaseModel):
    quote: str
    note: str = ""
    target: str = "self"  # self(自留) / chief(提示主编)

class HighlightIn(BaseModel):
    quote: str
    color: str = "amber"  # amber重点 / rose待改 / sky疑问

class RewritePassageIn(BaseModel):
    passage: str
    instruction: str = ""

@app.post("/works/{w}/chapters/{seq}/annotations")
def add_annotation(w: str, seq: int, b: AnnotationIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return {"annotation_id": d.add_annotation(w, seq, b.quote, b.note, b.target)}

@app.get("/works/{w}/chapters/{seq}/annotations")
def list_chapter_annotations(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_annotations(w, seq)

@app.get("/works/{w}/annotations")
def list_all_annotations(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_annotations(w)

@app.delete("/works/{w}/annotations/{aid}")
def delete_annotation(w: str, aid: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); d.delete_annotation(aid); return {"ok": True}

@app.post("/works/{w}/chapters/{seq}/highlights")
def add_highlight(w: str, seq: int, b: HighlightIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return {"highlight_id": d.add_highlight(w, seq, b.quote, b.color)}

@app.get("/works/{w}/chapters/{seq}/highlights")
def list_highlights(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_highlights(w, seq)

@app.delete("/works/{w}/highlights/{hid}")
def delete_highlight(w: str, hid: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); d.delete_highlight(hid); return {"ok": True}

@app.post("/works/{w}/chapters/{seq}/rewrite-passage")
def rewrite_passage(w: str, seq: int, b: RewritePassageIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """主编只重写选中的这一段(注入北极星/角色声音/记忆),按指令调整,不落库。"""
    owner(x_owner_id)
    ctx = build_writing_context(d, w, seq)
    prompt = (f"{ctx}\n\n【任务】只重写下面这一段落,保持与全书风格、人物声音、上下文的衔接,"
              f"按要求调整;只输出重写后的这一段,不要任何解释或引号。\n"
              f"调整要求:{b.instruction or '更凝练、去AI腔、更贴人物'}\n\n原段落:\n{b.passage}")
    return {"rewritten": _complete(prompt).strip()}

@app.post("/works/{w}/chapters/{seq}/extract-entities")
def extract_entities(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """从本章正文抽取候选设定(人物/设定/伏笔),只产候选不落库——供作者勾选后入库。"""
    owner(x_owner_id)
    prose = d.latest_prose(_cid(d, w, seq))
    if not prose.strip():
        return {"characters": [], "settings": [], "foreshadows": []}
    return _ed.extract_entities(prose, _complete)

@app.get("/works/{w}/chapters/{seq}/branches")
def list_branches(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_branches(_cid(d, w, seq))

@app.post("/works/{w}/chapters/{seq}/branches")
def create_branch(w: str, seq: int, b: BranchIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"snapshot_id": d.create_branch(w, _cid(d, w, seq), b.label, b.content)}

@app.post("/works/{w}/chapters/{seq}/branches/{label}/merge")
def merge_branch(w: str, seq: int, label: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"merged": d.merge_branch(w, _cid(d, w, seq), label)}

@app.get("/works/{w}/settings")
def list_settings(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_settings(w)

@app.post("/works/{w}/settings")
def add_setting(w: str, b: SettingIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return {"setting_id": d.add_setting(w, b.name, b.description or b.desc, b.type_, b.fields)}

@app.post("/works/{w}/search")
def search(w: str, b: SearchIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.search(w, b.query, b.k)

# ==== 写作面:圣经 CRUD + 生成 + 自动章记忆 ====
class IntentIn(BaseModel):
    reader_feeling: str = ""; core_emotional_arc: str = ""; why_write: str = ""
    central_promise: str = ""; red_lines: list[str] = []; do_not_betray: list[str] = []
class CharacterIn(BaseModel):
    name: str; motivation: str = ""; voice: str = ""
    voice_samples: list = []; core_contradiction: str = ""; wound: str = ""
    lie: str = ""; want: str = ""; need: str = ""; arc: str = ""; fear: str = ""
class ForeshadowIn(BaseModel):
    summary: str; chapter: int; importance: str = "normal"
class ActionIn(BaseModel):
    instruction: str = ""; target_chars: int = 850; prev: str = ""


@app.put("/works/{w}/author-intent")
def set_intent(w: str, b: IntentIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    red = b.do_not_betray or b.red_lines  # 前端发 do_not_betray
    d.set_intent(w, b.reader_feeling, b.core_emotional_arc, b.why_write, b.central_promise, red)
    return {"ok": True}

@app.get("/works/{w}/author-intent")
def get_intent(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.get_intent(w) or {}

@app.post("/works/{w}/characters")
def add_character(w: str, b: CharacterIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    # upsert:同名更新合并(支持前端编辑富字段),否则新建
    return {"character_id": d.upsert_character(
        w, b.name, b.motivation, b.voice, voice_samples=b.voice_samples or None,
        core_contradiction=b.core_contradiction, wound=b.wound, lie=b.lie,
        want=b.want, need=b.need, arc=b.arc, fear=b.fear)}

@app.get("/works/{w}/characters")
def list_characters(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_characters(w)

@app.get("/works/{w}/motifs")
def list_motifs(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_motifs(w)

@app.get("/works/{w}/entities/{name}/appearances")
def entity_appearances(w: str, name: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"name": name, "chapters": d.entity_appearances(w, name)}

class CharStateIn(BaseModel):
    character: str; chapter_seq: int; state_desc: str = ""; change_type: str = "add"

@app.post("/works/{w}/char-states")
def add_char_state(w: str, b: CharStateIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """Progressions:加一条人物状态变更(绑定生效章 chapter_seq;注入时按写作位置过滤,防剧透)。"""
    owner(x_owner_id)
    return {"state_id": d.add_char_state(w, b.character, b.chapter_seq, b.state_desc, b.change_type)}

@app.get("/works/{w}/char-states")
def list_char_states(w: str, character: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_char_states(w, character)

@app.post("/works/{w}/motifs")
def add_motif(w: str, b: MotifIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    return {"motif_id": d.add_motif(w, b.name, b.metaphor_unfolding, b.bound_theme,
                                    b.material_echoes, b.naming_logic)}

@app.post("/works/{w}/foreshadows")
def plant_foreshadow(w: str, b: ForeshadowIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"foreshadow_id": d.plant_foreshadow(w, b.summary, b.chapter, b.importance)}

@app.get("/works/{w}/foreshadows")
def list_foreshadows(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_open_foreshadows(w)

@app.get("/works/{w}/foreshadows-status")
def list_foreshadows_status(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """全部伏笔 + echoes(中途强化章)+ overdue(超期未回收告警)。"""
    owner(x_owner_id); return d.list_foreshadows_status(w)

class EchoIn(BaseModel):
    chapter: int

@app.post("/works/{w}/foreshadows-status/{fid}/echo")
def add_foreshadow_echo(w: str, fid: str, b: EchoIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"echoes": d.add_foreshadow_echo(w, fid, b.chapter)}

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
    chs = [{"seq": m.get("seq"), "summary_text": m.get("text", "")}
           for m in d.list_chapter_memories(w)]  # 前端契约 summary_text
    return {"global": d.get_global_memory(w), "chapters": chs}


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


# ==== WaveC:质量/成本/impact/任务态 + LLM 编辑功能 ====
class OptionGenIn(BaseModel):
    decision_point: str; n: int = 3
class DistillIn(BaseModel):
    target: str = "setting"
class TaskAdvIn(BaseModel):
    to: str; detail: str = ""

@app.get("/works/{w}/quality")
def quality(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.compute_quality(w)

@app.get("/works/{w}/quality/history")
def quality_history(w: str, scope: str = "work", x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_quality_history(w, scope)

@app.get("/works/{w}/cost")
def cost(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.get_cost(w)

@app.get("/works/{w}/impact")
def impact(w: str, name: str = "", x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.impact(w, name)

@app.get("/works/{w}/chapters/{seq}/task")
def get_task(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.get_task(w, seq)

@app.post("/works/{w}/chapters/{seq}/task/advance")
def advance_task(w: str, seq: int, b: TaskAdvIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id)
    try:
        return d.advance_task(w, seq, b.to, b.detail)
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.post("/works/{w}/chapters/{seq}/intent-check")
def intent_check(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return _ed.intent_check(d, w, seq, _complete)

@app.post("/works/{w}/chapters/{seq}/deep-check")
def deep_check(w: str, seq: int, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"new_flags": len(check_chapter(d, w, seq, _complete))}

@app.post("/works/{w}/proactive-review")
def proactive_review(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"new_insights": _ed.proactive_review(d, w, _complete)}

@app.post("/works/{w}/option-sets/generate")
def generate_options(w: str, b: OptionGenIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"option_set_id": _ed.generate_options(d, w, b.decision_point, b.n, _complete)}

@app.post("/works/{w}/materials/{mid}/process")
def process_material(w: str, mid: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return _ed.process_material(d, mid, _complete)

@app.post("/works/{w}/materials/{mid}/distill")
def distill_material(w: str, mid: str, b: DistillIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return _ed.distill_material(d, w, mid, b.target, _complete)

@app.post("/works/{w}/analyze")
def analyze_work(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return _ed.analyze(d, w, _complete)

@app.get("/works/{w}/pending-writes")
def pending_writes(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return []  # 确定性写流不入审批队列(MCP写工具走审批注册,无挂起队列)


# ==== WaveD:流式 SSE ====
@app.post("/works/{w}/chapters/{seq}/actions/{action}/stream")
def gen_stream(w: str, seq: int, action: str, b: ActionIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """流式逐字生成(SSE):data:{delta} … data:{done,content,prev_content}。"""
    owner(x_owner_id)
    prev = b.prev or d.latest_prose(_cid(d, w, seq)) if action != "continue" else b.prev
    ctx = build_writing_context(d, w, seq)
    prompt = build_chapter_prompt(ctx, seq, b.instruction, prev, b.target_chars)

    def gen():
        full = []
        try:
            for delta in _complete_stream(prompt):
                full.append(delta)
                yield f"data: {_json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'error': str(e)[:120]}, ensure_ascii=False)}\n\n"
        content = "".join(full)
        d.record_cost(w, int(_cjk(content) * 1.6))
        yield f"data: {_json.dumps({'done': True, 'content': content, 'prev_content': prev}, ensure_ascii=False)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/works/{w}/chat/stream")
def chat_stream(w: str, body: dict, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """主编 agentic 对话(SSE):经 Hermes /v1/responses,主编自己调 scribe2 MCP 工具查真实数据。
    事件:tool(工具调用提示)/delta(回复片段)/done(完整回复+thread_id)。"""
    owner(x_owner_id)
    message = body.get("message", "")
    thread_id = body.get("thread_id")
    model = body.get("model")
    wk = d.get_work(w) or {}
    instructions = (_CHIEF_SYSTEM +
                    f"\n\n作者当前在写《{wk.get('title') or '未命名'}》(work_id={w})。"
                    "查书里数据时把这个 work_id 传给 scribe2 工具。")

    def gen():
        full: list[str] = []
        try:
            for ev in _responses_events(message, instructions, model):
                t = ev.get("type", "")
                if t == "response.output_text.delta":
                    dlt = ev.get("delta", "")
                    if dlt:
                        full.append(dlt)
                        yield f"data: {_json.dumps({'delta': dlt}, ensure_ascii=False)}\n\n"
                elif t == "response.output_item.added":
                    item = ev.get("item", {}) or {}
                    if item.get("type") == "function_call":
                        yield f"data: {_json.dumps({'tool': item.get('name', ''), 'tool_args': item.get('arguments', '')}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
        content = "".join(full)
        tid = thread_id or d.add_thread(w, trigger="chat", topic=message[:30],
                                        messages=[{"role": "user", "content": message},
                                                  {"role": "assistant", "content": content}])
        yield f"data: {_json.dumps({'done': True, 'content': content, 'thread_id': tid}, ensure_ascii=False)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/chat")
def chat(body: dict, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    """简单对话(非流式)。"""
    msg = body.get("message", "")
    return {"content": _complete(msg)}


def _events_frame(snap: dict, last: dict | None) -> tuple[str, dict]:
    """计数变化才发 data(触发前端 bump 刷新);未变发 SSE 注释保活(不触发 onmessage)。
    避免每 3 秒无条件 data 导致前端全量重刷闪屏。"""
    if snap != last:
        return f"data: {_json.dumps(snap)}\n\n", snap
    return ": ping\n\n", last


@app.get("/works/{w}/events")
async def events(w: str, owner_q: str | None = Query(None, alias="owner"), d: Domain = Depends(get_domain)):
    """被动刷新 SSE:仅当待办计数变化时通知前端刷新(首屏由各面板自身加载,不重复刷)。"""
    def _snap():
        return {"insights": len(d.list_insights(w)),
                "option_sets": len(d.list_option_sets(w)),
                "flags": len(d.list_consistency_flags(w))}

    async def gen():
        last = _snap()  # 连接时基线,不发(避免连上即多刷一次)
        for _ in range(100000):  # 长连接;客户端断开即止
            await asyncio.sleep(3)
            frame, last = _events_frame(_snap(), last)
            yield frame
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"ok": True}
