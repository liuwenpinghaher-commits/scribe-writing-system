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


def apply_delta(store, delta: dict, seq: int) -> int:
    """把知识 delta 落到 store:新知→当事人知道;所为→当事人+在场者知道。返回应用条数。
    章级幂等:先清本章既有 ingest 产出,再重写——重复 ingest 不会残留悬挂边。
    P2-E1: 每条命题同时写 reader_knows(叙述揭示即读者已知,戏剧反讽闭环)。"""
    store.purge_ingest(seq)
    n = 0
    for i, it in enumerate(delta.get("learned") or []):
        who, fact = it.get("who"), it.get("fact")
        if not who or not fact:
            continue
        oid = _resolve_char(store, who, seq, "learned_who")
        if oid is None:
            continue
        fid = f"fact:k{seq}-{i}"
        store.add_fact(Fact(fid, oid, "获知", fact, valid_from=seq), ingest_seq=seq)
        store.add_knowledge(KnowledgeEdge(oid, fid, since_chapter=seq, acquired_via="learned"),
                           ingest_seq=seq)
        # 叙述揭示即读者已知:reader_knows 随 ingest_seq 参与幂等 purge
        try:
            store.add_knowledge(KnowledgeEdge("reader", fid, since_chapter=seq,
                                              acquired_via="narrated"),
                                ingest_seq=seq)
        except Exception as _e:
            import logging
            logging.getLogger("scribe3.ingest").warning(
                "reader_knows 写入失败(non-fatal),命题 %s: %s", fid, _e)
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
    return n


def ingest_chapter(store, seq: int, complete_fn) -> dict:
    """读某章正文 → Hermes 抽知识 delta → 应用到 store。
    若 parse_knowledge_delta 返回 None(坏 JSON / 截断),不调用 apply_delta(不 purge),
    返回 parse_failed=True——保留本章既有知识,避免静默数据丢失。"""
    ch = store.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"applied": 0, "delta": {"learned": [], "did": [], "voice_shift": []}}
    delta = parse_knowledge_delta(complete_fn(build_knowledge_extract_prompt(ch["prose"])))
    if delta is None:
        return {"applied": -1, "parse_failed": True, "delta": None}
    return {"applied": apply_delta(store, delta, seq), "delta": delta}
