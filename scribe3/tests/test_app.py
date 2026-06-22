"""S5a · scribe3 后端 API(FastAPI,端口 3321)TDD。

前端读 NS=scribe3 + 驱动渲染的桥。读端点不连网;render 注入假 complete_fn。
关键:/render 仍走知识帧投影——API 层也不泄露(帧外私密进不了 prompt)。
"""
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.scenario import luanshi_leak_world


def _client(store, complete_fn=None):
    A.set_store(store)
    A.set_complete_fn(complete_fn or (lambda prompt, **kw: "渲染的散文。"))
    return TestClient(A.app)


def test_health(store):
    assert _client(store).get("/health").json()["ok"] is True


def test_entities_and_facts(store):
    luanshi_leak_world(store)
    c = _client(store)
    names = [e["name"] for e in c.get("/entities").json()]
    assert "焦三" in names and "乱葬岗" in names
    facts = c.get("/facts", params={"chapter": 1}).json()
    assert any(f["id"] == "fact:治眼" for f in facts)


def test_frame_excludes_others_secret(store):
    luanshi_leak_world(store)
    c = _client(store)
    laodao = c.get("/frame", params={"focalizer": "role:老道", "chapter": 1}).json()
    assert not any(f["id"] == "fact:治眼" for f in laodao), "老道帧不含焦三私密"
    jiaosan = c.get("/frame", params={"focalizer": "role:焦三", "chapter": 1}).json()
    assert any(f["id"] == "fact:治眼" for f in jiaosan)


def test_render_feeds_frame_limited_prompt(store):
    luanshi_leak_world(store)
    cap = {}

    def fake(prompt, **kw):
        cap["p"] = prompt
        return "雨砸在乱葬岗上。"

    c = _client(store, fake)
    r = c.post("/render", json={"focalizer": "role:老道", "chapter": 1}).json()
    assert r["prose"] == "雨砸在乱葬岗上。"
    assert "治眼" not in cap["p"], "API 渲染仍限知:帧外私密不进 prompt"


def test_causal_clean(store):
    luanshi_leak_world(store)
    c = _client(store)
    assert c.get("/causal", params={"chapter": 1}).json() == []
