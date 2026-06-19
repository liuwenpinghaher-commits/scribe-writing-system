"""混合检索(实现4 · C2-5)—— 关键词 + 向量 + 图(关系/时间线)三路召回 + RRF 融合。

RRF(Reciprocal Rank Fusion):score(d)=Σ 1/(k0+rank_i(d)),对多路排序鲁棒融合,无需归一化分数。
reciprocal_rank_fusion 为纯函数,可离线单测;hybrid_search 组合三路(向量路可缺省)。
"""
from __future__ import annotations

import re


def reciprocal_rank_fusion(ranked_lists: list[list[str]], k0: int = 60) -> list[tuple[str, float]]:
    """输入多路排好序的 id 列表,输出融合后的 [(id, score)] 降序。"""
    scores: dict[str, float] = {}
    for lst in ranked_lists:
        for rank, doc_id in enumerate(lst):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k0 + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


def _keywords(query: str) -> list[str]:
    return [w for w in re.split(r"[，,。;；、\s]+", query or "") if 2 <= len(w) <= 12][:6]


def keyword_search(db, work_id: str, query: str, k: int = 10) -> list[tuple[str, str]]:
    """关键词路:正文段落 LIKE 命中。返回 [(segment_id, content)]。"""
    kws = _keywords(query) or ([query] if query else [])
    if not kws:
        return []
    where = " OR ".join("s.text LIKE ?" for _ in kws)
    params = [work_id] + [f"%{w}%" for w in kws]
    rows = db.conn.execute(
        f"SELECT s.id, s.text FROM segments s JOIN chapters c ON s.chapter_id=c.id "
        f"WHERE c.work_id=? AND ({where}) LIMIT ?", (*params, k)).fetchall()
    return [(r[0], r[1]) for r in rows]


def graph_search(db, work_id: str, query: str, upto_seq: int | None = None) -> list[str]:
    """图路:命中查询词的 关系/时间线 事实(返回文本片段,作为额外召回)。"""
    kws = _keywords(query)
    out: list[str] = []
    for r in db.list_relations(work_id, upto_seq):
        blob = f"{r['src_entity']}{r['relation']}{r['dst_entity']}"
        if any(w in blob for w in kws):
            out.append(f"〔关系〕{r['src_entity']}-{r['relation']}-{r['dst_entity']}")
    for t in db.list_timeline(work_id, upto_seq):
        if any(w in (t["description"] or "") for w in kws):
            out.append(f"〔事件·第{t['chapter_seq']}章〕{t['description']}")
    return out[:5]


def hybrid_search(db, work_id: str, query: str, k: int = 5,
                  vec_hits: list[tuple[str, float, str]] | None = None,
                  upto_seq: int | None = None) -> dict:
    """三路召回 + RRF 融合。vec_hits 由调用方传入(向量路,可为 None)。
    返回 {segments:[{id,content}], graph:[str]}。"""
    kw = keyword_search(db, work_id, query, k * 2)
    content_by_id = {sid: txt for sid, txt in kw}
    kw_ids = [sid for sid, _ in kw]
    vec_ids: list[str] = []
    if vec_hits:
        for sid, _dist, content in vec_hits:
            vec_ids.append(sid)
            content_by_id.setdefault(sid, content)
    fused = reciprocal_rank_fusion([kw_ids, vec_ids])
    seg_out = [{"id": sid, "content": content_by_id.get(sid, "")} for sid, _ in fused[:k]]
    return {"segments": seg_out, "graph": graph_search(db, work_id, query, upto_seq)}
