"""章节回写(ingest):读定稿 → 抽"谁新知道什么/做了什么" → 更新知识账本(单一真相源)。

闭合写循环:render → 存 → ingest → 世界知识态更新 → 下章限知渲染反映新知。
看见即知道:learned 给当事人发知识边;did 给当事人 + 在场 seen_by 都发边。
apply_delta 纯应用(可测,不连网);ingest_chapter 走 Hermes 抽取。
"""
from __future__ import annotations

from scribe3.critique import build_knowledge_extract_prompt, parse_knowledge_delta
from scribe3.ontology import Entity, Fact, KnowledgeEdge


def _ensure_char(store, name: str) -> str:
    """保证角色实体存在(知识边 RELATE 需端点存在);返回其 oid。"""
    oid = f"role:{name}"
    if store.entity(oid) is None:
        store.add_entity(Entity(oid, "character", name))
    return oid


def apply_delta(store, delta: dict, seq: int) -> int:
    """把知识 delta 落到 store:新知→当事人知道;所为→当事人+在场者知道。返回应用条数。"""
    n = 0
    for i, it in enumerate(delta.get("learned") or []):
        who, fact = it.get("who"), it.get("fact")
        if not who or not fact:
            continue
        oid = _ensure_char(store, who)
        fid = f"fact:k{seq}-{i}"
        store.add_fact(Fact(fid, oid, "新知", fact, valid_from=seq))
        store.add_knowledge(KnowledgeEdge(oid, fid, since_chapter=seq, acquired_via="learned"))
        n += 1
    for j, it in enumerate(delta.get("did") or []):
        who, action = it.get("who"), it.get("action")
        if not who or not action:
            continue
        actor = _ensure_char(store, who)
        fid = f"fact:d{seq}-{j}"
        store.add_fact(Fact(fid, actor, "所为", action, valid_from=seq))
        for w in [who] + list(it.get("seen_by") or []):
            store.add_knowledge(KnowledgeEdge(_ensure_char(store, w), fid,
                                              since_chapter=seq, acquired_via="saw"))
        n += 1
    for it in delta.get("voice_shift") or []:
        who, reason = it.get("who"), it.get("reason")
        if who and reason and hasattr(store, "add_voice_flag"):
            store.add_voice_flag(who, seq, reason)   # 只标记(角色名),不生成独白
    return n


def ingest_chapter(store, seq: int, complete_fn) -> dict:
    """读某章正文 → Hermes 抽知识 delta → 应用到 store。"""
    ch = store.get_chapter(seq)
    if not ch or not ch.get("prose"):
        return {"applied": 0, "delta": {"learned": [], "did": [], "voice_shift": []}}
    delta = parse_knowledge_delta(complete_fn(build_knowledge_extract_prompt(ch["prose"])))
    return {"applied": apply_delta(store, delta, seq), "delta": delta}
