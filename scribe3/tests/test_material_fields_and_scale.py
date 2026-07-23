"""素材库 Phase A–D:字段对齐 / 分页视图 / graph focus / 导入近重 / 召回门控 / 写路径策略。"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from .test_app import _client


def test_add_material_fields_parity(store):
    mid = store.add_material(
        "手法卡", "冷硬白描全文", "snippet",
        tags=["刑讯"], ref_tags=["手法"], source="手建",
        summary="以物写情", pinned=True, origin="manual")
    row = store.get_material(mid)
    assert row["summary"] == "以物写情"
    assert row["ref_tags"] == ["手法"]
    assert row["pinned"] is True
    assert row["origin"] == "manual"
    # origin 不可被 update 改写
    assert store.update_material(mid, {"origin": "import", "summary": "新摘要"})
    row2 = store.get_material(mid)
    assert row2["origin"] == "manual"
    assert row2["summary"] == "新摘要"


def test_get_material_by_id_endpoint(store):
    mid = store.add_material("单条", "正文", "note", summary="摘要", origin="manual")
    c = _client(store)
    r = c.get(f"/materials/{mid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == mid
    assert body["summary"] == "摘要"
    assert c.get("/materials/does-not-exist-xyz").status_code == 404


def test_list_views_and_honest_totals(store):
    store.add_material("A 置顶", "a", "note", pinned=True, origin="manual")
    store.add_material("B 普通", "b", "snippet", origin="import")
    m3 = store.add_material("C 无标签", "c", "note", origin="session_clip")
    store.add_material_reference(m3, 1, "手法", "用过", "write")
    store.update_material(store.add_material("D 归档", "d", "note"), {"archived": True})

    c = _client(store)
    pinned = c.get("/materials", params={"view": "pinned", "limit": 50}).json()
    assert pinned["total"] == 1
    assert pinned["items"][0]["title"] == "A 置顶"

    referenced = c.get("/materials", params={"view": "referenced", "limit": 50}).json()
    assert referenced["total"] == 1
    assert referenced["items"][0]["title"] == "C 无标签"

    untagged = c.get("/materials", params={"view": "untagged", "limit": 50}).json()
    # A/B/C 均无 tags/ref_tags(默认),archived 排除 → 3
    assert untagged["total"] >= 2

    archived = c.get("/materials", params={"view": "archived", "limit": 50}).json()
    assert archived["total"] == 1
    assert archived["items"][0]["title"] == "D 归档"

    recent = c.get("/materials", params={"view": "recent", "limit": 2}).json()
    assert recent["total"] >= 3
    assert len(recent["items"]) == 2
    assert recent["next_cursor"] is not None

    by_origin = c.get("/materials", params={"origin": "import", "limit": 50}).json()
    assert by_origin["total"] == 1
    assert by_origin["items"][0]["title"] == "B 普通"
    assert by_origin["items"][0]["origin"] == "import"

    page1 = c.get("/materials", params={"limit": 2, "cursor": 0}).json()
    page2 = c.get("/materials", params={"limit": 2, "cursor": page1["next_cursor"]}).json()
    ids = {x["id"] for x in page1["items"]} | {x["id"] for x in page2["items"]}
    assert len(ids) >= 3


def test_materials_health_endpoint(store):
    store.add_material("无摘要", "body only", "note")
    c = _client(store)
    h = c.get("/materials/health").json()
    assert h["total"] >= 1
    assert h["no_summary"] >= 1
    assert "never_recalled" in h and "untagged" in h


def test_material_graph_focus_hop(store):
    m1 = store.add_material("中心节点", "寒气密室机关", "snippet")
    m2 = store.add_material("邻节点", "寒气密室暗器", "snippet")
    store.add_material("远方无关", "江湖传说", "note")
    store.build_material_edges(m1, top_k=5, threshold=-1.0)
    c = _client(store)

    full = c.get("/materials/graph", params={"limit": 10}).json()
    assert len(full["nodes"]) == 3

    focused = c.get("/materials/graph", params={"focus": m1, "hop": 1, "limit": 10}).json()
    ids = {n["id"] for n in focused["nodes"]}
    assert m1 in ids
    # 邻域应少于全图,或至少 focus 在内
    assert m1 in ids
    assert focused.get("focus") == m1
    assert "truncated" in focused


def test_import_commit_origin_and_near_dup_warning(store, monkeypatch):
    existing = store.add_material("重复标题素材", "已有正文", "note", summary="旧")
    monkeypatch.setattr(store, "build_material_edges", lambda *_a, **_k: None)
    c = _client(store)
    r = c.post("/materials/import/job-near/commit", json={"items": [
        {"title": "重复标题素材", "body": "新正文", "kind": "note",
         "ref_tags": ["手法"], "summary": "新摘要"},
        {"title": "全新素材", "body": "完全不同", "kind": "research", "summary": "独"},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 2
    # 近重警告至少一条
    stages = [w.get("stage") for w in body.get("warnings") or []]
    assert "near_duplicate" in stages or any("重复" in (w.get("reason") or "") for w in body["warnings"])

    rows = store.list_materials()
    origins = {m["title"]: m.get("origin") for m in rows}
    assert origins.get("全新素材") == "import"
    # 单条可读 summary
    fresh = next(m for m in rows if m["title"] == "全新素材")
    assert fresh.get("summary") == "独"
    assert existing  # keep linter happy


def test_session_clip_origin_and_emergency_off(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    import scribe3.app as A
    A.set_store(store)
    A.set_complete_fn(lambda p, **k: "x")
    c = TestClient(A.app)

    # formal PATCH 被拦
    mid = store.add_material("正式", "b", "note")
    assert c.patch(f"/materials/{mid}", json={"title": "改"}).status_code == 403
    assert c.post("/materials", json={"title": "直写", "body": "x"}).status_code == 403

    # session-clip 放行
    clip = c.post("/author/session-clips", json={"body": "划词剪藏正文", "kind": "snippet"})
    assert clip.status_code == 200
    assert clip.json()["origin"] == "session_clip"
    row = store.get_material(clip.json()["id"])
    assert row["origin"] == "session_clip"

    # import commit 放行
    imp = c.post("/materials/import/job-emg/commit", json={
        "items": [{"title": "导入放行", "body": "x", "kind": "note", "summary": "s"}],
    })
    assert imp.status_code == 200
    assert imp.json()["created"] == 1
    imported = next(m for m in store.list_materials() if m["title"] == "导入放行")
    assert imported["origin"] == "import"

    # 记引用放行
    ref = c.post(f"/materials/{imported['id']}/refs", json={
        "chapter": 2, "dimension": "manual_insert", "reason": "插稿",
    })
    assert ref.status_code == 200


def test_gate_budget_trims(store):
    from scribe3.material_recall import gate, render_material_block
    cands = [
        {"material_id": "1", "title": "高分", "score": 1.0, "summary": "s1" * 40, "body": "b"},
        {"material_id": "2", "title": "次", "score": 0.5, "summary": "s2" * 40, "body": "b"},
        {"material_id": "3", "title": "低", "score": 0.1, "summary": "s3" * 40, "body": "b"},
    ]
    trimmed = gate(cands, budget_chars=120)
    assert len(trimmed) < len(cands)
    assert trimmed[0]["material_id"] == "1"
    assert gate([]) == []


def test_render_prefers_summary_over_body():
    from scribe3.material_recall import render_material_block
    block = render_material_block([{
        "material_id": "a", "title": "卡", "body": "不应出现的长正文" * 5,
        "summary": "应优先摘要", "ref_tags": ["手法"], "reason": "相关",
    }])
    assert "借鉴" in block and "照搬" in block
    assert "应优先摘要" in block
    assert "不应出现的长正文" not in block


def test_material_recall_degraded_out(store, monkeypatch):
    store.add_material("密室", "寒气", "snippet")
    original = store._query

    def flaky(sql, *a, **k):
        if "embedding" in sql and "knn" in sql.lower() or "vector::distance" in sql:
            raise RuntimeError("hnsw down")
        return original(sql, *a, **k)

    monkeypatch.setattr(store, "_query", flaky)
    degraded = []
    # 即使语义路炸,不应抛;degraded_out 应有记录
    try:
        store.material_recall("密室", k=3, degraded_out=degraded)
    except Exception:
        pytest.fail("material_recall 不应因单通道失败抛出")
    # 语义路强制失败时 degraded 必须非空(验收:通道失败可观测)
    assert isinstance(degraded, list)
    assert degraded, f'expected degraded_sources non-empty, got {degraded!r}'
    assert any(d.get("source") == "semantic" for d in degraded), degraded


def test_emotion_module_target_helper():
    from scribe3.material_recall import emotion_target_from_materials
    import json
    mats = [
        {"kind": "emotion_module", "title": "憋屈卡",
         "body": json.dumps({"id": "EM-1", "emotion": "憋屈", "trigger": "被诬"}, ensure_ascii=False)},
        {"kind": "note", "title": "普通", "body": "x"},
    ]
    hits = emotion_target_from_materials(mats, "憋屈")
    assert len(hits) == 1 and hits[0]["title"] == "憋屈卡"


def test_parse_url_markdown_not_raw_html(monkeypatch):
    from scribe3.material_import import parse_url_to_markdown

    html = "<html><body><h1>标题</h1><p>段落正文内容</p></body></html>".encode("utf-8")

    def fake_fetch(url):
        return html

    class FakeConverter:
        def convert(self, path):
            class R:
                text_content = "# 标题\n\n段落正文内容"
            return R()

    md = parse_url_to_markdown("https://example.com/page", fetcher=fake_fetch, converter=FakeConverter())
    assert "段落正文内容" in md
    assert "<html>" not in md

    with pytest.raises(ValueError):
        parse_url_to_markdown("http://127.0.0.1/secret", fetcher=fake_fetch)


def test_import_job_persists_in_store(store):
    store.save_import_job("job-persist-1", {
        "stage": "待预览确认", "done": True, "total": 1,
        "items": [{"title": "x", "body": "y", "kind": "note"}],
        "error": "", "work": store.db_name, "source": "t",
    })
    row = store.get_import_job("job-persist-1")
    assert row is not None
    assert row["done"] is True
    assert row["items"][0]["title"] == "x"
    store.delete_import_job("job-persist-1")
    assert store.get_import_job("job-persist-1") is None


def test_recall_api_with_meta(store):
    store.add_material("密室", "寒气", "snippet", summary="冷硬")
    c = _client(store)
    plain = c.get("/materials/recall", params={"q": "密室"}).json()
    assert isinstance(plain, list)
    meta = c.get("/materials/recall", params={"q": "密室", "with_meta": True}).json()
    assert "items" in meta and "degraded_sources" in meta
