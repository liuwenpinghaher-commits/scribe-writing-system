from .test_app import _client


def test_material_import_commit_requires_preview_job(store):
    """跳过预览的假 job_id 不得落库。"""
    c = _client(store)
    r = c.post("/materials/import/no-such-job/commit", json={"items": [
        {"title": "偷渡素材", "body": "不该入库", "kind": "note"},
    ]})
    assert r.status_code == 404, r.text
    assert store.list_materials() == [] or all(
        m.get("title") != "偷渡素材" for m in store.list_materials())


def test_material_import_commit_reports_failed_items(store, monkeypatch):
    original_add = store.add_material

    def fake_add(title, *args, **kwargs):
        if title == "坏素材":
            raise ValueError("非法分类 kind=bad")
        return original_add(title, *args, **kwargs)

    monkeypatch.setattr(store, "add_material", fake_add)
    monkeypatch.setattr(store, "build_material_edges", lambda *_args, **_kwargs: None)
    store.save_import_job("job-1", {
        "stage": "待预览确认", "done": True, "total": 3, "items": [],
        "error": "", "work": store.db_name, "source": "t",
    })
    c = _client(store)

    r = c.post("/materials/import/job-1/commit", json={"items": [
        {"title": "好素材", "body": "可导入", "kind": "note"},
        {"title": "坏素材", "body": "分类坏", "kind": "note"},
        {"title": "   ", "body": "无标题", "kind": "note"},
    ]})

    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 1
    assert len(body["ids"]) == 1
    assert body["failed"][0]["index"] == 1
    assert body["failed"][0]["title"] == "坏素材"
    assert "非法分类" in body["failed"][0]["reason"]
    assert body["failed"][1]["index"] == 2
    assert body["failed"][1]["reason"] == "标题为空"
    assert body["warnings"] == []


def test_material_graph_reports_edge_degraded(store, monkeypatch):
    store.add_material("孤立素材", "正文", "note")
    original_query = store._query

    def flaky_query(sql, *args, **kwargs):
        if "FROM relates" in sql:
            raise RuntimeError("relates 查询失败")
        return original_query(sql, *args, **kwargs)

    monkeypatch.setattr(store, "_query", flaky_query)
    c = _client(store)

    r = c.get("/materials/graph")

    assert r.status_code == 200
    body = r.json()
    assert body["nodes"]
    assert body["edges"] == []
    assert body["edges_degraded"] is True
    assert body["degraded_sources"]
    assert "relates" in body["degraded_sources"][0]["source"]
