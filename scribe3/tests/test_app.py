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


def test_graph_endpoint(store):
    from scribe3.ontology import Entity, Fact, KnowledgeEdge
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:x", "role:甲", "属性", "某值", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:甲", "fact:x", since_chapter=1))
    g = _client(store).get("/graph").json()
    assert any(n["type"] == "character" for n in g["nodes"])
    assert any(n["type"] == "proposition" for n in g["nodes"])
    assert any(e["rel"] == "knows" for e in g["edges"])


def test_quality_endpoint(store):
    store.save_chapter(1, "一段正常的志怪内容。", title="一")
    q = _client(store).get("/quality").json()
    assert q["chapters"][0]["seq"] == 1 and "foreshadow" in q and "total_words" in q


def test_character_crud(store):
    c = _client(store)
    c.post("/characters", json={"name": "测角", "backstory": "前史A"})
    es = c.get("/entities").json()
    me = next((e for e in es if e["name"] == "测角"), None)
    assert me and me["backstory"] == "前史A"
    c.patch("/characters/测角", json={"name": "测角", "backstory": "前史B"})
    me2 = next(e for e in c.get("/entities").json() if e["name"] == "测角")
    assert me2["backstory"] == "前史B"
    c.delete("/characters/测角")
    assert not any(e["name"] == "测角" for e in c.get("/entities").json())


def test_motif_crud(store):
    c = _client(store)
    c.post("/motifs-new", json={"name": "雪", "theme": "肃杀"})
    m = c.get("/motifs").json()[0]
    c.patch(f"/motifs/{m['id']}", json={"name": "雪", "theme": "纯白", "echoes": "", "unfolding": ""})
    assert c.get("/motifs").json()[0]["theme"] == "纯白"
    c.delete(f"/motifs/{m['id']}")
    assert c.get("/motifs").json() == []


def test_intent_crud(store):
    c = _client(store)
    assert c.get("/intent").json()["reader_feeling"] == ""
    c.put("/intent", json={"reader_feeling": "压抑中见微光", "emotional_arc": "由怯到决", "red_lines": "不洗白反派"})
    i = c.get("/intent").json()
    assert i["reader_feeling"] == "压抑中见微光" and "不洗白" in i["red_lines"]


def test_editor_system_injects_context(store):
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_fact(Fact("fact:s", "世界", "通货", "铜钱", valid_from=1, secret=False))
    store.set_intent({"reader_feeling": "压抑见微光", "emotional_arc": "", "red_lines": ""})
    from scribe3.app import _editor_system
    sysmsg = _editor_system(store)
    assert "焦三" in sysmsg and "铜钱" in sysmsg and "压抑见微光" in sysmsg


def test_chat_stream_sse(store, monkeypatch):
    import scribe3.llm as llm
    monkeypatch.setattr(llm, "hermes_complete_stream", lambda *a, **k: iter(["主编", "建议"]))
    r = _client(store).get("/chat/stream", params={"msg": "这章怎么改"})
    assert r.status_code == 200
    assert "主编" in r.text and '"done": true' in r.text


def test_chat_agentic_sse(store, monkeypatch):
    import scribe3.app as appmod

    def fake_events(msg, instructions, model=None):
        yield {"type": "response.output_item.added",
               "item": {"type": "function_call", "name": "s3_list_promises", "arguments": "{}"}}
        yield {"type": "response.output_text.delta", "delta": "已查"}
        yield {"type": "response.output_text.delta", "delta": "伏笔"}

    monkeypatch.setattr(appmod, "_responses_events", fake_events)
    r = _client(store).get("/chat/agentic-stream", params={"msg": "查伏笔"})
    assert r.status_code == 200
    body = r.text
    assert "s3_list_promises" in body and '"tool"' in body and "已查" in body and '"done": true' in body


def test_chat_write_splits_proposal(store, monkeypatch):
    import scribe3.app as appmod

    def fake_events(msg, instructions, model=None):
        for t in ["这样改：", "⟦PROPOSAL scope=selection⟧", "单嫣立于老槐之下。", "⟦/PROPOSAL⟧"]:
            yield {"type": "response.output_text.delta", "delta": t}

    monkeypatch.setattr(appmod, "_responses_events", fake_events)
    r = _client(store).get("/chat/write", params={"msg": "把这段写冷点", "chapter": 1, "focalizer": "role:x"})
    body = r.text
    assert '"delta": "这样改："' in body
    assert '"proposal"' in body and "单嫣立于老槐之下" in body
    assert '"scope": "selection"' in body


def test_chat_write_discuss_only(store, monkeypatch):
    import scribe3.app as appmod

    def fake_events(msg, instructions, model=None):
        for t in ["这章节奏偏慢，", "建议提速。"]:
            yield {"type": "response.output_text.delta", "delta": t}

    monkeypatch.setattr(appmod, "_responses_events", fake_events)
    body = _client(store).get("/chat/write", params={"msg": "这章节奏如何"}).text
    assert "建议提速" in body and '"proposal"' not in body


def test_save_chapter_runs_softcheck(store):
    r = _client(store).post("/save-chapter", json={"seq": 1, "prose": "一段正常的志怪。", "focalizer": "role:x"}).json()
    assert r["status"] == "saved" and "qc" in r and "leaks" in r
    assert set(r["qc"]) == {"repetition", "structural", "purple"}


def test_apply_delta_idempotent(store):
    from scribe3.ingest import apply_delta
    delta = {"learned": [{"who": "甲", "fact": "X 是真的"}], "did": []}
    apply_delta(store, delta, seq=1)
    apply_delta(store, delta, seq=1)   # 重复回写同章 → 不应抛 AlreadyExists
    facts = [f for f in store.facts_at(1) if f.value == "X 是真的"]
    assert len(facts) == 1   # 幂等:只一条


def test_save_chapter_triggers_bg_ingest(store, monkeypatch):
    """save-chapter 落库后注册后台 ingest 任务,响应含 ingesting=True,不阻塞。"""
    A.set_store(store)   # 注入活 store 到 work=main(否则命中其它测试遗留的死连接)
    called = {}
    monkeypatch.setattr(A, "_bg_ingest", lambda work, seq: called.setdefault("args", (work, seq)))
    client = TestClient(A.app)
    r = client.post("/save-chapter?work=main",
                    json={"seq": 7, "prose": "测试正文。", "title": "t", "focalizer": ""})
    assert r.status_code == 200
    assert r.json().get("ingesting") is True
    # TestClient 同步执行 BackgroundTasks → _bg_ingest 应以 (main, 7) 被调过
    assert called.get("args") == ("main", 7)


def test_editor_reminds_open_promises(store):
    """_editor_system 预注入"开着的伏笔"强提醒(防主编忘/漏接)。"""
    import scribe3.app as A
    store.plant_promise("井底那只青铜匣", setup_chapter=1)
    sysmsg = A._editor_system(store)
    assert "开着的承诺线" in sysmsg or "勿忘" in sysmsg
    assert "青铜匣" in sysmsg


def test_editor_no_full_motif_dump(store):
    """agentic 主编详情按需查:_editor_system 不全量灌母题(只给提醒,不堆母题清单)。无数据也不崩。"""
    import scribe3.app as A
    store.add_motif("铜炉", theme="代价", echoes="炉火", unfolding="X")
    sysmsg = A._editor_system(store)
    assert "炉火" not in sysmsg   # 母题靠主编按需调 s3_list_motifs,不在系统提示里全量展开
    assert isinstance(sysmsg, str) and len(sysmsg) > 0


def test_voice_rest(store):
    import scribe3.app as A
    A.set_store(store)
    from fastapi.testclient import TestClient
    client = TestClient(A.app)
    r = client.post("/voice?work=main",
                    json={"character": "role:焦三", "kind": "pressure", "text": "声细如蚊", "since_chapter": 1})
    assert r.status_code == 200
    got = client.get("/voice?character=role:焦三&work=main").json()
    assert any(v["kind"] == "pressure" and v["text"] == "声细如蚊" for v in got)
