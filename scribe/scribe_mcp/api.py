"""领域 REST API(FastAPI,供小说编辑器前端的面板读写)。

对齐 工程5/5b:聊天走 Hermes :8642/v1;本 API 服务小说专用面板(作品库/大纲/设定/伏笔/一致性…)。
复用 db.py(同一 SQLite);鉴权由你自建(此处用 owner_id 头占位,工程9 要求最小权限)。
跑:`uvicorn scribe_mcp.api:app --port 3320`(端口固定:前端 3310 / 后端 3320)。可用 TestClient 单测。
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .db import Database
from .foreshadow import ForeshadowStore
import asyncio

from .review import run_proactive_review, review_all_works
from .consistency import run_auto_check

_DB_PATH = os.environ.get("SCRIBE_DB") or str(Path(__file__).resolve().parent.parent / "scribe.db")
_HERMES = os.environ.get("HERMES_API", "http://127.0.0.1:8642/v1")  # 聊天经此转发
db = Database(_DB_PATH)
fs = ForeshadowStore(db.conn)
app = FastAPI(title="Scribe Domain API", version="0.1")
# ponytail: 本地单用户开发放开 CORS;多用户/上线再按 owner 收紧(工程9 最小权限)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# C3-4 横切:request_id + 结构化错误码 + 简易访问日志(工程10 可观测起步)
import logging as _logging
import time as _time
import uuid as _uuid
from starlette.requests import Request as _Request
from starlette.responses import JSONResponse as _JSONResponse

_logging.basicConfig(level=_logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = _logging.getLogger("scribe")


@app.middleware("http")
async def _observability(request: _Request, call_next):
    rid = request.headers.get("X-Request-Id") or _uuid.uuid4().hex[:12]
    t0 = _time.monotonic()
    try:
        resp = await call_next(request)
    except HTTPException:
        raise
    except Exception as e:  # 未捕获异常 → 结构化 500(不泄内部细节)
        _log.exception("rid=%s unhandled", rid)
        return _JSONResponse(status_code=500,
                             content={"error_code": "internal_error", "detail": str(e)[:200],
                                      "request_id": rid})
    dur = int((_time.monotonic() - t0) * 1000)
    resp.headers["X-Request-Id"] = rid
    _log.info("rid=%s %s %s -> %s %dms", rid, request.method, request.url.path,
              resp.status_code, dur)
    return resp


@app.exception_handler(HTTPException)
async def _http_exc(request: _Request, exc: HTTPException):
    rid = request.headers.get("X-Request-Id") or "-"
    code = {400: "bad_request", 401: "unauthorized", 402: "budget_exceeded",
            403: "forbidden", 404: "not_found", 502: "upstream_error"}.get(exc.status_code, "error")
    return _JSONResponse(status_code=exc.status_code,
                         content={"error_code": code, "detail": exc.detail, "request_id": rid})


def _owner(x_owner_id: str | None) -> str:
    # ponytail: 鉴权用户自建,这里只取边界 owner_id;缺失即 401
    if not x_owner_id:
        raise HTTPException(401, "缺少 X-Owner-Id(鉴权由上层自建)")
    return x_owner_id


def _page(rows: list[dict], response, cursor: str | None, limit: int | None,
          key: str = "id") -> list[dict]:
    """C3-4 游标分页(向后兼容:不传 limit=全量返回)。
    cursor=上一页末项的 key 值;下一页游标写入 X-Next-Cursor 头。"""
    if not limit or limit <= 0:
        return rows
    start = 0
    if cursor:
        for i, r in enumerate(rows):
            if str(r.get(key)) == str(cursor):
                start = i + 1
                break
    page = rows[start:start + limit]
    if start + limit < len(rows) and page:
        response.headers["X-Next-Cursor"] = str(page[-1].get(key))
    return page


class WorkIn(BaseModel):
    title: str
    premise: str = ""
    genre: str = ""


class IntentIn(BaseModel):
    reader_feeling: str = ""
    core_emotional_arc: str = ""
    why_write: str = ""
    central_promise: str = ""
    do_not_betray: list[str] = []


class ChapterIn(BaseModel):
    seq: int
    title: str = ""
    outline: dict = {}
    status: str = "draft"
    volume_id: str | None = None


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/metrics")
def metrics():
    """C6-1 极简指标(Prometheus 文本):LLM 调用数/总 token/总成本。"""
    t = _LEDGER.total_cost()
    lines = [
        "# scribe LLM usage",
        f"scribe_llm_calls_total {t['calls']}",
        f"scribe_llm_tokens_total {t['tokens']}",
        f"scribe_llm_cost_usd_total {t['cost_usd']}",
    ]
    from starlette.responses import PlainTextResponse
    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/works/{work_id}/cost")
def work_cost(work_id: str, x_owner_id: str | None = Header(default=None)):
    """C3-1/C3-5 本书 LLM 成本透明(调用数/token/估算 USD)。"""
    _own_work(work_id, _owner(x_owner_id))
    return _LEDGER.total_cost(work_id)


@app.get("/works/{work_id}/quality")
def quality_report(work_id: str, x_owner_id: str | None = Header(default=None)):
    """C6-2 全书质量报告:规模/回收率/一致性/AI腔密度/薄弱章。"""
    from .metrics import work_quality_report
    _own_work(work_id, _owner(x_owner_id))
    rep = work_quality_report(db, work_id)
    rep["cost"] = _LEDGER.total_cost(work_id)
    return rep


@app.get("/works/{work_id}/quality/history")
def quality_history(work_id: str, scope: str = "global",
                    x_owner_id: str | None = Header(default=None)):
    """C6-2 质量时序:随修订/时间累积的快照,供前端趋势图。"""
    _own_work(work_id, _owner(x_owner_id))
    return db.list_quality_snapshots(work_id, scope)


@app.get("/works/{work_id}/events")
async def sse_events(work_id: str, owner: str | None = None,
                     x_owner_id: str | None = Header(default=None)):
    """C3-2 SSE:轮询式服务端推送(待决方案数/新札记数变化即 emit)。前端替代 rev 轮询。
    EventSource 不能设头,故也接受 ?owner= 查询参数。"""
    _own_work(work_id, _owner(x_owner_id or owner))
    from starlette.responses import StreamingResponse

    async def gen():
        import asyncio
        import json as _j
        last = None
        for _ in range(600):  # 最长 ~20 分钟,客户端会自动重连
            try:
                snap = {"optionsets": len(db.list_open_option_sets(work_id)),
                        "insights": len(db.list_proactive_insights(work_id, "new")),
                        "flags": len(db.list_consistency_flags(work_id))}
            except Exception:
                snap = {}
            if snap != last:
                last = snap
                yield f"data: {_j.dumps(snap)}\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(gen(), media_type="text/event-stream")


# 主动引擎:后台周期体检(零 LLM,规则版;0=关闭)。默认 6h,开发可调小。
_REVIEW_INTERVAL = int(os.environ.get("SCRIBE_REVIEW_INTERVAL", "21600"))


@app.on_event("startup")
async def _start_proactive_loop():
    if _REVIEW_INTERVAL <= 0:
        return

    async def loop():
        while True:
            await asyncio.sleep(_REVIEW_INTERVAL)
            try:
                review_all_works(db)  # 安静产出札记,等作者打开看
            except Exception:
                pass

    asyncio.create_task(loop())


class ChatIn(BaseModel):
    message: str
    model: str = "doubao-seed-2.0-pro"
    work_id: str | None = None     # 传则把对话持久化到 discussion_threads
    thread_id: str | None = None   # 续话(为空则新建线程)


def _hermes_api_key() -> str:
    """新版 hermes api_server 要 API_SERVER_KEY:优先环境变量,回退 ~/.hermes/.env。"""
    k = os.environ.get("API_SERVER_KEY")
    if not k:
        try:
            for ln in open(os.path.expanduser("~/.hermes/.env"), encoding="utf-8"):
                if ln.startswith("API_SERVER_KEY="):
                    k = ln.split("=", 1)[1].strip(); break
        except Exception:
            pass
    return k or "local"


def _hermes_complete(message: str, model: str = "doubao-seed-2.0-pro", system: str | None = None) -> str:
    """调用 Hermes(主编/火山doubao)取一段补全文本。错误抛出不静默。"""
    msgs = ([{"role": "system", "content": system}] if system else []) + \
        [{"role": "user", "content": message}]
    try:
        r = httpx.post(f"{_HERMES}/chat/completions", timeout=180,
                       headers={"Authorization": f"Bearer {_hermes_api_key()}", "Content-Type": "application/json"},
                       json={"model": model, "messages": msgs, "stream": False})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(502, f"Hermes 转发失败: {e}")


# 主编对话:需要作者定夺/硬冲突时,用 scribe-card 结构块,前端渲染成可操作卡
_CHIEF_SYSTEM = (
    "你是这本长篇小说的主编,用中文与作者协作。正常对话即可。\n"
    "但当你①提出需要作者定夺的多个方案,或②发现硬冲突/重要建议时,"
    "在回复里插入一个 ```scribe-card 代码块,内容为 JSON:\n"
    '{"type":"option_set|hard_conflict|suggestion","title":"一句话","options":["A方案","B方案"]}\n'
    "(options 仅 option_set 需要)。代码块之外照常写解释。不要滥用,只在确有决策/冲突时用。"
)


import re as _re


def _load_volc() -> tuple[str, str, str]:
    """从 ~/.hermes/config.yaml + .env 读 火山 直连参数(base_url/model/key)。"""
    base, model, key = "", "doubao-seed-2.0-pro", ""
    try:
        t = (Path.home() / ".hermes" / "config.yaml").read_text(encoding="utf-8")
        m = _re.search(r"base_url:\s*['\"]?(\S+?)['\"]?\s*$", t, _re.M); base = m.group(1) if m else ""
        m = _re.search(r"^\s*default:\s*['\"]?(\S+?)['\"]?\s*$", t, _re.M); model = m.group(1) if m else model
        m = _re.search(r"api_key:\s*['\"]?(\S+?)['\"]?\s*$", t, _re.M); key = m.group(1) if m else ""
    except Exception:
        pass
    if not key:
        try:
            for ln in (Path.home() / ".hermes" / ".env").read_text().splitlines():
                if ln.startswith("OPENAI_API_KEY="):
                    key = ln.split("=", 1)[1].strip()
        except Exception:
            pass
    return base, model, key


_VOLC_BASE, _VOLC_MODEL, _VOLC_KEY = _load_volc()


from . import llm as _llm

_LEDGER = _llm.TokenLedger(db.conn)
_COST_BUDGET = float(os.environ.get("SCRIBE_COST_BUDGET_USD", "1000"))  # 每书成本熔断(USD)


def _volc_complete(message: str, role: str = "default", work_id: str | None = None,
                   system: str | None = None) -> str:
    """单次生成直连火山 doubao(C3-1 经 LLM 层:重试+账本+路由)。失败回退 agent。
    C3-5:按 work 成本熔断,超预算抛 402。"""
    if not (_VOLC_BASE and _VOLC_KEY):
        return _hermes_complete(message)
    if work_id and _LEDGER.total_cost(work_id)["cost_usd"] >= _COST_BUDGET:
        raise HTTPException(402, "本书生成成本已达预算上限(可调 SCRIBE_COST_BUDGET_USD)")
    try:
        res = _llm.complete(_VOLC_BASE, _VOLC_KEY, _llm.model_for(role), message, system=system)
    except Exception as e:
        raise HTTPException(502, f"火山生成失败: {e}")
    _LEDGER.record(work_id, role, res["model"], res["prompt_tokens"], res["completion_tokens"])
    return res["content"]


# ---- C0-1 语义检索接入 REST 写作路径(向量库延迟初始化,缺 sqlite-vec/fastembed 则静默跳过)----
_vec = {"store": None, "ok": None}


def _get_vec():
    if _vec["ok"] is False:
        return None
    if _vec["store"] is None:
        try:
            from .vec import VecStore, embed
            dim = len(embed(["probe"])[0])
            _vec["store"] = VecStore(db.conn, dim)
            _vec["ok"] = True
        except Exception:
            _vec["ok"] = False
            return None
    return _vec["store"]


def index_chapter_segments(work_id: str, chapter_id: str) -> int:
    """把一章的段落编入语义索引(写完即调,best-effort)。返回索引条数。"""
    vec = _get_vec()
    if vec is None:
        return 0
    try:
        from .vec import embed
        segs = db.list_segments(chapter_id)
        texts = [s["text"] for s in segs if s.get("text", "").strip()]
        if not texts:
            return 0
        vecs = embed(texts)
        for s, v in zip([s for s in segs if s.get("text", "").strip()], vecs):
            vec.add(s["id"], work_id, v, content=s["text"])
        return len(texts)
    except Exception:
        return 0


def _recall_segments(work_id: str, query: str, k: int = 3, exclude: str = "") -> list[str]:
    """语义召回相关旧段(防久远冲突/保持声音)。失败返回空,不阻塞写作。"""
    vec = _get_vec()
    if vec is None or not query.strip():
        return []
    try:
        from .vec import embed
        hits = vec.knn(work_id, embed([query])[0], k + 2)
        out = []
        for _sid, _dist, content in hits:
            if content and content not in exclude and content[:30] not in exclude:
                out.append(content)
            if len(out) >= k:
                break
        return out
    except Exception:
        return []


def _writing_context(work_id: str, owner: str, seq: int) -> str:
    """LP-1+C0-1:写作前注入个性化+一致性+语义召回上下文。
    确定性主体 + 向量召回 —— 既不跑题、保持一致、不出 AI 腔、防久远冲突。"""
    from .intent import red_lines
    from .taste import TasteStore
    from .antislop import constraint_block
    parts: list[str] = []
    import json as _json
    intent = db.get_author_intent(work_id) or {}
    if intent.get("reader_feeling"):
        parts.append(f"【北极星】这本书要让读者感受到:{intent['reader_feeling']}")
    if intent.get("core_emotional_arc"):
        parts.append(f"【情感弧·全书走向】{intent['core_emotional_arc']}")
    red = red_lines(intent)
    if red:
        parts.append("【红线·绝不可破】" + ";".join(r["text"] for r in red))
    chars = db.list_characters(work_id)
    if chars:
        def _c(c):
            m = (c.get("motivation") or "").strip()
            base = f"{c['name']}({m[:24]})" if m else c["name"]
            try:  # C0-4 注入角色声音指纹,保持台词/叙述一致
                vp = _json.loads(c.get("voice_profile") or "{}")
                tone = vp.get("tone") or vp.get("voice") or vp.get("说话风格") or ""
                if tone:
                    base += f"〔声音:{str(tone)[:20]}〕"
            except Exception:
                pass
            return base
        parts.append("【须保持一致的角色(含声音)】" + "、".join(_c(c) for c in chars[:15]))
    sets = db.list_settings(work_id)
    if sets:
        import json as _json
        def _s(s):
            try:
                d = (_json.loads(s.get("content") or "{}").get("description") or "").strip()
            except Exception:
                d = ""
            return f"{s['name']}:{d[:24]}" if d else s["name"]
        parts.append("【关键设定(不可矛盾)】" + ";".join(_s(s) for s in sets[:15]))
    # C2-1 全书主线记忆(滚动摘要)+ C2-6 时间对齐(只用 < 本章 的记忆,不剧透)
    glob = db.get_memory(work_id, "global")
    if glob and glob.get("summary_text"):
        parts.append("【全书主线记忆(至此为止)】" + glob["summary_text"][:300])
    recent = db.list_chapter_memories(work_id, upto_seq=seq - 1)[-3:]
    if recent:
        parts.append("【最近章节梗概】\n" + "\n".join(
            f"第{m['seq']}章:{m['summary_text']}" for m in recent))
    # C2-4 当前生效的人物状态(截至上一章)+ 实体关系
    try:
        cs_lines = []
        for c in db.list_characters(work_id)[:10]:
            st = db.get_char_state_at(c["id"], seq - 1)
            if st:
                cs_lines.append(f"{c['name']}:{st['state_desc'][:40]}")
        if cs_lines:
            parts.append("【人物当前状态(勿写矛盾)】" + ";".join(cs_lines))
        rels = db.list_relations(work_id, upto_seq=seq - 1)
        if rels:
            parts.append("【当前关系】" + ";".join(
                f"{r['src_entity']}-{r['relation']}-{r['dst_entity']}" for r in rels[:10]))
    except Exception:
        pass
    prev_tail = ""
    if seq > 1:
        prevch = db.get_chapter(work_id, seq - 1)
        if prevch:
            ps = db.list_snapshots(prevch["id"])
            if ps and ps[-1]["content"].strip():
                prev_tail = ps[-1]["content"]
                parts.append("【上一章结尾·需自然衔接】…" + prev_tail[-180:])
    # C0-1 语义召回:用上一章结尾或本书北极星做 query,召回相关旧段防久远冲突
    rq = prev_tail[-200:] or intent.get("reader_feeling", "") or ""
    recalled = _recall_segments(work_id, rq, k=3, exclude=prev_tail)
    if recalled:
        parts.append("【相关前文·语义召回(保持一致,勿矛盾)】\n" +
                     "\n".join("· " + r[:120] for r in recalled))
    # C4-2 素材注入:把相关素材(processed 优先)带进生成,关键词命中北极星/上文
    try:
        mats = db.list_materials(owner, work_id)
        if mats:
            kws = [w for w in _re.split(r"[，,。;；、\s]+",
                   intent.get("reader_feeling", "") + prev_tail[-100:]) if 2 <= len(w) <= 8]
            picked = []
            for m in mats:
                blob = (m.get("title") or "") + (m.get("tags") or "")
                if not kws or any(k in blob for k in kws) or m.get("status") == "processed":
                    try:
                        picked.append(_json.loads(m["content"] or "{}").get("text", "")[:80])
                    except Exception:
                        pass
                if len(picked) >= 4:
                    break
            if picked:
                parts.append("【可用素材(可化用,勿照抄)】\n" + "\n".join("· " + p for p in picked))
    except Exception:
        pass
    # C0-6 想象注入:把作者抛下、尚未用上的点子带进生成,鼓励在合适处落地
    try:
        unused = [im for im in db.list_imaginations(work_id) if im.get("status") != "used"]
        if unused:
            parts.append("【作者想抛的点子(尽量在合适处自然用上,别硬塞)】\n" +
                         "\n".join("· " + (im.get("raw_text") or "")[:80] for im in unused[:6]))
    except Exception:
        pass
    # C1-2 注入真实学习到的品味(从历史信号建模,非写死话术)
    try:
        tm = TasteStore(db.conn).get_taste_model(owner, work_id)
        if tm["prefers"] or tm["avoids"]:
            line = "【作者品味·据历史认可学习】"
            if tm["prefers"]:
                line += "倾向:" + "、".join(tm["prefers"][:8])
            if tm["avoids"]:
                line += (";" if tm["prefers"] else "") + "避免:" + "、".join(tm["avoids"][:8])
            parts.append(line)
    except Exception:
        pass
    parts.append(constraint_block())
    return "\n".join(parts)


@app.post("/chat")
def chat(body: ChatIn, x_owner_id: str | None = Header(default=None)):
    """前端聊天经此转发到 Hermes(主编,带工具),避开浏览器→:8642 的 CORS。
    传 work_id 则把对话持久化为 discussion_thread(C5-4)。"""
    _owner(x_owner_id)
    content = _hermes_complete(body.message, body.model, system=_CHIEF_SYSTEM)
    tid = body.thread_id
    if body.work_id:
        try:
            if not tid:
                tid = db.create_thread(body.work_id, body.message[:40], trigger="chat")
            db.add_thread_message(tid, "user", body.message)
            import re as _r
            cm = _r.search(r"```scribe-card\s*(\{.*?\})\s*```", content, _r.S)
            ctype = ""
            if cm:
                try:
                    ctype = __import__("json").loads(cm.group(1)).get("type", "")
                except Exception:
                    pass
            db.add_thread_message(tid, "editor", content, concern_type=ctype)
        except Exception:
            pass
    return {"content": content, "thread_id": tid}


# ---- P0-3 结构化 AI 动作:出草稿(ai-draft),不覆盖定稿;返回 diff 所需 prev ----
class ActionIn(BaseModel):
    instruction: str = ""   # rewrite=作者意见;continue/expand 可选补充


_ACTION_PROMPT = {
    "continue": "请为这本书第 {seq} 章续写约 150 字正文。只输出正文本身,不要任何解释或前后缀。",
    "rewrite": "下面是第 {seq} 章当前正文。请据作者意见「{instruction}」做定向重写(只改问题处,保留其余)。只输出重写后的完整正文,不要解释。\n\n当前正文:\n{prev}",
    "expand": "请把第 {seq} 章正文在不改情节的前提下扩写得更具体(感官细节、动作),约增加一半篇幅。只输出扩写后的完整正文,不要解释。\n\n当前正文:\n{prev}",
}


@app.post("/works/{work_id}/chapters/{seq}/actions/{action}")
def chapter_action(work_id: str, seq: int, action: str, body: ActionIn,
                   x_owner_id: str | None = Header(default=None)):
    """AI 动作(continue/rewrite/expand)→ 生成草稿(注入 LP-1 个性化+一致性上下文),
    返回 {content, prev_content},供前端 diff + 接受/拒绝。不落库,接受才定稿。"""
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    if action not in _ACTION_PROMPT:
        raise HTTPException(400, "action 必须是 continue/rewrite/expand")
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    snaps = db.list_snapshots(ch["id"])
    prev = snaps[-1]["content"] if snaps else ""
    if action != "continue" and not prev:
        raise HTTPException(400, "本章还没有正文,先 continue")
    ctx = _writing_context(work_id, owner, seq)
    prompt = (ctx + "\n\n" if ctx else "") + _ACTION_PROMPT[action].format(
        seq=seq, instruction=body.instruction, prev=prev)
    text = _volc_complete(prompt, role="draft", work_id=work_id)
    # 只生成草稿、不落库:接受时前端再调 /prose 存为定稿(放弃则什么都不留,语义干净)
    return {"content": text, "prev_content": prev}


@app.post("/works/{work_id}/chapters/{seq}/actions/{action}/stream")
async def chapter_action_stream(work_id: str, seq: int, action: str, body: ActionIn,
                                x_owner_id: str | None = Header(default=None)):
    """F 流式生成:逐字 SSE 输出草稿(注入同 chapter_action)。前端边写边显。"""
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    if action not in _ACTION_PROMPT:
        raise HTTPException(400, "action 必须是 continue/rewrite/expand")
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    snaps = db.list_snapshots(ch["id"])
    prev = snaps[-1]["content"] if snaps else ""
    if action != "continue" and not prev:
        raise HTTPException(400, "本章还没有正文,先 continue")
    ctx = _writing_context(work_id, owner, seq)
    prompt = (ctx + "\n\n" if ctx else "") + _ACTION_PROMPT[action].format(
        seq=seq, instruction=body.instruction, prev=prev)
    from starlette.responses import StreamingResponse

    def gen():
        import json as _j
        full = []
        if not (_VOLC_BASE and _VOLC_KEY):
            txt = _hermes_complete(prompt)
            yield f"data: {_j.dumps({'delta': txt})}\n\n"
            full.append(txt)
        else:
            try:
                for delta in _llm.complete_stream(_VOLC_BASE, _VOLC_KEY,
                                                  _llm.model_for("draft"), prompt):
                    full.append(delta)
                    yield f"data: {_j.dumps({'delta': delta})}\n\n"
            except Exception as e:
                yield f"data: {_j.dumps({'error': str(e)[:120]})}\n\n"
        text = "".join(full)
        _LEDGER.record(work_id, "draft", _llm.model_for("draft"),
                       _llm._approx_tokens(prompt), _llm._approx_tokens(text))
        yield f"data: {_j.dumps({'done': True, 'content': text, 'prev_content': prev})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


# ---- 作品库(多本书,owner 边界)----
@app.get("/works")
def list_works(x_owner_id: str | None = Header(default=None)):
    # P0-6:汇总(字数/章数/待看札记/待决方案),一次返回消 N+1
    return db.work_summaries(_owner(x_owner_id))


@app.post("/works")
def create_work(body: WorkIn, x_owner_id: str | None = Header(default=None)):
    wid = db.create_work(_owner(x_owner_id), body.title, body.premise, body.genre)
    return {"work_id": wid}


def _own_work(work_id: str, owner: str) -> dict:
    w = db.get_work(work_id)
    if not w:
        raise HTTPException(404, "作品不存在")
    if w["owner_id"] != owner:
        raise HTTPException(403, "无权访问他人作品")  # 工程9 最小权限 + 防越权
    return w


@app.get("/works/{work_id}")
def get_work(work_id: str, x_owner_id: str | None = Header(default=None)):
    return _own_work(work_id, _owner(x_owner_id))


# ---- 北极星 ----
@app.get("/works/{work_id}/author-intent")
def get_intent(work_id: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.get_author_intent(work_id) or {}


@app.put("/works/{work_id}/author-intent")
def put_intent(work_id: str, body: IntentIn, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    db.set_author_intent(work_id, reader_feeling=body.reader_feeling,
                         core_emotional_arc=body.core_emotional_arc, why_write=body.why_write,
                         central_promise=body.central_promise, do_not_betray=body.do_not_betray)
    return {"ok": True}


# ---- 大纲树:章 ----
# ---- 卷 Volume(P0-1)----
class VolumeIn(BaseModel):
    seq: int
    title: str = ""
    arc_goal: str = ""


@app.get("/works/{work_id}/volumes")
def list_volumes(work_id: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_volumes(work_id)


@app.post("/works/{work_id}/volumes")
def create_volume(work_id: str, body: VolumeIn, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return {"volume_id": db.create_volume(work_id, body.seq, body.title, body.arc_goal)}


@app.get("/works/{work_id}/chapters")
def list_chapters(work_id: str, response: Response, cursor: str | None = None,
                  limit: int | None = None, x_owner_id: str | None = Header(default=None)):
    """章列表;百万字规模可用 ?limit=&cursor=(按 seq)游标分页,下一页游标在 X-Next-Cursor。"""
    _own_work(work_id, _owner(x_owner_id))
    return _page(db.list_chapters(work_id), response, cursor, limit, key="seq")


@app.get("/works/{work_id}/chapters/{seq}")
def get_chapter(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    # 附上该章版本树(供 diff)
    ch["snapshots"] = db.list_snapshots(ch["id"])
    return ch


class FeedbackIn(BaseModel):
    nl_critique: str
    target_type: str = "chapter"
    target_id: str = ""


@app.post("/works/{work_id}/chapters/{seq}/feedback")
def chapter_feedback(work_id: str, seq: int, body: FeedbackIn,
                     x_owner_id: str | None = Header(default=None)):
    """记录作者意见(后续由主编 write-chapter 技能定向重写)。"""
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    fid = db.save_feedback(work_id, body.target_type, body.target_id or ch["id"], body.nl_critique)
    return {"feedback_id": fid}


class ProseIn(BaseModel):
    content: str
    lock: bool = False


def _post_save_chapter(work_id: str, chapter_id: str, seq: int):
    """落库后台收尾:语义索引(C0-1)+ 自动门槛校验(C0-2)+ 章记忆抽取(C2-1/C2-4)。"""
    index_chapter_segments(work_id, chapter_id)
    try:
        run_auto_check(db, work_id, seq)
    except Exception:
        pass
    try:
        from .memory import ingest_chapter
        ingest_chapter(db, _volc_complete, work_id, seq)  # 摘要+角色状态+时间线+关系
    except Exception:
        pass


@app.post("/works/{work_id}/chapters/{seq}/prose")
def save_prose(work_id: str, seq: int, body: ProseIn, background: BackgroundTasks,
               x_owner_id: str | None = Header(default=None)):
    """保存作者人工编辑的正文为新版本(created_by=human,human-final 分支)。
    lock=True 时锁定(AI 不可覆盖,工程9);也成为 LoRA 个性化的训练正例。
    落库后后台自动:语义索引 + 门槛校验(无需前端再调 /check)。"""
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    if not body.content.strip():
        raise HTTPException(400, "正文不能为空")
    sid = db.save_snapshot(work_id, ch["id"], body.content, created_by="human",
                           branch_label="human-final")
    if body.lock:
        db.lock_snapshot(sid)
    n = db.save_segments(work_id, ch["id"], body.content, created_by="human")  # P0-2 段落化+引用
    background.add_task(_post_save_chapter, work_id, ch["id"], seq)  # C0-1/C0-2 后台收尾
    return {"snapshot_id": sid, "locked": body.lock, "segments": n}


# ---- H 分支版本(工程4:多走向 A/B + 合并到定稿)----
class BranchIn(BaseModel):
    label: str
    content: str


@app.get("/works/{work_id}/chapters/{seq}/branches")
def list_branches(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    """各分支的最新版本(按 branch_label 聚合)。"""
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    latest: dict[str, dict] = {}
    for s in db.list_snapshots(ch["id"]):
        latest[s["branch_label"] or "main"] = {
            "label": s["branch_label"] or "main", "content": s["content"],
            "created_by": s["created_by"], "locked": s.get("is_human_locked", 0)}
    return list(latest.values())


@app.post("/works/{work_id}/chapters/{seq}/branches")
def create_branch(work_id: str, seq: int, body: BranchIn,
                  x_owner_id: str | None = Header(default=None)):
    """新建/追加一个命名分支版本(如 A走向/B走向)。"""
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    if body.label in ("human-final",):
        raise HTTPException(400, "保留分支名")
    sid = db.save_snapshot(work_id, ch["id"], body.content, created_by="human",
                           branch_label=body.label)
    return {"snapshot_id": sid, "label": body.label}


@app.post("/works/{work_id}/chapters/{seq}/branches/{label}/merge")
def merge_branch(work_id: str, seq: int, label: str, background: BackgroundTasks,
                 x_owner_id: str | None = Header(default=None)):
    """把某分支的最新内容合并为定稿(human-final + 锁定),并触发收尾。"""
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    snaps = [s for s in db.list_snapshots(ch["id"]) if (s["branch_label"] or "main") == label]
    if not snaps:
        raise HTTPException(404, "分支不存在")
    content = snaps[-1]["content"]
    sid = db.save_snapshot(work_id, ch["id"], content, created_by="human",
                           branch_label="human-final")
    db.lock_snapshot(sid)
    db.save_segments(work_id, ch["id"], content, created_by="human")
    background.add_task(_post_save_chapter, work_id, ch["id"], seq)
    return {"merged": label, "snapshot_id": sid}


@app.get("/works/{work_id}/chapters/{seq}/segments")
def list_segments(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    """章的段落 + 每段引用了哪些设定/角色(供前端 SegmentNode 与"引用展开")。"""
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    return db.list_segments(ch["id"])


@app.post("/works/{work_id}/chapters/{seq}/segments/rebuild")
def rebuild_segments(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    """按最新版本正文重建段落+引用(AI 写完/重写后调用)。"""
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    snaps = db.list_snapshots(ch["id"])
    if not snaps:
        return {"segments": 0}
    last = snaps[-1]
    n = db.save_segments(work_id, ch["id"], last["content"], created_by=last["created_by"])
    return {"segments": n}


@app.post("/works/{work_id}/chapters/{seq}/check")
def check_chapter(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    """门槛自动校验本章(符号状态矛盾 + AI 腔),写完即可调,产出 consistency_flag。"""
    _own_work(work_id, _owner(x_owner_id))
    flags = run_auto_check(db, work_id, seq)
    return {"new_flags": len(flags)}


@app.get("/works/{work_id}/chapters/{seq}/task")
def get_task(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    """C3-3 章编排任务状态 + 当前可选下一步。"""
    from .orchestrator import Orchestrator, next_states
    _own_work(work_id, _owner(x_owner_id))
    t = Orchestrator(db).ensure(work_id, seq)
    return {**t, "next": sorted(next_states(t["status"]))}


class TaskAdvanceIn(BaseModel):
    to: str
    detail: str = ""


@app.post("/works/{work_id}/chapters/{seq}/task/advance")
def advance_task(work_id: str, seq: int, body: TaskAdvanceIn,
                 x_owner_id: str | None = Header(default=None)):
    """C3-3 推进章编排状态(非法转移 400)。"""
    from .orchestrator import Orchestrator
    _own_work(work_id, _owner(x_owner_id))
    try:
        return Orchestrator(db).advance(work_id, seq, body.to, body.detail)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/works/{work_id}/chapters/{seq}/deep-check")
def deep_check_chapter(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    """C2-2 LLM 深度一致性(19 类):对照全书记忆/人物状态/关系/设定找矛盾。"""
    from .consistency import run_deep_check
    _own_work(work_id, _owner(x_owner_id))
    ids = run_deep_check(db, _volc_complete, work_id, seq)
    return {"new_flags": len(ids)}


@app.post("/works/{work_id}/chapters/{seq}/ingest")
def ingest_chapter_ep(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    """C2-1/C2-4 手动触发章记忆抽取(摘要+角色状态+时间线+关系)。"""
    from .memory import ingest_chapter
    from .metrics import work_quality_report
    _own_work(work_id, _owner(x_owner_id))
    res = ingest_chapter(db, _volc_complete, work_id, seq)
    rep = work_quality_report(db, work_id)
    db.add_quality_snapshot(work_id, "global", None, {
        "words": rep["words"], "slop_density": rep["avg_slop_density"],
        "consistency_score": rep["consistency"]["score"],
        "foreshadow_payoff": rep["foreshadow"]["payoff_rate"],
        "cost_usd": _LEDGER.total_cost(work_id)["cost_usd"]})
    return res


# ---- C4 素材库 ----
class MaterialIn(BaseModel):
    type: str = "snippet"     # snippet/quote/image_note/worldbuilding/character_ref/...
    title: str = ""
    content: str
    source: str = ""
    tags: list[str] = []
    scope: str = "work"        # work=本书;owner=跨作品


@app.post("/works/{work_id}/materials")
def add_material_ep(work_id: str, body: MaterialIn, x_owner_id: str | None = Header(default=None)):
    """C4-1 采集素材(粘贴/手记/剪藏)。scope=owner 则跨作品共享。"""
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    if not body.content.strip():
        raise HTTPException(400, "素材内容不能为空")
    wid = None if body.scope == "owner" else work_id
    mid = db.add_material(owner, body.type, body.title or body.content[:20],
                          body.content, body.source, body.tags, work_id=wid)
    return {"material_id": mid}


@app.get("/works/{work_id}/materials")
def list_materials_ep(work_id: str, response: Response, type: str | None = None,
                      cursor: str | None = None, limit: int | None = None,
                      x_owner_id: str | None = Header(default=None)):
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    return _page(db.list_materials(owner, work_id, type), response, cursor, limit, key="id")


@app.delete("/works/{work_id}/materials/{mid}")
def delete_material_ep(work_id: str, mid: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    db.delete_material(mid)
    return {"ok": True}


@app.delete("/works/{work_id}")
def delete_work_ep(work_id: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    db.delete_work(work_id)
    return {"ok": True}


@app.post("/works/{work_id}/materials/{mid}/process")
def process_material_ep(work_id: str, mid: str, x_owner_id: str | None = Header(default=None)):
    """C4-2 处理:LLM 产出摘要 + 标签,状态 raw→processed。"""
    import json as _json
    _own_work(work_id, _owner(x_owner_id))
    m = db.get_material(mid)
    if not m:
        raise HTTPException(404, "素材不存在")
    text = _json.loads(m["content"] or "{}").get("text", "")
    reply = _volc_complete(
        "为下面的写作素材产出 JSON:{\"summary\":\"一句话摘要\",\"tags\":[\"3-6个标签\"]}。\n\n" + text,
        role="extract", work_id=work_id)
    mm = _re.search(r"\{.*\}", reply, _re.S)
    tags = []
    summary = ""
    if mm:
        try:
            d = _json.loads(mm.group(0))
            summary = str(d.get("summary", ""))[:200]
            tags = [str(t) for t in (d.get("tags") or [])][:6]
        except Exception:
            pass
    db.update_material(mid, tags=tags, status="processed",
                       title=(m["title"] or summary[:20]))
    return {"summary": summary, "tags": tags, "status": "processed"}


class DistillIn(BaseModel):
    target: str = "setting"    # setting=提炼为设定条目;exemplar=存为文风范本
    name: str = ""


@app.post("/works/{work_id}/materials/{mid}/distill")
def distill_material_ep(work_id: str, mid: str, body: DistillIn,
                        x_owner_id: str | None = Header(default=None)):
    """C4-3 提炼:素材→设定条目 / 文风范本,并记出处(material_ref)。"""
    import json as _json
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    m = db.get_material(mid)
    if not m:
        raise HTTPException(404, "素材不存在")
    text = _json.loads(m["content"] or "{}").get("text", "")
    if body.target == "setting":
        name = body.name or (m["title"] or text[:16])
        sid = db.upsert_setting(work_id, "素材提炼", name, {"description": text[:400]})
        db.add_material_ref(mid, "setting_item", sid, "distill_setting")
        return {"setting_id": sid}
    else:
        db.conn.execute(
            "INSERT INTO style_exemplars(id,owner_id,work_id,label,sample_text,scope) "
            "VALUES(?,?,?,?,?,?)",
            (__import__("uuid").uuid4().hex, owner, work_id, body.name or m["title"],
             text[:1000], "work"))
        db.conn.commit()
        db.add_material_ref(mid, "style_exemplar", "", "distill_style")
        return {"ok": True}


class SearchIn(BaseModel):
    query: str
    k: int = 5
    upto: int | None = None


@app.post("/works/{work_id}/search")
def hybrid_search_ep(work_id: str, body: SearchIn, x_owner_id: str | None = Header(default=None)):
    """C2-5 混合检索:关键词+向量+图(关系/时间线)三路 RRF 融合。"""
    from .retrieval import hybrid_search
    _own_work(work_id, _owner(x_owner_id))
    vec_hits = None
    vec = _get_vec()
    if vec and body.query.strip():
        try:
            from .vec import embed
            vec_hits = vec.knn(work_id, embed([body.query])[0], body.k + 2)
        except Exception:
            vec_hits = None
    return hybrid_search(db, work_id, body.query, body.k, vec_hits, body.upto)


@app.get("/works/{work_id}/memory")
def get_memory_ep(work_id: str, x_owner_id: str | None = Header(default=None)):
    """全书主线记忆 + 分章梗概(供前端"记忆"视图)。"""
    _own_work(work_id, _owner(x_owner_id))
    g = db.get_memory(work_id, "global")
    return {"global": (g or {}).get("summary_text", ""),
            "chapters": db.list_chapter_memories(work_id)}


@app.get("/works/{work_id}/timeline")
def timeline_ep(work_id: str, response: Response, upto: int | None = None,
                cursor: str | None = None, limit: int | None = None,
                x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return _page(db.list_timeline(work_id, upto), response, cursor, limit, key="id")


@app.get("/works/{work_id}/relations")
def relations_ep(work_id: str, upto: int | None = None, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_relations(work_id, upto)


@app.get("/works/{work_id}/characters/{name}/states")
def char_states_ep(work_id: str, name: str, x_owner_id: str | None = Header(default=None)):
    """角色状态时间线(弧光):随章演进的状态变化。"""
    _own_work(work_id, _owner(x_owner_id))
    c = db.get_character_by_name(work_id, name)
    if not c:
        raise HTTPException(404, "角色不存在")
    return db.list_char_states(c["id"])


class CritiqueIn(BaseModel):
    content: str = ""      # 留空则用最新版本正文
    revise: bool = True    # True=评分+定向重写;False=仅评分


@app.post("/works/{work_id}/chapters/{seq}/critique")
def critique_chapter(work_id: str, seq: int, body: CritiqueIn,
                     x_owner_id: str | None = Header(default=None)):
    """C1-3 文学评改环:8 维 rubric 打分 → 不达标则定向重写,返回评分+改稿。"""
    from .critique import critique_revise, build_critique_prompt, parse_critique
    _own_work(work_id, _owner(x_owner_id))
    text = body.content.strip()
    if not text:
        ch = db.get_chapter(work_id, seq)
        snaps = db.list_snapshots(ch["id"]) if ch else []
        text = snaps[-1]["content"] if snaps else ""
    if not text:
        raise HTTPException(400, "无正文可评改")
    rf = (db.get_author_intent(work_id) or {}).get("reader_feeling", "")
    if not body.revise:
        crit = parse_critique(_volc_complete(build_critique_prompt(text, rf)))
        return {"critique": crit, "improved": False, "final": text}
    return critique_revise(text, rf, _volc_complete, max_rounds=1)


@app.post("/works/{work_id}/chapters/{seq}/intent-check")
def intent_check(work_id: str, seq: int, x_owner_id: str | None = Header(default=None)):
    """偏离检测(P0-7):本章是否偏离北极星/红线 → aligned/soft_deviation/hard_violation。"""
    from .intent import red_lines, build_prompt, parse_verdict
    _own_work(work_id, _owner(x_owner_id))
    ch = db.get_chapter(work_id, seq)
    if not ch:
        raise HTTPException(404, "章节不存在")
    snaps = db.list_snapshots(ch["id"])
    content = snaps[-1]["content"] if snaps else ""
    if not content.strip():
        return {"status": "aligned", "reason": "本章暂无正文", "red_lines": []}
    intent = db.get_author_intent(work_id) or {}
    red = red_lines(intent)
    verdict = parse_verdict(_volc_complete(build_prompt(intent, content, red)))
    return {**verdict, "red_lines": red}


class StatusIn(BaseModel):
    status: str


@app.post("/works/{work_id}/chapters/{seq}/status")
def set_chapter_status(work_id: str, seq: int, body: StatusIn, x_owner_id: str | None = Header(default=None)):
    """P1-3 标记完成:draft/done/revising,只改状态。"""
    _own_work(work_id, _owner(x_owner_id))
    if body.status not in ("draft", "done", "revising"):
        raise HTTPException(400, "status 必须是 draft/done/revising")
    if not db.get_chapter(work_id, seq):
        raise HTTPException(404, "章节不存在")
    db.set_chapter_status(work_id, seq, body.status)
    return {"status": body.status}


@app.post("/works/{work_id}/chapters/{seq}/move/{direction}")
def move_chapter(work_id: str, seq: int, direction: str, x_owner_id: str | None = Header(default=None)):
    """章节重排:up 上移 / down 下移(与相邻章交换 seq)。"""
    _own_work(work_id, _owner(x_owner_id))
    if direction not in ("up", "down"):
        raise HTTPException(400, "direction 必须是 up/down")
    moved = db.move_chapter(work_id, seq, -1 if direction == "up" else 1)
    return {"moved": moved}


@app.put("/works/{work_id}/chapters")
def put_chapter(work_id: str, body: ChapterIn, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    cid = db.save_chapter(work_id, body.seq, body.title, body.outline, body.status, body.volume_id)
    return {"chapter_id": cid}


# ---- 设定 / 角色 / 伏笔 / 一致性(面板)----
@app.get("/works/{work_id}/settings")
def settings(work_id: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_settings(work_id)


@app.get("/works/{work_id}/impact")
def impact(work_id: str, name: str, x_owner_id: str | None = Header(default=None)):
    """影响分析/角色时间线:引用过 name 的章节(seq+片段),按章序。"""
    _own_work(work_id, _owner(x_owner_id))
    return db.chapters_citing(work_id, name)


class SettingIn(BaseModel):
    type_: str = "设定"
    name: str
    description: str = ""


@app.post("/works/{work_id}/settings")
def add_setting(work_id: str, body: SettingIn, x_owner_id: str | None = Header(default=None)):
    """P3-4:从设定圣经面板新增/更新设定条目。"""
    _own_work(work_id, _owner(x_owner_id))
    if not body.name.strip():
        raise HTTPException(400, "name 不能为空")
    sid = db.upsert_setting(work_id, body.type_ or "设定", body.name.strip(),
                            {"description": body.description} if body.description else None)
    return {"setting_id": sid}


@app.get("/works/{work_id}/characters")
def characters(work_id: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_characters(work_id)


class CharacterIn(BaseModel):
    name: str
    motivation: str = ""


@app.post("/works/{work_id}/characters")
def add_character(work_id: str, body: CharacterIn, x_owner_id: str | None = Header(default=None)):
    """P3-4:从设定圣经面板新增/更新角色。"""
    _own_work(work_id, _owner(x_owner_id))
    if not body.name.strip():
        raise HTTPException(400, "name 不能为空")
    cid = db.upsert_character(work_id, body.name.strip(), motivation=body.motivation)
    return {"character_id": cid}


@app.get("/works/{work_id}/foreshadows")
def open_foreshadows(work_id: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return fs.list_open(work_id)


@app.get("/works/{work_id}/consistency-flags")
def flags(work_id: str, status: str = "open", x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_consistency_flags(work_id, status)


# ---- P3 可操作侧栏:一致性裁决 + 伏笔推进 ----
@app.post("/works/{work_id}/consistency-flags/{fid}/{action}")
def resolve_flag(work_id: str, fid: str, action: str, x_owner_id: str | None = Header(default=None)):
    """裁决一致性 flag:confirm(确认真错)/dismiss(误报)/fix(已修)。"""
    _own_work(work_id, _owner(x_owner_id))
    mp = {"confirm": "confirmed", "dismiss": "dismissed", "fix": "fixed"}
    if action not in mp:
        raise HTTPException(400, "action 必须是 confirm/dismiss/fix")
    db.resolve_consistency_flag(fid, mp[action])
    return {"status": mp[action]}


@app.post("/works/{work_id}/foreshadows/{fid}/{action}")
def advance_foreshadow(work_id: str, fid: str, action: str, x_owner_id: str | None = Header(default=None)):
    """推进伏笔:trigger(触发)/pay(回收)/abandon(放弃);非法转移 400。"""
    _own_work(work_id, _owner(x_owner_id))
    mp = {"trigger": "triggered", "pay": "paid", "abandon": "abandoned"}
    if action not in mp:
        raise HTTPException(400, "action 必须是 trigger/pay/abandon")
    try:
        fs.transition(fid, mp[action])
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"state": mp[action]}


# ---- 偏好回流(P0-5:选方案/接受重写/这是故意的 → 跨书品味底色)----
class PrefIn(BaseModel):
    source: str            # option_choice / feedback_accept / intentional / rating
    polarity: str = "+"
    weight: float = 1.0
    signal: dict | None = None


@app.post("/works/{work_id}/preference")
def record_preference(work_id: str, body: PrefIn, x_owner_id: str | None = Header(default=None)):
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    from .taste import TasteStore
    sid = TasteStore(db.conn).record_signal(owner, body.source, body.polarity, body.weight,
                                            body.signal, work_id=None)
    return {"signal_id": sid}


# ---- 想象捕获(// 零摩擦)----
class ImaginationIn(BaseModel):
    raw_text: str
    type: str = ""


@app.get("/works/{work_id}/imaginations")
def list_imaginations(work_id: str, status: str | None = None,
                      x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_imaginations(work_id, status)


@app.post("/works/{work_id}/imaginations")
def capture_imagination(work_id: str, body: ImaginationIn,
                        x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    if not body.raw_text.strip():
        raise HTTPException(400, "想象内容不能为空")
    return {"imagination_id": db.capture_imagination(work_id, body.raw_text, body.type)}


@app.post("/works/{work_id}/imaginations/{iid}/status/{status}")
def set_imagination_status(work_id: str, iid: str, status: str,
                           x_owner_id: str | None = Header(default=None)):
    """C0-6 推进想象状态:captured/structured/scheduled/used。用上即标 used,不再注入。"""
    _own_work(work_id, _owner(x_owner_id))
    if status not in ("captured", "structured", "scheduled", "used", "obsolete"):
        raise HTTPException(400, "非法状态")
    db.set_imagination_status(iid, status)
    return {"status": status}


# ---- C5-4 讨论线程(主编对话持久化)----
@app.get("/works/{work_id}/threads")
def list_threads_ep(work_id: str, status: str | None = None,
                    x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_threads(work_id, status)


@app.post("/works/{work_id}/threads/{tid}/resolve")
def resolve_thread_ep(work_id: str, tid: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    db.resolve_thread(tid, "resolved")
    return {"ok": True}


# ---- 内核0 完整版:跨会话记忆 agent_memory ----
class AgentMemIn(BaseModel):
    namespace: str             # working/session/episodic/semantic/meta
    key: str
    value: dict
    confidence: float = 1.0
    scope: str = "owner"       # owner=跨书


@app.get("/works/{work_id}/agent-memory")
def read_agent_memory_ep(work_id: str, namespace: str | None = None,
                         x_owner_id: str | None = Header(default=None)):
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    return db.read_agent_memory(owner, namespace, work_id)


@app.post("/works/{work_id}/agent-memory")
def write_agent_memory_ep(work_id: str, body: AgentMemIn,
                          x_owner_id: str | None = Header(default=None)):
    """写跨会话记忆;confidence<0.8 不入(设计要求)。"""
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    wid = None if body.scope == "owner" else work_id
    mid = db.write_agent_memory(owner, body.namespace, body.key, body.value,
                                body.confidence, work_id=wid)
    return {"memory_id": mid, "stored": mid is not None}


# ---- 内核0 完整版:自我优化技能 agent_skills(须人审批)----
class SkillIn(BaseModel):
    name: str
    spec: dict = {}


@app.get("/works/{work_id}/agent-skills")
def list_skills_ep(work_id: str, status: str | None = None,
                   x_owner_id: str | None = Header(default=None)):
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    return db.list_skills(owner, status)


@app.post("/works/{work_id}/agent-skills")
def propose_skill_ep(work_id: str, body: SkillIn, x_owner_id: str | None = Header(default=None)):
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    return {"skill_id": db.propose_skill(owner, body.name, body.spec)}


@app.post("/works/{work_id}/agent-skills/{sid}/{action}")
def act_skill_ep(work_id: str, sid: str, action: str, x_owner_id: str | None = Header(default=None)):
    """人审批门:approve/activate/retire(approve 置 approved_by_human=1)。"""
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    mp = {"approve": ("approved", True), "activate": ("active", True), "retire": ("retired", False)}
    if action not in mp:
        raise HTTPException(400, "action 必须是 approve/activate/retire")
    status, human = mp[action]
    db.set_skill_status(sid, status, human)
    return {"status": status}


# ---- 主编札记 ProactiveInsight + 全文体检 ----
@app.get("/works/{work_id}/insights")
def list_insights(work_id: str, status: str = "new",
                  x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_proactive_insights(work_id, status)


@app.post("/works/{work_id}/insights/{iid}/{action}")
def act_insight(work_id: str, iid: str, action: str,
                x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    mp = {"ack": "acked", "dismiss": "dismissed", "act": "acted"}
    if action not in mp:
        raise HTTPException(400, "action 必须是 ack/dismiss/act")
    db.update_insight_status(iid, mp[action])
    return {"ok": True}


@app.post("/works/{work_id}/proactive-review")
def proactive_review(work_id: str, current_chapter: int = 0,
                     x_owner_id: str | None = Header(default=None)):
    """全文体检:扫超期伏笔等 → 生成主编札记(去重)。current_chapter 省略则取最大章。"""
    _own_work(work_id, _owner(x_owner_id))
    if not current_chapter:
        chs = db.list_chapters(work_id)
        current_chapter = max((c["seq"] for c in chs), default=0)
    new_ids = run_proactive_review(db, work_id, current_chapter)
    return {"new_insights": len(new_ids)}


# ---- 多方案 OptionSet(选项式核心) ----
@app.get("/works/{work_id}/option-sets")
def open_option_sets(work_id: str, x_owner_id: str | None = Header(default=None)):
    _own_work(work_id, _owner(x_owner_id))
    return db.list_open_option_sets(work_id)


class GenOptionsIn(BaseModel):
    decision_point: str
    n: int = 3


def _gen_options(work_id: str, owner: str, decision_point: str, n: int) -> list[dict]:
    """C1-5 让主编对一个决策点生成 2–4 个差异化方案(含差异矩阵字段,至少一个反套路)。"""
    n = max(2, min(4, n))
    rf = (db.get_author_intent(work_id) or {}).get("reader_feeling", "")
    prompt = (
        f"你是这本小说的主编。针对决策点「{decision_point}」给作者 {n} 个**差异显著**的方案"
        f"(其中至少一个要反套路、出人意料)。{'本书北极星:'+rf if rf else ''}\n"
        '只输出 JSON 数组,每项:{"approach":"一句话方案","tradeoff":"代价",'
        '"emotional_direction":"情感走向","character_cost":"人物代价","plot_consequence":"情节后果"}。'
    )
    import json as _json
    reply = _volc_complete(prompt)
    m = _re.search(r"\[.*\]", reply, _re.S)
    opts: list[dict] = []
    if m:
        try:
            for i, o in enumerate(_json.loads(m.group(0))[:n]):
                if isinstance(o, dict) and o.get("approach"):
                    opts.append({"id": chr(65 + i), **{k: str(o.get(k, "")) for k in
                                 ("approach", "tradeoff", "emotional_direction",
                                  "character_cost", "plot_consequence")}})
        except Exception:
            pass
    if len(opts) < 2:
        raise HTTPException(502, "方案生成失败(模型未给出足够差异化方案)")
    return opts


@app.post("/works/{work_id}/option-sets/generate")
def generate_option_set(work_id: str, body: GenOptionsIn,
                        x_owner_id: str | None = Header(default=None)):
    """C1-5:AI 对决策点自动生成差异化方案并入库,等作者拍板。"""
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    if not body.decision_point.strip():
        raise HTTPException(400, "decision_point 不能为空")
    opts = _gen_options(work_id, owner, body.decision_point.strip(), body.n)
    oid = db.create_option_set(work_id, body.decision_point.strip(), opts)
    return {"option_set_id": oid, "options": opts}


class ChooseIn(BaseModel):
    chosen_option_id: str
    rationale: str = ""


@app.post("/works/{work_id}/option-sets/{oid}/choose")
def choose_option(work_id: str, oid: str, body: ChooseIn,
                  x_owner_id: str | None = Header(default=None)):
    owner = _owner(x_owner_id)
    _own_work(work_id, owner)
    try:
        res = db.choose_option(oid, body.chosen_option_id, body.rationale)
    except ValueError as e:
        raise HTTPException(400, str(e))
    # 选择即偏好信号 → 回流跨书品味底色(内核2);带上所选方案文本供 TasteModel 学习
    chosen_text = ""
    try:
        os_row = db.get_option_set(oid) if hasattr(db, "get_option_set") else None
        opts = json.loads(os_row["options"]) if os_row else []
        for o in opts:
            if str(o.get("id")) == str(body.chosen_option_id):
                chosen_text = str(o.get("approach") or o.get("label") or "")
                break
    except Exception:
        pass
    from .taste import TasteStore
    TasteStore(db.conn).record_signal(owner, source="option_choice", polarity="+", weight=1.0,
                                      signal={"option_set": oid, "text": chosen_text}, work_id=None)
    return res


@app.post("/works/{work_id}/analyze")
def analyze_work(work_id: str, x_owner_id: str | None = Header(default=None)):
    """批量分析全书:逐章清理→ingest(摘要/关系/时间线/状态)→落质量快照。幂等。"""
    from .memory import ingest_chapter
    from .metrics import work_quality_report
    _own_work(work_id, _owner(x_owner_id))
    chs = db.list_chapters(work_id)
    cnt = {"analyzed": 0, "relations": 0, "events": 0, "states": 0}
    for c in chs:
        db.clear_chapter_extractions(work_id, c["seq"])
        res = ingest_chapter(db, _volc_complete, work_id, c["seq"])
        if res.get("ok"):
            cnt["analyzed"] += 1
            cnt["relations"] += res.get("relations", 0)
            cnt["events"] += res.get("timeline", 0)
            cnt["states"] += res.get("char_states", 0)
    rep = work_quality_report(db, work_id)
    db.add_quality_snapshot(work_id, "global", None, {
        "words": rep["words"], "slop_density": rep["avg_slop_density"],
        "consistency_score": rep["consistency"]["score"],
        "foreshadow_payoff": rep["foreshadow"]["payoff_rate"],
        "cost_usd": _LEDGER.total_cost(work_id)["cost_usd"]})
    return cnt
