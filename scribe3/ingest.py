"""章节回写(ingest):读定稿 → 抽"谁新知道什么/做了什么" → 更新知识账本(单一真相源)。

闭合写循环:主编对话写作 → 存 → ingest → 世界知识态更新 → 下章限知帧反映新知。
看见即知道:learned 给当事人发知识边;did 给当事人 + 在场 seen_by 都发边。
apply_delta 纯应用(可测,不连网);ingest_chapter 走 Hermes 抽取。
"""
from __future__ import annotations

from scribe3.critique import build_knowledge_extract_prompt, parse_knowledge_delta
from scribe3.ontology import Entity, Fact, KnowledgeEdge


def _resolve_char(store, name: str, seq: int, role: str) -> str | None:
    """解析角色:已存在返回 oid;不存在则登记待确认,返回 None(不建实体、不发边)。
    替换原 _ensure_char(不验即建,致幻觉角色污染 characters())。"""
    oid = f"role:{name}"
    if store.entity(oid) is not None:
        return oid
    store.add_unverified_ref(name, seq, role)
    return None


def _resolve_motif(store, name: str) -> str | None:
    """按名精确匹配已立母题,返回 motif_id;匹配不到返回 None(不建母题,与 _resolve_char 同范式)。"""
    needle = (name or "").strip()
    if not needle:
        return None
    for m in store.list_motifs():
        if (m.get("name") or "").strip() == needle:
            return m.get("id")
    return None


def _resolve_promise(open_rows: list[dict], text: str) -> str | None:
    """在给定 open 伏笔候选里按原文匹配,返回 promise id;匹配不到返回 None。
    Task5-B①:抽取 prompt 里伏笔文案截断到 40 字,>40 字伏笔 LLM 只能回截断键——
    故支持截断键匹配:needle == text.strip() 或(needle == text.strip()[:40] 且该前缀
    在候选集内唯一命中;多条同前 40 字则歧义跳过,零误匹配)。
    Task5-B③:候选由调用方传入(复用 ingest_chapter 已取的 open_promises),免每条触及重查整表。"""
    needle = (text or "").strip()
    if not needle:
        return None
    prefix_hits: list[str] = []
    for p in open_rows:
        t = (p.get("text") or "").strip()
        if t == needle:
            return p.get("id")
        if len(t) > 40 and t[:40] == needle:
            prefix_hits.append(p.get("id"))
    if len(prefix_hits) == 1:
        return prefix_hits[0]
    return None


def _find_existing_learned_prop(store, fact_text: str) -> str | None:
    """在已有命题中查找与 fact_text 近精确匹配的"获知"类命题,返回其 oid 或 None。
    S3 去重策略:保守近精确匹配(归一化后完全相等,或长文本的包含关系),
    不使用语义相似度以防误合并——正确性优先于激进去重。
    fail-safe:任何异常返回 None(调用方继续创建新命题)。"""
    import logging
    _log = logging.getLogger("scribe3.ingest")
    try:
        # 归一化:去首尾空白
        needle = fact_text.strip()
        if not needle:
            return None
        # 全量扫描"获知"命题(数量通常较少)
        rows = store._query(
            "SELECT meta::id(id) AS local, value FROM proposition "
            "WHERE attribute = '获知'")
        for r in rows:
            existing = (r.get("value") or "").strip()
            if not existing:
                continue
            # 近精确:完全相等,或长文本互相包含(≥15字时才启用包含检查)
            if existing == needle:
                return f"fact:{r['local']}"
            if len(needle) >= 15 and len(existing) >= 15:
                if needle in existing or existing in needle:
                    return f"fact:{r['local']}"
    except Exception as e:
        _log.warning("learned 去重查找失败(fail-safe,将新建命题): %s", e)
    return None


def apply_delta(store, delta: dict, seq: int,
                open_promises: list[dict] | None = None) -> int:
    """把知识 delta 落到 store:新知→当事人知道;所为→当事人+在场者知道。返回应用条数。
    章级幂等:先清本章既有 ingest 产出,再重写——重复 ingest 不会残留悬挂边。
    P2-E1: 每条命题同时写 reader_knows(叙述揭示即读者已知,戏剧反讽闭环)。
    S3: learned 类命题去重——近精确匹配到已有客观命题时复用,只新发 knows 边。"""
    import logging
    _log = logging.getLogger("scribe3.ingest")
    store.purge_ingest(seq)
    n = 0
    for i, it in enumerate(delta.get("learned") or []):
        who, fact = it.get("who"), it.get("fact")
        if not who or not fact:
            continue
        oid = _resolve_char(store, who, seq, "learned_who")
        if oid is None:
            continue
        # S3: 尝试复用已有近精确命题(消重复真相)
        existing_fid = _find_existing_learned_prop(store, fact)
        if existing_fid is not None:
            # 复用:只发 knows 边,不创建新命题
            fid = existing_fid
            _log.debug("learned 去重:复用命题 %s (文本近似 %r)", fid, fact[:30])
        else:
            # 新建客观命题
            fid = f"fact:k{seq}-{i}"
            store.add_fact(Fact(fid, oid, "获知", fact, valid_from=seq), ingest_seq=seq)
            # reader_knows:新建命题才需要写 reader 边;复用已有命题的 reader 边已存在
            try:
                store.add_knowledge(KnowledgeEdge("reader", fid, since_chapter=seq,
                                                  acquired_via="narrated"),
                                    ingest_seq=seq)
            except Exception as _e:
                _log.warning("reader_knows 写入失败(non-fatal),命题 %s: %s", fid, _e)
        store.add_knowledge(KnowledgeEdge(oid, fid, since_chapter=seq, acquired_via="learned"),
                           ingest_seq=seq)
        n += 1
    for j, it in enumerate(delta.get("did") or []):
        who, action = it.get("who"), it.get("action")
        if not who or not action:
            continue
        actor = _resolve_char(store, who, seq, "did_who")
        if actor is None:
            continue
        fid = f"fact:d{seq}-{j}"
        store.add_fact(Fact(fid, actor, "行动", action, valid_from=seq), ingest_seq=seq)
        for w in [who] + list(it.get("seen_by") or []):
            woid = _resolve_char(store, w, seq, "seen_by")
            if woid is None:
                continue
            store.add_knowledge(KnowledgeEdge(woid, fid,
                                              since_chapter=seq, acquired_via="saw"),
                                ingest_seq=seq)
        # 叙述揭示即读者已知:did 类事件读者也知道
        try:
            store.add_knowledge(KnowledgeEdge("reader", fid, since_chapter=seq,
                                              acquired_via="narrated"),
                                ingest_seq=seq)
        except Exception as _e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "reader_knows 写入失败(non-fatal),命题 %s: %s", fid, _e)
        n += 1
    for it in delta.get("voice_shift") or []:
        who, reason = it.get("who"), it.get("reason")
        if who and reason and hasattr(store, "add_voice_flag"):
            store.add_voice_flag(who, seq, reason)   # 只标记(角色名),不生成独白
    # G4: 自动从正文抽取角色弧光(char_state)——边写边长出弧光,反哺下一章约束
    for it in delta.get("arc") or []:
        who = it.get("who")
        change_type = it.get("change_type")
        summary = it.get("summary")
        snapshot = it.get("snapshot")
        if not (who and change_type and summary):
            continue
        if change_type not in ("ability", "relation", "personality", "composite"):
            continue
        oid = _resolve_char(store, who, seq, "arc_who")
        if oid is None:
            continue
        # snapshot → after_state 按 change_type 归入对应键
        after_state: dict = {}
        if snapshot:
            if change_type == "ability":
                after_state = {"ability_snapshot": snapshot}
            elif change_type == "relation":
                after_state = {"relation_snapshot": snapshot}
            elif change_type == "personality":
                after_state = {"personality_snapshot": snapshot if isinstance(snapshot, str)
                               else str(snapshot)}
            else:  # composite
                after_state = snapshot if isinstance(snapshot, dict) else {}
        try:
            store.add_char_state(
                character_id=oid,
                chapter=seq,
                change_type=change_type,
                summary=summary,
                after_state=after_state or None,
                confidence="inferred",
                ingest_seq=seq,
            )
        except Exception as _arc_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "char_state 写入失败(non-fatal),角色 %s 章 %s: %s", who, seq, _arc_e)
    # 伏笔母题章感知:抽本章触及的已立母题 → 落 motif_instance(只在已立母题里选)
    for it in delta.get("motif") or []:
        name = it.get("motif") or it.get("name")
        if not name:
            continue
        mid = _resolve_motif(store, name)
        if mid is None:
            continue   # 解析不到的母题名跳过(fail-safe,不建母题)
        try:
            store.add_motif_instance(mid, chapter=seq,
                                     evidence=it.get("evidence") or "", ingest_seq=seq)
        except Exception as _mi_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "motif_instance 写入失败(non-fatal),母题 %s 章 %s: %s", name, seq, _mi_e)
    # 伏笔章触及:抽本章推进的已埋 open 伏笔 → promise_touch(只在已埋伏笔里选)
    # ingest_seq=seq 必须显式传:缺省=手动登记不可 purge,re-ingest 会双计 refresh_count
    touches = delta.get("promise_touch") or []
    if touches and open_promises is None:
        open_promises = store.open_promises()   # 调用方未传时兜底,只查一次
    for it in touches:
        pid = _resolve_promise(open_promises or [], it.get("text") or "")
        if pid is None:
            continue   # 解析不到的伏笔原文跳过(fail-safe,不建伏笔)
        try:
            store.add_promise_touch(pid, chapter=seq,
                                    evidence=it.get("evidence") or "", ingest_seq=seq)
        except Exception as _pt_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "promise_touch 写入失败(non-fatal),伏笔 %s 章 %s: %s", it.get("text"), seq, _pt_e)
    # Task5: lie_belief 位移——有 lie 锚角色本章的信念信奉度 → char_state(change_type='belief')
    # 值入库前 clamp [0,100](store 不钳,调用方负责);解析不到的角色跳过(同 _resolve_char 范式)
    for it in delta.get("belief") or []:
        who, value = it.get("who"), it.get("value")
        if not who or not isinstance(value, (int, float)):
            continue
        oid = _resolve_char(store, who, seq, "belief_who")
        if oid is None:
            continue
        try:
            store.add_char_state(character_id=oid, chapter=seq, change_type="belief",
                                 summary=it.get("why") or "信念位移",
                                 lie_belief=int(max(0, min(100, value))),
                                 confidence="inferred", ingest_seq=seq)
        except Exception as _b_e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "belief 写入失败(non-fatal),角色 %s 章 %s: %s", who, seq, _b_e)
    return n


def ingest_chapter(store, seq: int, complete_fn, max_attempts: int = 3) -> dict:
    """读某章正文 → Hermes 抽知识 delta → 应用到 store。
    抽取是非确定的:长 JSON 偶发截断/坏格式 → parse 返回 None。单次尝试会零星 parse_failed,
    故重试至多 max_attempts 次(每次重新抽取);全失败才返回 parse_failed=True(不 purge,保留既有知识)。"""
    ch = store.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"applied": 0, "delta": {"learned": [], "did": [], "voice_shift": []}}
    motif_names = [m.get("name") for m in store.list_motifs() if m.get("name")]
    promise_items = [{"id": p["id"], "text": p["text"]} for p in store.open_promises()]
    # Task5: 收集有 lie 锚的角色 → prompt belief 段(只评这些角色的信念信奉度)
    belief_chars = []
    for c in store.characters():
        a = store.char_anchors(c.id)
        if a.get("lie"):
            belief_chars.append({"name": c.name, "lie": a["lie"]})
    prompt = build_knowledge_extract_prompt(ch["prose"], motif_names=motif_names,
                                            promise_items=promise_items,
                                            belief_chars=belief_chars)
    delta = None
    for _ in range(max(1, max_attempts)):
        delta = parse_knowledge_delta(complete_fn(prompt))
        if delta is not None:
            break
    if delta is None:
        return {"applied": -1, "parse_failed": True, "delta": None}
    return {"applied": apply_delta(store, delta, seq, open_promises=promise_items),
            "delta": delta}
