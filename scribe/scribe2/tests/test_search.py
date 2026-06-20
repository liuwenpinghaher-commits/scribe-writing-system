from scribe2.store import Store

def test_search_hybrid(db):
    s = Store(db); s.init_schema()
    s.put_content("character", work="work:1", text="沈舟,沉默寡言的剑客", name="沈舟")
    s.put_content("setting", work="work:1", text="断魂剑,会让持有者失忆的古剑", name="断魂剑")
    s.put_content("setting", work="work:1", text="码头,雨夜常起雾", name="码头")
    hits = s.search_knowledge("work:1", "失忆的剑", k=3)
    assert hits and any("断魂剑" in (h.get("text") or "") for h in hits)
    # 最相关的排第一
    assert "断魂剑" in (hits[0].get("text") or "")

def test_search_filters_by_work(db):
    s = Store(db); s.init_schema()
    s.put_content("setting", work="work:1", text="断魂剑", name="断魂剑")
    s.put_content("setting", work="work:2", text="另一本书的剑", name="别剑")
    hits = s.search_knowledge("work:1", "剑", k=5)
    assert all(h["entity_type"] for h in hits)
    assert not any("另一本书" in (h.get("text") or "") for h in hits)
