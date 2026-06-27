"""S5a · scribe3 后端 API(FastAPI,端口 3321)TDD。

前端读 NS=scribe3。写作统一走主编对话(/chat/write),不经直接渲染。
"""
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.ontology import Event
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


# /render 端点已删除——写作统一走主编对话(/chat/write),不经直接渲染


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
    assert set(r["qc"]) == {"repetition", "structural", "purple", "cross_repetition"}


def test_apply_delta_idempotent(store):
    from scribe3.ingest import apply_delta
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:甲", "character", "甲"))
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
                    json={"character": "role:焦三", "voice_kind": "pressure", "text": "声细如蚊", "since_chapter": 1})
    assert r.status_code == 200
    got = client.get("/voice?character=role:焦三&work=main").json()
    assert any(v["kind"] == "pressure" and v["text"] == "声细如蚊" for v in got)


def test_checkpoint_and_versions(store):
    c = _client(store)
    r = c.post("/checkpoint", params={"seq": 1},
               json={"prose": "第一稿正文", "label": "初稿", "kind": "checkpoint",
                     "qc": {"repetition": 2}})
    assert r.status_code == 200
    vid = r.json()["id"]
    assert vid
    c.post("/checkpoint", params={"seq": 1},
           json={"prose": "定稿正文", "label": "定稿", "kind": "final", "qc": {}})
    lst = c.get("/chapter-versions", params={"seq": 1}).json()
    assert len(lst) == 2 and lst[0]["label"] == "定稿"
    one = c.get(f"/chapter-version/{vid}").json()
    assert one["prose"] == "第一稿正文"


def test_check_returns_qc_and_leaks_without_saving(store):
    luanshi_leak_world(store)
    c = _client(store)
    # 老道视角写出焦三私密 → 泄露;不落库
    r = c.post("/check", params={"seq": 1},
               json={"prose": "老道看见焦三在治眼。", "focalizer": "role:老道"}).json()
    assert "qc" in r and set(r["qc"]) >= {"repetition", "structural", "purple"}
    assert isinstance(r["leaks"], list)
    assert any(lk["marker"] for lk in r["leaks"])  # 至少一条泄露,marker 非空
    # 没有落库:章正文仍为空
    assert store.get_chapter(1) is None or not (store.get_chapter(1) or {}).get("prose")


def test_graph_does_not_leak_secret_value(store):
    luanshi_leak_world(store)
    g = _client(store).get("/graph").json()
    # 找出标记为 secret 的命题节点,断言其 label 不含私密原文
    secret_nodes = [n for n in g["nodes"] if n.get("secret")]
    assert secret_nodes, "应有 secret 命题节点"
    # luanshi_leak_world 的 secret 命题 value = "攒钱给老娘治眼",含「治眼」
    for n in secret_nodes:
        assert "治眼" not in (n.get("label") or ""), f"secret 节点 label 泄露明文: {n}"
        assert "攒钱" not in (n.get("label") or ""), f"secret 节点 label 泄露明文: {n}"


def test_world_rule_full_fields_roundtrip(store):
    c = _client(store)
    c.post("/world-rules", json={"name": "断契", "category": "magic", "source": "血契",
                                 "capabilities": ["斩断因果"], "limitations": ["需断臂"],
                                 "exceptions": ["满月无效"], "established_chapter": 3})
    rules = c.get("/world-rules").json()
    r = next((x for x in rules if x.get("name") == "断契"), None)
    assert r is not None
    assert r.get("limitations") == ["需断臂"], f"limitations 应写入: {r}"
    assert r.get("established_chapter") == 3


def test_faction_full_fields_roundtrip(store):
    c = _client(store)
    c.post("/factions", json={"name": "青叶门", "ideology": "复辟", "leader": "掌门",
                              "known_members": ["甲", "乙"], "first_mention_chapter": 2})
    facs = c.get("/factions").json()
    f = next((x for x in facs if x.get("name") == "青叶门"), None)
    assert f is not None
    assert f.get("known_members") == ["甲", "乙"], f"known_members 应写入: {f}"
    assert f.get("first_mention_chapter") == 2


def test_quality_word_count_matches_store_convention(store):
    c = _client(store)
    prose = "第一段。\n\n第二段,有标点和 空格。"
    c.post("/save-chapter", json={"seq": 1, "prose": prose, "title": "x", "focalizer": None})
    q = c.get("/quality").json()
    # /quality 各章 word_count 应与 store 字符数口径一致(去空白后的字符数)
    expected = len("".join(prose.split()))
    ch1 = next((x for x in q.get("chapters", q) if x.get("seq") == 1), None)
    assert ch1 is not None
    assert ch1["word_count"] == expected, f"字数口径应统一为字符数: {ch1['word_count']} != {expected}"


def test_quality_overdue_excludes_red_herring(store):
    c = _client(store)
    # 种两条都很早埋下、未回收;一条 promise、一条 red_herring
    store.plant_promise("正经伏笔", setup_chapter=1, kind="promise")
    store.plant_promise("红鲱鱼", setup_chapter=1, kind="red_herring")
    # max_chapter() 读 event 表的 valid_from 最大值;种一个 chapter=10 的事件使 1+3=4 < 10
    store.add_event(Event("ev:红鲱鱼测试", "action", story_time=10))
    q = c.get("/quality").json()
    # /quality 的 foreshadow.overdue 应只计 promise 类,不计 red_herring
    assert q["foreshadow"]["overdue"] == 1, (
        f"overdue 应为 1(仅 promise),实际为 {q['foreshadow']['overdue']}"
    )
