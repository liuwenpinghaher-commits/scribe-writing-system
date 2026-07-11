from .test_app import _client


def test_issue_ledger_normalizes_qc_hits(store):
    prose = "我很悲伤。\n我很悲伤。\n我很悲伤。"
    store.save_chapter(4, prose, title="情绪复读")
    c = _client(store)

    r = c.get("/issues", params={"chapter": 4})

    assert r.status_code == 200
    body = r.json()
    assert body["issues"]
    issue = body["issues"][0]
    assert issue["id"].startswith("issue:")
    assert issue["source"] == "qc"
    assert issue["severity"] in {"info", "warning", "error"}
    assert issue["chapter"] == 4
    assert isinstance(issue["range"], list) and len(issue["range"]) == 2
    assert issue["status"] == "open"
    assert issue["target_node"]["type"] == "chapter"
