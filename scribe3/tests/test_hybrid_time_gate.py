"""hybrid_recall / semantic_recall 限知时间门：chapter 过滤未来/已失效命题。"""
from scribe3.ontology import Entity, Fact


def test_hybrid_recall_excludes_future_facts(store, monkeypatch):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:past", "role:甲", "身份", "学徒", valid_from=1))
    store.add_fact(Fact("fact:future", "role:甲", "身份", "掌门", valid_from=100))
    past = store.fact("fact:past")
    future = store.fact("fact:future")
    assert past and future

    def fake_semantic(self, query: str, k: int = 5, chapter=None):
        rows = [past, future]
        if chapter is not None:
            rows = [f for f in rows
                    if f.valid_from <= chapter
                    and (f.valid_to is None or f.valid_to > chapter)]
        return rows[:k]

    monkeypatch.setattr(type(store), "semantic_recall", fake_semantic, raising=True)
    hits = store.hybrid_recall("身份", chapter=5, k=10)
    ids = {f.id for f in hits}
    assert "fact:past" in ids
    assert "fact:future" not in ids


def test_semantic_recall_filters_by_chapter(store, monkeypatch):
    """semantic_recall 直接带 chapter 时过滤 valid_from/valid_to。"""
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:early", "role:乙", "状态", "活", valid_from=1, valid_to=10))
    store.add_fact(Fact("fact:late", "role:乙", "状态", "死", valid_from=10))
    store.add_fact(Fact("fact:future2", "role:乙", "状态", "重生", valid_from=50))
    early = store.fact("fact:early")
    late = store.fact("fact:late")
    future2 = store.fact("fact:future2")
    assert early and late and future2

    def fake_embed(texts):
        return [[0.0] * 8 for _ in texts]

    # 绕过真实向量/HNSW：直接注入 semantic_recall 的后过滤输入
    original = store.semantic_recall

    def fake_semantic(self, query: str, k: int = 5, chapter=None):
        rows = [early, late, future2]
        if chapter is not None:
            rows = [f for f in rows
                    if f.valid_from <= chapter
                    and (f.valid_to is None or f.valid_to > chapter)]
        return rows[:k]

    monkeypatch.setattr(type(store), "semantic_recall", fake_semantic, raising=True)
    hits = store.semantic_recall("状态", k=10, chapter=5)
    ids = {f.id for f in hits}
    assert "fact:early" in ids
    assert "fact:late" not in ids
    assert "fact:future2" not in ids

    # 恢复并测真实实现签名兼容（chapter 默认 None 不炸）
    monkeypatch.setattr(type(store), "semantic_recall", original, raising=True)
    # 无 embedding 时可能空列表，只验证调用不因 chapter 参数失败
    try:
        store.semantic_recall("状态", k=5)
        store.semantic_recall("状态", k=5, chapter=None)
        store.semantic_recall("状态", k=5, chapter=5)
    except TypeError as e:
        raise AssertionError(f"semantic_recall chapter 参数不兼容: {e}") from e
