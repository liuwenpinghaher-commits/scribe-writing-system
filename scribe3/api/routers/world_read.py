"""Domain router (extracted from app_impl). URLs unchanged."""
from __future__ import annotations

import types
from typing import Any, Optional, List, Dict, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Body,
    Header,
    Depends,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

router = APIRouter(tags=['world_read'])


# Import app_impl constants/models used as signature defaults (late-safe for helpers).
def _import_core_defaults():
    from scribe3.api import app_impl as core
    g = globals()
    for k, v in core.__dict__.items():
        if k.startswith('__'):
            continue
        if k not in g:
            g[k] = v
try:
    _import_core_defaults()
except Exception:
    pass  # core may be partially init during first import cycle


def object_impact_ep(object_type: str, object_id: str, work: str = "main"):
    return _object_impact(_store_for(work), object_type, object_id, work)

def object_delete_ep(object_type: str, object_id: str,
                     confirm_impact_token: str | None = None,
                     work: str = "main"):
    return _delete_object_with_lifecycle(
        _store_for(work), object_type, object_id, work, confirm_impact_token)

def object_archive_ep(object_type: str, object_id: str, work: str = "main"):
    return _archive_object_with_lifecycle(_store_for(work), object_type, object_id, work)

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

def events(chapter: int = Query(ge=1), work: str = "main"):
    return [{"id": ev.id, "type": ev.type, "chapter": ev.story_time,
             "goal": ev.motivated_by_goal, "causal_root_reason": ev.causal_root_reason}
            for ev in _store_for(work).events_at(chapter)]

def patch_event_narrative(eid: str, body: NarrativeIn, work: str = "main"):
    """更新已有事件的叙事位(narrative_position)。
    body.narrative_position=null → 清除,回退 story_chapter(线性叙事默认)。
    body.narrative_position=N  → 设为叙事位 N(倒叙/闪回)。
    eid 为事件的本体 oid(如 'ev:xxx')或裸 local id(如 'xxx',自动补前缀)。"""
    st = _store_for(work)
    # 容忍裸 local id 或带前缀的 oid
    event_oid = eid if eid.startswith("ev:") else f"ev:{eid}"
    if not st.exists(event_oid):
        raise HTTPException(status_code=404, detail=f"事件 {event_oid} 不存在")
    st.update_event_narrative(event_oid, body.narrative_position)
    return {"ok": True, "event": event_oid, "narrative_position": body.narrative_position}

def patch_event_causal_root(eid: str, body: CausalRootIn, work: str = "main"):
    """登记同章独立场景的因果根理由；有入边的事件不可兼作根。"""
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="独立场景根理由不能为空")
    st = _store_for(work)
    event_oid = eid if eid.startswith("ev:") else f"ev:{eid}"
    if not st.exists(event_oid):
        raise HTTPException(status_code=404, detail=f"事件 {event_oid} 不存在")
    try:
        st.set_event_causal_root(event_oid, reason)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "event": event_oid, "causal_root_reason": reason}

def patch_event_causal(eid: str, body: CausalLinkIn, work: str = "main"):
    """为既有事件补同章因果前驱；成功后自动清除其独立场景根理由。"""
    st = _store_for(work)
    event_oid = eid if eid.startswith("ev:") else f"ev:{eid}"
    source_oid = (body.source_event or "").strip()
    source_oid = source_oid if source_oid.startswith("ev:") else f"ev:{source_oid}"
    ctype = (body.ctype or "enables").strip() or "enables"
    if not st.exists(event_oid) or not st.exists(source_oid):
        raise HTTPException(status_code=404, detail="目标事件或前驱事件不存在")
    try:
        st.add_event_causal_link(event_oid, source_oid, ctype)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "event": event_oid, "source_event": source_oid, "ctype": ctype}

def timeline(ch_from: int = Query(default=1, ge=1),
             ch_to: int | None = Query(default=None, ge=1),
             axis: str = Query(default="story"),
             limit: int = Query(default=500, ge=1, le=5000),
             work: str = "main"):
    """时间线工艺视图(F-02):返回 [ch_from, ch_to] 区间内按章排序的事件条目。
    作者全知视图,无限知门控。四类泳道:events / promise / arc / relation。
    完整期双轴(spec §3.1):axis='story'(默认,故事编年)| 'narrative'(叙事顺序,
    事件按 narrative_position ?? story_chapter 横铺,倒叙/闪回落叙事位)。
    axis 非法值回退 'story'(向后兼容)。

    Phase0-BE1(千万字基座):新增 total items 上限 limit(默认 500,防全书一次返上万条)。
    items 被截断时返回 truncated=true,前端可据此提示缩小区间;结构其余不变。"""
    if axis not in ("story", "narrative"):
        axis = "story"
    st = _store_for(work)
    # 多取一条探测是否溢出 limit,以便回报 truncated
    items = st.timeline(ch_from, ch_to, axis=axis, limit=limit + 1)
    truncated = len(items) > limit
    if truncated:
        items = items[:limit]
    max_ch = st.max_chapter()
    return {
        "from": ch_from,
        "to": ch_to if ch_to is not None else max_ch,
        "max_chapter": max_ch,
        "axis": axis,
        "limit": limit,
        "truncated": truncated,
        "items": items,
    }

def frame(focalizer: str, chapter: int = Query(ge=1), work: str = "main"):
    return _facts(project_frame(_store_for(work), focalizer, chapter).facts)

def irony(focalizer: str, chapter: int = Query(ge=1), work: str = "main"):
    return _facts(dramatic_irony(_store_for(work), focalizer, chapter))

def causal(chapter: int = Query(ge=1), work: str = "main"):
    """本章事件图的因果完整性校验。
    批D P1-5 假绿止血:返回对象 {no_event_data, violations} 而非裸 violations 列表——
    event 表对该章为空时 no_event_data=True(区分'因果完整=violations 空'与
    '根本没有事件数据可校验'),防空表恒返 [] 被前端读作'因果完整✅'的假信号。"""
    st = _store_for(work)
    violations = [{"event": v.event_id, "reason": v.reason} for v in causal_complete(st, chapter)]
    return {"no_event_data": not st.events_at(chapter), "violations": violations}

def recall(q: str, k: int = Query(default=5, ge=1, le=50),
           chapter: int | None = Query(default=None, ge=1),
           work: str = "main"):
    """语义召回。chapter 非空时时间门(valid_from/valid_to),与 store/MCP 一致。"""
    return _facts(_store_for(work).semantic_recall(q, k, chapter=chapter))

def global_search(q: str, limit: int = Query(default=30, ge=1, le=100), work: str = "main"):
    """全局搜索:正文/设定/素材/伏笔/母题的 typed target 聚合,供四栏钻取。"""
    query = (q or "").strip()
    if not query:
        return {"query": query, "results": []}
    st = _store_for(work)
    results = []

    def add(item):
        if len(results) < limit * 3:
            results.append(item)

    for c in st.list_chapters():
        ch = st.get_chapter(int(c["seq"])) or c
        text = "\n".join(str(ch.get(k) or "") for k in ("title", "synopsis", "prose", "scene_truth"))
        if _search_hit(query, text):
            seq = int(ch["seq"])
            title = ch.get("title") or f"第{seq}章"
            add({
                "id": f"search:chapter:{seq}",
                "type": "chapter",
                "label": title,
                "excerpt": _search_excerpt(text, query),
                "source": "正文",
                "chapter": seq,
                "score": 1.0 if _search_hit(query, title) else 0.75,
                "target_node": {"id": f"ch:{seq}", "type": "chapter", "ref": seq, "label": f"{seq} {title}".strip()},
            })

    for ev in st._all_events_bulk():
        from scribe3.knowledge import iter_participants
        _p_oids = [oid for _, oid in iter_participants(ev.participants)]
        text = "\n".join([
            ev.id or "",
            ev.type or "",
            ev.motivated_by_goal or "",
            ev.location or "",
            " ".join(ev.preconditions or []),
            " ".join(_p_oids),
        ])
        if _search_hit(query, text):
            seq = int(ev.story_time or 0)
            label = ev.type or ev.id
            add({
                "id": f"search:event:{ev.id}",
                "type": "event",
                "label": label,
                "excerpt": _search_excerpt(text, query),
                "source": "事件",
                "chapter": seq or None,
                "score": 0.78 if _search_hit(query, label) else 0.62,
                "target_node": {"id": ev.id, "type": "event", "chapter": seq, "label": label},
            })

    for m in st.list_materials():
        if m.get("archived"):
            continue
        text = "\n".join([m.get("title") or "", m.get("body") or "", " ".join(m.get("tags") or [])])
        if _search_hit(query, text):
            mid = str(m["id"])
            add({
                "id": f"search:material:{mid}",
                "type": "material",
                "label": m.get("title") or mid,
                "excerpt": _search_excerpt(text, query),
                "source": "素材",
                "score": 0.9 if _search_hit(query, m.get("title")) else 0.65,
                "target_node": {"id": f"material:{mid}", "type": "material", "ref": mid, "label": m.get("title") or mid,
                                "meta": {"kind": m.get("kind")}},
            })

    for e in st.all_entities():
        text = "\n".join([e.name or "", str((e.traits or {}).get("backstory") or ""), " ".join((e.traits or {}).get("aliases") or [])])
        if _search_hit(query, text):
            local = e.id.split(":", 1)[-1]
            add({
                "id": f"search:entity:{e.id}",
                "type": e.kind,
                "label": e.name,
                "excerpt": _search_excerpt(text, query),
                "source": "设定",
                "score": 0.8,
                "target_node": {"id": f"{e.kind}:{local}", "type": e.kind, "ref": local, "label": e.name},
            })

    max_ch = max(1, st.max_chapter())
    for f in st.facts_at(max_ch):
        text = "\n".join([f.entity_id or "", f.attribute or "", f.value or ""])
        if _search_hit(query, text):
            local = f.id.split(":", 1)[-1]
            add({
                "id": f"search:fact:{local}",
                "type": "proposition",
                "label": f.value or f.attribute or local,
                "excerpt": _search_excerpt(text, query),
                "source": "设定",
                "score": 0.7,
                "target_node": {"id": f"proposition:{local}", "type": "proposition", "ref": local, "label": f.value or local},
            })

    for p in st.list_promises():
        text = "\n".join(str(p.get(k) or "") for k in ("text", "status", "kind"))
        if _search_hit(query, text):
            pid = str(p.get("id") or p.get("text"))
            add({
                "id": f"search:promise:{pid}",
                "type": "promise",
                "label": p.get("text") or pid,
                "excerpt": _search_excerpt(text, query),
                "source": "伏笔",
                "chapter": p.get("setup_chapter"),
                "score": 0.6,
                "target_node": {"id": f"promise:{pid}", "type": "promise_view", "ref": "open", "label": p.get("text") or pid},
            })

    for m in st.list_motifs():
        text = "\n".join(str(m.get(k) or "") for k in ("name", "theme", "echoes", "unfolding"))
        if _search_hit(query, text):
            mid = str(m.get("id") or m.get("name"))
            add({
                "id": f"search:motif:{mid}",
                "type": "motif",
                "label": m.get("name") or mid,
                "excerpt": _search_excerpt(text, query),
                "source": "母题",
                "score": 0.6,
                "target_node": {"id": f"motif:{mid}", "type": "motif", "ref": mid, "label": m.get("name") or mid},
            })

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"query": query, "results": results[:limit]}

def promises(work: str = "main"):
    """P3-e1 Fix 1: 每条 promise 携带 overdue 字段(backend 单源,前端直读)。"""
    st = _store_for(work)
    proms = st.list_promises()
    mc = st.max_chapter()
    intent = st.get_intent()
    # 经 list_promises 补算窗口后 legacy slack 分支仅数据异常行可达,threshold 近似废弃,留防御
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    for p in proms:
        p["overdue"] = _overdue_flag(p, mc, slack)
    return proms

def promises_ledger(work: str = "main"):
    """作者工具 F-03 伏笔台账(单源):四栏(open/closed/red_herring/abandoned)+ 每条
    setup/payoff/overdue/跨度 + open/close bracket 完整性审计。
    overdue 阈值同 /promises、/quality(_overdue_flag 单源)。"""
    st = _store_for(work)
    intent = st.get_intent()
    # 经 list_promises 补算窗口后 legacy slack 分支仅数据异常行可达,threshold 近似废弃,留防御
    slack = intent.get("overdue_threshold") if intent.get("overdue_threshold") is not None else OVERDUE_SLACK
    return st.promise_ledger(slack)

def get_promise_ep(pid: str, work: str = "main"):
    """单条伏笔(type::record O(1),禁止 list_promises 全表扫)。"""
    row = _store_for(work).get_promise(pid)
    if not row:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return row

def motifs(work: str = "main"):
    return _store_for(work).list_motifs()

def get_motif_ep(mid: str, work: str = "main"):
    row = _store_for(work).get_motif(mid)
    if not row:
        raise HTTPException(status_code=404, detail=f"motif '{mid}' 不存在")
    return row

def motif_instances(chapter: int = Query(ge=1), work: str = "main"):
    """本章触及的母题:[{motif_id, name, evidence}]。ingest 抽取落库,未反哺的章返回空。"""
    return _store_for(work).list_motif_instances(chapter)

def motif_schedule_ep(seq: int = Query(ge=1), work: str = "main"):
    """相对即将写的章号 seq 的 heat 调度:must_echo / avoid_overuse / rows。"""
    return _store_for(work).motif_schedule(seq)

def motif_timeline_ep(mid: str, work: str = "main"):
    """单母题跨章触及史(chapter 升序)。母题不存在 → 404。"""
    st = _store_for(work)
    if not st.get_motif(mid):
        raise HTTPException(status_code=404, detail=f"motif '{mid}' 不存在")
    return st.list_motif_timeline(mid)

def get_char_anchors(character_id: str, work: str = "main"):
    """单角色的弧光锚(七键)+ 里程碑计划(按 target_chapter 有序)。"""
    st = _store_for(work)
    return {"anchors": st.char_anchors(character_id),
            "arc_plan": st.list_arc_plan(character_id)}

def patch_char_anchors(req: dict, work: str = "main"):
    """局部更新弧光锚:只写传入的键,未传字段不动(store 层 _ANCHOR_KEYS 白名单)。
    Task5-C④:角色不存在回 404,不再静默 200。
    Task7-C①:存在但非 character(如 place)同样 404,防误挂锚。"""
    st = _store_for(work)
    cid = req["character_id"]
    ent = st.entity(cid)
    if ent is None or ent.kind != "character":
        raise HTTPException(status_code=404, detail=f"角色 '{cid}' 不存在")
    st.set_char_anchors(cid, req.get("anchors") or {})
    return {"status": "updated"}

def post_arc_beat(req: dict, work: str = "main"):
    # Task5-C⑤:lie_belief_target 非 None 时须 0-100 数值,否则 422(应用层闸;DB 级 ASSERT 不做)
    lbt = req.get("lie_belief_target")
    if lbt is not None and (isinstance(lbt, bool)
                            or not isinstance(lbt, (int, float))
                            or not (0 <= lbt <= 100)):
        raise HTTPException(status_code=422,
                            detail="lie_belief_target 须为 0-100 的数值或不传")
    _store_for(work).add_arc_beat(
        req["character_id"], req["beat_name"], int(req["target_chapter"]),
        lbt, req.get("trigger_event") or "")
    return {"status": "created"}

def del_arc_beat(beat_id: str, work: str = "main"):
    _store_for(work).delete_arc_beat(beat_id)
    return {"status": "deleted"}

def forget_knowledge_ep(f: ForgetIn, work: str = "main"):
    _store_for(work).forget_knowledge(f.knower_id, f.proposition_id, f.until_chapter)
    return {"ok": True}

def add_prom(p: PromIn, work: str = "main"):
    tier = p.tier or "chapter"
    # 悬念存档答案强制(方案B任务21):book/arc 长期悬念必须在建伏笔时就写下真实答案,
    # 不能含糊留白;chapter 级短期悬念(本章内起落即兑现)豁免,向后兼容。
    if tier in ("book", "arc") and not (p.resolution and p.resolution.strip()):
        raise HTTPException(
            status_code=422,
            detail="悬念必须有文档记录的真实答案+预计回收章(tier=chapter 短期悬念豁免)")
    # B21 收尾清理批:plant_promise 已支持 resolution 落库,此处把已校验的字段透传;
    # 未传/空串时 or "" 保持向后兼容(store 层默认值不变)。返回稳定 id。
    try:
        planted = _store_for(work).plant_promise(
            p.text, p.setup_chapter, kind=p.promise_kind, tier=tier,
            resolution=p.resolution or "")
    except ValueError as e:  # 非法 tier → store 层 raise
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "id": planted.get("id"), "promise": planted}

def edit_prom(pid: str, p: PromIn, work: str = "main"):
    # P1-3:exclude_unset——只 SET 客户端真正提交的字段,未传字段保留库中旧值
    # (此前 promise_kind/setup_chapter 的默认值会静默把 red_herring 重置为 promise、setup 重置为 1)。
    sent = p.model_dump(exclude_unset=True)
    st = _store_for(work)
    fields: dict = {}
    if "text" in sent:
        fields["text"] = sent["text"]
    if "setup_chapter" in sent:
        fields["setup_chapter"] = sent["setup_chapter"]
    if "promise_kind" in sent:  # 端点入参名 promise_kind ↔ store 字段名 kind
        fields["kind"] = sent["promise_kind"]
    if sent.get("tier") is not None:  # 仅显式改 tier 时透传(缺省保留既有层级,由 update_promise 重算窗口)
        fields["tier"] = sent["tier"]
    if sent.get("resolution") is not None:  # B21 收尾清理批:PATCH 也可补写悬念真实答案
        fields["resolution"] = sent["resolution"]
    # B21 收尾清理批(审查发现的绕过口):把 tier 改成 book/arc 等于把短期悬念升格成
    # 长期悬念,须与 /promises-new 同约束——显式传入 tier∈{book,arc} 且改后无 resolution
    # (请求里没带、库里也没有)→ 422。pid 不存在时不在此拦(交给下面 404,语义更准)。
    if sent.get("tier") in ("book", "arc") and not (sent.get("resolution") or "").strip():
        row = next((x for x in st.list_promises() if x["id"] == pid), None)
        if row is not None and not (row.get("resolution") or "").strip():
            raise HTTPException(
                status_code=422,
                detail="悬念必须有文档记录的真实答案+预计回收章(tier=chapter 短期悬念豁免)")
    try:
        found = st.update_promise(pid, fields)
    except ValueError as e:  # 非法 tier → store 层 raise
        raise HTTPException(status_code=422, detail=str(e))
    if not found:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return {"ok": True}

def del_prom(pid: str, work: str = "main"):
    found = _store_for(work).delete_promise(pid)
    if not found:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return {"ok": True}

def advance_prom(pid: str, body: AdvanceIn, work: str = "main"):
    """回收伏笔(作者直编):标 closed + payoff_chapter。payoff≥setup 校验。"""
    try:
        _store_for(work).advance_promise(pid, body.payoff_chapter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}

def mark_herring(pid: str, work: str = "main"):
    """将伏笔标记为障眼法(red_herring)。伏笔不存在→404。"""
    try:
        found = _store_for(work).mark_promise_herring(pid)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not found:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return {"ok": True}

def abandon_prom(pid: str, work: str = "main"):
    """弃置伏笔:status→abandoned(账本结案,≠障眼法,≠兑现)。不存在→404。"""
    found = _store_for(work).abandon_promise(pid)
    if not found:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return {"ok": True, "status": "abandoned"}

def promise_timeline(pid: str, work: str = "main"):
    """单条伏笔时间线投影:plant/clue/touch/closed/abandoned 按章排序。"""
    tl = _store_for(work).promise_timeline(pid)
    if tl is None:
        raise HTTPException(status_code=404, detail=f"promise '{pid}' 不存在")
    return tl

def add_promise_clue(pid: str, body: ClueIn, work: str = "main"):
    """追加草蛇灰线中途线索到某条伏笔。body:{note, chapter}。
    R2.4: chapter 必须 >= setup_chapter;若 payoff 已设则也须 <= payoff_chapter。
    同时写 promise_touch(与 brief refresh 同源)。
    """
    st = _store_for(work)
    # R2.4: 先取 promise 的 setup/payoff 章号做范围校验
    prom = st.get_promise(pid)
    if prom is None:
        raise HTTPException(status_code=422, detail=f"promise '{pid}' 不存在")
    setup = prom.get("setup_chapter", 1)
    payoff = prom.get("payoff_chapter")
    if body.chapter < setup:
        raise HTTPException(
            status_code=422,
            detail=f"clue.chapter({body.chapter}) < setup_chapter({setup}):线索不能早于埋设章"
        )
    if payoff is not None and body.chapter > payoff:
        raise HTTPException(
            status_code=422,
            detail=f"clue.chapter({body.chapter}) > payoff_chapter({payoff}):线索不能晚于回收章"
        )
    try:
        st.add_promise_clue(pid, body.note, body.chapter)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}

def remove_promise_clue(pid: str, idx: int, work: str = "main"):
    """按下标(0-based)删除某条伏笔的线索。"""
    try:
        _store_for(work).remove_promise_clue(pid, idx)
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}

def setting_completeness(work: str = "main"):
    return _store_for(work).setting_completeness()

def entity_relations_ep(entity: str | None = None, chapter: int | None = None,
                        reveal_secret: bool = False, work: str = "main"):
    st = _store_for(work)
    rows = st.entity_relations_at(chapter, entity) if chapter is not None \
        else st.list_entity_relations(entity)
    return [_mask_field(dict(r), "truth", "truth_secret", reveal_secret) for r in rows]

def add_entity_relation_ep(req: dict, work: str = "main"):
    a = req.get("a")
    b = req.get("b")
    relation_type = req.get("relation_type")
    if not a or not b or not relation_type:
        raise HTTPException(status_code=422, detail="缺少必填字段: a/b/relation_type")
    if relation_type not in ENTITY_RELATION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"relation_type={relation_type!r} 非法(合法值: {list(ENTITY_RELATION_TYPES)})")

    sent = dict(req)
    # 掩码哨兵(Task 3 的血泪教训在此表复现):前端整行回传时 truth 若仍是掩码占位符
    # (未被作者真正编辑),绝不能把它当真值落库——那会把库里的真相永久覆盖成字面
    # "🔒 私密"。pop 掉即可:store.add_entity_relation 对未传字段走 MERGE 保留旧值。
    if sent.get("truth") == _SECRET_MASK:
        sent.pop("truth", None)

    kwargs = {k: sent[k] for k in
              ("perception_a", "perception_b", "truth", "truth_secret", "since_chapter")
              if k in sent}
    st = _store_for(work)
    try:
        st.add_entity_relation(a, b, relation_type, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"ok": True}

def del_entity_relation_ep(a: str, b: str, work: str = "main"):
    _store_for(work).delete_entity_relation(a, b)
    return {"ok": True}

def char_states(character_id: str, work: str = "main"):
    return _store_for(work).list_char_states(character_id)

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

def char_state_at(character_id: str, chapter: int, work: str = "main"):
    """查询角色在某章时刻的完整状态快照(时点查询,设计文档 §3.6)。
    返回该章时刻的能力/关系/性格/弧光阶段。"""
    return _store_for(work).char_state_at(character_id, chapter)

def get_voice_profile_endpoint(character_id: str, work: str = "main"):
    """获取角色声线指纹(9节 voice_profile,设计文档 §3.1.2)。
    批D P1-11 后端跟进:此前 store.get_voice_profile 无 REST 暴露 → 前端声线指纹只在
    fold 响应里一次性展示、刷新不回显。补此 GET(镜像 /char-states)让指纹常驻回显。
    角色无指纹时返回 null(不 500),前端据此隐藏声音区或提示尚未建立。"""
    return _store_for(work).get_voice_profile(character_id)

def add_motif_ep(m: MotifIn, work: str = "main"):
    name = (m.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name required")
    _store_for(work).add_motif(
        name, m.theme, m.echoes, m.unfolding,
        echo_terms=m.echo_terms, phase=m.phase or "seed",
        tier=m.tier or "book", scope=m.scope)
    return {"ok": True}

def edit_motif(mid: str, m: MotifIn, work: str = "main"):
    st = _store_for(work)
    fields = m.model_dump(exclude_unset=True)
    if "name" in fields and not str(fields.get("name") or "").strip():
        raise HTTPException(status_code=422, detail="name required")
    if not st.patch_motif(mid, fields):
        raise HTTPException(status_code=404, detail=f"motif '{mid}' 不存在")
    return {"ok": True}

def del_motif(mid: str, work: str = "main"):
    st = _store_for(work)
    row = st.get_motif(mid)
    if not row:
        raise HTTPException(status_code=404, detail=f"motif '{mid}' 不存在")
    st.delete_motif(row["id"])
    return {"ok": True}

def voice_flags(work: str = "main"):
    return _store_for(work).list_voice_flags("open")

def resolve_voice_flag_endpoint(fid: str, work: str = "main"):
    """关闭声音演变 flag(status: open → done)。flag 不存在→404。"""
    found = _store_for(work).resolve_voice_flag(fid)
    if not found:
        raise HTTPException(status_code=404, detail=f"voice_evolution_flag '{fid}' 不存在")
    return {"ok": True}

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

def graph(chapter: int | None = None, focus: str | None = None,
          limit: int = Query(default=300, ge=1, le=2000), hop: int = Query(default=1, ge=1, le=3),
          work: str = "main"):
    """知识图谱:角色/命题节点 + knows/关系 边(Atlas 视图)。
    Phase0-BE1(千万字基座):默认不再无上限全图返回。
    - focus 给定 → 该实体 ego 子图(focus + hop 跳邻居 + 它们之间的边)。
    - focus 为 None → top-limit 重要度子集(secret 优先),节点总数硬上限 limit。
    - chapter 时间门保留(截至该章;省略=全书)。"""
    return _store_for(work).graph(chapter=chapter, focus=focus, limit=limit, hop=hop)



def _bind_and_register() -> None:
    """Rebind handlers onto app_impl globals so monkeypatch keeps working."""
    from scribe3.api import app_impl as core
    g = globals()
    _fn = g['object_impact_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'object_impact_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'object_impact_ep', _re)
    g['object_impact_ep'] = _re
    router.add_api_route('/objects/{object_type}/{object_id}/impact', _re, methods=['GET'], name='object_impact_ep')

    _fn = g['object_delete_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'object_delete_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'object_delete_ep', _re)
    g['object_delete_ep'] = _re
    router.add_api_route('/objects/{object_type}/{object_id}', _re, methods=['DELETE'], name='object_delete_ep')

    _fn = g['object_archive_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'object_archive_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'object_archive_ep', _re)
    g['object_archive_ep'] = _re
    router.add_api_route('/objects/{object_type}/{object_id}/archive', _re, methods=['POST'], name='object_archive_ep')

    _fn = g['entities']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'entities', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'entities', _re)
    g['entities'] = _re
    router.add_api_route('/entities', _re, methods=['GET'], name='entities')

    _fn = g['events']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'events', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'events', _re)
    g['events'] = _re
    router.add_api_route('/events', _re, methods=['GET'], name='events')

    _fn = g['patch_event_narrative']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'patch_event_narrative', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'patch_event_narrative', _re)
    g['patch_event_narrative'] = _re
    router.add_api_route('/events/{eid}/narrative', _re, methods=['PATCH'], name='patch_event_narrative')

    _fn = g['patch_event_causal_root']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'patch_event_causal_root', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'patch_event_causal_root', _re)
    g['patch_event_causal_root'] = _re
    router.add_api_route('/events/{eid}/causal-root', _re, methods=['PATCH'], name='patch_event_causal_root')

    _fn = g['patch_event_causal']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'patch_event_causal', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'patch_event_causal', _re)
    g['patch_event_causal'] = _re
    router.add_api_route('/events/{eid}/causal', _re, methods=['PATCH'], name='patch_event_causal')

    _fn = g['timeline']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'timeline', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'timeline', _re)
    g['timeline'] = _re
    router.add_api_route('/timeline', _re, methods=['GET'], name='timeline')

    _fn = g['frame']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'frame', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'frame', _re)
    g['frame'] = _re
    router.add_api_route('/frame', _re, methods=['GET'], name='frame')

    _fn = g['irony']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'irony', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'irony', _re)
    g['irony'] = _re
    router.add_api_route('/irony', _re, methods=['GET'], name='irony')

    _fn = g['causal']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'causal', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'causal', _re)
    g['causal'] = _re
    router.add_api_route('/causal', _re, methods=['GET'], name='causal')

    _fn = g['recall']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'recall', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'recall', _re)
    g['recall'] = _re
    router.add_api_route('/recall', _re, methods=['GET'], name='recall')

    _fn = g['global_search']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'global_search', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'global_search', _re)
    g['global_search'] = _re
    router.add_api_route('/search', _re, methods=['GET'], name='global_search')

    _fn = g['promises']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'promises', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'promises', _re)
    g['promises'] = _re
    router.add_api_route('/promises', _re, methods=['GET'], name='promises')

    _fn = g['promises_ledger']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'promises_ledger', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'promises_ledger', _re)
    g['promises_ledger'] = _re
    router.add_api_route('/promises/ledger', _re, methods=['GET'], name='promises_ledger')

    _fn = g['get_promise_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_promise_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_promise_ep', _re)
    g['get_promise_ep'] = _re
    router.add_api_route('/promises/{pid}', _re, methods=['GET'], name='get_promise_ep')

    _fn = g['motifs']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'motifs', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'motifs', _re)
    g['motifs'] = _re
    router.add_api_route('/motifs', _re, methods=['GET'], name='motifs')

    _fn = g['get_motif_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_motif_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_motif_ep', _re)
    g['get_motif_ep'] = _re
    router.add_api_route('/motifs/{mid}', _re, methods=['GET'], name='get_motif_ep')

    _fn = g['motif_instances']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'motif_instances', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'motif_instances', _re)
    g['motif_instances'] = _re
    router.add_api_route('/motif-instances', _re, methods=['GET'], name='motif_instances')

    _fn = g['motif_schedule_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'motif_schedule_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'motif_schedule_ep', _re)
    g['motif_schedule_ep'] = _re
    router.add_api_route('/motif-schedule', _re, methods=['GET'], name='motif_schedule_ep')

    _fn = g['motif_timeline_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'motif_timeline_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'motif_timeline_ep', _re)
    g['motif_timeline_ep'] = _re
    router.add_api_route('/motifs/{mid}/timeline', _re, methods=['GET'], name='motif_timeline_ep')

    _fn = g['get_char_anchors']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_char_anchors', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_char_anchors', _re)
    g['get_char_anchors'] = _re
    router.add_api_route('/char-anchors', _re, methods=['GET'], name='get_char_anchors')

    _fn = g['patch_char_anchors']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'patch_char_anchors', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'patch_char_anchors', _re)
    g['patch_char_anchors'] = _re
    router.add_api_route('/char-anchors', _re, methods=['PATCH'], name='patch_char_anchors')

    _fn = g['post_arc_beat']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'post_arc_beat', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'post_arc_beat', _re)
    g['post_arc_beat'] = _re
    router.add_api_route('/arc-beats', _re, methods=['POST'], name='post_arc_beat')

    _fn = g['del_arc_beat']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_arc_beat', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_arc_beat', _re)
    g['del_arc_beat'] = _re
    router.add_api_route('/arc-beats/{beat_id}', _re, methods=['DELETE'], name='del_arc_beat')

    _fn = g['forget_knowledge_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'forget_knowledge_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'forget_knowledge_ep', _re)
    g['forget_knowledge_ep'] = _re
    router.add_api_route('/knowledge/forget', _re, methods=['POST'], name='forget_knowledge_ep')

    _fn = g['add_prom']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_prom', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_prom', _re)
    g['add_prom'] = _re
    router.add_api_route('/promises-new', _re, methods=['POST'], name='add_prom')

    _fn = g['edit_prom']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'edit_prom', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'edit_prom', _re)
    g['edit_prom'] = _re
    router.add_api_route('/promises/{pid}', _re, methods=['PATCH'], name='edit_prom')

    _fn = g['del_prom']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_prom', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_prom', _re)
    g['del_prom'] = _re
    router.add_api_route('/promises/{pid}', _re, methods=['DELETE'], name='del_prom')

    _fn = g['advance_prom']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'advance_prom', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'advance_prom', _re)
    g['advance_prom'] = _re
    router.add_api_route('/promises/{pid}/advance', _re, methods=['POST'], name='advance_prom')

    _fn = g['mark_herring']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'mark_herring', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'mark_herring', _re)
    g['mark_herring'] = _re
    router.add_api_route('/promises/{pid}/mark-herring', _re, methods=['POST'], name='mark_herring')

    _fn = g['abandon_prom']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'abandon_prom', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'abandon_prom', _re)
    g['abandon_prom'] = _re
    router.add_api_route('/promises/{pid}/abandon', _re, methods=['POST'], name='abandon_prom')

    _fn = g['promise_timeline']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'promise_timeline', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'promise_timeline', _re)
    g['promise_timeline'] = _re
    router.add_api_route('/promises/{pid}/timeline', _re, methods=['GET'], name='promise_timeline')

    _fn = g['add_promise_clue']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_promise_clue', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_promise_clue', _re)
    g['add_promise_clue'] = _re
    router.add_api_route('/promises/{pid}/clues', _re, methods=['POST'], name='add_promise_clue')

    _fn = g['remove_promise_clue']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'remove_promise_clue', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'remove_promise_clue', _re)
    g['remove_promise_clue'] = _re
    router.add_api_route('/promises/{pid}/clues/{idx}', _re, methods=['DELETE'], name='remove_promise_clue')

    _fn = g['setting_completeness']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'setting_completeness', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'setting_completeness', _re)
    g['setting_completeness'] = _re
    router.add_api_route('/setting-completeness', _re, methods=['GET'], name='setting_completeness')

    _fn = g['entity_relations_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'entity_relations_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'entity_relations_ep', _re)
    g['entity_relations_ep'] = _re
    router.add_api_route('/entity-relations', _re, methods=['GET'], name='entity_relations_ep')

    _fn = g['add_entity_relation_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_entity_relation_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_entity_relation_ep', _re)
    g['add_entity_relation_ep'] = _re
    router.add_api_route('/entity-relations', _re, methods=['POST'], name='add_entity_relation_ep')

    _fn = g['del_entity_relation_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_entity_relation_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_entity_relation_ep', _re)
    g['del_entity_relation_ep'] = _re
    router.add_api_route('/entity-relations', _re, methods=['DELETE'], name='del_entity_relation_ep')

    _fn = g['char_states']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'char_states', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'char_states', _re)
    g['char_states'] = _re
    router.add_api_route('/char-states', _re, methods=['GET'], name='char_states')

    _fn = g['add_char_state_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_char_state_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_char_state_endpoint', _re)
    g['add_char_state_endpoint'] = _re
    router.add_api_route('/char-states', _re, methods=['POST'], name='add_char_state_endpoint')

    _fn = g['char_state_at']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'char_state_at', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'char_state_at', _re)
    g['char_state_at'] = _re
    router.add_api_route('/char-state-at', _re, methods=['GET'], name='char_state_at')

    _fn = g['get_voice_profile_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'get_voice_profile_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'get_voice_profile_endpoint', _re)
    g['get_voice_profile_endpoint'] = _re
    router.add_api_route('/voice-profile', _re, methods=['GET'], name='get_voice_profile_endpoint')

    _fn = g['add_motif_ep']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'add_motif_ep', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'add_motif_ep', _re)
    g['add_motif_ep'] = _re
    router.add_api_route('/motifs-new', _re, methods=['POST'], name='add_motif_ep')

    _fn = g['edit_motif']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'edit_motif', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'edit_motif', _re)
    g['edit_motif'] = _re
    router.add_api_route('/motifs/{mid}', _re, methods=['PATCH'], name='edit_motif')

    _fn = g['del_motif']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'del_motif', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'del_motif', _re)
    g['del_motif'] = _re
    router.add_api_route('/motifs/{mid}', _re, methods=['DELETE'], name='del_motif')

    _fn = g['voice_flags']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'voice_flags', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'voice_flags', _re)
    g['voice_flags'] = _re
    router.add_api_route('/voice-flags', _re, methods=['GET'], name='voice_flags')

    _fn = g['resolve_voice_flag_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'resolve_voice_flag_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'resolve_voice_flag_endpoint', _re)
    g['resolve_voice_flag_endpoint'] = _re
    router.add_api_route('/voice-flags/{fid}/resolve', _re, methods=['POST'], name='resolve_voice_flag_endpoint')

    _fn = g['fold_voice_flags_endpoint']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'fold_voice_flags_endpoint', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'fold_voice_flags_endpoint', _re)
    g['fold_voice_flags_endpoint'] = _re
    router.add_api_route('/voice-flags/fold', _re, methods=['POST'], name='fold_voice_flags_endpoint')

    _fn = g['graph']
    _re = types.FunctionType(_fn.__code__, core.__dict__, 'graph', _fn.__defaults__, _fn.__closure__)
    if _fn.__annotations__:
        _re.__annotations__ = dict(_fn.__annotations__)
    setattr(core, 'graph', _re)
    g['graph'] = _re
    router.add_api_route('/graph', _re, methods=['GET'], name='graph')

_bind_and_register()
