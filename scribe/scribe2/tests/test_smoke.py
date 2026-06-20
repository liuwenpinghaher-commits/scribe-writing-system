def test_connect_and_query(db):
    db.query("CREATE work:x SET title='雨夜';")
    rows = db.query("SELECT title FROM work;")
    # SurrealDB SDK 返回归一:可能是 [{...}] 或 [{'result':[...]}]
    first = rows[0] if rows else None
    result = first.get("result") if isinstance(first, dict) and "result" in first else rows
    assert result and result[0]["title"] == "雨夜"
