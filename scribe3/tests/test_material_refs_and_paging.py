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
