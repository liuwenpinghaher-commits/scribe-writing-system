from scribe2.store import Store

def test_store_create_and_get(db):
    s = Store(db)
    wid = s.create("work", {"title": "雨夜", "genre": "悬疑"})
    w = s.get("work", wid)
    assert w["title"] == "雨夜" and w["genre"] == "悬疑"

def test_store_list_and_update(db):
    s = Store(db)
    wid = s.create("work", {"title": "晨光"})
    s.update("work", wid, {"genre": "治愈"})
    rows = s.list("work")
    assert len(rows) == 1 and rows[0]["genre"] == "治愈"
