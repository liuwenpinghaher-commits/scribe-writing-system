"""设定库 Phase A–D:树命题 / 单条读 / MCP 对称 / 搜索健康 / emergency 写闸。"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from scribe3.ontology import Entity, Fact
from .test_app import _client


def test_project_tree_includes_proposition(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:p1", "role:甲", "状态", "清醒", valid_from=1))
    tree = store.project_tree()
    codex = tree.get("codex") or {}
    cats = {c["ref"]: c for c in (codex.get("children") or [])}
    assert "proposition" in cats, f"设定支缺命题分类: {list(cats)}"
    props = cats["proposition"].get("children") or []
    assert any(p.get("ref") == "p1" for p in props)


def test_get_promise_o1_not_list_scan(store, monkeypatch):
    """GET /promises/{pid} 与 store.get_promise 走 type::record,禁止 list 全表扫。"""
    store.plant_promise("铜炉要回收", setup_chapter=2, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "铜炉要回收" in p["text"])

    queries: list[str] = []
    orig_query = store._query

    def spy_query(sql, *args, **kwargs):
        queries.append(sql if isinstance(sql, str) else str(sql))
        return orig_query(sql, *args, **kwargs)

    monkeypatch.setattr(store, "_query", spy_query)

    def boom_list(*_a, **_k):
        raise AssertionError("get_promise 不得回落到 list_promises 全表扫描")

    monkeypatch.setattr(store, "list_promises", boom_list)

    row = store.get_promise(pid)
    assert row is not None
    assert row["id"] == pid
    assert "铜炉要回收" in (row.get("text") or "")
    assert any("type::record('promise'" in q for q in queries), queries
    assert store.get_promise("不存在的伏笔") is None

    c = _client(store)
    r = c.get(f"/promises/{pid}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == pid
    assert "铜炉要回收" in body["text"]
    assert c.get("/promises/不存在的伏笔").status_code == 404


def test_get_character_by_id_endpoint(store):
    store.add_entity(Entity("role:沈砚", "character", "沈砚"))
    store.update_record("role:沈砚", {"appearance": "白衣", "surface_goal": "寻仇"})
    c = _client(store)
    r = c.get("/characters/沈砚")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "沈砚"
    assert body["appearance"] == "白衣"
    assert c.get("/characters/不存在的人").status_code == 404


def test_get_faction_item_term_rule(store):
    store.add_faction("衔尾蛇", ideology="长生")
    store.add_item("镇煞钉", description="钉子")
    store.add_term("灵力", definition="能量")
    store.add_world_rule("因果律", "physical", note="不可逆")
    c = _client(store)
    assert c.get("/factions/衔尾蛇").json()["ideology"] == "长生"
    assert c.get("/items/镇煞钉").json()["description"] == "钉子"
    assert c.get("/terms/灵力").json()["definition"] == "能量"
    assert c.get("/world-rules/因果律").json()["category"] == "physical"


def test_codex_search_and_health(store):
    store.add_entity(Entity("role:甲", "character", "甲", traits={}))  # sparse
    store.add_faction("秘会", ideology="隐秘")
    store.add_fact(Fact("fact:x", "role:甲", "秘密", "井底", valid_from=1, secret=True))
    c = _client(store)
    s = c.get("/codex/search", params={"q": "秘会"}).json()
    assert any(i.get("label") == "秘会" for i in s["items"])
    h = c.get("/codex/health").json()
    assert h["characters"] >= 1
    assert h["sparse_dossiers"] >= 1
    assert h["propositions_open"] >= 1
    assert isinstance(h["isolated_characters"], int)


def test_codex_schema_character_registered(store):
    c = _client(store)
    r = c.get("/codex-schema/character")
    assert r.status_code == 200
    keys = {f["key"] for f in r.json()}
    assert "appearance" in keys and "surface_goal" in keys
    assert c.get("/codex-schema/faction").status_code == 200


class _AcceptCtx:
    async def elicit(self, message, schema):
        return type("_R", (), {"action": "accept"})()


def test_mcp_patch_faction_and_delete_codex(store):
    import scribe3.mcp as M
    store.add_faction("天龙座", ideology="旧")
    M.set_store(store)

    res = asyncio.run(M.s3_patch_faction(_AcceptCtx(), "天龙座", ideology="新意识形态"))
    assert res.get("status") == "written", res
    assert store.get_faction("天龙座")["ideology"] == "新意识形态"

    res2 = asyncio.run(M.s3_delete_codex(_AcceptCtx(), "faction", "天龙座", archive=False))
    assert res2.get("status") == "written", res2
    assert store.get_faction("天龙座") is None


def test_mcp_patch_item_term_world_rule(store):
    import scribe3.mcp as M
    store.add_item("铜炉", description="旧")
    store.add_term("气", definition="旧")
    store.add_world_rule("天道", "magic", cost="寿元")
    M.set_store(store)

    assert asyncio.run(M.s3_patch_item(_AcceptCtx(), "铜炉", description="新描"))["status"] == "written"
    assert store.get_item("铜炉")["description"] == "新描"
    assert asyncio.run(M.s3_patch_term(_AcceptCtx(), "气", definition="新义"))["status"] == "written"
    assert store.get_term("气")["definition"] == "新义"
    assert asyncio.run(M.s3_patch_world_rule(_AcceptCtx(), "天道", note="注"))["status"] == "written"
    assert store.get_world_rule("天道").get("note") == "注"


def test_emergency_off_blocks_rest_allows_mcp(store, monkeypatch):
    monkeypatch.setenv("SCRIBE3_EMERGENCY_REST_WRITE", "0")
    import scribe3.app as A
    import scribe3.mcp as M
    A.set_store(store)
    A.set_complete_fn(lambda p, **k: "x")
    M.set_store(store)
    c = TestClient(A.app)

    assert c.post("/characters", json={"name": "直写角色"}).status_code == 403
    assert c.post("/factions", json={"name": "直写势力"}).status_code == 403
    assert c.delete("/factions", params={"name": "x"}).status_code == 403

    res = asyncio.run(M.s3_add_character(_AcceptCtx(), "role:批角色", "批角色"))
    assert res.get("status") == "written", res
    assert store.entity("role:批角色") is not None

    res2 = asyncio.run(M.s3_add_faction(_AcceptCtx(), "批势力", ideology="i"))
    assert res2.get("status") == "written", res2
    assert store.get_faction("批势力") is not None


def test_seed_names_real_tools():
    """chiefSeed 必须点名真实 MCP 工具名(结构守卫)。"""
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "chiefSeed.js"
    text = p.read_text(encoding="utf-8")
    assert "s3_patch_faction" in text
    assert "s3_patch_item" in text
    assert "s3_patch_world_rule" in text
    assert "s3_delete_codex" in text
    assert "s3_patch_character" in text


def test_graph_includes_faction_and_item_nodes(store):
    """图谱含势力/物件节点,并可按 focus 取 ego。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_faction("秘会", ideology="隐", known_members=["甲"])
    store.add_item("铜炉", description="钉", current_owner="甲")
    g = store.graph(limit=200)
    types = {n["type"] for n in g["nodes"]}
    assert "faction" in types and "item" in types
    ids = {n["id"] for n in g["nodes"]}
    assert "faction:秘会" in ids and "item:铜炉" in ids
    # 成员/持有边
    assert any(e.get("rel") == "member" and e.get("src") == "faction:秘会" for e in g["edges"])
    assert any(e.get("rel") == "held_by" and e.get("src") == "item:铜炉" for e in g["edges"])
    ego = store.graph(focus="faction:秘会", hop=1)
    ego_ids = {n["id"] for n in ego["nodes"]}
    assert "faction:秘会" in ego_ids
    assert "role:甲" in ego_ids


def test_codex_schema_item_term_world_rule(store):
    c = _client(store)
    for kind in ("item", "term", "world_rule"):
        r = c.get(f"/codex-schema/{kind}")
        assert r.status_code == 200, kind
        keys = {f["key"] for f in r.json()}
        assert "name" in keys, kind
    item_keys = {f["key"] for f in c.get("/codex-schema/item").json()}
    assert "symbolic_state" in item_keys and "current_owner" in item_keys
    rule_keys = {f["key"] for f in c.get("/codex-schema/world_rule").json()}
    assert "category" in rule_keys and "scope" in rule_keys
