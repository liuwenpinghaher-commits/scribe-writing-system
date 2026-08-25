from .test_app import _client


def test_materials_list_supports_cursor_paging(store):
    for i in range(3):
        store.add_material(f"素材 {i}", f"正文 {i}", "note")
    c = _client(store)

    first = c.get("/materials", params={"limit": 2}).json()

    assert "items" in first
    assert "next_cursor" in first
    assert len(first["items"]) == 2
    assert first["next_cursor"] is not None


def test_material_graph_limit_reports_truncated(store):
    for i in range(3):
        store.add_material(f"节点 {i}", f"正文 {i}", "note")
    c = _client(store)

    graph = c.get("/materials/graph", params={"limit": 2}).json()

    assert len(graph["nodes"]) == 2
    assert graph["truncated"] is True


def test_material_refs_by_chapter_enriches_material_rows(store):
    mid = store.add_material("借命仪式资料", "铜炉资料", "research")
    store.add_material_reference(mid, 4, "final", "正文采用", "write")
    c = _client(store)

    refs = c.get("/materials/refs-by-chapter", params={"chapter": 4}).json()

    assert refs[0]["material_id"] == mid
    assert refs[0]["title"] == "借命仪式资料"
    assert refs[0]["kind"] == "research"


def test_materials_exist_does_not_scan_full_table(store, monkeypatch):
    store.add_material("探针", "正文", "note")
    listed = []
    orig = store.list_materials

    def wrap(*a, **k):
        listed.append(1)
        return orig(*a, **k)

    monkeypatch.setattr(store, "list_materials", wrap)
    assert store.materials_exist() is True
    assert listed == []


def test_list_materials_page_simple_view_uses_sql_limit(store, monkeypatch):
    for i in range(5):
        store.add_material(f"分页条 {i}", f"正文 {i}", "note")
    seen: list[str] = []
    orig = store._query

    def wrap(sql, *a, **k):
        seen.append(sql)
        return orig(sql, *a, **k)

    monkeypatch.setattr(store, "_query", wrap)
    page = store.list_materials_page(view="all", limit=2, cursor=0)
    assert len(page["items"]) == 2
    assert page["total"] >= 5
    assert any("LIMIT" in s and ("START" in s or "$start" in s) for s in seen), seen
    assert any("count()" in s for s in seen), seen


def test_author_can_record_manual_material_reference_after_accepting_insert(store):
    mid = store.add_material("盐港勘察", "盐层与潮闸", "research")
    c = _client(store)

    created = c.post(f"/materials/{mid}/refs", json={
        "chapter": 3,
        "dimension": "manual_insert",
        "reason": "作者采纳素材插稿",
    })

    assert created.status_code == 200
    refs = c.get("/materials/refs-by-chapter", params={"chapter": 3}).json()
    assert [(r["material_id"], r["via"], r["dimension"]) for r in refs] == [
        (mid, "manual_insert", "manual_insert")
    ]
