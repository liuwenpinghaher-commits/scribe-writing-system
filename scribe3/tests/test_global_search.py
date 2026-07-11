from .test_app import _client


def test_global_search_returns_typed_targets(store):
    store.save_chapter(4, "崔判在铜炉前提出借命交易。", title="借命铜炉")
    mid = store.add_material("借命仪式资料", "铜炉、寿数与替身交易的民俗记录。", "research")
    c = _client(store)

    r = c.get("/search", params={"q": "借命"})

    assert r.status_code == 200
    body = r.json()
    types = {item["type"] for item in body["results"]}
    assert types >= {"chapter", "material"}
    assert all("target_node" in item for item in body["results"])
    assert any(item["target_node"]["type"] == "chapter" and item["target_node"]["ref"] == 4 for item in body["results"])
    assert any(item["target_node"]["type"] == "material" and item["target_node"]["ref"] == mid for item in body["results"])


def test_global_search_includes_events_as_jumpable_story_targets(store):
    from scribe3.ontology import Event

    store.add_event(Event("ev:借命摊牌", "借命摊牌", story_time=4,
                          motivated_by_goal="崔判逼柳怀玉签契"))
    c = _client(store)

    r = c.get("/search", params={"q": "摊牌"})

    assert r.status_code == 200
    body = r.json()
    events = [item for item in body["results"] if item["type"] == "event"]
    assert events
    assert events[0]["source"] == "事件"
    assert events[0]["target_node"]["type"] == "event"
    assert events[0]["target_node"]["chapter"] == 4
