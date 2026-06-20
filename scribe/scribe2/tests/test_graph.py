from scribe2.store import Store

def _rid(table, uid):  # uuid 可能以数字开头 → 反引号包
    return f"{table}:`{uid}`"

def test_relate_and_traverse(db):
    s = Store(db); s.init_schema()
    a = s.put_content("character", work="work:1", text="沈舟", name="沈舟")
    b = s.put_content("setting", work="work:1", text="断魂剑", name="断魂剑")
    s.relate(_rid("character", a), "holds", _rid("setting", b),
             {"category": "从属", "weight": 2, "valid_from": 1})
    nb = s.neighbors(_rid("character", a), "holds")
    assert any("断魂剑" in str(x) for x in nb)
