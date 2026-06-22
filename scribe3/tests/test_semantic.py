"""S3b · 向量 RAG 语义召回(真 embedding,确定性)。

设定/命题存 embedding,语义查询经 HNSW <|K,COSINE|> 召回最相关——头部工具仍多用字面匹配,
这是 scribe3 的差异化(单库多模:向量召回可同句追因果)。
"""
from scribe3.ontology import Fact


def _seed(store):
    rows = [("fact:治眼", "role:焦三", "动机", "攒钱给老娘治眼"),
            ("fact:雨", "place:乱岗", "天气", "暴雨倾盆"),
            ("fact:铜炉", "item:炉", "来历", "乱世铜炉能炼化尸骨成丹")]
    for oid, ent, attr, val in rows:
        store.add_fact(Fact(oid, ent, attr, val, valid_from=1))
        store.semantic_index(oid, val)


def test_semantic_recall_ranks_by_meaning(store):
    _seed(store)
    hits = store.semantic_recall("给母亲看病筹钱", k=1)
    assert hits, "应有召回"
    assert hits[0].id == "fact:治眼", f"语义最近应是治眼,得到 {[h.id for h in hits]}"


def test_semantic_recall_other_query(store):
    _seed(store)
    hits = store.semantic_recall("炼丹的法器", k=1)
    assert hits and hits[0].id == "fact:铜炉", f"应召回铜炉,得到 {[h.id for h in hits]}"
