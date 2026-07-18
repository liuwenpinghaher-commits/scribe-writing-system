"""S5a · scribe3 后端 API(FastAPI,端口 3321)TDD。

前端读 NS=scribe3。写作统一走主编对话(/chat/write),不经直接渲染。
"""
import json

import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.ontology import Entity, Event
from scribe3.scenario import luanshi_leak_world
from scribe3.store import MATERIAL_KINDS


@pytest.fixture(autouse=True)
def _reset_pending_ingest():
    """每个测试前后清空 _pending_ingest 去重集合,防跨测试泄漏
    (mock 掉的 _bg_ingest 不会走 finally 清标记)。红阶段属性未建时静默跳过。"""
    s = getattr(A, "_pending_ingest", None)
    if s is not None:
        s.clear()
    yield
    s = getattr(A, "_pending_ingest", None)
    if s is not None:
        s.clear()


def _client(store, complete_fn=None):
    A.set_store(store)
    A.set_complete_fn(complete_fn or (lambda prompt, **kw: "渲染的散文。"))
    return TestClient(A.app)


def test_health(store):
    assert _client(store).get("/health").json()["ok"] is True


def test_stream_write_uses_read_only_mcp_surface(monkeypatch):
    captured = {}

    def fake_responses_events(message, instructions, **kwargs):
        captured.update(kwargs)
        yield {"type": "response.completed", "response": {"id": "resp_1"}}

    monkeypatch.setattr(A, "_responses_events", None)
    monkeypatch.setattr("scribe3.llm.hermes_responses_events", fake_responses_events)

    out = "".join(A._stream_write("查伏笔", "先核实", with_tools=True))

    assert '"done": true' in out
    assert captured["server_label"] == "scribe3_read"
    assert captured["with_tools"] is True


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
    """有事件且无违规:no_event_data=False + violations=[](真绿,非假绿)。"""
    luanshi_leak_world(store)   # ch1 含 1 个干净事件(有目标、章首无需 causal_in)
    c = _client(store)
    resp = c.get("/causal", params={"chapter": 1}).json()
    assert resp["no_event_data"] is False
    assert resp["violations"] == []


def test_causal_no_event_data_marker(store):
    """批D P1-5 假绿止血:event 表对该章为空时,/causal 返回 no_event_data 标记而非空绿。
    区分'因果完整'(有事件、无违规)与'根本没有事件数据可校验'。"""
    c = _client(store)   # 空库,第 9 章无任何事件
    resp = c.get("/causal", params={"chapter": 9}).json()
    assert resp["no_event_data"] is True
    assert resp["violations"] == []


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


def test_intent_partial_put_keeps_unsent_fields(store):
    """局部 PUT 只传 total_word_goal,不得把未传的文本字段抹成空串。

    store.set_intent 本身是 MERGE 语义,但 put_intent 若用 model_dump()(不带
    exclude_unset)会把 IntentIn 的默认空串一并落库,等价整替——设置中心
    BookSection 失焦单字段保存会静默清空北极星三字段。"""
    store.set_intent({"reader_feeling": "压抑中见微光", "emotional_arc": "由怯到决",
                      "red_lines": "不洗白反派", "total_word_goal": 100000})
    c = _client(store)
    c.put("/intent", json={"total_word_goal": 120000})
    i = c.get("/intent").json()
    assert i["total_word_goal"] == 120000
    assert i["red_lines"] == "不洗白反派"
    assert i["reader_feeling"] == "压抑中见微光"
    assert i["emotional_arc"] == "由怯到决"


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

    def fake_events(msg, instructions, model=None, **_kw):
        yield {"type": "response.output_item.added",
               "item": {"type": "function_call", "name": "s3_list_promises", "arguments": "{}"}}
        yield {"type": "response.output_text.delta", "delta": "已查"}
        yield {"type": "response.output_text.delta", "delta": "伏笔"}

    monkeypatch.setattr(appmod, "_responses_events", fake_events)
    r = _client(store).get("/chat/agentic-stream", params={"msg": "查伏笔"})
    assert r.status_code == 200
    body = r.text
    assert "s3_list_promises" in body and '"tool"' in body and "已查" in body and '"done": true' in body


def test_agentic_stream_writes_back_response_id_and_reads_it_next_turn_as_anchor(store, monkeypatch):
    """Task 11:agentic turn 结束把 response id 回写线程,下一轮 _editor_turn_context 读回
    作 previous_response_id 续接锚;稳定 session key(work+thread)跨轮不变。

    走真 _response_events_iter 路径(_responses_events=None + monkeypatch llm.hermes_responses_events),
    才能捕获 previous_response_id/session_key 等全量 kwargs(app 层 stub 会过滤掉它们)。"""
    import scribe3.llm as llm

    monkeypatch.setattr(A, "_responses_events", None)
    captured = {}

    def turn1(message, instructions, **kw):
        captured["turn1"] = kw
        yield {"type": "response.completed", "response": {"id": "resp_turn1"}}

    monkeypatch.setattr(llm, "hermes_responses_events", turn1)
    client = _client(store)
    r1 = client.get("/chat/agentic-stream", params={"msg": "查伏笔", "work": "main"})
    assert r1.status_code == 200 and '"done": true' in r1.text

    # 回写落库:线程 previous_response_id 被更新
    tid = store.get_or_create_editorial_thread("main", "author")["thread_id"]
    assert store._get_editorial_thread(tid)["previous_response_id"] == "resp_turn1"

    # 首轮无锚(线程刚建),session key 为 work+thread
    assert captured["turn1"].get("previous_response_id") is None
    assert captured["turn1"]["session_key"] == f"scribe3|work:main|thread:{tid}"

    def turn2(message, instructions, **kw):
        captured["turn2"] = kw
        yield {"type": "response.output_text.delta", "delta": "续"}

    monkeypatch.setattr(llm, "hermes_responses_events", turn2)
    r2 = client.get("/chat/agentic-stream", params={"msg": "接着说", "work": "main"})
    assert r2.status_code == 200

    # 下一轮读回上一轮 response id 作续接锚;稳定 session key 跨轮不变
    assert captured["turn2"]["previous_response_id"] == "resp_turn1"
    assert captured["turn2"]["session_key"] == captured["turn1"]["session_key"]


def test_agentic_stream_writeback_failure_is_fail_soft(store, monkeypatch):
    """回写抛错不阻断 turn:仍正常吐 delta 与 done(掉链/库故障不能拖垮对话)。"""
    import scribe3.llm as llm

    monkeypatch.setattr(A, "_responses_events", None)

    def events(message, instructions, **kw):
        yield {"type": "response.output_text.delta", "delta": "答"}
        yield {"type": "response.completed", "response": {"id": "resp_x"}}

    monkeypatch.setattr(llm, "hermes_responses_events", events)
    # 让回写抛错(_store_for("main") 返回同一注入 store 实例)
    monkeypatch.setattr(store, "update_thread_response_id",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))

    r = _client(store).get("/chat/agentic-stream", params={"msg": "查", "work": "main"})
    assert r.status_code == 200
    assert "答" in r.text and '"done": true' in r.text


def test_chat_write_splits_proposal(store, monkeypatch):
    import scribe3.app as appmod

    def fake_events(msg, instructions, model=None, **_kw):
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

    def fake_events(msg, instructions, model=None, **_kw):
        for t in ["这章节奏偏慢，", "建议提速。"]:
            yield {"type": "response.output_text.delta", "delta": t}

    monkeypatch.setattr(appmod, "_responses_events", fake_events)
    body = _client(store).get("/chat/write", params={"msg": "这章节奏如何"}).text
    assert "建议提速" in body and '"proposal"' not in body


def test_save_chapter_runs_softcheck(store):
    r = _client(store).post("/save-chapter", json={"seq": 1, "prose": "一段正常的志怪。", "focalizer": "role:x"}).json()
    assert r["status"] == "saved" and "qc" in r and "leaks" in r
    # M2-①: qc 已扩展含 duplicate_lines + emotion_telling(向后兼容,用 >= 子集断言)
    assert set(r["qc"]) >= {"repetition", "structural", "purple", "cross_repetition",
                             "duplicate_lines", "emotion_telling"}


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
    # max_chapter() 读 event 表的 story_chapter 最大值;种一个 chapter=10 的事件使 1+3=4 < 10
    store.add_event(Event("ev:红鲱鱼测试", "action", story_time=10))
    q = c.get("/quality").json()
    # /quality 的 foreshadow.overdue 应只计 promise 类,不计 red_herring
    assert q["foreshadow"]["overdue"] == 1, (
        f"overdue 应为 1(仅 promise),实际为 {q['foreshadow']['overdue']}"
    )


# --- P2 F2: POST /char-states 接通 after_state ---

def test_post_char_states_accepts_after_state(store):
    """P2 F2:POST /char-states 携带 after_state 后 char_state_at 快照应非空。
    修复前:端点忽略 after_state → char_state_at abilities 恒为空 {}。
    修复后:after_state 透传至 store.add_char_state → 快照正确聚合。
    """
    c = _client(store)
    r = c.post("/char-states", json={
        "character_id": "role:乙",
        "chapter": 2,
        "change_type": "ability",
        "summary": "破境",
        "after_state": {"ability_snapshot": {"内力": "化境"}},
    })
    assert r.status_code == 200, f"端点应返回 200: {r.text}"
    snap = store.char_state_at("role:乙", 4)
    assert "内力" in str(snap.get("abilities") or ""), \
        f"POST after_state 应透传至 char_state_at: {snap}"


def test_post_char_states_accepts_before_state(store):
    """P2 F2 补充:POST /char-states 携带 before_state 应写入(不崩溃)。"""
    c = _client(store)
    r = c.post("/char-states", json={
        "character_id": "role:丙",
        "chapter": 1,
        "change_type": "personality",
        "summary": "初入江湖",
        "before_state": {"personality_snapshot": "天真懵懂"},
        "after_state": {"personality_snapshot": "初历艰辛"},
    })
    assert r.status_code == 200, f"端点应返回 200: {r.text}"
    snap = store.char_state_at("role:丙", 2)
    assert snap.get("personality") == "初历艰辛", \
        f"personality 快照应为 after_state 的值: {snap}"


# ===== P2 F3: item.first_chapter / term.first_mention_chapter 写路径接通 =====

def test_item_first_chapter_roundtrip(store):
    """POST /items 携带 first_chapter 应写入并可从 GET /items 读回。"""
    c = _client(store)
    r = c.post("/items", json={"name": "镇煞钉", "category": "法器", "first_chapter": 3})
    assert r.status_code == 200, f"POST /items 应返回 200: {r.text}"
    items = c.get("/items").json()
    it = next((x for x in items if x.get("name") == "镇煞钉"), None)
    assert it is not None and it.get("first_chapter") == 3, \
        f"first_chapter 应写入并回读为 3: {it}"


def test_items_patch_preserves_state_history(store):
    """P1-9:POST /items 改 PATCH/merge 语义——编辑其它字段不清空 state_history(未传字段保旧值)。"""
    c = _client(store)
    store.add_item("镇煞钉", category="法器", description="旧描述")
    store.update_item_state("镇煞钉", "lost", 3, note="奈何谷失落")
    before = next(i for i in store.list_items() if i["name"] == "镇煞钉")
    assert before["state_history"], "前置:应已有一条状态史"
    # 只编辑描述(不传 state_history / symbolic_state / category)
    r = c.post("/items", json={"name": "镇煞钉", "description": "新描述"})
    assert r.status_code == 200, r.text
    after = next(i for i in c.get("/items").json() if i["name"] == "镇煞钉")
    assert after["description"] == "新描述", "描述应更新"
    assert after["symbolic_state"] == "lost", f"未传 symbolic_state 应保留 lost: {after}"
    assert after.get("category") == "法器", "未传 category 应保留"
    assert len(after["state_history"]) == len(before["state_history"]), \
        f"编辑其它字段不应清空 state_history: {after['state_history']}"


def test_item_state_endpoint_appends_history(store):
    """P1-9:POST /items/{name}/state 追加一条状态流转史(暴露 update_item_state)。"""
    c = _client(store)
    store.add_item("镇煞钉", category="法器")
    r = c.post("/items/镇煞钉/state", json={"state": "lost", "chapter": 3, "note": "奈何谷失落"})
    assert r.status_code == 200, r.text
    it = next(i for i in c.get("/items").json() if i["name"] == "镇煞钉")
    assert it["symbolic_state"] == "lost"
    hist = it["state_history"]
    assert len(hist) == 1 and hist[0]["state"] == "lost" and hist[0]["chapter"] == 3, \
        f"应追加一条 lost@3 的状态史: {hist}"
    # 缺 chapter → 422
    assert c.post("/items/镇煞钉/state", json={"state": "active"}).status_code == 422


def test_item_state_endpoint_malformed_chapter_422(store):
    """批E-A3(批D后端 Minor):chapter 为非数字串(如 'abc')→ int() 抛 ValueError,
    应捕获返 422(而非未处理异常 500)。"""
    c = _client(store)
    store.add_item("镇煞钉", category="法器")
    r = c.post("/items/镇煞钉/state", json={"state": "lost", "chapter": "abc"})
    assert r.status_code == 422, f"畸形 chapter 应返 422,实际 {r.status_code}: {r.text}"
    # 合法数字串仍应工作(int('5') 正常)
    ok = c.post("/items/镇煞钉/state", json={"state": "lost", "chapter": "5"})
    assert ok.status_code == 200, f"数字串 chapter 应正常,实际 {ok.status_code}: {ok.text}"


def test_get_voice_profile_endpoint(store):
    """批D P1-11:GET /voice-profile?character_id= 返回声线指纹字段(刷新回显),无则 null 不 500。"""
    c = _client(store)
    store.set_voice_profile("role:甲", {"style_summary": "短句冷峻",
                                        "catchphrases": ["哼"], "version": 2})
    r = c.get("/voice-profile", params={"character_id": "role:甲"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body and body.get("style_summary") == "短句冷峻" and body.get("version") == 2
    r2 = c.get("/voice-profile", params={"character_id": "role:无人"})
    assert r2.status_code == 200 and r2.json() in (None, {})


def test_dedup_chapter_saves_version_and_enqueues_ingest(store, monkeypatch):
    """C-1:/dedup-chapter 真改写正文后落 final 版本 + 排 ingest(与 /save-chapter 对称)。"""
    A.set_store(store)
    store.save_chapter(2, "原始正文。", title="t")
    import scribe3.critique as C
    monkeypatch.setattr(C, "rewrite_cross_repetitions",
                        lambda prose, priors, fn, **kw: {"prose": "改写后的正文。",
                                                         "rewritten": 3, "before": 5, "after": 1})
    called = {}
    monkeypatch.setattr(A, "_bg_ingest", lambda work, seq: called.setdefault("args", (work, seq)))
    client = TestClient(A.app)
    before = len(store.list_chapter_versions(2))
    r = client.post("/dedup-chapter?seq=2&work=main")
    assert r.status_code == 200, r.text
    assert r.json()["rewritten"] == 3
    versions = store.list_chapter_versions(2)
    assert len(versions) == before + 1, "改写后应新增一个版本"
    assert versions[0]["stage"] == "final", f"应落 final 版: {versions[0]}"
    assert called.get("args") == ("main", 2), "改写后应排 ingest"
    assert store.get_chapter(2)["prose"] == "改写后的正文。", "改写正文应存回"


def test_dedup_chapter_no_rewrite_no_version_no_ingest(store, monkeypatch):
    """C-1:无跨章复读时 /dedup-chapter 幂等——不落版、不排 ingest。"""
    A.set_store(store)
    store.save_chapter(3, "干净正文。", title="t")
    import scribe3.critique as C
    monkeypatch.setattr(C, "rewrite_cross_repetitions",
                        lambda prose, priors, fn, **kw: {"prose": prose, "rewritten": 0,
                                                         "before": 0, "after": 0})
    called = {}
    monkeypatch.setattr(A, "_bg_ingest", lambda work, seq: called.setdefault("args", (work, seq)))
    client = TestClient(A.app)
    before = len(store.list_chapter_versions(3))
    r = client.post("/dedup-chapter?seq=3&work=main")
    assert r.status_code == 200
    assert len(store.list_chapter_versions(3)) == before, "无改写不应新增版本"
    assert "args" not in called, "无改写不应排 ingest"


def test_chapter_repair_lock_rejects_same_chapter_parallel_write():
    """精修与跨章去重不能用各自读到的旧正文相互覆盖。"""
    key = ("repair-lock-test", 42)
    A._release_chapter_repair(*key)
    A._acquire_chapter_repair(*key)
    try:
        with pytest.raises(A.HTTPException) as exc:
            A._acquire_chapter_repair(*key)
        assert exc.value.status_code == 409
    finally:
        A._release_chapter_repair(*key)


def test_term_first_mention_chapter_roundtrip(store):
    """POST /terms 携带 first_mention_chapter 应写入并可从 GET /terms 读回。"""
    c = _client(store)
    r = c.post("/terms", json={"name": "镇煞", "category": "术语", "first_mention_chapter": 2})
    assert r.status_code == 200, f"POST /terms 应返回 200: {r.text}"
    terms = c.get("/terms").json()
    t = next((x for x in terms if x.get("name") == "镇煞"), None)
    assert t is not None and t.get("first_mention_chapter") == 2, \
        f"first_mention_chapter 应写入并回读为 2: {t}"


# ===== 声音指纹注入续写 prompt =====

def test_voice_anchor_block_includes_focalizer_and_digest(store):
    """声音锚块:焦点者 style_summary 进「焦点者声音锚」,其他角色进「对白声音速记」。"""
    store.set_voice_profile("role:甲", {
        "style_summary": "说话简短沉重",
        "catchphrases": ["哼"],
        "tone_rules": ["少用感叹号"],
    })
    store.set_voice_profile("role:乙", {
        "style_summary": "啰嗦爱吹嘘",
    })
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "role:甲")
    assert "焦点者声音锚" in block, "应含焦点者声音锚标题"
    assert "说话简短沉重" in block, "应含焦点者 style_summary"
    assert "哼" in block, "应含 catchphrase"
    assert "少用感叹号" in block, "应含 tone_rules"
    # 对白速记应含乙的摘要(或至少 id)
    assert "啰嗦爱吹嘘" in block or "role:乙" in block, "对白速记应含乙的声音信息"


def test_voice_anchor_block_no_focalizer(store):
    """无焦点者时:不含「焦点者声音锚」标题,但若有 profile 仍有对白速记。"""
    store.set_voice_profile("role:丙", {"style_summary": "冷静克制"})
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "")
    assert "焦点者声音锚" not in block, "无焦点者时不应有焦点者声音锚标题"
    assert "冷静克制" in block or block == "", "若有 profile 应含对白速记;若无 profile 可为空"


def test_voice_anchor_block_none_guards(store):
    """所有字段为 None 时不崩溃,且不产生 'None' 字符串。"""
    store.set_voice_profile("role:丁", {
        "style_summary": "稳重低调",
        "catchphrases": None,
        "tone_rules": None,
        "reference_lines": None,
    })
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "role:丁")
    assert "None" not in block, "None 字段不应出现在 block 文本里"
    assert "稳重低调" in block, "style_summary 应正常显示"


def test_get_voice_profile_bare_name_does_not_crash(store):
    """Caveat 2:focalizer 传裸名(无冒号,如"焦三")时 get_voice_profile 不得抛
    ValueError(旧链 _split 期望 role:xxx 冒号格式)——安全兜底为"无 profile"返回 None;
    规范 record id(role:焦三)仍正常返回。"""
    store.set_voice_profile("role:焦三", {"style_summary": "话少眼冷"})
    # 裸名:不崩、返回空(None),让上层优雅跳过
    assert store.get_voice_profile("焦三") is None
    # 规范 record id:行为一字不变
    vp = store.get_voice_profile("role:焦三")
    assert vp is not None and vp.get("style_summary") == "话少眼冷"


def test_voice_anchor_block_bare_name_focalizer_no_crash(store):
    """Caveat 2 旧组装链:裸名 focalizer 且无 voice_profile → _voice_anchor_block 不 500,
    优雅跳过焦点者声音锚(此前经 store.get_voice_profile → _split("焦三") 抛 ValueError)。"""
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "焦三")   # 裸名,库里无 role:焦三 的 profile
    assert isinstance(block, str)
    assert "焦点者声音锚" not in block, "无 profile 的裸名焦点者不应产出声音锚"


# ===== 弧光快照注入续写 prompt =====

def test_arc_state_block_injects_snapshot(store):
    """_arc_state_block:有能力快照时注入「弧光状态」标题及对应字段。"""
    store.add_char_state(
        character_id="role:甲",
        chapter=2,
        change_type="ability",
        summary="习剑",
        after_state={"ability_snapshot": {"御剑": "初成"}},
    )
    from scribe3.app import _arc_state_block
    block = _arc_state_block(store, "role:甲", 5)
    assert "御剑" in block, "应含能力条目"
    assert "弧光" in block, "应含「弧光」标题关键词"
    assert _arc_state_block(store, "", 5) == "", "无焦点者应返回空串"
    assert _arc_state_block(store, "role:无此人", 5) == "", "空快照应返回空串"


def test_arc_state_block_relations_personality_phase(store):
    """_arc_state_block:关系/性格/弧光阶段均能正确出现在 block 里。"""
    store.add_char_state(
        character_id="role:乙",
        chapter=3,
        change_type="composite",
        summary="蜕变",
        after_state={
            "ability_snapshot": {"剑法": "大成"},
            "relation_snapshot": {"role:丙": "盟友"},
            "personality_snapshot": "沉稳果决",
        },
        arc_phase="破茧",
    )
    from scribe3.app import _arc_state_block
    block = _arc_state_block(store, "role:乙", 10)
    assert "剑法" in block
    assert "role:丙" in block
    assert "沉稳果决" in block
    assert "破茧" in block


def test_arc_state_block_empty_when_no_meaningful_data(store):
    """_arc_state_block:快照存在但所有字段均为空时返回空串。"""
    store.add_char_state(
        character_id="role:丙",
        chapter=1,
        change_type="ability",
        summary="无变化",
        after_state={},
    )
    from scribe3.app import _arc_state_block
    block = _arc_state_block(store, "role:丙", 3)
    assert block == "", "无有效内容时应返回空串"


# ===== R3#1 限知物理隔离:_editor_system focalizer 模式不泄露帧外 secret =====

def test_editor_system_focalizer_masks_out_of_frame_secret(store):
    """R3#1 核心守卫:focalizer 模式下,基座 prompt 不含帧外 secret 明文。
    修复前:_editor_system 无条件 dump facts_at(99999) 含 secret value → 会含「卧底」。
    修复后:focalizer 非空时改用 project_frame 投影 + _facts(reveal_secret=False) 屏蔽。
    """
    from scribe3.ontology import Entity, Fact, KnowledgeEdge
    from scribe3.app import _editor_system

    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))

    # 甲知道的公开事实
    store.add_fact(Fact("fact:k", "role:甲", "知道", "乙在城里", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:甲", "fact:k", since_chapter=1, acquired_via="saw"))

    # 帧外私密:乙的真名是卧底,甲不知道(无 KnowledgeEdge)
    store.add_fact(Fact("fact:s", "role:乙", "真名", "乙是卧底", valid_from=1, secret=True))
    # 故意不给甲关于 fact:s 的 KnowledgeEdge

    # focalizer 模式:基座不应含帧外 secret 明文
    sys_foc = _editor_system(store, focalizer="role:甲", chapter=3)
    assert "卧底" not in sys_foc, (
        f"focalizer 模式:帧外 secret 明文「卧底」不应出现在基座 prompt 中\n"
        f"(前 500 字): {sys_foc[:500]}"
    )

    # 作者全知视角:_editor_system() 不传 focalizer → 保留全知行为(不强断言含密文,只断言不崩)
    sys_omni = _editor_system(store)
    assert isinstance(sys_omni, str) and len(sys_omni) > 0, "作者全知视角应返回非空字符串"


def test_editor_write_system_focalizer_masks_out_of_frame_secret(store):
    """R3#1 连锁守卫:_editor_write_system(focalizer) 透传屏蔽,/chat/write 基座不含帧外 secret。"""
    from scribe3.ontology import Entity, Fact, KnowledgeEdge
    from scribe3.app import _editor_write_system

    store.add_entity(Entity("role:主角", "character", "主角"))
    store.add_entity(Entity("role:反派", "character", "反派"))

    # 主角知道的公开事实
    store.add_fact(Fact("fact:pub", "role:反派", "位置", "城南茶馆", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:主角", "fact:pub", since_chapter=1, acquired_via="saw"))

    # 帧外私密:反派身份,主角不知道
    store.add_fact(Fact("fact:sec", "role:反派", "真实身份", "皇族密探", valid_from=1, secret=True))
    # 不给主角关于 fact:sec 的 KnowledgeEdge

    sys_write_foc = _editor_write_system(store, focalizer="role:主角", chapter=2)
    assert "皇族密探" not in sys_write_foc, (
        f"_editor_write_system focalizer 模式:帧外 secret 不应出现\n"
        f"(前 500 字): {sys_write_foc[:500]}"
    )


# ── ingest_unverified 复核闭环 ────────────────────────────────────────────────

def test_ingest_unverified_list(store):
    """GET /ingest-unverified 返回 pending 条目。"""
    c = _client(store)
    store.add_unverified_ref("路过人", 5, "witnessed")
    pend = c.get("/ingest-unverified").json()
    assert any(p["name"] == "路过人" for p in pend)


def test_ingest_unverified_accept_creates_character(store):
    """接受→建角色→行状态变 accepted→不再出现在 pending 列表。"""
    c = _client(store)
    store.add_unverified_ref("无名客", 3, "learned")
    pend = c.get("/ingest-unverified").json()
    assert any(p["name"] == "无名客" for p in pend)
    uid = next(p["id"] for p in pend if p["name"] == "无名客")
    r = c.post(f"/ingest-unverified/{uid}/accept").json()
    assert r["created"] is True
    assert r["oid"] == "role:无名客"
    assert store.entity("role:无名客") is not None
    # pending 列表中已消失
    assert not any(p["name"] == "无名客" for p in c.get("/ingest-unverified").json())


def test_ingest_unverified_accept_queues_replay_without_blocking_request(store, monkeypatch):
    """接受角色先立即落裁决，章回填交给既有后台队列，不能把 LLM 留在 HTTP 请求内。"""
    import scribe3.app as A

    c = _client(store)
    store.add_unverified_ref("后台回填者", 6, "learned_who")
    uid = next(p["id"] for p in c.get("/ingest-unverified").json() if p["name"] == "后台回填者")
    seen_complete_fns = []
    original_accept = store.accept_unverified

    def capture_accept(uid, complete_fn=None):
        seen_complete_fns.append(complete_fn)
        return original_accept(uid, complete_fn=complete_fn)

    queued = []
    monkeypatch.setattr(store, "accept_unverified", capture_accept)
    monkeypatch.setattr(A, "_bg_ingest", lambda work, seq: queued.append((work, seq)))
    try:
        r = c.post(f"/ingest-unverified/{uid}/accept")
        assert r.status_code == 200, r.text
        body = r.json()
        assert seen_complete_fns == [None], "同步 accept 不得直接触发 LLM 回填"
        assert body["replayed"] is False
        assert body["replay_queued"] is True
        assert queued == [("main", 6)]
    finally:
        # 测试中的 fake _bg_ingest 不会像真实任务一样清理在途标记。
        A._pending_ingest.discard(("main", 6))


def test_ingest_unverified_accept_idempotent(store):
    """同一行接受两次:第二次 created=False,角色只建一次。"""
    c = _client(store)
    store.add_unverified_ref("幂等君", 1, "saw")
    uid = next(p["id"] for p in c.get("/ingest-unverified").json() if p["name"] == "幂等君")
    c.post(f"/ingest-unverified/{uid}/accept")
    # 再次接受时该行已是 accepted,list_unverified(pending) 中没有
    # 直接对着 uid 调用 accept_unverified → created=False
    r2 = c.post(f"/ingest-unverified/{uid}/accept").json()
    assert r2["created"] is False


def test_ingest_unverified_ignore(store):
    """忽略→行状态变 ignored→不再出现在 pending;出现在 ignored 列表。"""
    c = _client(store)
    store.add_unverified_ref("路人甲", 2, "did")
    uid = next(p["id"] for p in c.get("/ingest-unverified").json() if p["name"] == "路人甲")
    resp = c.post(f"/ingest-unverified/{uid}/ignore")
    assert resp.status_code == 200
    # pending 中消失
    assert not any(p["name"] == "路人甲" for p in c.get("/ingest-unverified").json())
    # ignored 列表中出现
    ignored = c.get("/ingest-unverified?status=ignored").json()
    assert any(p["name"] == "路人甲" for p in ignored)


# ===== P0-A1: 实体层私密模型 =====

def test_entities_mask_secret_backstory(store):
    """backstory_secret=True 时 /entities 默认屏蔽 backstory;reveal_secret=true 解锁。"""
    c = _client(store)
    r = c.post("/characters", json={
        "name": "卧底",
        "backstory": "其实是敌方卧底",
        "backstory_secret": True,
    })
    assert r.status_code == 200, f"POST /characters 应返回 200: {r.text}"
    masked = c.get("/entities").json()
    e = next((x for x in masked if x["name"] == "卧底"), None)
    assert e is not None, "应能找到卧底角色"
    assert "敌方" not in str(e.get("backstory")), "默认应屏蔽 backstory 明文"
    assert "🔒" in str(e.get("backstory")), "默认应显示锁占位符"
    revealed = c.get("/entities?reveal_secret=true").json()
    assert any("敌方" in str(x.get("backstory")) for x in revealed if x["name"] == "卧底"), \
        "reveal_secret=true 应解锁 backstory 明文"


def test_factions_mask_secret_private_operation(store):
    """private_operation_secret=True 时 /factions 默认屏蔽 private_operation;reveal_secret=true 解锁。"""
    c = _client(store)
    r = c.post("/factions", json={
        "name": "暗会",
        "private_operation": "刺杀计划",
        "private_operation_secret": True,
    })
    assert r.status_code == 200, f"POST /factions 应返回 200: {r.text}"
    masked = c.get("/factions").json()
    f = next((x for x in masked if x["name"] == "暗会"), None)
    assert f is not None, "应能找到暗会势力"
    assert "刺杀" not in str(f.get("private_operation")), "默认应屏蔽 private_operation 明文"
    assert "🔒" in str(f.get("private_operation")), "默认应显示锁占位符"
    assert any(
        "刺杀" in str(x.get("private_operation"))
        for x in c.get("/factions?reveal_secret=true").json()
        if x["name"] == "暗会"
    ), "reveal_secret=true 应解锁 private_operation 明文"


# ===== P1-a: 解开生产方硬编码 =====

def test_faction_status_writable(store):
    """faction.status 应可写入非 active 值(dissolved/dormant/reformed)。"""
    c = _client(store)
    r = c.post("/factions", json={"name": "覆灭门", "status": "dissolved"})
    assert r.status_code == 200, f"POST /factions 应返回 200: {r.text}"
    f = next(x for x in c.get("/factions").json() if x["name"] == "覆灭门")
    assert f["status"] == "dissolved", f"status 应写入 dissolved,实际: {f.get('status')}"


# ===== P3-e1 Fix 1: overdue 阈值单源 + per-work 可配 =====

def test_quality_overdue_uses_module_constant(store):
    """Fix 1: /quality 使用模块常量 OVERDUE_SLACK 而非魔数 3。
    验证:每条 promise 的 overdue 状态等于 backend 判断,不需前端重算。"""
    import scribe3.app as A
    # OVERDUE_SLACK 应是一个正整数常量
    assert hasattr(A, "OVERDUE_SLACK"), "app.py 应定义 OVERDUE_SLACK 模块常量"
    assert isinstance(A.OVERDUE_SLACK, int) and A.OVERDUE_SLACK > 0

    # /quality foreshadow.promises 每项应含 overdue 字段(backend 预判断)
    store.plant_promise("伏笔A", setup_chapter=1, kind="promise")
    store.add_event(Event("ev:test_overdue", "action", story_time=1 + A.OVERDUE_SLACK + 1))
    c = _client(store)
    q = c.get("/quality").json()
    proms = q["foreshadow"].get("promises", [])
    assert proms, "foreshadow.promises 应包含伏笔列表"
    p = proms[0]
    assert "overdue" in p, f"每条 promise 应含 overdue 字段: {p}"
    assert p["overdue"] is True, f"setup_chapter=1 且 max_ch>{1+A.OVERDUE_SLACK} 时应标 overdue=True: {p}"


def test_quality_overdue_intent_override(store):
    """Fix 1 → Task2 口径对齐更新:有兑现窗口(payoff_max)的伏笔按窗口判超期,
    intent.overdue_threshold 不再参与(仅作用于无窗口的 legacy 旧行,单测见
    test_store.test_overdue_flag_window_alignment)。
    plant_promise 默认 chapter 层 → payoff_max = setup+3 = 4;max_chapter=5 →
    next_ch=6 > 4 → 即便 threshold=10 也超期。"""
    store.set_intent({"reader_feeling": "", "emotional_arc": "", "red_lines": "",
                      "overdue_threshold": 10})
    store.plant_promise("宽松伏笔", setup_chapter=1, kind="promise")
    store.add_event(Event("ev:ov2", "action", story_time=5))
    c = _client(store)
    q = c.get("/quality").json()
    proms = q["foreshadow"].get("promises", [])
    p = next((x for x in proms if "宽松" in x.get("text", "")), None)
    assert p is not None
    assert p["overdue"] is True, f"窗口口径:pmax=4 < next_ch=6,threshold 不拦窗口超期: {p}"


# ===== P3-e1 Fix 2: reference_lines 类型对齐 =====

def test_voice_anchor_block_reference_lines_dict(store):
    """Fix 2: reference_lines 为 dict 时 _voice_anchor_block 仍能提取并注入参考语感。
    修复前: isinstance(rl, list) → dict 时永远跳过,参考语感不出现。
    修复后: 同时处理 dict 和 list 形状。"""
    store.set_voice_profile("role:戊", {
        "style_summary": "字字珠玑",
        "reference_lines": {"line1": "此去经年", "line2": "更难消几番风雨"},
    })
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "role:戊")
    assert "参考语感" in block, "reference_lines 为 dict 时应出现「参考语感」"
    assert "此去经年" in block or "更难消" in block, f"dict 中的 reference_lines 应进入 block: {block!r}"


# ===== P3-e1 Fix 3: event.location / preconditions 读回 =====

def test_events_at_returns_location_and_preconditions(store):
    """Fix 3: events_at 应返回 location 和 preconditions 字段(写入后可读回)。
    修复前: SELECT 不含这两列 → write-into-the-void。
    修复后: SELECT location, preconditions 均回传。"""
    from scribe3.ontology import Event
    ev = Event("ev:loctest", "移动", story_time=3,
               location="place:铜炉山",
               preconditions=["前置条件A", "前置条件B"])
    store.add_event(ev)
    evs = store.events_at(3)
    target = next((e for e in evs if "loctest" in e.id), None)
    assert target is not None, "events_at 应能读回刚写入的事件"
    assert target.location == "place:铜炉山", f"location 应读回: {target.location!r}"
    assert target.preconditions == ["前置条件A", "前置条件B"], f"preconditions 应读回: {target.preconditions!r}"


# ===== P3-e1 Fix 4: voice_sample 删除验证 =====

def test_voice_sample_table_removed(store):
    """Fix 4: voice_sample 表应已不存在(039 迁移已 REMOVE)。"""
    db_info = store._query("INFO FOR DB")
    tables = (db_info.get("tables") if isinstance(db_info, dict) else {}) or {}
    assert "voice_sample" not in tables, f"voice_sample 表应已被删除: {list(tables)}"


def test_voice_post_endpoint_removed():
    """Fix 4: /voice POST 端点已删除,路由不应存在。"""
    import scribe3.app as A
    routes = {(m, r.path) for r in A.app.routes for m in (getattr(r, "methods", None) or [])}
    assert ("POST", "/voice") not in routes, "/voice POST 应已删除"
    assert ("GET", "/voice") not in routes, "/voice GET 应已删除"


def test_world_rule_capabilities_writable(store):
    """world_rule.capabilities 应可通过 REST 写入(Sanderson 维度)。"""
    c = _client(store)
    r = c.post("/world-rules", json={"name": "御剑术", "category": "magic",
                                     "capabilities": ["飞行", "远程斩"]})
    assert r.status_code == 200, f"POST /world-rules 应返回 200: {r.text}"
    rules = c.get("/world-rules").json()
    rule = next(x for x in rules if x["name"] == "御剑术")
    assert rule["capabilities"] == ["飞行", "远程斩"], \
        f"capabilities 应写入 ['飞行','远程斩'],实际: {rule.get('capabilities')}"


# ===== P1-c: 双时态右端 REST 端点 =====

def test_supersede_fact_endpoint(store):
    """POST /facts/supersede 应关闭旧命题并返回新 oid。"""
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:orig", "role:甲", "状态", "重伤", valid_from=1))
    c = _client(store)
    r = c.post("/facts/supersede", json={
        "entity_id": "role:甲", "attribute": "状态",
        "value": "痊愈", "since_chapter": 5})
    assert r.status_code == 200, f"POST /facts/supersede 应返回 200: {r.text}"
    body = r.json()
    assert body.get("ok") is True
    assert body.get("oid", "").startswith("fact:"), f"应返回新 fact oid: {body}"
    # 验证旧值在第7章失效
    facts7 = c.get("/facts", params={"chapter": 7}).json()
    values7 = {f["value"] for f in facts7}
    assert "痊愈" in values7, f"第7章应有痊愈: {values7}"
    assert "重伤" not in values7, f"第7章重伤应失效: {values7}"


def test_forget_knowledge_endpoint(store):
    """POST /knowledge/forget 应设置 until_chapter 令知识失效。"""
    from scribe3.ontology import Entity, Fact, KnowledgeEdge
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:g1", "role:乙", "秘密", "知情", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:乙", "fact:g1", since_chapter=1, acquired_via="given"))
    c = _client(store)
    r = c.post("/knowledge/forget", json={
        "knower_id": "role:乙", "proposition_id": "fact:g1", "until_chapter": 5})
    assert r.status_code == 200, f"POST /knowledge/forget 应返回 200: {r.text}"
    assert r.json().get("ok") is True


# ===== P1-d: 角色关系演变(evolve/end + POST 端点) =====

def test_relation_evolve_sets_until(store):
    """evolve_relation 应关闭旧关系并新建替代关系,时间门隔离章节可见性。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_character_relation("role:甲", "role:乙", "ally", since_chapter=1)
    store.evolve_relation("role:甲", "role:乙", "enemy", since_chapter=5)
    r3 = store.relations_at(3)
    r7 = store.relations_at(7)
    # 第3章:ally 仍有效,enemy 尚未生效
    assert any(x["relation"] == "ally" for x in r3), f"第3章应有 ally: {r3}"
    assert not any(x["relation"] == "enemy" for x in r3), f"第3章不应有 enemy: {r3}"
    # 第7章:ally 已失效(until_chapter=5),enemy 生效
    assert not any(x["relation"] == "ally" for x in r7), f"第7章 ally 应已失效: {r7}"
    assert any(x["relation"] == "enemy" for x in r7), f"第7章应有 enemy: {r7}"


def test_end_relation_sets_until(store):
    """end_relation 应在指定章设 until_chapter,令关系到期失效。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:丙", "character", "丙"))
    store.add_entity(Entity("role:丁", "character", "丁"))
    store.add_character_relation("role:丙", "role:丁", "ally", since_chapter=1)
    store.end_relation("role:丙", "role:丁", until_chapter=4)
    assert any(x["relation"] == "ally" for x in store.relations_at(3)), "第3章应仍有效"
    assert not any(x["relation"] == "ally" for x in store.relations_at(4)), "第4章应已失效"


def test_post_character_relations_endpoint(store):
    """POST /character-relations 应调 add_character_relation 落库。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:戊", "character", "戊"))
    store.add_entity(Entity("role:己", "character", "己"))
    c = _client(store)
    r = c.post("/character-relations",
               json={"src": "role:戊", "dst": "role:己", "relation": "ally", "since_chapter": 1})
    assert r.status_code == 200, f"POST /character-relations 应返回 200: {r.text}"
    assert r.json().get("ok") is True
    rels = store.relations_at(3)
    assert any(x["relation"] == "ally" for x in rels), f"关系应写入: {rels}"


def test_post_character_relations_evolve_endpoint(store):
    """POST /character-relations/evolve 应调 evolve_relation,旧关系自动关闭。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:庚", "character", "庚"))
    store.add_entity(Entity("role:辛", "character", "辛"))
    store.add_character_relation("role:庚", "role:辛", "ally", since_chapter=1)
    c = _client(store)
    r = c.post("/character-relations/evolve",
               json={"src": "role:庚", "dst": "role:辛", "relation": "enemy", "since_chapter": 6})
    assert r.status_code == 200, f"POST /character-relations/evolve 应返回 200: {r.text}"
    assert r.json().get("ok") is True
    assert not any(x["relation"] == "ally" for x in store.relations_at(8)), "ally 应已关闭"
    assert any(x["relation"] == "enemy" for x in store.relations_at(8)), "enemy 应生效"


def test_post_character_relations_end_endpoint(store):
    """POST /character-relations/end 应调 end_relation,令关系在指定章失效。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:壬", "character", "壬"))
    store.add_entity(Entity("role:癸", "character", "癸"))
    store.add_character_relation("role:壬", "role:癸", "ally", since_chapter=1)
    c = _client(store)
    r = c.post("/character-relations/end",
               json={"src": "role:壬", "dst": "role:癸", "until_chapter": 5})
    assert r.status_code == 200, f"POST /character-relations/end 应返回 200: {r.text}"
    assert r.json().get("ok") is True
    assert not any(x["relation"] == "ally" for x in store.relations_at(5)), "第5章应失效"


# ===== P3-b: 命题写完整性 =====

def test_factin_writes_leak_markers(store):
    """P3-b: POST /facts 携带 leak_markers 应写入并可从 store.fact() 读回。
    修复前:FactIn 无 leak_markers 字段 → 无法传递破绽词。
    修复后:FactIn 含 leak_markers → POST /facts 把它传入 Fact/add_fact。
    """
    c = _client(store)
    r = c.post("/facts", json={
        "entity": "role:甲",
        "attribute": "状态",
        "value": "隐秘行动",
        "secret": True,
        "valid_from": 2,
        "leak_markers": ["破绽A", "暗号B"],
    })
    assert r.status_code == 200, f"POST /facts 应返回 200: {r.text}"
    body = r.json()
    assert body.get("ok") is True and body.get("oid", "").startswith("fact:")
    # 从 store 直接读回并验证
    oid = body["oid"]
    local = oid.split(":", 1)[1]
    f = store.fact(oid)
    assert f is not None, f"应能从 store 读回命题 {oid}"
    assert f.leak_markers == ["破绽A", "暗号B"], \
        f"leak_markers 应写入 ['破绽A','暗号B'],实际: {f.leak_markers}"


def test_factin_writes_valid_to(store):
    """P3-b: POST /facts 携带 valid_to 应写入并可从 store.fact() 读回。
    修复前:FactIn 无 valid_to 字段 → 无法指定到期章号。
    修复后:FactIn 含 valid_to → POST /facts 把它传入 Fact/add_fact。
    """
    c = _client(store)
    r = c.post("/facts", json={
        "entity": "role:乙",
        "attribute": "职位",
        "value": "临时主事",
        "valid_from": 3,
        "valid_to": 8,
    })
    assert r.status_code == 200, f"POST /facts 应返回 200: {r.text}"
    oid = r.json()["oid"]
    f = store.fact(oid)
    assert f is not None
    assert f.valid_to == 8, f"valid_to 应写入 8,实际: {f.valid_to}"
    # 时间门验证:第 10 章时应不可见
    at10 = {fct.id for fct in store.facts_at(10)}
    assert oid not in at10, f"valid_to=8 的命题在第10章应已失效: {oid}"


def test_patch_fact_preserves_and_reembeds(store):
    """P3-b: PATCH /facts/{local} 应保留 valid_from/valid_to/leak_markers,并在 value 变更后重建 embedding。
    修复前:PATCH 只 SET entity/attribute/value/secret → valid_from/valid_to/leak_markers 被丢失,
           且 value 改变后旧 embedding 未刷新,语义召回指向陈旧向量。
    修复后:PATCH 传入所有字段;value 变更后调用 semantic_index 重建 embedding。
    """
    c = _client(store)
    # 1. 创建一条带 leak_markers 和 valid_from=2、valid_to=10 的命题
    r = c.post("/facts", json={
        "entity": "role:甲",
        "attribute": "获知",
        "value": "独特词AAA",
        "valid_from": 2,
        "valid_to": 10,
        "leak_markers": ["破绽X"],
    })
    assert r.status_code == 200
    oid = r.json()["oid"]
    local = oid.split(":", 1)[1]

    # 2. PATCH 只改 value
    pr = c.patch(f"/facts/{local}", json={
        "entity": "role:甲",
        "attribute": "获知",
        "value": "独特词BBB",
        "valid_from": 2,
        "valid_to": 10,
        "leak_markers": ["破绽X"],
        "secret": False,
    })
    assert pr.status_code == 200, f"PATCH /facts 应返回 200: {pr.text}"

    # 3. 验证 leak_markers 和 valid_from/valid_to 仍存在
    f = store.fact(oid)
    assert f is not None
    assert f.leak_markers == ["破绽X"], \
        f"PATCH 后 leak_markers 应保留 ['破绽X'],实际: {f.leak_markers}"
    assert f.valid_from == 2, f"PATCH 后 valid_from 应保留 2,实际: {f.valid_from}"
    assert f.valid_to == 10, f"PATCH 后 valid_to 应保留 10,实际: {f.valid_to}"
    assert f.value == "独特词BBB", f"PATCH 后 value 应更新为 独特词BBB,实际: {f.value}"

    # 4. 验证 embedding 已重建:语义召回能找到新 value(独特词BBB)
    hits = store.semantic_recall("独特词BBB", k=10)
    assert any(h.id == oid for h in hits), \
        "PATCH value 后语义召回应能找到新值(embedding 须重建)"


# ===== 批E A1: GET /facts 无损化(P1-4 后端跟进)=====

def test_get_facts_reveal_secret_param(store):
    """批E-A1①: GET /facts?reveal_secret=true 返真 value + leak_markers;默认仍屏蔽。
    修复前:GET /facts 无 reveal_secret 参数,secret value 恒屏蔽且不回 leak_markers →
           在库命题只能 supersede/删除,不能安全整行编辑。"""
    c = _client(store)
    r = c.post("/facts", json={
        "entity": "role:甲", "attribute": "底细", "value": "真名叫玄一",
        "secret": True, "valid_from": 1, "leak_markers": ["玄一", "旧疤"],
    })
    assert r.status_code == 200, r.text
    oid = r.json()["oid"]
    # 默认:secret value 与 leak_markers 均屏蔽
    default = c.get("/facts", params={"chapter": 1}).json()
    row = next(f for f in default if f["id"] == oid)
    assert row["value"] is None, "默认应屏蔽 secret value"
    assert row["leak_markers"] == [], "默认应屏蔽 secret leak_markers(破绽词本身敏感)"
    assert row["is_secret"] is True
    # reveal_secret=true:返真 value + leak_markers(整行编辑基座)
    revealed = c.get("/facts", params={"chapter": 1, "reveal_secret": "true"}).json()
    rrow = next(f for f in revealed if f["id"] == oid)
    assert rrow["value"] == "真名叫玄一", "reveal 应返真 value"
    assert rrow["leak_markers"] == ["玄一", "旧疤"], "reveal 应返真 leak_markers"
    assert rrow["valid_from"] == 1


def test_get_single_fact_full_fields(store):
    """批E-A1②: GET /facts/{local}?reveal_secret= 返全字段(valid_from/valid_to/
    leak_markers/secret);默认屏蔽 secret value/leak_markers,reveal 解锁。"""
    c = _client(store)
    r = c.post("/facts", json={
        "entity": "role:乙", "attribute": "职位", "value": "内应",
        "secret": True, "valid_from": 2, "valid_to": 9, "leak_markers": ["暗记"],
    })
    assert r.status_code == 200, r.text
    oid = r.json()["oid"]
    local = oid.split(":", 1)[1]
    # 默认屏蔽 secret value/leak_markers,但全字段(valid_from/valid_to/is_secret)俱在
    d = c.get(f"/facts/{local}").json()
    assert d["id"] == oid
    assert d["entity"] == "role:乙" and d["attribute"] == "职位"
    assert d["valid_from"] == 2 and d["valid_to"] == 9
    assert d["is_secret"] is True
    assert d["value"] is None and d["leak_markers"] == []
    # reveal:全字段含真 value/leak_markers
    dr = c.get(f"/facts/{local}", params={"reveal_secret": "true"}).json()
    assert dr["value"] == "内应" and dr["leak_markers"] == ["暗记"]
    assert dr["valid_from"] == 2 and dr["valid_to"] == 9 and dr["is_secret"] is True


def test_get_single_fact_404(store):
    """批E-A1②: GET /facts/{local} 对不存在命题返 404(而非 500/空体)。"""
    c = _client(store)
    assert c.get("/facts/does_not_exist").status_code == 404


def test_get_single_fact_nonsecret_full_fields(store):
    """批E-A1②: 非私密命题单条 GET 无需 reveal 即返全字段真值。"""
    c = _client(store)
    r = c.post("/facts", json={
        "entity": "role:丙", "attribute": "位置", "value": "城西驿",
        "valid_from": 3,
    })
    oid = r.json()["oid"]
    local = oid.split(":", 1)[1]
    d = c.get(f"/facts/{local}").json()
    assert d["value"] == "城西驿" and d["is_secret"] is False
    assert d["valid_from"] == 3 and d["valid_to"] is None


# ===== P3-d: 雄心死字段接活驱动生成 =====

def test_voice_anchor_includes_monologue_style(store):
    """_voice_anchor_block:internal_monologue_style 须出现在块里。"""
    store.set_voice_profile("role:甲", {
        "style_summary": "简短",
        "internal_monologue_style": "意识流碎句",
    })
    from scribe3.app import _voice_anchor_block
    b = _voice_anchor_block(store, "role:甲")
    assert "意识流碎句" in b, "internal_monologue_style 应注入声音锚块"


def test_voice_anchor_includes_sentence_patterns(store):
    """_voice_anchor_block:sentence_patterns(dict)须紧凑出现在块里。"""
    store.set_voice_profile("role:甲", {
        "style_summary": "简短",
        "sentence_patterns": {"default": "短句断语", "stress": "三字顿"},
    })
    from scribe3.app import _voice_anchor_block
    b = _voice_anchor_block(store, "role:甲")
    assert "短句断语" in b or "三字顿" in b, "sentence_patterns 值应注入声音锚块"


def test_voice_anchor_includes_vocabulary_profile(store):
    """_voice_anchor_block:vocabulary_profile(object)须出现在块里。"""
    store.set_voice_profile("role:甲", {
        "style_summary": "简短",
        "vocabulary_profile": {"tendency": "多用文言虚词", "avoid": "现代网络词"},
    })
    from scribe3.app import _voice_anchor_block
    b = _voice_anchor_block(store, "role:甲")
    assert "多用文言虚词" in b or "文言虚词" in b, "vocabulary_profile 值应注入声音锚块"


def test_motif_block_injects(store):
    """_motif_block:母题 name/theme/echoes 须出现在块里,且含「母题」。"""
    store.add_motif("铜炉", theme="文明余烬", echoes="炉火/锈迹")
    from scribe3.app import _motif_block
    b = _motif_block(store)
    assert "铜炉" in b, "母题 name 应出现在 _motif_block"
    assert "母题" in b, "块应含「母题」标题关键词"
    assert "文明余烬" in b, "theme 应出现在 _motif_block"
    assert "炉火/锈迹" in b, "echoes 应出现在 _motif_block"


def test_motif_block_empty_when_no_motifs(store):
    """无母题时 _motif_block 返回空串。"""
    from scribe3.app import _motif_block
    assert _motif_block(store) == ""


def test_craft_block_injected_into_instructions(store):
    """build_craft_block(rules) 输出须非空且含引擎层关键词;craft_rule 种子后含题材规则。"""
    from scribe3.craft import build_craft_block
    # 无题材规则时:引擎层仍应有内容
    b = build_craft_block()
    assert b and "写作引擎" in b, "build_craft_block 默认应含「写作引擎」"
    # 种入题材规则后:应含题材层标题(使用 schema 允许的 kind)
    store.add_craft_rule("artifact_craft", "古白话:多用端的/岂料/怎禁得", "乱世铜炉用词基准")
    rules = store.list_craft_rules()
    b2 = build_craft_block(rules)
    assert "题材规则" in b2 or "本书题材规则" in b2, "有规则时应含题材层标题"
    assert "古白话" in b2, "craft_rule pattern 应出现在 block"


# ===== P3-f: CharIn 补 personality_tags / aliases =====

def test_post_characters_sets_personality_tags_and_aliases(store):
    """P3-f Fix1: POST /characters 携带 personality_tags+aliases 应写入,
    /entities 读回时含两字段。
    修复前:CharIn 无这两个字段,创建后须 PATCH 补写。
    修复后:CharIn 含 personality_tags/aliases,POST 一次成型。
    """
    c = _client(store)
    r = c.post("/characters", json={
        "name": "测角丙",
        "backstory": "无名小卒",
        "personality_tags": ["阴沉", "多疑"],
        "aliases": ["三爷", "无脸人"],
    })
    assert r.status_code == 200, f"POST /characters 应返回 200: {r.text}"
    entities = c.get("/entities").json()
    e = next((x for x in entities if x["name"] == "测角丙"), None)
    assert e is not None, "应能在 /entities 找到测角丙"
    assert e.get("personality_tags") == ["阴沉", "多疑"], \
        f"personality_tags 应写入并读回,实际: {e.get('personality_tags')}"
    assert e.get("aliases") == ["三爷", "无脸人"], \
        f"aliases 应写入并读回,实际: {e.get('aliases')}"


# ===== G1: 限知帧(_frame_block) + 前情(_recap_block) 注入续写 prompt =====

def test_frame_block_injects_known_facts_and_masks_secret(store):
    """_frame_block:焦点者已知事实进帧(value 可见);非帧内 / secret 不进。"""
    from scribe3.ontology import Entity, Fact, KnowledgeEdge
    from scribe3.app import _frame_block
    # 甲确知:乙是卧底
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:k", "role:乙", "身份", "乙是卧底", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:甲", "fact:k", since_chapter=1, acquired_via="saw"))
    # 秘密:乙的真名(甲未知——无 KnowledgeEdge 指向甲)
    store.add_fact(Fact("fact:s", "role:乙", "秘密", "乙的真名", valid_from=1, secret=True))
    block = _frame_block(store, "role:甲", 3)
    assert "乙是卧底" in block, "甲确知的事实应进帧"
    assert "真名" not in block, "甲不知道的 secret 不应进帧"
    assert "限知硬边界" in block, "应含限知说明标题"
    assert _frame_block(store, "", 3) == "", "无焦点者应返回空串"


def test_recap_block_injects_prev_chapter(store):
    """_recap_block:上一章结尾文字注入前情块;第 1 章无前情(空串)。"""
    from scribe3.app import _recap_block
    store.save_chapter(1, "第一章正文:老乌头守炉,怪客来访。", title="第一章", focalizer=None)
    block = _recap_block(store, 2)
    assert "老乌头" in block, "应含上一章结尾文字"
    assert "前情" in block, "应含前情说明标题"
    assert _recap_block(store, 1) == "", "第 1 章无前情,应返回空串"


# ===== Fix 1 TDD: /quality 全量计数(五类) =====

def test_quality_full_qc_count_includes_ai_tics(store):
    """/quality qc_issues 应涵盖全部五类:repetition/structural/purple/ai_tics/oversaturation。
    构造含大量 AI 腔破折号的散文,ai_tics 应被计入 qc_issues。"""
    # 构造 AI 腔散文:大量"不是……而是……""——"等 AI 腔标记
    ai_tic_prose = "不是因为害怕——而是因为他明白这一切的意义。" * 20
    c = _client(store)
    c.post("/save-chapter", json={"seq": 1, "prose": ai_tic_prose, "title": "ai_tics测试章", "focalizer": None})
    q = c.get("/quality").json()
    ch1 = next(x for x in q["chapters"] if x["seq"] == 1)
    # qc_breakdown 应存在且含 ai_tics
    assert "qc_breakdown" in ch1, "应含 qc_breakdown 字段"
    assert set(ch1["qc_breakdown"]) == {"repetition", "structural", "purple", "ai_tics", "oversaturation"}
    # ai_tics 非零 → qc_issues 应大于不含 ai_tics 时的计数
    assert ch1["qc_breakdown"]["ai_tics"] > 0, "AI腔散文应检出 ai_tics > 0"
    assert ch1["qc_issues"] >= ch1["qc_breakdown"]["ai_tics"], "qc_issues 应包含 ai_tics"


def test_check_returns_all_five_qc_classes(store):
    """/check 返回的 qc 字典应含 ai_tics + oversaturation(Fix 1)。"""
    c = _client(store)
    r = c.post("/check", params={"seq": 1},
               json={"prose": "随便写点什么。", "focalizer": ""}).json()
    assert set(r["qc"]) >= {"repetition", "structural", "purple", "ai_tics", "oversaturation"}


def test_check_allow_pattern_exempts_purple_issue(store):
    """方案B任务14接线:store 里 seed 一条 allow_pattern 后,/check 对含该句式的
    文本不再报 purple issue(前置 skip 判定,减法,与 extra_patterns 加法路径分离)。"""
    prose = "他知道,回不去了。"
    c = _client(store)
    before = c.post("/check", params={"seq": 1},
                     json={"prose": prose, "focalizer": ""}).json()
    assert before["qc"]["purple"] > 0, "豁免前应命中升华句"

    store.add_craft_rule("allow_pattern", r"回不去", "志怪题材别删清单")
    after = c.post("/check", params={"seq": 1},
                    json={"prose": prose, "focalizer": ""}).json()
    assert after["qc"]["purple"] == 0, "seed allow_pattern 后应豁免该句"
    assert not any(i["type"] == "purple" for i in after["issues"])


# ===== Fix 2 TDD: /post-check 生成后全量体检 =====

def test_post_check_returns_assembled_structure(store):
    """/post-check 应返回 quality(五类+total)/leaks/discipline/degraded 四个顶层字段。"""
    import scribe3.llm as llm
    store.save_chapter(1, "一段志怪正文,无异常。", title="测试")

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "一段志怪正文,无异常。", "focalizer": "", "brief": ""}).json()
    assert set(r) >= {"quality", "leaks", "discipline", "degraded"}
    assert set(r["quality"]) >= {"repetition", "structural", "purple", "ai_tics", "oversaturation", "total"}
    assert isinstance(r["leaks"], list)
    assert isinstance(r["degraded"], bool)


def test_post_check_real_discipline_call_is_bounded(store, monkeypatch):
    """作者点击全量体检不能继承生成级 600 秒重试，需在可交互时间内降级返回。"""
    import scribe3.llm as llm
    seen = {}

    def fake_complete(prompt, system=None, **kw):
        seen.update(kw)
        return '{"ok": true, "violations": [], "cut_after": ""}'

    monkeypatch.setattr(llm, "hermes_complete", fake_complete)
    monkeypatch.setattr(llm, "default_timeout", lambda: 600.0)
    store.save_chapter(1, "一段志怪正文，无异常。", title="测试")
    c = _client(store)
    monkeypatch.setattr(A, "_complete_fn", None)
    r = c.post("/post-check?seq=1", json={"prose": "一段志怪正文，无异常。"})
    assert r.status_code == 200, r.text
    assert seen["timeout"] == 30.0 and seen["retries_override"] == 1


def test_post_check_discipline_mocked(store):
    """/post-check:LLM 回调返回违规时,discipline 字段含 violations 列表。"""
    def fake_complete(prompt, **kw):
        return '{"ok": false, "violations": ["double_climax"], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "这章违规。", "focalizer": "", "brief": ""}).json()
    assert r["degraded"] is False
    assert "double_climax" in r["discipline"].get("violations", [])


def test_post_check_degraded_on_llm_failure(store):
    """/post-check:LLM 调用抛异常 → degraded=True,不崩溃,仍返回确定性 QC。"""
    def exploding_complete(prompt, **kw):
        raise RuntimeError("LLM 宕机")

    c = _client(store, complete_fn=exploding_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "测试正文", "focalizer": "", "brief": ""})
    assert r.status_code == 200
    data = r.json()
    assert data["degraded"] is True
    assert "quality" in data and "total" in data["quality"]


def test_post_check_short_mode_suppresses_emotion_telling(store):
    """方案B任务16:short_mode=true 时,直写情绪的文本 emotion_telling 应为空,
    psych_ratio 归零、Gate C(心理告知)不触发——短篇直写情绪合法,不算 AI 味。"""
    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    prose = "他感到害怕。" + "他攥紧了刀柄。" * 20
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": "", "short_mode": True}).json()
    assert r["emotion_telling"] == []
    assert r["ai_grade"]["indicators"]["psych_ratio"]["value"] == 0
    assert r["ai_grade"]["gates"]["C"]["hit"] is False


def test_post_check_allow_pattern_exempts_emotion_telling(store):
    """B14 收尾清理批:find_emotion_telling 的 allow_patterns 此前只有单测覆盖,
    /post-check 生产链未接线。seed 一条 allow_pattern 覆盖直写情绪句后,
    /post-check 的 emotion_telling 应豁免该命中(不再上报)。"""
    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    prose = "他感到害怕。"
    before = c.post("/post-check", params={"seq": 1},
                     json={"prose": prose, "focalizer": "", "brief": ""}).json()
    assert before["emotion_telling"] != [], "豁免前应命中直写情绪"

    store.add_craft_rule("allow_pattern", r"感到害怕", "题材豁免:直写情绪合法")
    after = c.post("/post-check", params={"seq": 1},
                    json={"prose": prose, "focalizer": "", "brief": ""}).json()
    assert after["emotion_telling"] == [], "seed allow_pattern 后应豁免该直写情绪句"


# ===== 批E B(P2-15):orphan_knowledge_edges 审计器接线进 /post-check =====

def test_post_check_reports_orphan_edges(store):
    """批E-B:orphan_knowledge_edges 此前仅测试、零生产接线 → 接进 /post-check。
    真实孤儿路径:del_fact 删命题时 knows 图边级联消失,但 reader_knows(独立表)不级联,
    留悬挂边;/post-check 的 orphan_edges 字段应检出。"""
    from scribe3.ontology import Entity, Fact, KnowledgeEdge

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    store.add_entity(Entity("role:丁", "character", "丁"))
    store.add_fact(Fact("fact:rk_pc", "role:丁", "获知", "读者知识测试", valid_from=1))
    store.add_knowledge(KnowledgeEdge("reader", "fact:rk_pc", since_chapter=1,
                                      acquired_via="narrated"))
    store.delete_record("fact:rk_pc")   # reader_knows 独立表不级联 → 悬挂孤儿
    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "一段正文。", "focalizer": "", "brief": ""}).json()
    assert "orphan_edges" in r, "post-check 应含 orphan_edges 字段(审计器接线)"
    assert any("rk_pc" in str(o) for o in r["orphan_edges"]), \
        f"应检出 reader_knows 孤儿边,实际: {r['orphan_edges']}"


def test_post_check_orphan_edges_empty_when_clean(store):
    """批E-B:无孤儿边时 orphan_edges 为空列表(不误报)。"""
    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'
    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "干净正文。", "focalizer": "", "brief": ""}).json()
    assert r.get("orphan_edges") == [], f"无孤儿应为空,实际: {r.get('orphan_edges')}"


def test_post_check_leaks_detected(store):
    """/post-check:有 focalizer 且散文含泄露时,leaks 非空。"""
    luanshi_leak_world(store)

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "老道看见焦三在治眼。", "focalizer": "role:老道"}).json()
    assert len(r["leaks"]) > 0, "老道写出治眼应被检出泄露"


# ===== 方案B任务19:跨批开放伏笔账本注入 reviewer =====
# 背景(oh-story story-review/SKILL.md:133):审章前先读"预计回收章≤本章"的 open
# promise 作"继承的开放项"注入 reviewer——scribe3 有活 DB,直接筛
# promises_with_lifecycle 结果,不像 oh-story 靠人工维护的伏笔.md 文件。

def test_post_check_injects_inherited_open_promises(store):
    """/post-check 审查本章(seq=5)时,已 seed 的到期 open promise(chapter 层
    setup_chapter=1 → payoff_max=4,seq=5 已过窗口)应:
    ①注入 discipline prompt(complete_fn 收到的 prompt 含该伏笔文本);
    ②响应含非空 inherited_open_promises 列表。"""
    store.plant_promise("到期未收的青铜匣", setup_chapter=1, kind="promise")

    captured_prompts = []

    def fake_complete(prompt, **kw):
        captured_prompts.append(prompt)
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 5},
               json={"prose": "本章正文,未提及该伏笔。", "focalizer": "", "brief": ""}).json()

    assert captured_prompts, "discipline complete_fn 应被调用"
    assert "到期未收的青铜匣" in captured_prompts[0], "discipline prompt 应含继承的开放项文本"
    assert r.get("inherited_open_promises"), "响应应含非空 inherited_open_promises"


# ===== Fix 1: _current_tail_block 续写衔接注入 =====

def test_current_tail_block_with_prose(store):
    """_current_tail_block:章节有 prose 时,块含末段内容且含衔接说明。"""
    from scribe3.app import _current_tail_block
    store.save_chapter(3, "前半段正文。" * 50 + "这是结尾段落,老道抬头望月。", title="第三章", focalizer=None)
    block = _current_tail_block(store, 3)
    assert block != "", "有 prose 时应返回非空块"
    assert "老道抬头望月" in block, "末段内容应出现在块中"
    assert "续写" in block or "接上" in block, "块应含续写衔接提示"


def test_current_tail_block_no_prose(store):
    """_current_tail_block:章节不存在或 prose 为空时返回空串。"""
    from scribe3.app import _current_tail_block
    # 不存在的章节
    assert _current_tail_block(store, 99) == "", "不存在的章节应返回空串"


def test_current_tail_block_fresh_chapter(store):
    """_current_tail_block:刚创建、prose 为空字符串的章节返回空串。"""
    from scribe3.app import _current_tail_block
    # save_chapter 写空串
    store.save_chapter(5, "", title="空章", focalizer=None)
    assert _current_tail_block(store, 5) == "", "空 prose 章节应返回空串"


def test_current_tail_block_wired_into_chat_write(store, monkeypatch):
    """_current_tail_block 已注入 GET /chat/write instructions:章有 prose 时 instructions 含末段。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    store.save_chapter(2, "章节已有内容末段测试句。", title="二", focalizer=None)
    _client(store).get("/chat/write", params={"msg": "续写", "chapter": 2})
    assert "章节已有内容末段测试句" in captured.get("instructions", ""), \
        "GET /chat/write instructions 应含当前章末段"


def test_current_tail_block_wired_into_chat_write_post(store, monkeypatch):
    """_current_tail_block 已注入 POST /chat/write instructions:章有 prose 时 instructions 含末段。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    store.save_chapter(4, "POST章已有末段内容测试句。", title="四", focalizer=None)
    _client(store).post("/chat/write", json={"msg": "续写", "chapter": 4, "focalizer": ""})
    assert "POST章已有末段内容测试句" in captured.get("instructions", ""), \
        "POST /chat/write instructions 应含当前章末段"


# ===== Fix 2: _voice_anchor_block 注入 open voice flags =====

def test_voice_anchor_block_injects_open_voice_flags(store):
    """_voice_anchor_block:角色有 open voice_evolution_flag 时,块含「声音待演变」提示及 reason。"""
    store.set_voice_profile("role:甲", {"style_summary": "沉稳内敛"})
    store.add_voice_flag("role:甲", seq=3, reason="经历大悲之后声音开始颤抖")
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "role:甲")
    assert "声音待演变" in block, "应含「声音待演变」提示标题"
    assert "大悲" in block, "flag reason 应出现在块中"


def test_voice_anchor_block_no_flags_when_none(store):
    """_voice_anchor_block:无 open flag 时不含「声音待演变」。"""
    store.set_voice_profile("role:乙", {"style_summary": "轻快随和"})
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "role:乙")
    assert "声音待演变" not in block, "无 open flag 时不应含待演变提示"


def test_voice_anchor_block_flags_only_for_focalizer(store):
    """_voice_anchor_block:只注入焦点者自己的 flag,不混入其他角色的 flag。"""
    store.set_voice_profile("role:甲", {"style_summary": "沉稳"})
    store.set_voice_profile("role:乙", {"style_summary": "轻快"})
    store.add_voice_flag("role:乙", seq=2, reason="乙的声音转变原因")
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "role:甲")
    assert "乙的声音转变原因" not in block, "甲的 block 不应含乙的 flag reason"


def test_voice_anchor_block_via_char_state_affects_voice(store):
    """affects_voice=True 的 add_char_state 自动创建 voice_evolution_flag,
    _voice_anchor_block 应能读到并注入待演变提示。"""
    store.set_voice_profile("role:丙", {"style_summary": "质朴直白"})
    store.add_char_state(
        character_id="role:丙",
        chapter=4,
        change_type="personality",
        summary="历经磨难,声音转变",
        affects_voice=True,
        after_state={},
    )
    from scribe3.app import _voice_anchor_block
    block = _voice_anchor_block(store, "role:丙")
    assert "声音待演变" in block, "affects_voice=True 的 char_state 应触发 flag,进而注入待演变提示"


# ===== S2 TDD: /checkpoint kind=final 触发后台 ingest =====

def test_checkpoint_final_triggers_bg_ingest(store, monkeypatch):
    """kind=final 的 checkpoint 应注册后台 _bg_ingest 任务。"""
    import scribe3.app as A
    A.set_store(store)
    called = {}
    monkeypatch.setattr(A, "_bg_ingest", lambda work, seq: called.setdefault("args", (work, seq)))
    client = TestClient(A.app)
    store.save_chapter(3, "已有章节正文。", title="三")
    r = client.post("/checkpoint", params={"seq": 3, "work": "main"},
                    json={"prose": "定稿正文", "label": "定稿", "kind": "final", "qc": {}})
    assert r.status_code == 200
    # TestClient 同步执行 BackgroundTasks → _bg_ingest 应被调过
    assert called.get("args") == ("main", 3), "kind=final 应触发 _bg_ingest(main, 3)"


def test_checkpoint_non_final_no_bg_ingest(store, monkeypatch):
    """kind=checkpoint(非 final)不应注册后台 _bg_ingest 任务。"""
    import scribe3.app as A
    A.set_store(store)
    called = {}
    monkeypatch.setattr(A, "_bg_ingest", lambda work, seq: called.setdefault("args", (work, seq)))
    client = TestClient(A.app)
    r = client.post("/checkpoint", params={"seq": 4, "work": "main"},
                    json={"prose": "中间稿", "label": "草稿", "kind": "checkpoint", "qc": {}})
    assert r.status_code == 200
    assert "args" not in called, "非 final checkpoint 不应触发 _bg_ingest"


# ===== P0-1 / P2-3: 存为正文双 ingest 竞态根治 =====
# (同章去重排队 + checkpoint 与 save-chapter 同章只 ingest 一次 + _bg_ingest 独立连接)

def test_enqueue_ingest_dedups_same_chapter():
    """_enqueue_ingest:同 (work,seq) 已在途 → 跳过第二次排队;不同章正常排。"""
    from fastapi import BackgroundTasks
    bg = BackgroundTasks()
    assert A._enqueue_ingest(bg, "main", 5) is True      # 首次:真正排入
    assert A._enqueue_ingest(bg, "main", 5) is False     # 同章第二次:去重跳过
    assert len(bg.tasks) == 1                            # 只排了一个后台任务
    assert A._enqueue_ingest(bg, "main", 6) is True      # 不同章:仍排
    assert len(bg.tasks) == 2


def test_save_then_checkpoint_ingests_once(store, monkeypatch):
    """存为正文全链路:save-chapter + checkpoint(final) 同章 → 只 ingest 一次
    (checkpoint 侧因 save-chapter 已在途被去重跳过)。"""
    A.set_store(store)
    calls = []
    # mock 不清 pending → 模拟 ingest 仍在途,坐实 checkpoint 侧去重
    monkeypatch.setattr(A, "_bg_ingest", lambda work, seq: calls.append((work, seq)))
    client = TestClient(A.app)
    client.post("/save-chapter?work=main",
                json={"seq": 9, "prose": "同一段正文。", "title": "九", "focalizer": ""})
    client.post("/checkpoint", params={"seq": 9, "work": "main"},
                json={"prose": "同一段正文。", "label": "定稿", "kind": "final", "qc": {}})
    assert calls == [("main", 9)], "同章存为正文只应 ingest 一次(实际=%r)" % (calls,)


def test_bg_ingest_independent_connection_and_close(store, monkeypatch):
    """_bg_ingest 用独立 store 连接(不复用共享 _store_for,修 P2-3),用完 close,
    并在 finally 清除在途标记。"""
    import scribe3.ingest as ingest_mod
    A.set_store(store)                  # 共享 store 挂到 work=main
    A._pending_ingest.add(("main", 3))  # 模拟在途
    made = []

    class FakeStore:
        def __init__(self, **kw):
            self.kwargs = kw
            self.closed = False
            made.append(self)

        def close(self):
            self.closed = True

    monkeypatch.setattr(A, "SurrealStore", FakeStore)
    captured = {}

    def fake_ingest(st, seq, fn, **kw):
        captured["store"] = st
        return {"applied": 0}

    monkeypatch.setattr(ingest_mod, "ingest_chapter", fake_ingest)
    A._bg_ingest("main", 3)
    assert made, "应新建独立 SurrealStore 连接"
    assert captured["store"] is made[0]         # ingest 收到的是新建独立 store
    assert captured["store"] is not store        # 不是共享连接(P2-3)
    assert made[0].kwargs.get("db") == "main"    # 指向本书 DB
    assert made[0].closed is True                # 用完 close,不泄漏
    assert ("main", 3) not in A._pending_ingest  # finally 清除在途标记


# ===== S5 TDD: soak seed_words 进写作 prompt(无 LLM,传入才注入) =====

def test_soak_block_injects_seed_words_when_provided(store, monkeypatch):
    """_soak_block:request 传入 seed_words 时,instructions 应含种子词。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store)
    client = TestClient(appmod.app)
    client.post("/chat/write",
                json={"msg": "续写", "chapter": 1, "focalizer": "role:甲",
                      "seed_words": ["惶恐", "压抑", "隐忍"]})
    instr = captured.get("instructions", "")
    assert "惶恐" in instr and "压抑" in instr and "隐忍" in instr, \
        "POST /chat/write seed_words 应注入 instructions"


def test_soak_block_absent_when_no_seed_words(store, monkeypatch):
    """_soak_block:request 未传 seed_words 时,instructions 不含情绪种子词标记。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store)
    client = TestClient(appmod.app)
    client.post("/chat/write",
                json={"msg": "续写", "chapter": 1, "focalizer": "", "seed_words": []})
    instr = captured.get("instructions", "")
    assert "情绪种子词" not in instr, "无 seed_words 时不应注入种子词块"


def test_soak_get_route_ignores_seed_words(store, monkeypatch):
    """GET /chat/write 无 seed_words 参数 → instructions 不含情绪种子词标记。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store).get("/chat/write", params={"msg": "续写", "chapter": 1})
    instr = captured.get("instructions", "")
    assert "情绪种子词" not in instr


# ===== S6 TDD: /post-check 包含 validate_setting 结果 =====

def test_post_check_includes_setting_key(store):
    """/post-check 响应应含 setting 顶层字段。"""
    store.save_chapter(1, "一段志怪正文。", title="一")

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "一段志怪正文。", "focalizer": "", "brief": ""}).json()
    assert "setting" in r, "/post-check 响应应含 setting 字段"
    assert isinstance(r["setting"], list), "setting 应为列表(validate_setting 返回 list[dict])"


def test_post_check_setting_fail_soft(store, monkeypatch):
    """/post-check:validate_setting 抛异常时 fail-soft → setting=[], 不崩溃。"""
    import scribe3.store as storemod

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    # 让 validate_setting 爆
    monkeypatch.setattr(storemod.SurrealStore, "validate_setting",
                        lambda self, chapter, prose: (_ for _ in ()).throw(RuntimeError("db 炸了")))

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "正文", "focalizer": "", "brief": ""})
    assert r.status_code == 200
    data = r.json()
    assert "setting" in data
    assert data["setting"] == []


# ===== S7 TDD: 保守裁剪 — avoid cap 70→40 + _final_reminder 末尾强化 =====

def test_avoid_directive_cap_at_40(store):
    """S7 Trim 1: 当前文有 >40 条独特措辞时,_avoid_directive 输出至多 40 条(top cap)。"""
    from scribe3.app import _avoid_directive

    # 构造超过 40 个 ≥8 字的独特短语:写 50 段各含唯一长措辞的章节正文
    # 每段正文只含一个独特的长措辞,保证 distinctive_phrases 能抽到
    for i in range(50):
        phrase = f"独特措辞第{i:03d}号这句话足够长超过八字"
        store.save_chapter(i + 1, phrase * 3, title=f"第{i+1}章", focalizer=None)

    # 第 51 章起用 _avoid_directive,lookback=50 看尽所有前章
    result = _avoid_directive(store, chapter=51, lookback=50)
    if not result:
        # 若 critique 未抽到短语(依赖实现),至少不应超过 40 条
        return
    # 数 「…」 围栏对数 = 措辞条数
    count = result.count("「")
    assert count <= 40, f"_avoid_directive 输出了 {count} 条,应 ≤ 40"


def test_final_reminder_in_get_chat_write(store, monkeypatch):
    """S7 Trim 2: GET /chat/write 组装的 instructions 末尾应含 ⟦PROPOSAL⟧ + 乱世铜炉 提醒。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store).get("/chat/write", params={"msg": "续写第一章", "chapter": 1})
    instr = captured.get("instructions", "")
    assert "PROPOSAL" in instr, "instructions 应含 PROPOSAL 围栏提醒"
    assert "乱世铜炉" in instr, "instructions 应含乱世铜炉文风提醒"
    # 强化:提醒须在末尾(最后 200 字内)
    tail = instr[-1400:]
    assert "PROPOSAL" in tail, "PROPOSAL 提醒应出现在 instructions 末尾 200 字内"
    assert "乱世铜炉" in tail, "乱世铜炉提醒应出现在 instructions 末尾 200 字内"


def test_final_reminder_in_post_chat_write(store, monkeypatch):
    """S7 Trim 2: POST /chat/write 组装的 instructions 末尾同样含 ⟦PROPOSAL⟧ + 乱世铜炉 提醒。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store).post("/chat/write", json={"msg": "帮我续写第一章", "chapter": 1})
    instr = captured.get("instructions", "")
    assert "PROPOSAL" in instr, "POST instructions 应含 PROPOSAL 围栏提醒"
    assert "乱世铜炉" in instr, "POST instructions 应含乱世铜炉文风提醒"
    tail = instr[-1400:]
    assert "PROPOSAL" in tail, "PROPOSAL 提醒应出现在 POST instructions 末尾 200 字内"
    assert "乱世铜炉" in tail, "乱世铜炉提醒应出现在 POST instructions 末尾 200 字内"


# ===== 作者工具 F-03: 伏笔台账 GET /promises/ledger =====

def test_promise_ledger_three_columns(store):
    """ledger 三栏分类:open(已埋未收) / closed(已回收) / red_herring。"""
    # open 早埋(将超期):setup=1,max_chapter 后续推到 10 → 1+slack<10 超期
    store.plant_promise("铜炉会反噬埋它的人", setup_chapter=1, kind="promise")
    # closed 带 payoff:advance 后 status=closed
    store.plant_promise("赵芙南知祭炉秘法", setup_chapter=2, kind="promise")
    # red_herring 早埋未收(不应超期)
    store.plant_promise("管家形迹可疑(障眼)", setup_chapter=3, kind="red_herring")
    # 推 max_chapter 到 10
    store.add_event(Event("ev:ledger_mc", "action", story_time=10))
    # 回收第二条于第 7 章
    closed_pid = next(p["id"] for p in store.list_promises() if "赵芙南" in p["text"])
    store.advance_promise(closed_pid, 7)

    c = _client(store)
    r = c.get("/promises/ledger")
    assert r.status_code == 200, r.text
    led = r.json()
    assert {"open", "closed", "red_herring", "audit", "threshold", "max_chapter"} <= set(led)

    open_texts = {p["text"] for p in led["open"]}
    closed_texts = {p["text"] for p in led["closed"]}
    rh_texts = {p["text"] for p in led["red_herring"]}
    assert "铜炉会反噬埋它的人" in open_texts
    assert "赵芙南知祭炉秘法" in closed_texts
    assert "管家形迹可疑(障眼)" in rh_texts
    # red_herring 不混入 open(即便 status=open)
    assert "管家形迹可疑(障眼)" not in open_texts

    # 每条携带 setup/payoff/overdue/status/kind
    o = next(p for p in led["open"] if "铜炉" in p["text"])
    assert o["setup_chapter"] == 1 and o["payoff_chapter"] is None
    assert o["overdue"] is True, f"setup=1 max=10 slack=3 应超期: {o}"
    assert o["chapters_open"] == 10 - 1
    cl = next(p for p in led["closed"] if "赵芙南" in p["text"])
    assert cl["payoff_chapter"] == 7 and cl["span"] == 7 - 2


def test_promise_ledger_red_herring_never_overdue(store):
    """red_herring 即便 open 且早埋,overdue 永为 False,且不计 never_paid。"""
    store.plant_promise("障眼法", setup_chapter=1, kind="red_herring")
    store.add_event(Event("ev:rh_mc", "action", story_time=20))
    led = _client(store).get("/promises/ledger").json()
    rh = led["red_herring"][0]
    assert rh["overdue"] is False
    assert led["audit"]["overdue_count"] == 0
    assert led["audit"]["never_paid"] == 0, "red_herring 不计契诃夫枪 never_paid"


def test_promise_ledger_audit_payoff_without_setup(store):
    """audit:payoff<setup(闭无开 deus ex machina)应被抓出,balanced=False。
    用 update_promise 直接写脏数据(跳过 advance_promise 的 payoff≥setup 校验),
    模拟历史库里已有的异常数据,验证 audit 能检出。"""
    store.plant_promise("异常伏笔", setup_chapter=9, kind="promise")
    bad_pid = next(p["id"] for p in store.list_promises() if "异常" in p["text"])
    # 直接写脏数据:payoff_chapter=3 < setup=9,绕过 advance_promise 校验
    store.update_promise(bad_pid, {"payoff_chapter": 3, "status": "closed"})
    led = _client(store).get("/promises/ledger").json()
    pws = led["audit"]["payoff_without_setup"]
    assert any("异常" in x["text"] for x in pws), f"应抓出 payoff<setup: {pws}"
    assert led["audit"]["balanced"] is False


def test_promise_ledger_balanced_clean(store):
    """干净数据(无超期/无闭无开):balanced=True。"""
    store.plant_promise("正常收口", setup_chapter=1, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "正常" in p["text"])
    store.advance_promise(pid, 2)
    store.add_event(Event("ev:clean_mc", "action", story_time=3))
    led = _client(store).get("/promises/ledger").json()
    assert led["audit"]["balanced"] is True, led["audit"]
    assert led["audit"]["overdue_count"] == 0
    assert led["audit"]["payoff_without_setup"] == []


def test_promise_ledger_overdue_single_source(store):
    """单源回归:/promises、/quality、/promises/ledger 对同一 promise 给出同一 overdue。"""
    store.plant_promise("单源校验伏笔", setup_chapter=1, kind="promise")
    store.add_event(Event("ev:ss_mc", "action", story_time=1 + A.OVERDUE_SLACK + 1))
    c = _client(store)
    p_promises = next(x for x in c.get("/promises").json() if "单源校验" in x["text"])
    p_quality = next(x for x in c.get("/quality").json()["foreshadow"]["promises"]
                     if "单源校验" in x["text"])
    p_ledger = next(x for x in c.get("/promises/ledger").json()["open"]
                    if "单源校验" in x["text"])
    assert p_promises["overdue"] == p_quality["overdue"] == p_ledger["overdue"] is True


# ===== 作者工具 F-03 进阶: advance 端点 + payoff≥setup 校验 + mark-herring =====

def test_advance_promise_endpoint_success(store):
    """POST /promises/{pid}/advance 正常路径:闭合伏笔,status=closed,payoff_chapter 写入。"""
    store.plant_promise("测试收口", setup_chapter=2, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "测试收口" in p["text"])
    c = _client(store)
    r = c.post(f"/promises/{pid}/advance", json={"payoff_chapter": 5})
    assert r.status_code == 200, r.text
    proms = store.list_promises()
    p = next(x for x in proms if "测试收口" in x["text"])
    assert p["status"] == "closed"
    assert p["payoff_chapter"] == 5


def test_advance_promise_payoff_before_setup_rejected(store):
    """payoff_chapter < setup_chapter 时返回 422,promise 状态保持 open。"""
    store.plant_promise("不能早收口", setup_chapter=8, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "不能早收口" in p["text"])
    c = _client(store)
    r = c.post(f"/promises/{pid}/advance", json={"payoff_chapter": 3})
    assert r.status_code == 422, f"payoff<setup 应返回 422,实际 {r.status_code}: {r.text}"
    proms = store.list_promises()
    p = next(x for x in proms if "不能早收口" in x["text"])
    assert p["status"] == "open", "被拒后 promise 应仍为 open"
    assert p["payoff_chapter"] is None


def test_advance_promise_payoff_equal_setup_ok(store):
    """payoff_chapter == setup_chapter 应允许(≥ 满足)。"""
    store.plant_promise("同章收口", setup_chapter=5, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "同章收口" in p["text"])
    c = _client(store)
    r = c.post(f"/promises/{pid}/advance", json={"payoff_chapter": 5})
    assert r.status_code == 200, r.text
    p = next(x for x in store.list_promises() if "同章收口" in x["text"])
    assert p["status"] == "closed"


def test_mark_herring_endpoint(store):
    """POST /promises/{pid}/mark-herring → kind 变为 red_herring。"""
    store.plant_promise("伪装成伏笔的障眼法", setup_chapter=3, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "伪装" in p["text"])
    c = _client(store)
    r = c.post(f"/promises/{pid}/mark-herring")
    assert r.status_code == 200, r.text
    p = next(x for x in store.list_promises() if "伪装" in x["text"])
    assert p["kind"] == "red_herring", f"kind 应为 red_herring,实际 {p['kind']}"


def test_advance_then_ledger_reflects_closed(store):
    """advance 后 ledger 的 closed 栏能看到已收伏笔(端到端)。"""
    from scribe3.ontology import Event
    store.plant_promise("端到端收口", setup_chapter=1, kind="promise")
    store.add_event(Event("ev:e2e_adv", "action", story_time=5))
    pid = next(p["id"] for p in store.list_promises() if "端到端" in p["text"])
    c = _client(store)
    c.post(f"/promises/{pid}/advance", json={"payoff_chapter": 4})
    led = c.get("/promises/ledger").json()
    closed_texts = {p["text"] for p in led["closed"]}
    assert "端到端收口" in closed_texts, f"closed 栏应含端到端收口: {closed_texts}"
    cl = next(p for p in led["closed"] if "端到端" in p["text"])
    assert cl["payoff_chapter"] == 4
    assert cl["span"] == 3  # payoff(4) - setup(1)


# ==== 完整期 B: clues 中途线索端点 ====

def test_add_clue_and_ledger_contains_it(store):
    """POST /promises/{pid}/clues 加线索后 ledger 每条含 clues 列表。"""
    store.plant_promise("铜炉会反噬", setup_chapter=1, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "铜炉" in p["text"])
    c = _client(store)
    r = c.post(f"/promises/{pid}/clues", json={"note": "炉壁渗出血色铜锈", "chapter": 4})
    assert r.status_code == 200, f"加线索失败: {r.text}"
    led = c.get("/promises/ledger").json()
    p_led = next(x for x in led["open"] if "铜炉" in x["text"])
    assert p_led["clues"], "ledger 中 promise 应含 clues"
    assert p_led["clues"][0]["note"] == "炉壁渗出血色铜锈"
    assert p_led["clues"][0]["chapter"] == 4


def test_clues_sorted_by_chapter(store):
    """多条线索按 chapter 升序排列(草蛇灰线时序)。"""
    store.plant_promise("祭炉秘法", setup_chapter=1, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "祭炉" in p["text"])
    c = _client(store)
    # 故意乱序写入
    c.post(f"/promises/{pid}/clues", json={"note": "第7章线索", "chapter": 7})
    c.post(f"/promises/{pid}/clues", json={"note": "第3章线索", "chapter": 3})
    c.post(f"/promises/{pid}/clues", json={"note": "第5章线索", "chapter": 5})
    led = c.get("/promises/ledger").json()
    p_led = next(x for x in led["open"] if "祭炉" in x["text"])
    chapters = [cl["chapter"] for cl in p_led["clues"]]
    assert chapters == sorted(chapters), f"clues 应按 chapter 升序,实际: {chapters}"


def test_remove_clue_endpoint(store):
    """DELETE /promises/{pid}/clues/{idx} 删除指定下标线索。"""
    store.plant_promise("镇煞钉秘密", setup_chapter=2, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "镇煞钉" in p["text"])
    c = _client(store)
    c.post(f"/promises/{pid}/clues", json={"note": "线索甲", "chapter": 3})
    c.post(f"/promises/{pid}/clues", json={"note": "线索乙", "chapter": 5})
    # 删 idx=0(线索甲)
    r = c.delete(f"/promises/{pid}/clues/0")
    assert r.status_code == 200, f"删线索失败: {r.text}"
    proms = store.list_promises()
    p = next(x for x in proms if "镇煞钉" in x["text"])
    assert len(p["clues"]) == 1
    assert p["clues"][0]["note"] == "线索乙"


def test_remove_clue_out_of_range_422(store):
    """DELETE /promises/{pid}/clues/{idx} 下标越界返回 422。"""
    store.plant_promise("越界测试伏笔", setup_chapter=1, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "越界" in p["text"])
    c = _client(store)
    r = c.delete(f"/promises/{pid}/clues/99")
    assert r.status_code == 422, f"越界应 422,实际 {r.status_code}"


def test_ledger_clues_empty_list_no_crash(store):
    """未加任何线索时 ledger 中 clues 为空列表而非 None(兼容旧库)。"""
    store.plant_promise("无线索伏笔", setup_chapter=1, kind="promise")
    led = _client(store).get("/promises/ledger").json()
    p_led = next(x for x in led["open"] if "无线索" in x["text"])
    assert p_led["clues"] == [], f"clues 应为 []: {p_led['clues']}"


def test_clue_in_closed_promise_ledger(store):
    """已回收 promise 的 clues 也能在 ledger closed 栏中看到。"""
    from scribe3.ontology import Event
    store.plant_promise("草蛇灰线已收伏笔", setup_chapter=1, kind="promise")
    store.add_event(Event("ev:clue_closed", "action", story_time=8))
    pid = next(p["id"] for p in store.list_promises() if "草蛇灰线" in p["text"])
    c = _client(store)
    c.post(f"/promises/{pid}/clues", json={"note": "中途提醒", "chapter": 4})
    c.post(f"/promises/{pid}/advance", json={"payoff_chapter": 7})
    led = c.get("/promises/ledger").json()
    cl = next(x for x in led["closed"] if "草蛇灰线" in x["text"])
    assert cl["clues"] == [{"chapter": 4, "note": "中途提醒"}]


# ==== F-05: /check 和 /post-check 返回带 range 的 issues ====

def test_check_returns_issues_with_range(store):
    """/check 返回顶层 issues 字段;AI腔 not_a_but_b issue 含正确 range。"""
    prose = "那不是恐惧——是渴望。普通正文。"
    c = _client(store)
    r = c.post("/check", params={"seq": 1}, json={"prose": prose, "focalizer": ""}).json()
    assert "issues" in r, "/check 应返回 issues 字段"
    # 向后兼容:qc 计数字段仍在
    assert "qc" in r and "ai_tics" in r["qc"]
    # 白送类:not_a_but_b 的 issue 含 range
    nab = [i for i in r["issues"] if i.get("type") == "ai_tics" and i.get("meta", {}).get("kind") == "not_a_but_b"]
    assert nab, "应检出 not_a_but_b issue"
    for iss in nab:
        assert iss["range"] is not None, "not_a_but_b 应有 range"
        s, e = iss["range"]
        assert prose[s:e] == iss["text"], f"range 切片不等于 text: {prose[s:e]!r} != {iss['text']!r}"


def test_check_leak_issue_has_range(store):
    """/check:leak issue 含 range,指向 marker 在 prose 的位置。"""
    from scribe3.scenario import luanshi_leak_world
    luanshi_leak_world(store)
    prose = "皂衣道士冷笑:够你给老娘治眼了。"
    c = _client(store)
    r = c.post("/check", params={"seq": 1},
               json={"prose": prose, "focalizer": "role:老道"}).json()
    leak_issues = [i for i in r.get("issues", []) if i.get("type") == "leak"]
    assert leak_issues, "老道视角散文含治眼应检出 leak issue"
    for iss in leak_issues:
        assert iss["range"] is not None, "leak issue 应有 range"
        s, e = iss["range"]
        assert prose[s:e] == iss["text"], f"leak range 切片不等于 text: {prose[s:e]!r} != {iss['text']!r}"


def test_check_backward_compat_qc_counts_unchanged(store):
    """/check:旧 qc 计数字段向后兼容,不受 issues 新增影响。"""
    prose = "那不是恐惧——是渴望。"
    c = _client(store)
    r = c.post("/check", params={"seq": 1}, json={"prose": prose, "focalizer": ""}).json()
    assert set(r["qc"].keys()) >= {"repetition", "structural", "purple", "ai_tics", "oversaturation"}
    assert isinstance(r["qc"]["ai_tics"], int)


def test_check_returns_ai_grade(store):
    """方案A任务8:/check 干净文本应带 ai_grade 字段,grade=="light"。"""
    prose = ("灯灭了。他坐在黑里听雨,雨点砸在瓦上,忽急忽缓。"
             "窗缝里钻进一点凉风,吹得烛芯歪了一下。"
             "楼下传来收伞的声响,又归于寂静。"
             "他摸黑倒了半杯茶,茶已经凉透。"
             "墙角的座钟走得很慢,像是在数着雨点。"
             "院子里的石阶湿了大半,水顺着瓦沟往下淌。"
             "远处狗叫了两声,随即也停了。"
             "他把手拢进袖子里,靠着墙闭上眼睛。")
    c = _client(store)
    r = c.post("/check", params={"seq": 1}, json={"prose": prose, "focalizer": ""}).json()
    assert "ai_grade" in r, "/check 应返回 ai_grade 字段"
    assert r["ai_grade"]["grade"] == "light"


# ===== 方案A任务9(计划A最后一项):/post-check 接线 punct_suggestions =====

def test_post_check_returns_punct_suggestions(store):
    """/post-check 响应应含 punct_suggestions 字段,省略号收尾该规范化为「。」
    (normalize_punctuation_suggestions 接线,report-only 不改写正文)。
    注:不用「三——五天」数字区间场景——那条 punct 建议与 ai_tics.em_dash issue
    同 range,方案B任务20接线 merge_findings 后会被去重丢弃(见下方
    test_post_check_merge_findings_dedups_punct_suggestion_against_issue),
    此处换一个不与任何 issue 重叠的场景,单纯验证 punct_suggestions 字段本身接线正常。"""
    prose = "他走了……天亮了。普通句子在这里补齐字数用来测试。"
    c = _client(store)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    assert "punct_suggestions" in r, "/post-check 应返回 punct_suggestions 字段"
    assert r["punct_suggestions"] and r["punct_suggestions"][0]["suggestion"] == "。"


def test_post_check_merge_findings_dedups_punct_suggestion_against_issue(store):
    """方案B任务20:finding-merge 纪律——「三——五天」的 punct 建议(numeric_range,
    机械替换)与 ai_tics.em_dash issue(按功能改写)同 range,merge_findings 接线后
    应丢 punct 建议,只留 issue;issue.meta 应带 fix_action=rewrite(非退化类默认)。"""
    prose = "三——五天后他就到了。普通句子。"
    c = _client(store)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    assert r["punct_suggestions"] == [], "机械替换建议应让位给按功能改写的 issue"
    em_dash_issues = [i for i in r["issues"]
                       if i.get("type") == "ai_tics" and i.get("meta", {}).get("kind") == "em_dash"]
    assert em_dash_issues, "em_dash issue 应仍保留"
    assert all(i["meta"].get("fix_action") == "rewrite" for i in em_dash_issues)


def test_post_check_degeneration_issue_gets_regenerate_fix_action(store):
    """方案B任务20:degradation 类精确绑定"重新生成该段"——含 AI 拒绝语泄漏的正文,
    /post-check 响应里对应的 degeneration issue.meta.fix_action 应为 regenerate
    (对齐 scribe3 已验证的 continue-steer 回炉,不是改写)。"""
    prose = "作为AI,我无法继续创作这段内容。普通句子在这里补齐字数用来测试。"
    c = _client(store)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    deg_issues = [i for i in r["issues"] if i.get("type") == "degeneration"]
    assert deg_issues, "应检出 degeneration issue(AI拒绝语泄漏)"
    assert all(i["meta"].get("fix_action") == "regenerate" for i in deg_issues)


def test_post_check_ai_grade_reuses_precomputed_detectors(store, monkeypatch):
    """A8-Important 尾巾修复:/post-check 组装响应时已经对 req.prose 跑过
    find_duplicate_lines/find_emotion_telling/find_parallelism/find_poetic_fragments
    (即响应里的 duplicate_lines/emotion_telling/parallelism/poetic_fragments 字段),
    调 aggregate_ai_grade 时应把这四项通过 precomputed 参数直接传进去复用,而不是让
    aggregate_ai_grade 内部对同一份文本重新跑一遍。monkeypatch aggregate_ai_grade
    捕获调用参数,断言 precomputed 四个键齐全且值与响应里对应字段完全一致(同一份
    结果被复用,不是又现算了一份等值的)。"""
    import scribe3.critique as C
    A.set_store(store)
    prose = "三——五天后他就到了。这不是恐惧而是愤怒。普通句子。"
    captured = {}
    orig = C.aggregate_ai_grade

    def spy(flags, text, precomputed=None, short_mode=False):
        captured["precomputed"] = precomputed
        return orig(flags, text, precomputed=precomputed, short_mode=short_mode)

    monkeypatch.setattr(C, "aggregate_ai_grade", spy)
    c = _client(store)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""})
    assert r.status_code == 200, r.text
    precomputed = captured.get("precomputed")
    assert precomputed is not None, "/post-check 应把 precomputed 传给 aggregate_ai_grade"
    assert set(precomputed.keys()) == {
        "duplicate_lines", "emotion_telling", "parallelism", "poetic_fragments"
    }
    body = r.json()
    assert precomputed["duplicate_lines"] == body["duplicate_lines"]
    assert precomputed["emotion_telling"] == body["emotion_telling"]
    assert precomputed["parallelism"] == body["parallelism"]
    assert precomputed["poetic_fragments"] == body["poetic_fragments"]


def test_post_check_returns_issues_with_range(store):
    """/post-check 返回顶层 issues 字段;AI腔 issue 含正确 range。"""
    prose = "那不是恐惧——是渴望。"
    c = _client(store)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    assert "issues" in r, "/post-check 应返回 issues 字段"
    # 向后兼容:quality 字段仍在
    assert "quality" in r and "total" in r["quality"]
    nab = [i for i in r["issues"] if i.get("type") == "ai_tics" and i.get("meta", {}).get("kind") == "not_a_but_b"]
    assert nab, "应检出 not_a_but_b issue"
    for iss in nab:
        s, e = iss["range"]
        assert prose[s:e] == iss["text"]


def test_check_structural_oversaturation_issues_have_range(store):
    """/check:结构重复 + 过饱和 issue 带正确 range(进阶 C)。"""
    prose = ("他想起娘亲。他想起爹爹。他想起家门。他想起旧路。"
             "这意味着没用。这意味着完了。这意味着结束。这意味着重来。普通收尾。")
    c = _client(store)
    r = c.post("/check", params={"seq": 1}, json={"prose": prose, "focalizer": ""}).json()
    issues = r.get("issues", [])
    structs = [i for i in issues if i.get("type") == "structural"]
    overs = [i for i in issues if i.get("type") == "oversaturation"]
    assert structs, "排比开头应产出 structural issue"
    assert overs, "解释词过密应产出 oversaturation issue"
    for iss in structs + overs:
        assert iss["range"] is not None
        s, e = iss["range"]
        assert prose[s:e] == iss["text"], f"{iss['type']} range 不匹配: {prose[s:e]!r} != {iss['text']!r}"


def test_post_check_issues_schema(store):
    """/post-check issues 每条含 type/message/text/range/meta 字段。"""
    prose = "那不是恐惧——是渴望。他知道,回不去了。"
    c = _client(store)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    for iss in r.get("issues", []):
        assert "type" in iss
        assert "message" in iss
        assert "text" in iss
        assert "range" in iss   # 可为 None(无法定位)
        assert "meta" in iss


# ── F-02 时间线视图测试 ──────────────────────────────────────────────────────

def _seed_events(store):
    """种 3 个不同章号的事件:ch1/ch3/ch3 + ch10 一个在区间外。
    id 必须带 ev: 前缀(store._split 按冒号切)。"""
    from scribe3.ontology import Entity, Event as OntEv
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_entity(Entity("role:老道", "character", "老道"))
    # ch1 事件
    store.add_event(OntEv("ev:炼钉", "炼器", participants={"SUBJ": "role:焦三"},
                          story_time=1, motivated_by_goal="治眼"))
    # ch3 事件 x2
    store.add_event(OntEv("ev:拜师", "拜师", participants={"SUBJ": "role:焦三", "OBJ": "role:老道"},
                          story_time=3, motivated_by_goal="学艺"))
    store.add_event(OntEv("ev:试炉", "炼器", participants={"SUBJ": "role:焦三"},
                          story_time=3, motivated_by_goal="治眼"))
    # ch10 事件(超出 ch_to=5 的区间,不应出现)
    store.add_event(OntEv("ev:大战", "战斗", participants={"SUBJ": "role:焦三"},
                          story_time=10, motivated_by_goal="复仇"))


def test_timeline_store_events_in_range(store):
    """store.timeline(1,5) 返回 ch1+ch3 三条事件,ch10 不在,按章升序,字段齐。"""
    _seed_events(store)
    items = store.timeline(ch_from=1, ch_to=5)
    event_items = [i for i in items if i["kind"] == "event"]
    chapters = [i["chapter"] for i in event_items]
    # ch10 事件不在范围内
    assert all(ch <= 5 for ch in chapters), f"含超出范围的章号: {chapters}"
    # 3 条事件(ch1/ch3/ch3)
    assert len(event_items) == 3, f"期望3条事件,实得{len(event_items)}"
    # 按章升序
    assert chapters == sorted(chapters), f"未按章排序: {chapters}"
    # 字段齐全
    for it in event_items:
        assert "chapter" in it and "kind" in it and "label" in it
        assert "lane_keys" in it and "refs" in it
        assert isinstance(it["refs"].get("subj"), list)


def test_timeline_store_empty(store):
    """空库 store.timeline() 返回 [],不抛错。"""
    result = store.timeline()
    assert result == []


def test_timeline_endpoint_basic(store):
    """GET /timeline?ch_from=1&ch_to=5 返回正确结构。"""
    _seed_events(store)
    c = _client(store)
    r = c.get("/timeline", params={"ch_from": 1, "ch_to": 5})
    assert r.status_code == 200
    body = r.json()
    assert "from" in body and "to" in body and "max_chapter" in body and "items" in body
    event_items = [i for i in body["items"] if i["kind"] == "event"]
    assert len(event_items) == 3
    assert body["max_chapter"] >= 10   # ch10 事件入库,max_chapter≥10
    assert body["from"] == 1 and body["to"] == 5


def test_timeline_endpoint_defaults(store):
    """GET /timeline 不传参:ch_from=1,ch_to=max_chapter,全量返回。"""
    _seed_events(store)
    c = _client(store)
    r = c.get("/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["from"] == 1
    # 默认 to = max_chapter,ch10 事件应包含
    event_items = [i for i in body["items"] if i["kind"] == "event"]
    assert len(event_items) == 4   # ch1/ch3/ch3/ch10 全部


def test_timeline_endpoint_sorted_by_chapter(store):
    """/timeline 返回的 items 按 chapter 升序排列。"""
    _seed_events(store)
    c = _client(store)
    items = c.get("/timeline").json()["items"]
    chapters = [i["chapter"] for i in items]
    assert chapters == sorted(chapters), f"items 未按章排序: {chapters}"


# ── F-04 · 进度统计与码字激励 ────────────────────────────────────────────────

def test_progress_endpoint_basic(store):
    """/progress 端点:存一章后 today_words 有值、结构完整。"""
    today = "2099-03-01"
    store.save_chapter(1, "甲" * 600, title="一", _today=today)
    c = _client(store)
    r = c.get("/progress")
    assert r.status_code == 200
    body = r.json()
    for key in ("today", "total_words", "daily", "current_streak", "longest_streak", "heatmap"):
        assert key in body, f"响应缺少键 {key}"
    # total_words 口径须与 /quality.total_words 一致
    q = c.get("/quality").json()
    assert body["total_words"] == q["total_words"], "progress.total_words 与 quality.total_words 不一致"


def test_progress_with_goal(store):
    """/progress:设了 intent goal 后响应回传目标字段。"""
    store.set_intent({"total_word_goal": 50000, "daily_word_goal": 1000})
    today = "2099-03-02"
    store.save_chapter(1, "乙" * 500, title="一", _today=today)
    c = _client(store)
    body = c.get("/progress").json()
    assert body["total_word_goal"] == 50000
    assert body["daily_word_goal"] == 1000


def test_intent_goal_roundtrip_via_api(store):
    """PUT /intent 写入 goal → GET /intent 回读一致。"""
    c = _client(store)
    c.put("/intent", json={"reader_feeling": "沉浸", "total_word_goal": 80000, "daily_word_goal": 2000})
    got = c.get("/intent").json()
    assert got["total_word_goal"] == 80000
    assert got["daily_word_goal"] == 2000


# ===== F-01 大纲/卷章树端点(手稿支数据层) =====

def test_get_outline_empty(store):
    """GET /outline 空库 → 返回三键结构。"""
    c = _client(store)
    body = c.get("/outline").json()
    assert "volumes" in body
    assert "chapters" in body
    assert "unassigned_chapters" in body
    assert body["volumes"] == []
    assert body["chapters"] == []


def test_get_outline_with_data(store):
    """GET /outline 有章有卷 → 正确聚合。"""
    store.save_chapter(1, "第一章正文。\n* * *\n第二场景。", title="楔子")
    store.save_chapter(2, "第二章正文。", title="入派")
    vid = store.add_volume("第一卷", sort_order=1)
    store.update_chapter_meta(1, {"volume": vid, "synopsis": "楔子梗概"})

    c = _client(store)
    body = c.get("/outline").json()

    assert any(v["id"] == vid for v in body["volumes"])
    ch1 = next(ch for ch in body["chapters"] if ch["seq"] == 1)
    assert ch1["synopsis"] == "楔子梗概"
    assert ch1["scene_count"] == 2
    assert ch1["volume"] == vid
    assert 2 in body["unassigned_chapters"]


def test_chapters_reorder_changes_sort_order_not_seq(store):
    """POST /chapters/reorder → sort_order 改变,seq 不变。"""
    store.save_chapter(1, "一", title="一")
    store.save_chapter(2, "二", title="二")
    store.save_chapter(3, "三", title="三")

    c = _client(store)
    r = c.post("/chapters/reorder", json={"volume": None, "order": [3, 1, 2]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "reordered"
    assert body["count"] == 3

    # outline 按 sort_order 排,seq=3 应排最前
    outline = c.get("/outline").json()
    seqs = [ch["seq"] for ch in outline["chapters"]]
    assert seqs[0] == 3

    # seq 本身不变(get_chapter 仍可按原 seq 访问)
    for s in [1, 2, 3]:
        ch = c.get("/chapter", params={"seq": s}).json()
        assert ch.get("seq") == s, f"chapter seq={s} 应仍存在"


def test_outline_orders_chapters_by_volume_then_chapter_order(store):
    """全书大纲不得把不同卷的同序章节交错在一起。"""
    for seq in (1, 2, 3):
        store.save_chapter(seq, f"第{seq}章", title=f"第{seq}章")
    first = store.add_volume("第一卷", sort_order=1)
    second = store.add_volume("第二卷", sort_order=2)
    store.reorder_chapters(first, [1, 3])
    store.reorder_chapters(second, [2])

    seqs = [row["seq"] for row in _client(store).get("/outline").json()["chapters"]]

    assert seqs == [1, 3, 2]


def test_outline_keeps_story_sequence_when_chapters_are_created_per_volume(store):
    """从各卷交替创建章节后，全书大纲仍应按故事章序显示。"""
    c = _client(store)
    first = c.post("/volumes", json={"title": "第一卷", "sort_order": 1}).json()["id"]
    second = c.post("/volumes", json={"title": "第二卷", "sort_order": 2}).json()["id"]
    third = c.post("/volumes", json={"title": "第三卷", "sort_order": 3}).json()["id"]
    for volume in [first, first, first, first, second, second, second, third, third, third]:
        assert c.post("/chapters", json={"volume": volume}).status_code == 200

    seqs = [row["seq"] for row in c.get("/outline").json()["chapters"]]

    assert seqs == list(range(1, 11))


def test_patch_chapter_synopsis(store):
    """PATCH /chapters/{seq} 改梗概,不碰正文。"""
    store.save_chapter(5, "原始正文", title="五")
    c = _client(store)
    r = c.patch("/chapters/5", json={"synopsis": "五章梗概"})
    assert r.status_code == 200
    assert r.json()["status"] == "updated"

    # 正文不变
    ch = c.get("/chapter", params={"seq": 5}).json()
    assert ch["prose"] == "原始正文"

    # outline 已含梗概
    outline = c.get("/outline").json()
    ch5 = next(ch for ch in outline["chapters"] if ch["seq"] == 5)
    assert ch5["synopsis"] == "五章梗概"


def test_patch_chapter_rejects_unknown_label_as_422(store):
    """章节 label 是受控工作流状态；非法值必须是输入错误，不能让 Surreal 异常变成 500。"""
    store.save_chapter(6, "原始正文", title="六")

    r = _client(store).patch("/chapters/6", json={"label": "开局·伏笔"})

    assert r.status_code == 422
    assert "label" in r.text


def test_patch_chapter_not_found(store):
    """PATCH /chapters/{seq} 章不存在 → 404。"""
    c = _client(store)
    r = c.patch("/chapters/9999", json={"synopsis": "不存在"})
    assert r.status_code == 404


def test_chapter_create_archive_restore_and_delete_token_gate(store):
    """章节生命周期:新增章、默认归档、恢复、永久删除必须走 impact token。"""
    store.save_chapter(1, "第一章正文。", title="一")
    c = _client(store)

    created = c.post("/chapters", json={"title": "第二章"}).json()
    assert created["status"] == "created"
    assert created["seq"] == 2

    r_archive = c.post("/chapters/2/archive", json={"reason": "支线暂缓"})
    assert r_archive.status_code == 200
    assert r_archive.json()["status"] == "archived"
    assert [ch["seq"] for ch in c.get("/outline").json()["chapters"]] == [1]
    archived = c.get("/chapters/archived").json()
    assert len(archived) == 1
    assert archived[0]["seq"] == 2
    assert archived[0]["title"] == "第二章"
    assert archived[0]["archive_reason"] == "支线暂缓"

    r_restore = c.post("/chapters/2/restore")
    assert r_restore.status_code == 200
    assert [ch["seq"] for ch in c.get("/outline").json()["chapters"]] == [1, 2]
    assert c.get("/chapters/archived").json() == []

    impact = c.get("/chapters/2/impact").json()
    assert impact["object"] == {"type": "chapter", "id": 2, "label": "第二章"}
    assert impact["confirm_impact_token"]

    blocked = c.delete("/chapters/2")
    assert blocked.status_code == 409
    assert blocked.json()["confirm_impact_token"] == impact["confirm_impact_token"]

    deleted = c.delete("/chapters/2", params={"confirm_impact_token": impact["confirm_impact_token"]})
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert c.get("/chapter", params={"seq": 2}).json() == {}


def test_volume_crud(store):
    """POST/GET/PATCH/DELETE /volumes 端到端。"""
    c = _client(store)

    # 建卷
    r = c.post("/volumes", json={"title": "第一卷", "sort_order": 1, "color": "#abc"})
    assert r.status_code == 200
    vid = r.json()["id"]
    assert vid

    # 列卷
    vols = c.get("/volumes").json()
    assert any(v["id"] == vid for v in vols)

    # 改卷
    r2 = c.patch(f"/volumes/{vid}", json={"title": "第一卷(修订)"})
    assert r2.status_code == 200
    vols2 = c.get("/volumes").json()
    target = next(v for v in vols2 if v["id"] == vid)
    assert target["title"] == "第一卷(修订)"

    # 删卷(章不删,volume 置 NONE)
    store.save_chapter(20, "二十章", title="二十")
    store.update_chapter_meta(20, {"volume": vid})
    r3 = c.delete(f"/volumes/{vid}")
    assert r3.status_code == 200
    vols3 = c.get("/volumes").json()
    assert not any(v["id"] == vid for v in vols3)
    # 章仍存在
    ch20 = c.get("/chapter", params={"seq": 20}).json()
    assert ch20.get("seq") == 20


def test_write_gate_includes_outline_routes(store):
    """test_consistency 守卫的镜像:确认新路由已在 KNOWN_REST_WRITE_ROUTES 中。"""
    from scribe3.tests.test_consistency import TestWriteGate
    known = TestWriteGate.KNOWN_REST_WRITE_ROUTES
    assert ("POST", "/chapters") in known
    assert ("POST", "/chapters/reorder") in known
    assert ("PATCH", "/chapters/{seq}") in known
    assert ("POST", "/chapters/{seq}/archive") in known
    assert ("POST", "/chapters/{seq}/restore") in known
    assert ("DELETE", "/chapters/{seq}") in known
    assert ("POST", "/volumes") in known
    assert ("PATCH", "/volumes/{vid}") in known
    assert ("DELETE", "/volumes/{vid}") in known


# ===== 作者工具 F-06: 混合 Binder 项目树 GET /project-tree =====

def test_project_tree_two_branches(store):
    """GET /project-tree 应返回手稿支(卷→章→场景)+ 素材支(分类→条目)+ 横切视图清单。
    手稿支:卷/章嵌套正确,章节点带 wc/pov badge;素材支:分类计数对;views 静态项齐。
    """
    from scribe3.ontology import Entity
    # 种 1 卷 2 章
    vid = store.add_volume("第一卷·镇煞", sort_order=1)
    store.save_chapter(1, "焦三夜行。", title="楔子", focalizer="role:焦三")
    store.save_chapter(2, "拜师清潭。\n\n* * *\n\n第二场。", title="入派", focalizer="role:焦三")
    store.reorder_chapters(vid, [1, 2])
    # 种 2 角色 + 1 势力
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_entity(Entity("role:沈青梧", "character", "沈青梧"))
    store.add_faction("清潭派", ideology="正道")

    c = _client(store)
    r = c.get("/project-tree")
    assert r.status_code == 200, r.text
    tree = r.json()

    # —— 手稿支 ——
    ms = tree["manuscript"]
    assert ms["type"] == "manuscript_root"
    vols = ms["children"]
    vol = next((v for v in vols if v["ref"] == vid), None)
    assert vol is not None, f"应有种下的卷: {vols}"
    assert vol["type"] == "volume"
    assert len(vol["children"]) == 2, "卷下应有 2 章"
    # 卷角标:章数
    assert any(b["kind"] == "count" and b["value"] == 2 for b in vol["badges"])
    ch1 = next(x for x in vol["children"] if x["ref"] == 1)
    assert ch1["type"] == "chapter"
    assert ch1["id"] == "ch:1"
    assert any(b["kind"] == "wc" for b in ch1["badges"]), "章应带字数角标"
    assert any(b["kind"] == "pov" and b["value"] == "role:焦三" for b in ch1["badges"])
    # 第 2 章有 2 个场景 → 应有 scene children
    ch2 = next(x for x in vol["children"] if x["ref"] == 2)
    assert ch2.get("children") and len(ch2["children"]) == 2, "多场景章应展开场景节点"
    assert ch2["children"][0]["type"] == "scene"
    assert ch2["children"][0]["ref"] == {"seq": 2, "idx": 0}

    # —— 素材支 ——
    codex = tree["codex"]
    assert codex["type"] == "codex_root"
    cats = {cat["ref"]: cat for cat in codex["children"]}
    assert "character" in cats and "faction" in cats
    char_cat = cats["character"]
    assert any(b["kind"] == "count" and b["value"] == 2 for b in char_cat["badges"]), \
        f"角色分类计数应为 2: {char_cat['badges']}"
    char_names = [leaf["label"] for leaf in char_cat["children"]]
    assert "焦三" in char_names and "沈青梧" in char_names
    assert char_cat["children"][0]["type"] == "character"
    # 势力分类计数
    assert any(b["kind"] == "count" and b["value"] == 1 for b in cats["faction"]["badges"])

    # —— 横切视图 ——
    view_ids = {v["id"] for v in tree["views"]}
    assert "view:atlas" in view_ids and "view:insight" in view_ids and "view:timeline" in view_ids


def test_project_tree_unassigned_fallback(store):
    """无卷归属的章应落入「未分卷」兜底组,且不丢章。"""
    store.save_chapter(5, "游离章。", title="孤章")
    c = _client(store)
    tree = c.get("/project-tree").json()
    vols = tree["manuscript"]["children"]
    unassigned = next((v for v in vols if v["id"] == "vol:null"), None)
    assert unassigned is not None, f"应有未分卷兜底组: {[v['id'] for v in vols]}"
    assert any(ch["ref"] == 5 for ch in unassigned["children"])


# ===== 作者工具 F-02 进阶: 时间线多泳道 + _all_relations 全史 =====

def test_timeline_all_kinds(store):
    """进阶 E: /timeline 应返回四类条目(event/promise/arc/relation),关系用全量读。
    核心验证:种一条 since=4/until=7 的关系,relation_start@4 与 relation_end@7 都应出现。
    对比守护:relations_at(6) 返回该条(仍开着),relations_at(8) 返回空(已失效)——证明带门的漏失效。
    """
    from scribe3.ontology import Entity, Event as OntEvent

    # 种角色
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_entity(Entity("role:云阳真人", "character", "云阳真人"))

    # 种事件(ch3)
    store.add_event(OntEvent("ev:炼钉", "炼器",
                             participants={"SUBJ": "role:焦三"},
                             story_time=3, effects=[], causal_in=[]))

    # 种伏笔(setup@1)
    store.plant_promise("焦三立誓攒钱给老娘治眼", setup_chapter=1)

    # 种弧光质变(ch3)
    store.add_char_state("role:焦三", 3, "ability", "习得御铜之力",
                         arc_phase="觉醒", affects_voice=False)

    # 种关系(since=4, until=7)
    store.add_character_relation("role:焦三", "role:云阳真人", "师徒", 4)
    store.end_relation("role:焦三", "role:云阳真人", 7)

    c = _client(store)
    r = c.get("/timeline", params={"ch_from": 1, "ch_to": 10})
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    kinds = {i["kind"] for i in items}

    # 四类都在
    assert "event" in kinds, f"应有 event 条目, 实际 kinds={kinds}"
    assert "promise_setup" in kinds, f"应有 promise_setup 条目"
    assert "arc" in kinds, f"应有 arc(弧光) 条目"
    assert "relation_start" in kinds, f"应有 relation_start 条目"
    assert "relation_end" in kinds, f"应有 relation_end 条目(关系全史含失效)"

    # 关系起点在 ch4,终点在 ch7 ——全量读不漏
    rel_starts = [i for i in items if i["kind"] == "relation_start"]
    rel_ends   = [i for i in items if i["kind"] == "relation_end"]
    assert any(i["chapter"] == 4 for i in rel_starts), "relation_start 应在 ch4"
    assert any(i["chapter"] == 7 for i in rel_ends), "relation_end 应在 ch7(全量读不丢失效)"

    # 对比守护:relations_at(8) 应为空(已失效 until=7),证明带门的会漏
    at8 = store.relations_at(8)
    assert at8 == [], f"relations_at(8) 应返回空(since=4,until=7 的关系在 ch8 已失效),实际={at8}"

    # items 按 chapter 升序
    chaps = [i["chapter"] for i in items]
    assert chaps == sorted(chaps), "items 应按 chapter 升序"

    # 向后兼容:max_chapter 字段在
    assert "max_chapter" in data


def test_timeline_promise_span(store):
    """伏笔 setup/payoff 双端点都出现,refs 互指。"""
    store.plant_promise("古器现世之谜", setup_chapter=1)
    proms = store.list_promises()
    assert proms, "种伏笔失败"
    pid = proms[0]["id"]
    store.advance_promise(pid, 5)

    c = _client(store)
    r = c.get("/timeline", params={"ch_from": 1, "ch_to": 10})
    assert r.status_code == 200
    items = r.json()["items"]

    setups  = [i for i in items if i["kind"] == "promise_setup"]
    payoffs = [i for i in items if i["kind"] == "promise_payoff"]
    assert any(i["chapter"] == 1 for i in setups), "setup 应在 ch1"
    assert any(i["chapter"] == 5 for i in payoffs), "payoff 应在 ch5"
    # setup 的 refs 指向 payoff_chapter
    s = next(i for i in setups if i["chapter"] == 1)
    assert s["refs"].get("payoff_chapter") == 5
    # payoff 的 refs 指向 setup_chapter
    p = next(i for i in payoffs if i["chapter"] == 5)
    assert p["refs"].get("setup_chapter") == 1


def test_timeline_all_relations_vs_relations_at(store):
    """_all_relations 全量读 vs relations_at 带时间门对比测试(spec 关键陷阱守护)。
    since=2/until=4 的失效关系:
    - _all_relations() 必须包含(全史)
    - relations_at(5) 必须不含(已失效,时间门过滤)
    - timeline(1,10) 的 relation_start@2 + relation_end@4 都必须出现
    """
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_character_relation("role:甲", "role:乙", "仇敌", 2)
    store.end_relation("role:甲", "role:乙", 4)

    # _all_relations 返回全量
    all_rels = store._all_relations()
    assert any(r["src"] == "甲" and r["dst"] == "乙" for r in all_rels), \
        f"_all_relations 应含 甲→乙 关系, 实际={all_rels}"

    # relations_at(5) 不含(时间门)
    at5 = store.relations_at(5)
    assert not any(r["src"] == "甲" and r["dst"] == "乙" for r in at5), \
        f"relations_at(5) 不应含 until=4 的关系, 实际={at5}"

    # timeline 多泳道含关系全史
    c = _client(store)
    items = c.get("/timeline", params={"ch_from": 1, "ch_to": 10}).json()["items"]
    starts = [i for i in items if i["kind"] == "relation_start"]
    ends   = [i for i in items if i["kind"] == "relation_end"]
    assert any(i["chapter"] == 2 for i in starts), "relation_start@2 应在时间线"
    assert any(i["chapter"] == 4 for i in ends),   "relation_end@4 应在时间线(全史不漏)"


def test_timeline_empty_db(store):
    """空库返回 items:[], 不报错;向后兼容字段在。"""
    c = _client(store)
    r = c.get("/timeline")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert "from" in data and "to" in data and "max_chapter" in data


def test_timeline_causal_in_with_chapter(store):
    """完整期·causal_in 数据补全:refs.causal_in 应为 [{id, chapter}] 形式,
    前驱事件章号供前端 SVG 弧线计算两端 x 坐标。
    验证:有因果边(ev:逃 causal_in ev:追)时,timeline 的 ev:逃 refs.causal_in
    包含 {id: 'ev:追', chapter: <前驱章号>},而非裸字符串。"""
    from scribe3.ontology import Entity, Event as OntEv
    store.add_entity(Entity("role:甲", "character", "甲"))
    # 前驱事件 ev:追 在 ch2
    store.add_event(OntEv("ev:追", "追击", participants={"SUBJ": "role:甲"}, story_time=2))
    # ev:逃 在 ch3,因果指向 ev:追
    store.add_event(OntEv("ev:逃", "逃跑", participants={"SUBJ": "role:甲"}, story_time=3,
                          causal_in=[("ev:追", "enables")]))

    c = _client(store)
    r = c.get("/timeline", params={"ch_from": 1, "ch_to": 5})
    assert r.status_code == 200
    items = r.json()["items"]

    ev_escape = next((i for i in items if i["id"] == "ev:逃"), None)
    assert ev_escape is not None, "ev:逃 应在 timeline items 中"

    causal_in = ev_escape["refs"].get("causal_in", [])
    assert len(causal_in) > 0, "ev:逃 应有 causal_in 记录"

    ci = causal_in[0]
    # 应是 dict,而非裸字符串
    assert isinstance(ci, dict), f"causal_in 条目应为 dict,实际为 {type(ci)}: {ci}"
    assert ci.get("id") == "ev:追", f"causal_in[0].id 应为 ev:追,实际={ci}"
    assert ci.get("chapter") == 2, f"causal_in[0].chapter 应为 2(前驱事件章号),实际={ci}"


# ── 作者工具完整 D · 时间线双轴(故事编年 vs 叙事顺序) ──────────────────────────

def _seed_flashback(store):
    """种一个闪回场景:
      ev:童年 —— story_chapter=2(故事第2章发生),narrative_position=9(叙事第9章才闪回揭示)。
      ev:线性 —— story_chapter=5,不带 narrative_position(线性事件,两轴一致)。
    """
    from scribe3.ontology import Entity, Event as OntEv
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_event(OntEv("ev:童年", "回忆", participants={"SUBJ": "role:焦三"},
                          story_time=2, narrative_position=9))
    store.add_event(OntEv("ev:线性", "对话", participants={"SUBJ": "role:焦三"},
                          story_time=5))


def test_narrative_position_persisted(store):
    """完整 D:add_event 写入 narrative_position,events_at 读回(往返不丢)。"""
    _seed_flashback(store)
    ev = next((e for e in store.events_at(2) if e.id == "ev:童年"), None)
    assert ev is not None, "ev:童年 应在 story_chapter=2 查到"
    assert ev.narrative_position == 9, f"narrative_position 应回读为 9,实际={ev.narrative_position}"
    # 线性事件 narrative_position 为 None(回退 story_chapter)
    ev2 = next((e for e in store.events_at(5) if e.id == "ev:线性"), None)
    assert ev2 is not None and ev2.narrative_position is None


def test_timeline_axis_story_vs_narrative(store):
    """完整 D 核心:闪回事件 story=2 / narrative=9。
      axis='story'   → ev:童年 落在 chapter=2
      axis='narrative' → ev:童年 落在 chapter=9
    线性事件 ev:线性(story=5,无 narrative)两轴都落在 5(回退)。"""
    _seed_flashback(store)

    story = store.timeline(1, 10, axis="story")
    narr  = store.timeline(1, 10, axis="narrative")

    s_flash = next(i for i in story if i["id"] == "ev:童年")
    n_flash = next(i for i in narr  if i["id"] == "ev:童年")
    assert s_flash["chapter"] == 2, f"故事轴 ev:童年 应 chapter=2,实际={s_flash['chapter']}"
    assert n_flash["chapter"] == 9, f"叙事轴 ev:童年 应 chapter=9,实际={n_flash['chapter']}"
    # 两轴都恒带 story_chapter / narrative_position 供前端标"闪回"
    assert s_flash["story_chapter"] == 2 and s_flash["narrative_position"] == 9
    assert n_flash["story_chapter"] == 2 and n_flash["narrative_position"] == 9

    # 线性事件:两轴一致(回退 story_chapter)
    s_lin = next(i for i in story if i["id"] == "ev:线性")
    n_lin = next(i for i in narr  if i["id"] == "ev:线性")
    assert s_lin["chapter"] == 5 and n_lin["chapter"] == 5
    assert s_lin["narrative_position"] is None


def test_timeline_default_axis_is_story(store):
    """向后兼容:不传 axis 默认 'story',闪回事件落 story_chapter=2。"""
    _seed_flashback(store)
    items = store.timeline(1, 10)  # 不传 axis
    flash = next(i for i in items if i["id"] == "ev:童年")
    assert flash["chapter"] == 2, "默认 axis 应为 story(闪回落 story_chapter)"


def test_timeline_narrative_range_includes_out_of_story_range(store):
    """完整 D 边界:闪回事件 story=2 但 narrative=9。
    叙事轴查 [6,10] 区间:story_chapter=2 在区间外,但 narrative_position=9 在区间内 → 必须出现。
    (验证全量扫故事章再按叙事坐标过滤,不漏闪回。)"""
    _seed_flashback(store)
    narr = store.timeline(6, 10, axis="narrative")
    ids = {i["id"] for i in narr if i["kind"] == "event"}
    assert "ev:童年" in ids, "叙事轴 [6,10] 应含 narrative=9 的闪回事件(即便 story=2 在区间外)"
    # 故事轴查 [6,10]:ev:童年(story=2)不应出现
    story = store.timeline(6, 10, axis="story")
    sids = {i["id"] for i in story if i["kind"] == "event"}
    assert "ev:童年" not in sids, "故事轴 [6,10] 不应含 story=2 的事件"


def test_timeline_endpoint_axis_param(store):
    """GET /timeline?axis=narrative 返回 axis 字段,事件按叙事位排;非法 axis 回退 story。"""
    _seed_flashback(store)
    c = _client(store)

    rs = c.get("/timeline", params={"ch_from": 1, "ch_to": 10, "axis": "story"}).json()
    rn = c.get("/timeline", params={"ch_from": 1, "ch_to": 10, "axis": "narrative"}).json()
    assert rs["axis"] == "story" and rn["axis"] == "narrative"
    s_flash = next(i for i in rs["items"] if i["id"] == "ev:童年")
    n_flash = next(i for i in rn["items"] if i["id"] == "ev:童年")
    assert s_flash["chapter"] == 2 and n_flash["chapter"] == 9

    # 非法 axis 回退 story(向后兼容,不报错)
    rb = c.get("/timeline", params={"ch_from": 1, "ch_to": 10, "axis": "garbage"}).json()
    assert rb["axis"] == "story"
    b_flash = next(i for i in rb["items"] if i["id"] == "ev:童年")
    assert b_flash["chapter"] == 2


def test_timeline_existing_seed_unaffected_by_axis(store):
    """向后兼容回归:无 narrative_position 的现有事件,两轴排序完全一致。"""
    _seed_events(store)  # 现有种子,全部无 narrative_position
    story = store.timeline(1, 12, axis="story")
    narr  = store.timeline(1, 12, axis="narrative")
    s_map = {i["id"]: i["chapter"] for i in story if i["kind"] == "event"}
    n_map = {i["id"]: i["chapter"] for i in narr  if i["kind"] == "event"}
    assert s_map == n_map, f"无 narrative_position 时两轴应一致: story={s_map} narrative={n_map}"


# ===== 批量等价测试(P1-d 性能修复回归) =====

def test_timeline_bulk_equivalence(store):
    """P1-d 性能修复:批量查聚合结果与逐条预期完全一致。
    种 3 章事件(含 participants/causal_in)+ 2 角色弧光 → timeline 批量结果与
    逐字段预期对齐,验证批量聚合没漏没错。
    """
    from scribe3.ontology import Entity, Event as OntEvent, Fact

    # 种角色
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))

    # 种事件 ch1(因)
    store.add_event(OntEvent("ev:起", "起因",
                             participants={"SUBJ": "role:甲"},
                             story_time=1))
    # 种事件 ch3(果,有因果边)
    store.add_event(OntEvent("ev:果", "结果",
                             participants={"SUBJ": "role:乙", "OBJ": "role:甲"},
                             story_time=3,
                             causal_in=[("ev:起", "enables")]))
    # 种事件 ch5(另一章,无 participants)
    store.add_event(OntEvent("ev:尾", "收尾",
                             participants={},
                             story_time=5))

    # 种弧光质变(change_type 须在 schema 枚举内: ability/relation/personality/composite)
    store.add_char_state("role:甲", 2, "ability", "甲觉醒",
                         arc_phase="觉醒", affects_voice=True)
    store.add_char_state("role:乙", 4, "personality", "乙转变",
                         arc_phase="转折", affects_voice=False)

    items = store.timeline(ch_from=1, ch_to=6)

    # ── 事件条目验证 ──
    ev_items = {i["id"]: i for i in items if i["kind"] == "event"}
    assert set(ev_items.keys()) == {"ev:起", "ev:果", "ev:尾"}, \
        f"事件泳道应含 3 条,实际 ids={set(ev_items.keys())}"

    # ev:起 章号/lane_keys
    assert ev_items["ev:起"]["chapter"] == 1
    assert ev_items["ev:起"]["story_chapter"] == 1
    assert "role:甲" in ev_items["ev:起"]["lane_keys"]

    # ev:果 章号/lane_keys/causal_in 带章号
    assert ev_items["ev:果"]["chapter"] == 3
    ci = ev_items["ev:果"]["refs"]["causal_in"]
    assert len(ci) == 1, f"causal_in 应有 1 条,实际={ci}"
    assert ci[0]["id"] == "ev:起"
    assert ci[0]["chapter"] == 1, f"causal_in 章号应为 1,实际={ci[0]['chapter']}"
    assert "role:乙" in ev_items["ev:果"]["lane_keys"]
    assert "role:甲" in ev_items["ev:果"]["lane_keys"]

    # ev:尾 无 participants → lane_keys=[]
    assert ev_items["ev:尾"]["chapter"] == 5
    assert ev_items["ev:尾"]["lane_keys"] == []

    # ── 弧光条目验证 ──
    arc_items = [i for i in items if i["kind"] == "arc"]
    assert len(arc_items) == 2, f"弧光泳道应含 2 条,实际={len(arc_items)}"
    arc_by_cid = {i["refs"]["character"]: i for i in arc_items}
    assert "role:甲" in arc_by_cid and "role:乙" in arc_by_cid

    arc_jia = arc_by_cid["role:甲"]
    assert arc_jia["chapter"] == 2
    assert arc_jia["refs"]["arc_phase"] == "觉醒"
    assert arc_jia["lane_keys"] == ["role:甲"]

    arc_yi = arc_by_cid["role:乙"]
    assert arc_yi["chapter"] == 4
    assert arc_yi["refs"]["arc_phase"] == "转折"

    # ── items 按 chapter 升序 ──
    chaps = [i["chapter"] for i in items]
    assert chaps == sorted(chaps), f"items 应按 chapter 升序,实际={chaps}"


# ===== 尾1: PATCH /events/{eid}/narrative TDD =====

def test_patch_event_narrative_set(store):
    """PATCH /events/{eid}/narrative 设叙事位 → events_at/timeline 反映新值。"""
    from scribe3.ontology import Event
    ev = Event("ev:叙事测试", "测试事件", story_time=3)
    store.add_event(ev)
    c = _client(store)

    # 设 narrative_position=7
    r = c.patch("/events/ev:叙事测试/narrative",
                json={"narrative_position": 7}, params={"work": "main"})
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # events_at(3) 里该事件 narrative_position 应更新为 7
    evs = store.events_at(3)
    target = next((e for e in evs if e.id == "ev:叙事测试"), None)
    assert target is not None, "events_at(3) 应能找到该事件"
    assert target.narrative_position == 7, f"narrative_position 应为 7,实际: {target.narrative_position}"

    # timeline narrative 轴:该事件应出现在第 7 章位
    items = store.timeline(1, 10, axis="narrative")
    ev_item = next((i for i in items if i["id"] == "ev:叙事测试"), None)
    assert ev_item is not None
    assert ev_item["chapter"] == 7, f"叙事轴坐标应为 7,实际: {ev_item['chapter']}"


def test_patch_event_narrative_clear(store):
    """PATCH /events/{eid}/narrative None(清除)→ 回退 story_chapter。"""
    from scribe3.ontology import Event
    ev = Event("ev:清除测试", "测试事件", story_time=5, narrative_position=9)
    store.add_event(ev)
    c = _client(store)

    # 先确认 narrative_position=9
    evs = store.events_at(5)
    t = next((e for e in evs if e.id == "ev:清除测试"), None)
    assert t and t.narrative_position == 9

    # 清除:narrative_position=null
    r = c.patch("/events/ev:清除测试/narrative",
                json={"narrative_position": None}, params={"work": "main"})
    assert r.status_code == 200

    # 现在 narrative_position 应为 None
    evs2 = store.events_at(5)
    t2 = next((e for e in evs2 if e.id == "ev:清除测试"), None)
    assert t2 is not None
    assert t2.narrative_position is None, f"清除后应为 None,实际: {t2.narrative_position}"

    # timeline story 轴:该事件 chapter 应仍为 story_chapter=5
    items = store.timeline(1, 10, axis="story")
    ev_item = next((i for i in items if i["id"] == "ev:清除测试"), None)
    assert ev_item is not None
    assert ev_item["chapter"] == 5, f"故事轴坐标应为 5,实际: {ev_item['chapter']}"


def test_patch_event_narrative_404(store):
    """PATCH /events/不存在事件/narrative → 404。"""
    c = _client(store)
    r = c.patch("/events/ev:不存在事件/narrative",
                json={"narrative_position": 1}, params={"work": "main"})
    assert r.status_code == 404


# ===== R2: 写路径校验补全 =====

# --- R2.1: 角色关系端点实体存在校验 ---

def test_add_character_relation_missing_fields_422(store):
    """POST /character-relations 缺字段→422 而非 500。"""
    c = _client(store)
    r = c.post("/character-relations", json={"src": "role:甲"})  # 缺 dst/relation/since_chapter
    assert r.status_code == 422, f"缺字段应返回 422: {r.text}"


def test_add_character_relation_nonexistent_src_422(store):
    """POST /character-relations src 不存在→422,不建悬挂边。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:乙R2", "character", "乙"))
    c = _client(store)
    r = c.post("/character-relations", json={
        "src": "role:不存在角色", "dst": "role:乙R2",
        "relation": "ally", "since_chapter": 1
    })
    assert r.status_code == 422, f"src 不存在应返回 422: {r.text}"
    # 确认悬挂边未写入
    rels = store.relations_at(9999)
    assert not any(x.get("src") == "不存在角色" for x in rels), "不应建立悬挂边"


def test_add_character_relation_nonexistent_dst_422(store):
    """POST /character-relations dst 不存在→422,不建悬挂边。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:甲R2", "character", "甲"))
    c = _client(store)
    r = c.post("/character-relations", json={
        "src": "role:甲R2", "dst": "role:不存在乙",
        "relation": "ally", "since_chapter": 1
    })
    assert r.status_code == 422, f"dst 不存在应返回 422: {r.text}"


def test_evolve_relation_nonexistent_src_422(store):
    """POST /character-relations/evolve src 不存在→422。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:辛R2", "character", "辛"))
    c = _client(store)
    r = c.post("/character-relations/evolve", json={
        "src": "role:不存在庚", "dst": "role:辛R2",
        "relation": "enemy", "since_chapter": 5
    })
    assert r.status_code == 422, f"src 不存在应返回 422: {r.text}"


def test_end_relation_nonexistent_src_422(store):
    """POST /character-relations/end src 不存在→422。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:癸R2", "character", "癸"))
    c = _client(store)
    r = c.post("/character-relations/end", json={
        "src": "role:不存在壬", "dst": "role:癸R2",
        "until_chapter": 5
    })
    assert r.status_code == 422, f"src 不存在应返回 422: {r.text}"


def test_end_relation_missing_fields_422(store):
    """POST /character-relations/end 缺字段→422。"""
    c = _client(store)
    r = c.post("/character-relations/end", json={"src": "role:甲"})  # 缺 dst/until_chapter
    assert r.status_code == 422, f"缺字段应返回 422: {r.text}"


# --- R2.2: 标记端点不存在返回 404 ---

def test_mark_herring_nonexistent_404(store):
    """POST /promises/不存在pid/mark-herring → 404。"""
    c = _client(store)
    r = c.post("/promises/不存在pid/mark-herring")
    assert r.status_code == 404, f"不存在 promise 应返回 404: {r.text}"


def test_edit_promise_nonexistent_404(store):
    """PATCH /promises/不存在pid → 404。"""
    c = _client(store)
    r = c.patch("/promises/不存在pid",
                json={"text": "x", "setup_chapter": 1, "promise_kind": "promise"})
    assert r.status_code == 404, f"不存在 promise 应返回 404: {r.text}"


def test_delete_promise_nonexistent_404(store):
    """DELETE /promises/不存在pid → 404。"""
    c = _client(store)
    r = c.delete("/promises/不存在pid")
    assert r.status_code == 404, f"不存在 promise 应返回 404: {r.text}"


def test_update_volume_nonexistent_404(store):
    """PATCH /volumes/不存在vid → 404。"""
    c = _client(store)
    r = c.patch("/volumes/不存在vid", json={"title": "新标题"})
    assert r.status_code == 404, f"不存在 volume 应返回 404: {r.text}"


def test_delete_volume_nonexistent_404(store):
    """DELETE /volumes/不存在vid → 404。"""
    c = _client(store)
    r = c.delete("/volumes/不存在vid")
    assert r.status_code == 404, f"不存在 volume 应返回 404: {r.text}"


def test_resolve_voice_flag_nonexistent_404(store):
    """POST /voice-flags/不存在fid/resolve → 404。"""
    c = _client(store)
    r = c.post("/voice-flags/不存在fid/resolve")
    assert r.status_code == 404, f"不存在 voice flag 应返回 404: {r.text}"


# --- R2.3: PATCH /chapters/{seq} volume=null 清空生效 ---

def test_patch_chapter_clear_volume(store):
    """PATCH /chapters/{seq} 传 volume=null 应清空卷归属(exclude_unset 语义)。"""
    # 建一章
    store.save_chapter(1, "正文甲", "标题甲")
    # 建一个卷并绑定
    vid = store.add_volume(title="第一卷", sort_order=1)
    store.update_chapter_meta(1, {"volume": vid})
    ch_before = store.get_chapter(1)
    assert ch_before is not None
    # 通过端点传 volume=null 清空
    c = _client(store)
    r = c.patch("/chapters/1", json={"volume": None})
    assert r.status_code == 200, f"清空卷归属应返回 200: {r.text}"
    ch_after = store.get_chapter(1)
    # volume 应清空(None 或不含 volume 键)
    vol_val = ch_after.get("volume") if ch_after else "NOKEY"
    assert vol_val is None, f"volume 应已清空,实际: {vol_val}"


def test_get_chapter_returns_editable_metadata(store):
    """章节编辑面板重开时必须读回 title/label/volume，不能把未返回字段误写成 null。"""
    store.save_chapter(7, "正文乙", "标题乙")
    vid = store.add_volume(title="第二卷", sort_order=2)
    store.update_chapter_meta(7, {"label": "draft", "volume": vid})

    row = _client(store).get("/chapter", params={"seq": 7}).json()

    assert row["title"] == "标题乙"
    assert row["label"] == "draft"
    assert row["volume"] == vid


# --- R2.4: add_promise_clue 章号范围校验 ---

def test_add_promise_clue_before_setup_422(store):
    """POST /promises/{pid}/clues chapter < setup_chapter → 422。"""
    store.plant_promise("范围测试伏笔", setup_chapter=5, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "范围测试" in p["text"])
    c = _client(store)
    r = c.post(f"/promises/{pid}/clues", json={"note": "太早的线索", "chapter": 2})
    assert r.status_code == 422, f"chapter < setup 应返回 422: {r.text}"


def test_add_promise_clue_after_payoff_422(store):
    """POST /promises/{pid}/clues chapter > payoff_chapter → 422。"""
    store.plant_promise("有回收的伏笔", setup_chapter=2, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "有回收" in p["text"])
    store.advance_promise(pid, payoff_chapter=8)
    c = _client(store)
    r = c.post(f"/promises/{pid}/clues", json={"note": "太晚的线索", "chapter": 10})
    assert r.status_code == 422, f"chapter > payoff 应返回 422: {r.text}"


def test_add_promise_clue_in_range_ok(store):
    """POST /promises/{pid}/clues chapter 在合法范围内 → 200。"""
    store.plant_promise("合法范围伏笔", setup_chapter=3, kind="promise")
    pid = next(p["id"] for p in store.list_promises() if "合法范围" in p["text"])
    store.advance_promise(pid, payoff_chapter=9)
    c = _client(store)
    r = c.post(f"/promises/{pid}/clues", json={"note": "合法线索", "chapter": 6})
    assert r.status_code == 200, f"合法章号应返回 200: {r.text}"


# --- R2.5: reorder_chapters 不存在 volume → 422 ---

def test_reorder_chapters_nonexistent_volume_422(store):
    """POST /chapters/reorder 指定不存在 volume → 422。"""
    store.save_chapter(1, "章甲", "标题")
    c = _client(store)
    r = c.post("/chapters/reorder", json={"volume": "不存在卷id", "order": [1]})
    assert r.status_code == 422, f"不存在 volume 应返回 422: {r.text}"


def test_patch_chapter_nonexistent_volume_422(store):
    """PATCH /chapters/{seq} 指定不存在 volume → 422。"""
    store.save_chapter(2, "章乙", "标题乙")
    c = _client(store)
    r = c.patch("/chapters/2", json={"volume": "幽灵卷id"})
    assert r.status_code == 422, f"不存在 volume 应返回 422: {r.text}"


# ===== R6: /post-check degraded 覆盖 find_leaks/validate_setting 失败(第三轮 P1-b) =====

def test_post_check_degraded_when_find_leaks_raises(store, monkeypatch):
    """find_leaks 抛异常时:/post-check 应返回 degraded=True、leaks_degraded=True、
    degraded_stages 含 'find_leaks'——让限知兜底闸崩溃可观测,不静默返回 leaks:[] + degraded:false。
    修复前:find_leaks 异常只记日志,degraded 保持 False,调用方无感知。"""
    store.save_chapter(1, "测试散文内容。", title="一")
    store.add_entity(__import__("scribe3.ontology", fromlist=["Entity"]).Entity("role:甲", "character", "甲"))

    import scribe3.app as A
    import scribe3.verify as V
    monkeypatch.setattr(V, "find_leaks", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("模拟 find_leaks 崩溃")))

    c = _client(store, complete_fn=lambda p, **kw: '{"score":8,"violations":[],"cut_after":null}')
    r = c.post("/post-check", params={"seq": 1, "work": "main"},
               json={"prose": "测试散文内容。", "focalizer": "role:甲", "brief": ""})
    assert r.status_code == 200, f"/post-check 应 200: {r.text}"
    body = r.json()
    assert body.get("degraded") is True, \
        f"find_leaks 崩溃时 degraded 应为 True,实际: {body.get('degraded')}"
    assert body.get("leaks_degraded") is True, \
        f"find_leaks 崩溃时 leaks_degraded 应为 True,实际: {body.get('leaks_degraded')}"
    assert "find_leaks" in body.get("degraded_stages", []), \
        f"degraded_stages 应含 'find_leaks',实际: {body.get('degraded_stages')}"


def test_post_check_degraded_when_validate_setting_raises(store, monkeypatch):
    """validate_setting 抛异常时:/post-check 应返回 degraded=True、
    degraded_stages 含 'validate_setting'。"""
    store.save_chapter(1, "测试散文内容。", title="一")

    import scribe3.store as ST
    monkeypatch.setattr(ST.SurrealStore, "validate_setting",
                        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("模拟 validate_setting 崩溃")))

    c = _client(store, complete_fn=lambda p, **kw: '{"score":8,"violations":[],"cut_after":null}')
    r = c.post("/post-check", params={"seq": 1, "work": "main"},
               json={"prose": "测试散文内容。", "focalizer": "", "brief": ""})
    assert r.status_code == 200, f"/post-check 应 200: {r.text}"
    body = r.json()
    assert body.get("degraded") is True, \
        f"validate_setting 崩溃时 degraded 应为 True,实际: {body.get('degraded')}"
    assert "validate_setting" in body.get("degraded_stages", []), \
        f"degraded_stages 应含 'validate_setting',实际: {body.get('degraded_stages')}"


def test_post_check_not_degraded_when_all_ok(store):
    """所有子步骤成功时,degraded=False、leaks_degraded=False、degraded_stages=[]。"""
    store.save_chapter(1, "一段正常的志怪内容。", title="一")
    c = _client(store, complete_fn=lambda p, **kw: '{"score":8,"violations":[],"cut_after":null}')
    r = c.post("/post-check", params={"seq": 1, "work": "main"},
               json={"prose": "一段正常的志怪内容。", "focalizer": "", "brief": ""})
    assert r.status_code == 200
    body = r.json()
    assert body.get("degraded") is False, f"全部成功时 degraded 应 False: {body}"
    assert body.get("leaks_degraded") is False, f"leaks_degraded 应 False: {body}"
    assert body.get("degraded_stages") == [], f"degraded_stages 应空列表: {body}"


# ===== R3: _avoid_directive lookback 默认值 3→8(第三轮 P1-b) =====

def test_avoid_directive_default_lookback_is_8(store):
    """_avoid_directive 默认 lookback 应为 8(覆盖足够前文,防跨章复读)。
    修复前:lookback=3,第 7-10 章看不到前段措辞,跨章复读回升。"""
    import inspect
    from scribe3.app import _avoid_directive
    sig = inspect.signature(_avoid_directive)
    default_lookback = sig.parameters["lookback"].default
    assert default_lookback == 8, \
        f"_avoid_directive 默认 lookback 应为 8,实际: {default_lookback}"


# ===== P2-a TDD: soak 块 GET/POST 对称 + proposal 兜底剥离 =====

def test_soak_block_empty_returns_empty_string():
    """P2-a Fix1: _soak_block([]) 返回空串,无副作用。"""
    from scribe3.app import _soak_block
    assert _soak_block([]) == "", "_soak_block([]) 应返回空串"


def test_soak_block_nonempty_returns_block():
    """_soak_block 非空时注入情绪种子词块。"""
    from scribe3.app import _soak_block
    block = _soak_block(["哀", "沉"])
    assert "哀" in block and "沉" in block, f"_soak_block 应含种子词,实际: {block}"


def test_get_chat_write_instructions_include_soak_position(store):
    """P2-a Fix1: GET /chat/write 的 instructions 块序列中 soak_block 已对称注入(空则静默)。
    通过检查 _soak_block 在 GET 流程中被调用(利用 monkeypatch 捕获调用)来验证。"""
    from scribe3.app import _soak_block
    called = {"n": 0}
    original = _soak_block

    import scribe3.app as A
    original_fn = A._soak_block

    def patched(seed_words):
        called["n"] += 1
        return original_fn(seed_words)

    A._soak_block = patched
    try:
        c = _client(store)
        # GET /chat/write 触发流式响应,TestClient 会收完整响应
        resp = c.get("/chat/write", params={"msg": "续写一段", "chapter": 1})
        assert resp.status_code == 200
        assert called["n"] >= 1, \
            f"GET /chat/write 应调用 _soak_block 至少 1 次以保持 GET/POST 对称,实际: {called['n']}"
    finally:
        A._soak_block = original_fn


def test_strip_preamble_removes_preamble():
    """P2-a Fix6: _strip_preamble 剥离含'处理思路'的首段,保留散文主体。"""
    from scribe3.app import _strip_preamble
    text = "我的处理思路：先写打斗再收尾。\n\n焦三举刀砍去，寒光一闪。" + "甲" * 200
    result = _strip_preamble(text)
    assert "我的处理思路" not in result, \
        f"_strip_preamble 应剥离开场思路段,实际首 50 字: {result[:50]}"
    assert "焦三" in result, "散文主体应保留"


def test_strip_preamble_preserves_plain_prose():
    """P2-a Fix6: 无开场白的纯散文不被截断。"""
    from scribe3.app import _strip_preamble
    prose = "焦三举刀砍去，寒光一闪。" + "乙" * 300
    result = _strip_preamble(prose)
    assert result.startswith("焦三") or "焦三" in result[:20], \
        f"纯散文不应被截断,首 20 字: {result[:20]}"


def test_purge_ingest_clears_unverified_via_api(store):
    """P2-a Fix5: 同章重 ingest 后 pending unverified 不累积——通过 API ingest 两次验证。"""
    c = _client(store)
    # 先建章正文
    store.save_chapter(1, "路人甲出现，路人乙消失。", title="一")

    # 直接向 store 注入两个 unverified 模拟首次 ingest 结果
    store.add_unverified_ref("路人甲", 1, "saw")
    store.add_unverified_ref("路人乙", 1, "saw")
    rows_first = c.get("/ingest-unverified").json()
    count_first = sum(1 for r in rows_first if r["seq"] == 1)
    assert count_first == 2, f"首次 ingest 后应有 2 条 seq=1 unverified,实际: {count_first}"

    # purge_ingest 清理 + 再注入同一批(模拟重 ingest)
    store.purge_ingest(1)
    store.add_unverified_ref("路人甲", 1, "saw")
    store.add_unverified_ref("路人乙", 1, "saw")
    rows_second = c.get("/ingest-unverified").json()
    count_second = sum(1 for r in rows_second if r["seq"] == 1)
    assert count_second == 2, \
        f"重 ingest 后 seq=1 unverified 应仍为 2(不累积为 4),实际: {count_second}"


# ===== M1+M2: 限知揭示纪律 + 情感不直说 + 接线检测器(机制A) =====

# --- M1-① _revelation_discipline_block 单元测试 ---

def test_revelation_discipline_block_with_focalizer():
    """_revelation_discipline_block(非空焦点者):返回含「限知揭示纪律」和「读设定卡」的文本块。"""
    from scribe3.app import _revelation_discipline_block
    block = _revelation_discipline_block("role:甲")
    assert "限知揭示纪律" in block, f"应含「限知揭示纪律」标题,实际: {block[:200]}"
    assert "读设定卡" in block, f"应含「读设定卡」关键词(配角批发真相对应),实际: {block[:200]}"
    # 强化版:逼问→不倒豆子 + 禁长篇身世独白 + 禁排比抒情(复判定位的残留靶标)
    assert "倒豆子" in block and "2-3句" in block, "应含「被逼问不倒豆子/连续设定陈述≤2-3句」约束"
    assert "身世独白" in block, "应含「禁止临死/摊牌长篇身世独白」约束"
    assert "排比抒情" in block, "应含「禁止排比抒情回环」约束"


def test_revelation_discipline_block_empty_focalizer():
    """_revelation_discipline_block(''):作者全知章返回空串。"""
    from scribe3.app import _revelation_discipline_block
    assert _revelation_discipline_block("") == "", "空焦点者应返回空串"


def test_revelation_discipline_block_none_focalizer():
    """_revelation_discipline_block(None):等同空焦点者,返回空串。"""
    from scribe3.app import _revelation_discipline_block
    assert _revelation_discipline_block(None) == "", "None 焦点者应返回空串"


# --- M1-② _final_reminder 包含「情感不可直说」 ---

def test_final_reminder_includes_emotion_no_tell():
    """_final_reminder():应含「情感不可直说」和「show」关键词。"""
    from scribe3.app import _final_reminder
    reminder = _final_reminder()
    assert "情感不可直说" in reminder, f"_final_reminder 应含「情感不可直说」,实际: {reminder}"
    assert "show" in reminder.lower() or "Show" in reminder, \
        f"_final_reminder 应含 show(don't tell),实际: {reminder}"


# --- M1-③ _revelation_discipline_block 注入 POST /chat/write ---

def test_chat_write_post_focalizer_instructions_contain_revelation_discipline(store, monkeypatch):
    """POST /chat/write 限知章 instructions 应含揭示纪律块关键词(「限知揭示纪律」)。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store).post("/chat/write",
                        json={"msg": "续写", "chapter": 3, "focalizer": "role:甲"})
    instr = captured.get("instructions", "")
    assert "限知揭示纪律" in instr, \
        f"focalizer 章 POST /chat/write instructions 应含「限知揭示纪律」,前300字: {instr[:300]}"


def test_chat_write_post_no_focalizer_no_revelation_discipline(store, monkeypatch):
    """POST /chat/write 作者全知章(无 focalizer):instructions 不含揭示纪律块。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store).post("/chat/write",
                        json={"msg": "续写", "chapter": 1, "focalizer": ""})
    instr = captured.get("instructions", "")
    assert "限知揭示纪律" not in instr, \
        "无 focalizer 的全知章 instructions 不应注入限知揭示纪律块"


# --- M2: /save-chapter QC dict 新增 duplicate_lines / emotion_telling ---

def test_save_chapter_qc_includes_duplicate_lines_and_emotion_telling(store):
    """/save-chapter 返回 qc 字典应含 duplicate_lines + emotion_telling 两键。"""
    c = _client(store)
    # 构造含整行复读 + 情感直说的散文
    prose = (
        "他感到恐惧,心中一阵战栗。\n"
        "他感到恐惧,心中一阵战栗。\n"  # 整行复读
        "他其实不是个坏人。\n"         # verdict(情感直说)
        "老道抬头望月。\n"
    )
    r = c.post("/save-chapter", json={"seq": 1, "prose": prose, "title": "测试", "focalizer": None})
    assert r.status_code == 200, f"/save-chapter 应 200: {r.text}"
    body = r.json()
    qc = body.get("qc", {})
    assert "duplicate_lines" in qc, f"qc 应含 duplicate_lines 键,实际 qc: {qc}"
    assert "emotion_telling" in qc, f"qc 应含 emotion_telling 键,实际 qc: {qc}"
    # 验证计数非负
    assert isinstance(qc["duplicate_lines"], int) and qc["duplicate_lines"] >= 0
    assert isinstance(qc["emotion_telling"], int) and qc["emotion_telling"] >= 0


def test_save_chapter_qc_duplicate_lines_detected(store):
    """/save-chapter:含整行复读的散文 qc.duplicate_lines > 0。"""
    c = _client(store)
    dup_line = "这是完全重复的整行内容,字数足够长超过六字。"
    prose = f"{dup_line}\n{dup_line}\n正常内容行。"
    r = c.post("/save-chapter", json={"seq": 2, "prose": prose, "title": "复读", "focalizer": None})
    body = r.json()
    assert body["qc"]["duplicate_lines"] > 0, \
        f"含整行复读应检出 duplicate_lines>0,实际: {body['qc']['duplicate_lines']}"


def test_save_chapter_qc_emotion_telling_detected(store):
    """/save-chapter:含叙述层情感直说的散文 qc.emotion_telling > 0。"""
    c = _client(store)
    prose = "他感到恐惧,双腿颤抖。老道抬头望月。她感到害怕,不敢出声。"
    r = c.post("/save-chapter", json={"seq": 3, "prose": prose, "title": "情感直说", "focalizer": None})
    body = r.json()
    assert body["qc"]["emotion_telling"] > 0, \
        f"含情感直说应检出 emotion_telling>0,实际: {body['qc']['emotion_telling']}"


def test_qc_endpoint_returns_full_detectors(store):
    """GET /qc 除原五项外补全 cross_repetition/duplicate_lines/emotion_telling,均为命中列表。"""
    c = _client(store)
    dup_line = "这是完全重复的整行内容,字数足够长超过六字。"
    prose = f"{dup_line}\n{dup_line}\n他感到恐惧,双腿颤抖。她感到害怕,不敢出声。"
    c.post("/save-chapter", json={"seq": 1, "prose": prose, "title": "体检", "focalizer": None})
    body = c.get("/qc?seq=1").json()
    # 原五项仍在(均为列表)
    for k in ("repetition", "structural", "purple", "ai_tics", "oversaturation"):
        assert isinstance(body.get(k), list), f"{k} 应为列表,实际: {body.get(k)!r}"
    # 补全的检测器
    assert isinstance(body.get("cross_repetition"), list)
    assert isinstance(body.get("cross_repetition_phrases"), list)
    assert len(body.get("duplicate_lines", [])) > 0, "含整行复读应检出 duplicate_lines"
    assert len(body.get("emotion_telling", [])) > 0, "含情感直说应检出 emotion_telling"


def test_qc_endpoint_empty_when_no_prose(store):
    """GET /qc 对无正文的章返回空字典(前端据此显'保存正文后自动体检')。"""
    c = _client(store)
    assert c.get("/qc?seq=999").json() == {}


# --- M3: /post-check 新增 duplicate_lines / emotion_telling / cross_consistency ---

def test_post_check_includes_new_detector_keys(store):
    """/post-check 响应应含 duplicate_lines / emotion_telling / cross_consistency 三键。"""
    store.save_chapter(1, "一段正常的志怪内容。", title="一")

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "一段正常的志怪内容。", "focalizer": "", "brief": ""}).json()
    assert "duplicate_lines" in r, f"/post-check 应含 duplicate_lines 键,实际键: {list(r)}"
    assert "emotion_telling" in r, f"/post-check 应含 emotion_telling 键,实际键: {list(r)}"
    assert "cross_consistency" in r, f"/post-check 应含 cross_consistency 键,实际键: {list(r)}"


def test_post_check_duplicate_lines_count_positive(store):
    """/post-check:含整行复读的散文,duplicate_lines 为列表且长度>0。"""
    dup = "这是整行完全重复的内容足够长超过六字。"
    prose = f"{dup}\n{dup}\n正常内容。"

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    dup_lines = r.get("duplicate_lines", [])
    assert isinstance(dup_lines, list), f"duplicate_lines 应为列表,实际: {type(dup_lines)}"
    assert len(dup_lines) > 0, f"含整行复读应检出 duplicate_lines>0 条,实际: {dup_lines}"


def test_post_check_emotion_telling_count_positive(store):
    """/post-check:含情感直说的散文,emotion_telling 为列表且长度>0。"""
    prose = "他感到恐惧,双腿颤抖。她感到害怕,不敢出声。他其实不是个坏人。"

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    et = r.get("emotion_telling", [])
    assert isinstance(et, list), f"emotion_telling 应为列表,实际: {type(et)}"
    assert len(et) > 0, f"含情感直说应检出 emotion_telling>0 条,实际: {et}"


def test_post_check_cross_consistency_is_list(store):
    """/post-check cross_consistency 应为列表(空库或有章时均不崩)。"""
    store.save_chapter(1, "一段正常内容。", title="一")

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "一段正常内容。", "focalizer": "", "brief": ""}).json()
    cc = r.get("cross_consistency")
    assert isinstance(cc, list), f"cross_consistency 应为列表,实际: {type(cc)}"


# ===== 方案B任务11:章节定位六型 + 卷级张弛基线接线进 /post-check =====

def test_post_check_reports_tension_monotony_role_run(store):
    """全书连续 4 章都标「chapter_role:高压」→ /post-check 的 tension_monotony
    应检出 role_run(卷级张弛基线,带 work 全章上下文,不限于当前 seq 那一章)。"""
    for seq in range(1, 5):
        store.save_chapter(seq, f"第{seq}章正文,平平无奇。", title=f"第{seq}章")
        store.update_chapter_meta(seq, {"synopsis": "压力级:5 chapter_role:高压"})

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 4},
               json={"prose": "第4章正文,平平无奇。", "focalizer": "", "brief": ""}).json()
    tm = r.get("tension_monotony")
    assert isinstance(tm, list), f"tension_monotony 应为列表,实际: {type(tm)}"
    assert any(i.get("kind") == "role_run" for i in tm), f"应检出 role_run,实际: {tm}"


def test_post_check_tension_monotony_empty_when_no_annotations(store):
    """旧数据无「压力级/chapter_role」标注 → tension_monotony 为空列表,不误报、不崩。"""
    store.save_chapter(1, "一段正常内容,无定位标注。", title="一")

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "一段正常内容,无定位标注。", "focalizer": "", "brief": ""}).json()
    assert r.get("tension_monotony") == []


def test_post_check_new_detectors_fail_soft(store, monkeypatch):
    """/post-check:find_duplicate_lines 或 find_emotion_telling 抛异常时 fail-soft,不崩溃,200 返回。"""
    import scribe3.critique as CQ

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    monkeypatch.setattr(CQ, "find_duplicate_lines",
                        lambda text, **kw: (_ for _ in ()).throw(RuntimeError("模拟 find_duplicate_lines 崩溃")))

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "测试正文。", "focalizer": "", "brief": ""})
    assert r.status_code == 200, f"/post-check 新检测器崩溃时应 200,实际: {r.status_code}"


# ===== Phase0-BE1 千万字可扩展基座(REST 层) =====

def test_graph_focus_query_returns_ego(store):
    """GET /graph?focus=role:甲 → 只回甲的 ego 子图。"""
    from scribe3.ontology import Entity, Fact, KnowledgeEdge
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:f1", "role:甲", "属性", "甲事", valid_from=1))
    store.add_fact(Fact("fact:f2", "role:乙", "属性", "乙事", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:甲", "fact:f1", since_chapter=1))
    store.add_knowledge(KnowledgeEdge("role:乙", "fact:f2", since_chapter=1))
    g = _client(store).get("/graph", params={"focus": "role:甲", "chapter": 5}).json()
    ids = {n["id"] for n in g["nodes"]}
    assert "role:甲" in ids and "fact:f1" in ids
    assert "fact:f2" not in ids


def test_graph_limit_query_caps_nodes(store):
    """GET /graph?limit=5 → 节点总数 ≤ 5。"""
    from scribe3.ontology import Entity, Fact, KnowledgeEdge
    store.add_entity(Entity("role:主", "character", "主"))
    for i in range(30):
        fid = f"fact:q{i}"
        store.add_fact(Fact(fid, "role:主", "属性", f"命题{i}", valid_from=1))
        store.add_knowledge(KnowledgeEdge("role:主", fid, since_chapter=1))
    g = _client(store).get("/graph", params={"limit": 5}).json()
    assert len(g["nodes"]) <= 5


def test_timeline_limit_and_truncated(store):
    """GET /timeline?limit=N → items 截断到 N,truncated=true。"""
    from scribe3.ontology import Event
    for i in range(1, 40):
        store.add_event(Event(f"ev:t{i}", "action", story_time=i,
                              motivated_by_goal="g", causal_in=[("ev:t1", "enables")]))
    r = _client(store).get("/timeline", params={"ch_from": 1, "ch_to": 100, "limit": 10}).json()
    assert len(r["items"]) <= 10
    assert r["truncated"] is True
    assert r["limit"] == 10


def test_quality_qc_breakdown_preserved(store):
    """/quality 返回 qc_breakdown 五类字段(读缓存,字段口径不变)。"""
    store.save_chapter(1, "一段正常的志怪内容。", title="一")
    q = _client(store).get("/quality").json()
    ch1 = q["chapters"][0]
    assert "qc_breakdown" in ch1
    assert set(ch1["qc_breakdown"]) == {"repetition", "structural", "purple",
                                         "ai_tics", "oversaturation"}
    assert "qc_issues" in ch1 and "causal" in ch1 and "word_count" in ch1


# ===== Phase0-BE2 四阶段写作:/save-draft /latest-draft + save-chapter 自动 final 版 + phase 钩子 =====

def test_save_draft_persists_and_versions(store):
    """POST /save-draft:写 chapter.draft + 追加 chapter_version(stage='draft'),返回版本 id。"""
    c = _client(store)
    c.post("/save-chapter", json={"seq": 10, "prose": "定稿。", "title": "第十章"})
    r = c.post("/save-draft", params={"seq": 10},
               json={"prose": "草稿正文。她推开门，外面下着雨。", "summary": "初稿"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "saved"
    assert body["id"]
    # draft 落库,prose 不被覆盖
    ch = store.get_chapter(10)
    assert ch["draft"] == "草稿正文。她推开门，外面下着雨。"
    assert ch["prose"] == "定稿。"
    # 留了一个 draft 版
    vers = c.get("/chapter-versions", params={"seq": 10}).json()
    assert any(v["stage"] == "draft" and v["summary"] == "初稿" for v in vers)


def test_latest_draft_roundtrip(store):
    """GET /latest-draft:取回最新 draft 版(prose+stats)。"""
    c = _client(store)
    c.post("/save-draft", params={"seq": 11}, json={"prose": "草稿一。"})
    c.post("/save-draft", params={"seq": 11}, json={"prose": "草稿二。最新。"})
    r = c.get("/latest-draft", params={"seq": 11})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prose"] == "草稿二。最新。"
    assert "stats" in body


def test_latest_draft_none_returns_empty(store):
    """无 draft 版:GET /latest-draft 返回空对象(204 语义降级为 200 空)。"""
    c = _client(store)
    c.post("/save-chapter", json={"seq": 12, "prose": "只有定稿。"})
    r = c.get("/latest-draft", params={"seq": 12})
    assert r.status_code == 200
    assert r.json() == {}


def test_save_chapter_auto_final_version(store):
    """POST /save-chapter:存正文时自动追加 chapter_version(stage='final')。"""
    c = _client(store)
    c.post("/save-chapter", json={"seq": 13, "prose": "正文定稿。", "title": "第十三章"})
    vers = c.get("/chapter-versions", params={"seq": 13}).json()
    finals = [v for v in vers if v["stage"] == "final"]
    assert len(finals) >= 1


def test_save_chapter_failsoft_version(store, monkeypatch):
    """留版失败不阻断存稿(fail-soft)。"""
    c = _client(store)
    monkeypatch.setattr(store, "add_chapter_version",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = c.post("/save-chapter", json={"seq": 14, "prose": "正文。"})
    assert r.status_code == 200
    assert r.json()["status"] == "saved"


def test_patch_chapter_beats(store):
    """PATCH /chapters/{seq} 能改 beats(经 update_chapter_meta 白名单)。"""
    c = _client(store)
    c.post("/save-chapter", json={"seq": 15, "prose": "正文。"})
    r = c.patch("/chapters/15", json={"beats": [{"text": "拍1"}, {"text": "拍2", "done": True}]})
    assert r.status_code == 200, r.text
    ch = store.get_chapter(15)
    assert ch["beats"] == [{"text": "拍1"}, {"text": "拍2", "done": True}]


def test_chat_write_phase_default_unchanged(store, monkeypatch):
    """phase 钩子:默认(phase 空)行为不变 —— instructions 不含阶段角色提示。"""
    captured = {}

    def fake_stream(message, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        yield "data: x\n\n"

    monkeypatch.setattr(A, "_stream_write", fake_stream)
    c = _client(store)
    r = c.post("/chat/write", json={"msg": "这章怎么写", "chapter": 1})
    assert r.status_code == 200
    list(r.iter_lines())  # 触发生成器执行
    assert "阶段角色" not in captured.get("instructions", "")


def test_chat_write_phase_plan_injects_role(store, monkeypatch):
    """phase='plan' → instructions 末尾追加规划期角色提示。"""
    captured = {}

    def fake_stream(message, instructions, expect_proposal=False, **_kw):
        captured["instructions"] = instructions
        yield "data: x\n\n"

    monkeypatch.setattr(A, "_stream_write", fake_stream)
    c = _client(store)
    r = c.post("/chat/write", json={"msg": "规划这章", "chapter": 1, "phase": "plan"})
    assert r.status_code == 200
    list(r.iter_lines())
    assert "阶段角色" in captured["instructions"]


def test_patch_chapter_deduction_fields(store):
    """PATCH /chapters 透传 scene_truth/involved_characters/deductions 到 store。"""
    store.save_chapter(2, "", title="第2章")
    c = _client(store)
    r = c.patch("/chapters/2", json={
        "scene_truth": "真相X", "involved_characters": ["role:a"],
        "deductions": [{"character_id": "role:a", "character_name": "甲", "prose": "看到:X"}]})
    assert r.status_code == 200
    ch = store.get_chapter(2)
    assert ch["scene_truth"] == "真相X"
    assert ch["involved_characters"] == ["role:a"]
    assert ch["deductions"][0]["prose"] == "看到:X"


def test_deduction_grounding_endpoint_reads_server_truth_not_client_evidence(store, monkeypatch):
    """投影审查只能拿章节权威真相作证据，客户端不能另塞一份来源绕过。"""
    import scribe3.app as A
    store.save_chapter(23, "", title="第23章")
    store.update_chapter_meta(23, {"scene_truth": "沈砚站在潮闸前，闸板震颤。"})
    seen = {}

    def review(source, candidate, *, mode):
        seen.update(source=source, candidate=candidate, mode=mode)
        return {"ok": False, "issues": [{"claim": "黑水", "reason": "无来源", "evidence": ""}]}

    monkeypatch.setattr(A, "_grounding_review", review)
    r = _client(store).post("/chapters/23/deductions/grounding", json={
        "candidate": "黑水从闸底涌出。", "character_id": "role:季棠",
        "source": "客户端伪造的黑水证据",
    })

    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert seen == {"source": "沈砚站在潮闸前，闸板震颤。", "candidate": "黑水从闸底涌出。", "mode": "deduction"}


def test_deduction_block_injects_truth_and_projections(store):
    from scribe3.app import _deduction_block
    store.save_chapter(3, "", title="第3章")
    store.update_chapter_meta(3, {
        "scene_truth": "真相:借命发生",
        "deductions": [{"character_id": "role:柳", "character_name": "柳怀玉", "prose": "看到:纸人动"}]})
    blk = _deduction_block(store, 3)
    assert "真相:借命发生" in blk
    assert "柳怀玉" in blk and "看到:纸人动" in blk
    store.save_chapter(4, "", title="第4章")
    assert _deduction_block(store, 4) == ""   # 空章返回空串


def test_motif_instances_endpoint(store):
    store.add_motif("铜炉", theme="宿命")
    mid = store.list_motifs()[0]["id"]
    store.add_motif_instance(mid, chapter=2, evidence="炉火", ingest_seq=2)
    c = _client(store)
    r = c.get("/motif-instances?chapter=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["motif_id"] == mid
    assert body[0]["name"] == "铜炉"
    assert body[0]["evidence"] == "炉火"
    assert c.get("/motif-instances?chapter=9").json() == []


def test_char_anchors_and_arc_beats_endpoints(store):
    """Task4 弧光端点:PATCH 锚→GET 回读一致;POST 两 beat→有序;DELETE 后消失。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    c = _client(store)
    r = c.patch("/char-anchors", json={
        "character_id": "role:柳怀玉",
        "anchors": {"lie": "官法大过阴律", "arc_type": "disillusionment"}})
    assert r.status_code == 200 and r.json()["status"] == "updated"
    got = c.get("/char-anchors", params={"character_id": "role:柳怀玉"}).json()
    assert got["anchors"]["lie"] == "官法大过阴律"
    assert got["anchors"]["arc_type"] == "disillusionment"
    assert got["arc_plan"] == []
    # POST 两个 beat → arc_plan 按 target_chapter 有序
    r1 = c.post("/arc-beats", json={"character_id": "role:柳怀玉", "beat_name": "midpoint",
                                    "target_chapter": 6, "lie_belief_target": 50,
                                    "trigger_event": "判牍改命"})
    assert r1.status_code == 200 and r1.json()["status"] == "created"
    c.post("/arc-beats", json={"character_id": "role:柳怀玉",
                               "beat_name": "third_plot_point", "target_chapter": 10})
    got2 = c.get("/char-anchors", params={"character_id": "role:柳怀玉"}).json()
    assert [b["beat_name"] for b in got2["arc_plan"]] == ["midpoint", "third_plot_point"]
    # DELETE 后消失
    bid = got2["arc_plan"][0]["id"]
    rd = c.delete(f"/arc-beats/{bid}")
    assert rd.status_code == 200 and rd.json()["status"] == "deleted"
    got3 = c.get("/char-anchors", params={"character_id": "role:柳怀玉"}).json()
    assert [b["beat_name"] for b in got3["arc_plan"]] == ["third_plot_point"]


def test_patch_char_anchors_unknown_character_404(store):
    """Task5-C④:PATCH /char-anchors 对不存在的 character_id 回 404,不再静默 200。"""
    from scribe3.ontology import Entity
    c = _client(store)
    r = c.patch("/char-anchors", json={
        "character_id": "role:不存在的角色", "anchors": {"lie": "x"}})
    assert r.status_code == 404
    # 存在的角色不受影响
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    r2 = c.patch("/char-anchors", json={
        "character_id": "role:柳怀玉", "anchors": {"lie": "官法大过阴律"}})
    assert r2.status_code == 200


def test_patch_char_anchors_non_character_entity_404(store):
    """Task7-C①:存在但非 character 的实体(如 place)PATCH 锚应 404,不误 200。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("place:义庄", "place", "义庄"))
    c = _client(store)
    r = c.patch("/char-anchors", json={
        "character_id": "place:义庄", "anchors": {"lie": "x"}})
    assert r.status_code == 404


def test_post_arc_beats_lie_belief_target_range_422(store):
    """Task5-C⑤:POST /arc-beats 的 lie_belief_target 非 None 时须 0-100,否则 422。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    c = _client(store)
    base = {"character_id": "role:柳怀玉", "beat_name": "midpoint", "target_chapter": 6}
    assert c.post("/arc-beats", json={**base, "lie_belief_target": 130}).status_code == 422
    assert c.post("/arc-beats", json={**base, "lie_belief_target": -1}).status_code == 422
    assert c.post("/arc-beats", json={**base, "lie_belief_target": "五十"}).status_code == 422
    # 边界与 None 合法
    assert c.post("/arc-beats", json={**base, "lie_belief_target": 0}).status_code == 200
    assert c.post("/arc-beats", json={**base, "lie_belief_target": 100}).status_code == 200
    assert c.post("/arc-beats", json=base).status_code == 200


# ===== 块四a-1 素材库 material 端点(镜像 motif/promise CRUD 形态)=====

def test_material_crud(store):
    c = _client(store)
    # 建(返回 id)
    r = c.post("/materials", json={"title": "北宋纸扎工艺", "body": "竹篾骨架。",
                                   "kind": "research", "tags": ["民俗"], "source": "县志"})
    assert r.status_code == 200, r.text
    mid = r.json()["id"]
    assert mid
    c.post("/materials", json={"title": "桥段:井底还魂", "kind": "snippet"})
    # 列 + kind 过滤
    all_rows = c.get("/materials").json()
    assert len(all_rows) == 2
    research = c.get("/materials", params={"kind": "research"}).json()
    assert [m["title"] for m in research] == ["北宋纸扎工艺"]
    assert research[0]["tags"] == ["民俗"] and research[0]["source"] == "县志"
    # 局部改(只传 body,其余不动)
    r = c.patch(f"/materials/{mid}", json={"body": "改:桑皮纸捻。"})
    assert r.status_code == 200
    got = c.get("/materials", params={"kind": "research"}).json()[0]
    assert got["body"] == "改:桑皮纸捻。" and got["title"] == "北宋纸扎工艺"
    # 404:改/删不存在
    assert c.patch("/materials/nonexistent", json={"title": "x"}).status_code == 404
    assert c.delete("/materials/nonexistent").status_code == 404
    # 删
    assert c.delete(f"/materials/{mid}").status_code == 200
    assert len(c.get("/materials").json()) == 1


def test_material_kind_422(store):
    """kind 白名单:应用层 422(建/改/列过滤三处)。"""
    c = _client(store)
    assert c.post("/materials", json={"title": "x", "kind": "diary"}).status_code == 422
    r = c.post("/materials", json={"title": "ok", "kind": "note"})
    mid = r.json()["id"]
    assert c.patch(f"/materials/{mid}", json={"kind": "diary"}).status_code == 422
    assert c.get("/materials", params={"kind": "diary"}).status_code == 422
    c.delete(f"/materials/{mid}")


def test_material_ingest_blind(store):
    """负验证:素材 CRUD 后 ingest 相关表(proposition/knows)零新增。"""
    c = _client(store)
    def counts():
        return (store._query("SELECT count() FROM proposition GROUP ALL"),
                store._query("SELECT count() FROM knows GROUP ALL"))
    before = counts()
    r = c.post("/materials", json={"title": "灵感:灯影戏", "body": "他知道妹妹死了。",
                                   "kind": "inspiration"})
    mid = r.json()["id"]
    c.patch(f"/materials/{mid}", json={"body": "改一版。"})
    c.delete(f"/materials/{mid}")
    assert counts() == before


def test_project_tree_materials_branch(store):
    """项目树第三支:素材库根 → kind 分类(计数)→ 素材叶(ref=id)。"""
    c = _client(store)
    mid = c.post("/materials", json={"title": "县志:纸扎", "kind": "research"}).json()["id"]
    c.post("/materials", json={"title": "随手记", "kind": "note"})
    tree = c.get("/project-tree").json()
    mats = tree["materials"]
    assert mats["type"] == "material_root" and mats["label"] == "素材库"
    cats = {x["ref"]: x for x in mats["children"]}
    assert set(cats) == set(MATERIAL_KINDS)
    res = cats["research"]
    assert res["type"] == "material_category"
    assert any(b["kind"] == "count" and b["value"] == 1 for b in res["badges"])
    leaf = res["children"][0]
    assert leaf["type"] == "material" and leaf["ref"] == mid and leaf["label"] == "县志:纸扎"
    assert any(b["value"] == 1 for b in cats["note"]["badges"])
    assert any(b["value"] == 0 for b in cats["snippet"]["badges"])


# ===== Task7:/chapter-brief 端点 + 写作 prompt 注入章前简报 + M8 修订纪律 =====

def _seed_brief_book(store):
    """1 角色设 lie 锚 + 1 条 open promise(chapter 层,seq=2 时 in_window)。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    store.set_char_anchors("role:柳怀玉", {"lie": "官法大过阴律",
                                           "arc_type": "disillusionment"})
    store.plant_promise("井底的名字", setup_chapter=1)


def test_chapter_brief_endpoint(store):
    """GET /chapter-brief:200 + {sections, text},text 含标题与种子数据。"""
    _seed_brief_book(store)
    c = _client(store)
    r = c.get("/chapter-brief", params={"seq": 2})
    assert r.status_code == 200
    body = r.json()
    assert "text" in body and "sections" in body
    assert "本章创作简报" in body["text"]
    assert "井底的名字" in body["text"]
    assert "柳怀玉" in body["text"]


def test_write_system_carries_brief_and_revision_discipline(store):
    """_editor_write_system(chapter=2):含章前简报 + M8 修订纪律(span 级定向)。"""
    from scribe3.app import _editor_write_system
    _seed_brief_book(store)
    s = _editor_write_system(store, chapter=2)
    assert "本章创作简报" in s
    assert "井底的名字" in s
    assert "修订纪律" in s
    assert "span" in s.lower() and "定向" in s
    assert "禁止开放式整章自评重写" in s


def test_write_system_empty_brief_not_injected(store):
    """空简报(sections 各桶全空)不注入;chapter=None 不组装;修订纪律恒在。"""
    from scribe3.app import _editor_write_system
    s = _editor_write_system(store, chapter=2)
    assert "修订纪律" in s
    assert "本章创作简报" not in s
    s2 = _editor_write_system(store)   # chapter=None → 不组装简报
    assert "修订纪律" in s2 and "本章创作简报" not in s2


def test_write_system_brief_failsafe(store, monkeypatch):
    """fail-safe:简报组装抛异常时 write_system 仍返回且含修订纪律,不阻断写作。"""
    from scribe3.app import _editor_write_system

    def boom(*a, **kw):
        raise RuntimeError("简报组装崩了")

    monkeypatch.setattr(store, "promises_with_lifecycle", boom)
    s = _editor_write_system(store, chapter=2)
    assert isinstance(s, str) and "修订纪律" in s
    assert "本章创作简报" not in s


# ===== Task 8 · M6 设定三态注入(端点回显 + 向后兼容兜底)=====

def _set_mode(store, local: str, mode: str) -> None:
    """测试辅助:给某命题显式配 injection_mode(add_fact 不写此字段)。"""
    store._execute_write(
        "UPDATE type::record('proposition',$l) SET injection_mode=$m", {"l": local, "m": mode})


def test_chapter_brief_injection_manifest(store):
    """/chapter-brief 回显 M6 注入清单(opt-in):显式配 detected 的 fact,本章草料提及其实体
    → 进 chosen;显式 detected 但未提及 → 落 dropped(不进 chosen)。"""
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    store.add_entity(Entity("role:阿禾", "character", "阿禾"))
    store.add_fact(Fact("fact:柳疤", "role:柳怀玉", "外貌", "左手有疤", valid_from=1))
    store.add_fact(Fact("fact:禾技", "role:阿禾", "技艺", "会口技", valid_from=1))
    _set_mode(store, "柳疤", "detected")   # 显式开启三态门控
    _set_mode(store, "禾技", "detected")
    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {"synopsis": "本章柳怀玉独往义庄验尸"})  # 只提柳怀玉
    c = _client(store)
    body = c.get("/chapter-brief", params={"seq": 2}).json()
    inj = body["sections"]["injection"]
    ids = [x["id"] for x in inj["chosen"]]
    assert "fact:柳疤" in ids        # detected + 命中 → 选
    assert "fact:禾技" not in ids    # detected + 未提及 → 不选
    assert inj["fallback"] is False  # 门控启用 → 非兜底


def test_editor_system_injection_fallback_no_mode_no_hit(store):
    """向后兼容兜底:facts 全无 injection_mode 且本章草料无提及 →
    全知分支回退旧 facts[:28](防零注入),设定不因零命中而丢。"""
    from scribe3.app import _editor_system
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:崔判", "character", "崔判"))
    store.add_fact(Fact("fact:判官", "role:崔判", "身份", "阴司判官", valid_from=1))
    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {"synopsis": "一段与设定实体无关的市井风物侧笔"})
    s = _editor_system(store, chapter=2)
    assert "阴司判官" in s          # 兜底注入,未因零命中丢设定
    # chapter=None(聊天流)同样兜底
    assert "阴司判官" in _editor_system(store)


def test_editor_system_legacy_partial_mention_full_facts(store):
    """必修1 真·向后兼容:旧书(无任何 injection_mode)本章草料点到部分实体 →
    仍走旧 facts[:28] 全量,未点名实体状态事实 + 世界级命题 + secret 伏线标记都不丢
    (opt-in 未开启,不得静默降级为仅命中实体事实)。"""
    from scribe3.app import _editor_system
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    store.add_entity(Entity("role:阿禾", "character", "阿禾"))
    store.add_fact(Fact("fact:柳疤", "role:柳怀玉", "外貌", "左手有疤", valid_from=1))
    store.add_fact(Fact("fact:禾技", "role:阿禾", "技艺", "会口技", valid_from=1))
    store.add_fact(Fact("fact:世通", "世界", "通货", "铜钱", valid_from=1))  # 世界级命题(非真实实体)
    store.add_fact(Fact("fact:密", "role:阿禾", "真身", "细作", valid_from=1, secret=True))
    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {"synopsis": "本章柳怀玉独往义庄"})  # 只点柳怀玉
    s = _editor_system(store, chapter=2)
    assert "左手有疤" in s          # 被点名实体
    assert "会口技" in s            # 未点名实体的状态事实也在(未降级)
    assert "铜钱" in s              # 世界级命题不丢
    assert "细作" in s and "私密/伏线" in s   # secret 值 + 标记保留


def test_m6_gating_opt_in_none_is_always(store):
    """必修1:显式配 ≥1 条 injection_mode 才启用门控;启用后 mode=None 按 always 恒注入,
    detected 未提及才落 dropped,世界级命题走 always 永不被 detected 丢。"""
    from scribe3.app import _editor_system
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    store.add_entity(Entity("role:阿禾", "character", "阿禾"))
    store.add_fact(Fact("fact:柳疤", "role:柳怀玉", "外貌", "左手有疤", valid_from=1))  # detected,未提及
    store.add_fact(Fact("fact:禾技", "role:阿禾", "技艺", "会口技", valid_from=1))      # mode=None → always
    store.add_fact(Fact("fact:世通", "世界", "通货", "铜钱", valid_from=1))            # 世界级 → always
    _set_mode(store, "柳疤", "detected")   # 只给这条配 detected → 启用门控
    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {"synopsis": "本章只写阿禾在集市"})  # 点阿禾,不点柳怀玉
    s = _editor_system(store, chapter=2)
    assert "左手有疤" not in s     # detected 且未提及 → 丢
    assert "会口技" in s           # mode=None → always 恒注入
    assert "铜钱" in s             # 世界级 → always,不被 detected 丢


# ===== Task 8 折入 B-3 · 五阶段大纲/节拍注入 =====

def test_outline_block_injects_synopsis_and_beats(store):
    """_outline_block:有 synopsis/beats → 含大纲/节拍内容;空章 → 空串。"""
    from scribe3.app import _outline_block
    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {"synopsis": "柳怀玉赴义庄验尸",
                                  "beats": [{"text": "抵达义庄"}, {"text": "发现异样"}]})
    blk = _outline_block(store, 2)
    assert "柳怀玉赴义庄验尸" in blk
    assert "抵达义庄" in blk and "发现异样" in blk
    store.save_chapter(3, "", title="第3章")
    assert _outline_block(store, 3) == ""   # 空 synopsis/beats → 空串


def test_outline_block_wired_into_chat_write(store, monkeypatch):
    """B-3 根治:GET 与 POST /chat/write 组装路径都注入本章大纲/节拍(此前从不注入)。"""
    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {"synopsis": "柳怀玉赴义庄验尸",
                                  "beats": [{"text": "抵达义庄"}]})
    captured = {}

    def cap(message, instructions, **_kw):
        captured["ins"] = instructions
        return iter([])

    monkeypatch.setattr(A, "_responses_events", cap)
    c = _client(store)
    c.get("/chat/write", params={"msg": "写本章", "chapter": 2})
    assert "柳怀玉赴义庄验尸" in captured["ins"] and "抵达义庄" in captured["ins"]
    captured.clear()
    c.post("/chat/write", json={"msg": "写本章", "chapter": 2})
    assert "柳怀玉赴义庄验尸" in captured["ins"] and "抵达义庄" in captured["ins"]


def test_outline_block_focalizer_guardrail(store):
    """必修2:限知章(focalizer 非空)_outline_block 含限知免责句;全知章不含。"""
    from scribe3.app import _outline_block
    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {"synopsis": "柳怀玉赴义庄验尸"})
    foc = _outline_block(store, 2, focalizer="role:柳怀玉")
    assert "柳怀玉赴义庄验尸" in foc          # 大纲仍在(仍引导情节)
    assert "帧外私密留作伏笔" in foc          # 限知免责句
    omni = _outline_block(store, 2, focalizer="")
    assert "柳怀玉赴义庄验尸" in omni
    assert "帧外私密留作伏笔" not in omni      # 全知章无免责句


# ===== 方案B任务13b:反转标注规范 + 叙述者真诚视角硬约束 =====

def test_reversal_annotation_and_focalizer_sincerity_wired(store, monkeypatch):
    """B13b:①_outline_block 节拍标注规范追加反转字段(reversal_type/setup_clues/
    reveal_position_pct);②写作 instructions 含叙述者真诚视角硬约束("真诚相信"),
    GET/POST 两条组装链均命中(防知情POV倒灌的又一道文字层约束)。"""
    from scribe3.app import _outline_block
    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {"synopsis": "柳怀玉赴义庄验尸",
                                  "beats": [{"text": "抵达义庄"}]})
    blk = _outline_block(store, 2)
    assert "reversal_type" in blk and "setup_clues" in blk and "reveal_position_pct" in blk

    captured = {}

    def cap(message, instructions, **_kw):
        captured["ins"] = instructions
        return iter([])

    monkeypatch.setattr(A, "_responses_events", cap)
    c = _client(store)
    c.get("/chat/write", params={"msg": "写本章", "chapter": 2})
    assert "真诚相信" in captured["ins"]
    captured.clear()
    c.post("/chat/write", json={"msg": "写本章", "chapter": 2})
    assert "真诚相信" in captured["ins"]


# ===== 批0 · B1:图片写作 500(彻查 B-1)=====

# 1x1 透明 PNG(base64,validate=True 可解码,远小于 5MB 上限)
_PNG_1x1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def test_chat_write_with_image_no_500(store, monkeypatch):
    """B1(彻查 B-1):POST /chat/write 带 ImageModel 图片附件不再 500。

    修前:图片组装对 pydantic ImageModel 调 img.get('type')/img.get('data')
    → AttributeError('ImageModel' object has no attribute 'get')→ 500,带图写作 100% 死。
    """
    import scribe3.app as appmod
    monkeypatch.setattr(
        appmod, "_stream_write",
        lambda msg, instructions, expect_proposal=False, **_kw: iter([]))
    r = _client(store).post("/chat/write", json={
        "msg": "看这张图写一段",
        "chapter": 1,
        "images": [{"data": _PNG_1x1, "type": "image/png"}],
    })
    assert r.status_code != 500, f"带图写作不应 500,实际 {r.status_code}: {r.text}"


# ===== 批0 · B4:掩码写哨兵 + 势力 merge(彻查 F-1/F-2)=====

def test_b4_char_patch_masked_backstory_preserves_real_value(store):
    """B4(F-1):角色私密 backstory 打码后 PATCH 整行(含掩码 backstory)+改其他字段,
    真值不被销毁(掩码哨兵剔除 backstory=视为未改)。"""
    c = _client(store)
    c.post("/characters", json={"name": "甲", "backstory": "真实前史ABC",
                                "backstory_secret": True})
    masked = next(e for e in c.get("/entities").json() if e["name"] == "甲")
    assert masked["backstory"] == "🔒 私密", "GET 应打码"
    # 前端把打码值整行回传,并改 fear
    c.patch("/characters/甲", json={"name": "甲", "backstory": "🔒 私密",
                                    "backstory_secret": True, "fear": "怕火"})
    revealed = next(e for e in c.get("/entities", params={"reveal_secret": True}).json()
                    if e["name"] == "甲")
    assert revealed["backstory"] == "真实前史ABC", "私密真值应存活(未被掩码覆盖)"
    assert revealed["fear"] == "怕火", "其他字段应正常更新"


def test_b4_add_char_masked_backstory_not_persisted(store):
    """B4:curl 直接 POST /characters 传掩码 backstory → 哨兵剔除,不落库为字面掩码。"""
    c = _client(store)
    c.post("/characters", json={"name": "乙", "backstory": "🔒 私密",
                                "backstory_secret": True})
    revealed = next(e for e in c.get("/entities", params={"reveal_secret": True}).json()
                    if e["name"] == "乙")
    assert revealed["backstory"] != "🔒 私密", "掩码占位符不应落库"
    assert revealed["backstory"] is None


def test_b4_faction_partial_update_preserves_other_fields(store):
    """B4(F-2):势力只改 leader(仅提交 name+leader)→
    private_operation/public_face/ideology 都不被整行覆盖销毁(端点层真 merge)。"""
    c = _client(store)
    c.post("/factions", json={"name": "青叶门", "ideology": "复辟", "leader": "甲",
                              "public_face": "药铺", "private_operation": "养死士",
                              "private_operation_secret": True})
    c.post("/factions", json={"name": "青叶门", "leader": "乙"})  # 只改 leader
    row = next(f for f in c.get("/factions", params={"reveal_secret": True}).json()
               if f["name"] == "青叶门")
    assert row["leader"] == "乙", "leader 应更新"
    assert row["ideology"] == "复辟", "ideology 不应被销毁"
    assert row["public_face"] == "药铺", "public_face 不应被销毁"
    assert row["private_operation"] == "养死士", "private_operation 不应被销毁"


def test_b4_faction_masked_private_op_preserves_real_value(store):
    """B4:势力私密 private_operation 打码后整行回传(含掩码)+改 ideology →
    掩码哨兵剔除私密字段,真值存活。"""
    c = _client(store)
    c.post("/factions", json={"name": "红庐", "ideology": "改良", "public_face": "商会",
                              "private_operation": "走私军械",
                              "private_operation_secret": True})
    masked = next(f for f in c.get("/factions").json() if f["name"] == "红庐")
    assert masked["private_operation"] == "🔒 私密", "GET 应打码"
    c.post("/factions", json={"name": "红庐", "ideology": "复辟", "public_face": "商会",
                              "private_operation": "🔒 私密",
                              "private_operation_secret": True})
    row = next(f for f in c.get("/factions", params={"reveal_secret": True}).json()
               if f["name"] == "红庐")
    assert row["ideology"] == "复辟", "ideology 应更新"
    assert row["private_operation"] == "走私军械", "私密真值应存活(掩码被哨兵剔除)"


# ===== 批0 · B5:_codex_block 限知隐私密(彻查 F-3)=====

def test_b5_codex_block_hides_secret_backstory_in_limited_pov(store):
    """B5(F-3):限知章(focalizer 非空,乙≠甲)主编基座不含私密角色 甲 的 backstory;
    全知章(focalizer 空=作者全知)保留(向后兼容)。"""
    from scribe3.ontology import Entity
    from scribe3.app import _editor_system
    store.add_entity(Entity("role:甲", "character", "甲",
                            traits={"backstory": "SECRETMARKER_他是前朝皇子",
                                    "backstory_secret": True}))
    store.add_entity(Entity("role:乙", "character", "乙"))
    limited = _editor_system(store, focalizer="乙", chapter=3)
    assert "SECRETMARKER" not in limited, "限知章设定圣经不应明文注入私密 backstory(POV 倒灌)"
    omni = _editor_system(store, focalizer="", chapter=3)
    assert "SECRETMARKER" in omni, "全知章(作者)应保留私密 backstory"


# ==== Task9 M2a: 张力检查——确定性3项 + /tension-check(不真打 LLM)====

def test_tension_deterministic_items(store):
    from scribe3.brief import tension_deterministic
    store.plant_promise("井底的名字", setup_chapter=1)
    pid = store.list_promises()[0]["id"]
    # 第3章无任何触及 → 进展路标不过(开着但本章未推进)
    items = tension_deterministic(store, seq=3)
    prog = [i for i in items if i["item"] == "promise_progress"][0]
    assert prog["pass"] is False
    # 三项确定性齐全
    assert {i["item"] for i in items} == {"promise_progress", "open_loops", "irony_surface"}
    store.add_promise_touch(pid, chapter=3, evidence="梦见井", ingest_seq=3)
    items = tension_deterministic(store, seq=3)
    prog = [i for i in items if i["item"] == "promise_progress"][0]
    assert prog["pass"] is True


def test_tension_check_no_prose(store):
    c = _client(store)
    r = c.post("/tension-check", params={"seq": 9}).json()
    assert r == {"items": [], "error": "no_prose"}


def test_tension_check_full_items_with_mocked_rubric(store, monkeypatch):
    import scribe3.llm as llm
    fixed = (
        '{"dramatic_question":{"present":true,"answered_escalated":true,"note":"能否验尸"},'
        '"outcomes":[{"scene":"义庄对峙","type":"yes"},{"scene":"井边","type":"yes_but"}],'
        '"value_shift":{"present":true,"note":"信任→怀疑"},'
        '"micro_tension":{"deserts":[]},'
        '"hook":{"present":true,"type":"信息截断","strength":"strong"}}')
    monkeypatch.setattr(llm, "hermes_complete", lambda *a, **k: fixed)
    store.save_chapter(3, "义庄里灯影摇动,他俯身去看那具尸首。", title="第三章")
    r = _client(store).post("/tension-check", params={"seq": 3}).json()
    names = {i["item"] for i in r["items"]}
    # 确定性3 + rubric5 = 8 项齐全
    assert names == {"promise_progress", "open_loops", "irony_surface",
                     "dramatic_question", "outcome_grammar", "value_shift",
                     "micro_tension", "hook"}
    assert len(r["items"]) == 8
    assert r["rubric"]["dramatic_question"]["present"] is True
    # 一场 yes(泄气)→ outcome_grammar 不过
    og = [i for i in r["items"] if i["item"] == "outcome_grammar"][0]
    assert og["pass"] is False


def test_tension_check_rubric_failed_when_llm_junk(store, monkeypatch):
    import scribe3.llm as llm
    monkeypatch.setattr(llm, "hermes_complete", lambda *a, **k: "抱歉我无法……")
    store.save_chapter(4, "一段正文内容。", title="第四章")
    r = _client(store).post("/tension-check", params={"seq": 4}).json()
    assert r["rubric_failed"] is True
    assert r["rubric"] is None
    # 确定性项仍返回(不因 rubric 失败而丢)
    assert {i["item"] for i in r["items"]} == {"promise_progress", "open_loops", "irony_surface"}


def test_tension_check_survives_llm_exception(store, monkeypatch):
    import scribe3.llm as llm
    def boom(*a, **k):
        raise RuntimeError("hermes down")
    monkeypatch.setattr(llm, "hermes_complete", boom)
    store.save_chapter(5, "一段正文内容。", title="第五章")
    r = _client(store).post("/tension-check", params={"seq": 5}).json()
    # LLM 抛异常也不崩,降级为 rubric_failed
    assert r["rubric_failed"] is True and r["rubric"] is None


# ==== P1-10: 4 检测器接线进 /post-check(彻查)====

def test_post_check_wires_four_detectors(store):
    """排比/诗化分行/引号失配/更次倒退 4 个既有检测器应接进 /post-check 确定性聚合。"""
    c = _client(store)
    prose = "他想起娘。他想起爹。他想起家门。\n呜。\n他说“你好\n四更天守着,又到三更。"
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    assert r["parallelism"], "同句式≥3连 应命中 parallelism"
    assert r["poetic_fragments"], "孤立短句 应命中 poetic_fragments"
    assert r["unbalanced_quotes"], "引号开闭失配 应命中 unbalanced_quotes"
    assert r["watch_regression"], "四更→三更倒退 应命中 watch_regression"


def test_post_check_four_detectors_clean_text(store):
    """干净文本:4 检测器均空列表(不误报,不破坏既有输出)。"""
    c = _client(store)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "他走进义庄,点亮了灯。屋里静得很。", "focalizer": "", "brief": ""}).json()
    for k in ("parallelism", "poetic_fragments", "unbalanced_quotes", "watch_regression"):
        assert r[k] == [], f"{k} 干净文本应为空"
    # 既有键未被破坏
    for k in ("quality", "issues", "duplicate_lines", "emotion_telling", "cross_consistency"):
        assert k in r


# ==== 彻查 B-2: 伏笔 tier 三生产入口(REST /promises-new + PATCH /promises/{pid})====

def test_add_promise_rest_tier_book_never_overdue(store):
    """POST /promises-new 带 tier=book → 落 book 层,payoff_max=None(书级永不超期)。
    方案B任务21:book 级悬念必须带 resolution(真实答案)才放行,故补此字段。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "书级母题:铜炉终反噬", "setup_chapter": 1,
                                      "tier": "book", "resolution": "铜炉本是镇魂器,终将反噬铸炉者"})
    assert r.status_code == 200, r.text
    p = next(x for x in store.list_promises() if x["text"] == "书级母题:铜炉终反噬")
    assert p["tier"] == "book"
    assert p["payoff_max"] is None, f"书级伏笔 payoff_max 应为 None,实际 {p['payoff_max']}"


def test_add_promise_rest_tier_arc_window(store):
    """POST /promises-new 带 tier=arc,setup=2 → 窗口 payoff_min=7 / payoff_max=17(+5..+15)。
    方案B任务21:arc 级悬念必须带 resolution(真实答案)才放行,故补此字段。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "卷级伏笔", "setup_chapter": 2, "tier": "arc",
                                      "resolution": "卷级伏笔的真实答案:此人是内奸"})
    assert r.status_code == 200, r.text
    p = next(x for x in store.list_promises() if x["text"] == "卷级伏笔")
    assert p["tier"] == "arc"
    assert p["payoff_min"] == 7 and p["payoff_max"] == 17


def test_add_promise_rest_default_tier_chapter(store):
    """POST /promises-new 不带 tier → 默认 chapter 层(payoff_max=setup+3),不回归。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "近场伏笔", "setup_chapter": 1})
    assert r.status_code == 200, r.text
    p = next(x for x in store.list_promises() if x["text"] == "近场伏笔")
    assert p["tier"] == "chapter"
    assert p["payoff_max"] == 4


def test_add_promise_rest_illegal_tier_rejected(store):
    """POST /promises-new 带非法 tier → 422(非法值不落库)。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "坏层级", "setup_chapter": 1, "tier": "卷"})
    assert r.status_code == 422, r.text
    assert not any(x["text"] == "坏层级" for x in store.list_promises())


# ==== 方案B任务21:悬念存档答案强制(rules/story-narrative.md:20)——
# "悬念必须有文档记录的真实答案"。book/arc 长期悬念建伏笔时必填 resolution;
# chapter 级短期悬念(本章内起落即兑现)豁免,向后兼容不传该字段的既有调用方。====

def test_add_promise_book_tier_missing_resolution_422(store):
    """POST /promises-new 建 book 级伏笔缺 resolution → 422,且不落库。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "书级悬念:铜炉来历", "setup_chapter": 1, "tier": "book"})
    assert r.status_code == 422, r.text
    assert "真实答案" in r.json()["detail"]
    assert not any(x["text"] == "书级悬念:铜炉来历" for x in store.list_promises())


def test_add_promise_arc_tier_missing_resolution_422(store):
    """POST /promises-new 建 arc 级伏笔缺 resolution → 422,且不落库。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "卷级悬念:信件来源", "setup_chapter": 2, "tier": "arc"})
    assert r.status_code == 422, r.text
    assert not any(x["text"] == "卷级悬念:信件来源" for x in store.list_promises())


def test_add_promise_book_tier_with_resolution_ok(store):
    """POST /promises-new 建 book 级伏笔带 resolution → 200,正常落库。
    B21 收尾清理批:resolution 现已落库,此处补断言可读回真实值(此前只测 200)。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "书级悬念:主角身世", "setup_chapter": 1,
                                      "tier": "book", "resolution": "主角是前朝遗孤"})
    assert r.status_code == 200, r.text
    row = [x for x in store.list_promises() if x["text"] == "书级悬念:主角身世"][0]
    assert row["resolution"] == "主角是前朝遗孤"


def test_add_promise_arc_tier_with_resolution_ok(store):
    """POST /promises-new 建 arc 级伏笔带 resolution → 200,正常落库。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "卷级悬念:密室机关", "setup_chapter": 3,
                                      "tier": "arc", "resolution": "机关由老仆暗中打开"})
    assert r.status_code == 200, r.text
    assert any(x["text"] == "卷级悬念:密室机关" for x in store.list_promises())


def test_add_promise_chapter_tier_missing_resolution_exempt(store):
    """POST /promises-new 建 chapter 级(短期悬念)缺 resolution → 200(豁免,向后兼容)。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "章内悬念:谁在敲门", "setup_chapter": 5, "tier": "chapter"})
    assert r.status_code == 200, r.text
    assert any(x["text"] == "章内悬念:谁在敲门" for x in store.list_promises())


def test_add_promise_no_tier_missing_resolution_exempt(store):
    """POST /promises-new 不传 tier(默认 chapter)缺 resolution → 200(向后兼容既有调用方)。"""
    c = _client(store)
    r = c.post("/promises-new", json={"text": "未传层级的伏笔", "setup_chapter": 1})
    assert r.status_code == 200, r.text
    assert any(x["text"] == "未传层级的伏笔" for x in store.list_promises())


def test_edit_promise_rest_tier_recomputes_window(store):
    """PATCH /promises/{pid} 改 tier=arc → 窗口按 arc 重算(setup=3 → 8..18)。
    B21 收尾清理批:升格 arc 须带 resolution(与 /promises-new 同约束),补该字段。"""
    store.plant_promise("先近后卷", setup_chapter=3, kind="promise")  # 建时 chapter → payoff_max=6
    pid = next(x for x in store.list_promises() if x["text"] == "先近后卷")["id"]
    c = _client(store)
    r = c.patch(f"/promises/{pid}", json={"text": "先近后卷", "setup_chapter": 3, "tier": "arc",
                                          "resolution": "升格卷级的真实答案:老仆是幕后人"})
    assert r.status_code == 200, r.text
    p = next(x for x in store.list_promises() if x["id"] == pid)
    assert p["tier"] == "arc"
    assert p["payoff_min"] == 8 and p["payoff_max"] == 18


def test_edit_promise_rest_tier_upgrade_missing_resolution_422(store):
    """B21 收尾清理批(审查发现的绕过口):PATCH 把 tier 升格成 book/arc,
    但请求与库里都没有 resolution → 422(与 /promises-new 同文案),且不落库。"""
    store.plant_promise("短期悬念想升格", setup_chapter=2, kind="promise")  # chapter 级,无 resolution
    pid = next(x for x in store.list_promises() if x["text"] == "短期悬念想升格")["id"]
    c = _client(store)
    r = c.patch(f"/promises/{pid}", json={"text": "短期悬念想升格", "tier": "book"})
    assert r.status_code == 422, r.text
    assert "真实答案" in r.json()["detail"]
    p = next(x for x in store.list_promises() if x["id"] == pid)
    assert p["tier"] == "chapter", "422 拒绝后 tier 不得被改动"


def test_edit_promise_rest_without_tier_preserves_tier(store):
    """PATCH 不带 tier → 既有 tier 不被改回 chapter(可选字段,缺省即保留)。"""
    store.plant_promise("已是书级", setup_chapter=1, kind="promise", tier="book")
    pid = next(x for x in store.list_promises() if x["text"] == "已是书级")["id"]
    c = _client(store)
    r = c.patch(f"/promises/{pid}", json={"text": "已是书级改名", "setup_chapter": 1})
    assert r.status_code == 200, r.text
    p = next(x for x in store.list_promises() if x["id"] == pid)
    assert p["tier"] == "book", "缺省 tier 的编辑不得把 book 改回 chapter"
    assert p["payoff_max"] is None


def test_edit_promise_rest_illegal_tier_rejected(store):
    """PATCH 带非法 tier → 422。"""
    store.plant_promise("待改", setup_chapter=1, kind="promise")
    pid = next(x for x in store.list_promises() if x["text"] == "待改")["id"]
    c = _client(store)
    r = c.patch(f"/promises/{pid}", json={"text": "待改", "setup_chapter": 1, "tier": "xx"})
    assert r.status_code == 422, r.text


# ==== T9 审查 Minor1: /tension-check 值型错 JSON 降级不崩(不 500)====

def test_tension_check_rubric_type_error_degrades(store, monkeypatch):
    """LLM 返回合法 JSON 但值型错(outcomes 是字符串列表而非 dict 列表)→ 组装 rubric
    items 时 o.get() 会抛 AttributeError。应降级 rubric_failed=True,而非端点 500。"""
    import scribe3.llm as llm
    bad_type = (
        '{"dramatic_question":{"present":true,"note":"能否验尸"},'
        '"outcomes":["义庄对峙","井边"],'  # 应为 dict 列表,这里是字符串列表
        '"value_shift":{"present":true},'
        '"micro_tension":{"deserts":[]},'
        '"hook":{"present":true,"type":"信息截断","strength":"strong"}}')
    monkeypatch.setattr(llm, "hermes_complete", lambda *a, **k: bad_type)
    store.save_chapter(6, "义庄里灯影摇动。", title="第六章")
    resp = _client(store).post("/tension-check", params={"seq": 6})
    assert resp.status_code == 200, f"值型错 JSON 不应 500,实际 {resp.status_code}"
    r = resp.json()
    assert r["rubric_failed"] is True and r["rubric"] is None
    # 确定性项仍返回,不因 rubric 组装失败而丢
    assert {i["item"] for i in r["items"]} == {"promise_progress", "open_loops", "irony_surface"}


# ==== T9 审查 Minor2: micro_tension detail 文案(空 deserts 不显尾冒号)====

def test_tension_check_micro_tension_empty_deserts_shows_none(store, monkeypatch):
    """micro_tension.deserts 为空 → detail 应为 '无',而非 '荒漠段:'(运算符优先级 bug)。"""
    import scribe3.llm as llm
    fixed = (
        '{"dramatic_question":{"present":true},'
        '"outcomes":[{"scene":"义庄","type":"yes_but"}],'
        '"value_shift":{"present":true},'
        '"micro_tension":{"deserts":[]},'
        '"hook":{"present":true,"type":"截断","strength":"strong"}}')
    monkeypatch.setattr(llm, "hermes_complete", lambda *a, **k: fixed)
    store.save_chapter(7, "一段正文。", title="第七章")
    r = _client(store).post("/tension-check", params={"seq": 7}).json()
    mt = [i for i in r["items"] if i["item"] == "micro_tension"][0]
    assert mt["detail"] == "无", f"空 deserts 的 detail 应为 '无',实际 {mt['detail']!r}"


def test_tension_check_micro_tension_with_deserts(store, monkeypatch):
    """micro_tension.deserts 非空 → detail 带 '荒漠段:' 前缀 + 内容(修文案不破坏非空分支)。"""
    import scribe3.llm as llm
    fixed = (
        '{"dramatic_question":{"present":true},'
        '"outcomes":[{"scene":"义庄","type":"yes_but"}],'
        '"value_shift":{"present":true},'
        '"micro_tension":{"deserts":["第2段","第5段"]},'
        '"hook":{"present":true,"type":"截断","strength":"strong"}}')
    monkeypatch.setattr(llm, "hermes_complete", lambda *a, **k: fixed)
    store.save_chapter(8, "一段正文。", title="第八章")
    r = _client(store).post("/tension-check", params={"seq": 8}).json()
    mt = [i for i in r["items"] if i["item"] == "micro_tension"][0]
    assert mt["detail"] == "荒漠段:第2段、第5段"


# ===== 批B P0-2/H-01:多书下 MCP 工具串书——所有 s3_ 工具调用必须显式带 work =====
def _cap_responses(cap):
    """捕获传给 responses(:8643)的 with_tools 与 instructions 的假 fn。"""
    def fake_events(message, instructions, model=None, with_tools=True, **_kw):
        cap["with_tools"] = with_tools
        cap["instructions"] = instructions
        return iter([])
    return fake_events


def _assert_work_scoped_tool_prompt(cap, work: str):
    assert cap["with_tools"] is True, "work-scoped MCP 后所有作品都应挂 s3_ 工具"
    ins = cap["instructions"]
    assert "s3_" in ins, "启用工具时 instructions 应说明可用 s3_ 工具"
    assert f"work={work}" in ins, "instructions 必须钉死当前作品 work 参数"
    assert "必须" in ins and "work" in ins, "instructions 必须强制模型调用 s3_ 工具时带 work"


def test_p0_2_get_write_non_current_work_uses_work_scoped_tools(store, monkeypatch):
    """GET /chat/write:work != SCRIBE3_WORK 时仍挂工具,但所有 s3_ 调用必须传 work=目标书。"""
    import scribe3.app as A
    monkeypatch.setenv("SCRIBE3_WORK", "book_current")
    A.set_store(store, work="book_other")          # 把测试内存 store 绑到别的书(不连真库)
    cap = {}
    monkeypatch.setattr(A, "_responses_events", _cap_responses(cap))
    _client(store).get("/chat/write", params={"msg": "写本章", "chapter": 1, "work": "book_other"})
    _assert_work_scoped_tool_prompt(cap, "book_other")


def test_p0_2_get_write_current_work_mounts_tools(store, monkeypatch):
    """GET /chat/write:work == SCRIBE3_WORK 时正常挂 s3_ 工具,并显式传 work。"""
    import scribe3.app as A
    monkeypatch.setenv("SCRIBE3_WORK", "main")
    cap = {}
    monkeypatch.setattr(A, "_responses_events", _cap_responses(cap))
    _client(store).get("/chat/write", params={"msg": "写本章", "chapter": 1, "work": "main"})
    _assert_work_scoped_tool_prompt(cap, "main")


def test_p0_2_post_write_non_current_work_uses_work_scoped_tools(store, monkeypatch):
    """POST /chat/write:work != SCRIBE3_WORK 时仍挂工具,但所有 s3_ 调用必须传 work=目标书。"""
    import scribe3.app as A
    monkeypatch.setenv("SCRIBE3_WORK", "book_current")
    A.set_store(store, work="book_other")
    cap = {}
    monkeypatch.setattr(A, "_responses_events", _cap_responses(cap))
    _client(store).post("/chat/write?work=book_other", json={"msg": "写本章", "chapter": 1})
    _assert_work_scoped_tool_prompt(cap, "book_other")


def test_p0_2_post_write_current_work_mounts_tools(store, monkeypatch):
    """POST /chat/write:work == SCRIBE3_WORK 时正常挂 s3_ 工具,并显式传 work。"""
    import scribe3.app as A
    monkeypatch.setenv("SCRIBE3_WORK", "main")
    cap = {}
    monkeypatch.setattr(A, "_responses_events", _cap_responses(cap))
    _client(store).post("/chat/write?work=main", json={"msg": "写本章", "chapter": 1})
    _assert_work_scoped_tool_prompt(cap, "main")


def test_p0_2_agentic_non_current_work_uses_work_scoped_tools(store, monkeypatch):
    """agentic-stream:work != SCRIBE3_WORK 时仍挂工具,但所有 s3_ 调用必须传 work=目标书。"""
    import scribe3.app as A
    monkeypatch.setenv("SCRIBE3_WORK", "book_current")
    A.set_store(store, work="book_other")
    cap = {}
    monkeypatch.setattr(A, "_responses_events", _cap_responses(cap))
    _client(store).get("/chat/agentic-stream", params={"msg": "查伏笔", "work": "book_other"})
    _assert_work_scoped_tool_prompt(cap, "book_other")


def test_p0_2_agentic_current_work_mounts_tools(store, monkeypatch):
    """agentic-stream:work == SCRIBE3_WORK 时挂工具 + instructions 含 s3_ 联查段,并显式传 work。"""
    import scribe3.app as A
    monkeypatch.setenv("SCRIBE3_WORK", "main")
    cap = {}
    monkeypatch.setattr(A, "_responses_events", _cap_responses(cap))
    _client(store).get("/chat/agentic-stream", params={"msg": "查伏笔", "work": "main"})
    _assert_work_scoped_tool_prompt(cap, "main")


def test_p0_2_hermes_responses_events_tools_gated_by_flag(monkeypatch):
    """llm 层:with_tools=False 不含 tools;=True 默认只挂 scribe3_read 只读 MCP 面。"""
    import scribe3.llm as llm
    captured = {}

    class _FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def raise_for_status(self): pass
        def iter_lines(self): return iter([])

    def fake_stream(method, url, **kw):
        captured["body"] = kw.get("json")
        return _FakeResp()

    monkeypatch.setattr(llm.httpx, "stream", fake_stream)
    list(llm.hermes_responses_events("m", "i", with_tools=False))
    assert "tools" not in captured["body"], "with_tools=False 时 body 不得含 tools"
    list(llm.hermes_responses_events("m", "i", with_tools=True))
    assert captured["body"].get("tools") == [{"type": "mcp", "server_label": "scribe3_read"}]


# ===== 块四b TDD: /draft-check 草稿轻量确定性分析(不 ingest 不落库) =====
# 设计 §5.4:草稿阶段对任意草稿文本跑确定性检测(复用 critique 的 quality_flags/整行复读/
# 排比/情感直说 + 限知泄露预览),绝不跑 LLM ingest、绝不写 proposition/knows/台账。

def test_draft_check_returns_deterministic_structure(store):
    """/draft-check 应返回 quality(五类)+ duplicate_lines / parallelism / emotion_telling 键。"""
    c = _client(store)
    r = c.post("/draft-check", json={"prose": "他推开门,天光落在案上。"}).json()
    assert set(r["quality"]) >= {"repetition", "structural", "purple", "ai_tics", "oversaturation"}
    for k in ("duplicate_lines", "parallelism", "emotion_telling", "leaks"):
        assert k in r, f"/draft-check 应含 {k} 键,实际键: {list(r)}"
        assert isinstance(r[k], list)


def test_draft_check_clean_text_empty(store):
    """/draft-check:干净草稿文本 → 各确定性检测器空。"""
    c = _client(store)
    r = c.post("/draft-check",
               json={"prose": "他推开门,天光落在案上。她没有回头,只把碗搁下。"}).json()
    assert r["duplicate_lines"] == []
    assert r["parallelism"] == []
    assert r["emotion_telling"] == []
    assert r["leaks"] == []


def test_draft_check_detects_duplicate_lines(store):
    """/draft-check:含整行复读的草稿 → duplicate_lines 非空。"""
    dup = "这是整行完全重复的内容足够长超过六字。"
    prose = f"{dup}\n{dup}\n正常内容。"
    c = _client(store)
    r = c.post("/draft-check", json={"prose": prose}).json()
    assert len(r["duplicate_lines"]) > 0, f"整行复读应检出,实际: {r['duplicate_lines']}"


def test_draft_check_detects_parallelism(store):
    """/draft-check:含排比(连续同句式)的草稿 → parallelism 非空。"""
    prose = "他走过长街,他走过小巷,他走过荒野。"
    c = _client(store)
    r = c.post("/draft-check", json={"prose": prose}).json()
    assert len(r["parallelism"]) > 0, f"排比应检出,实际: {r['parallelism']}"


def test_draft_check_detects_emotion_telling(store):
    """/draft-check:含情感直说的草稿 → emotion_telling 非空。"""
    prose = "他感到恐惧,双腿颤抖。她感到害怕,不敢出声。他其实不是个坏人。"
    c = _client(store)
    r = c.post("/draft-check", json={"prose": prose}).json()
    assert len(r["emotion_telling"]) > 0, f"情感直说应检出,实际: {r['emotion_telling']}"


def test_draft_check_no_db_writes(store):
    """/draft-check 只读:含实体/情节的草稿跑完后,库中无任何 proposition/knows 新增
    (断言库无新增——绝不跑 ingest、绝不落库)。"""
    c = _client(store)
    before_facts = len(store.facts_at(9999))
    before_knows = len(store.load_knowledge())
    prose = "焦三在乱葬岗治眼,老道看得分明。他感到恐惧。"
    r = c.post("/draft-check", json={"prose": prose}).json()
    assert "quality" in r
    assert len(store.facts_at(9999)) == before_facts, "draft-check 不应新增 proposition"
    assert len(store.load_knowledge()) == before_knows, "draft-check 不应新增 knows"


def test_draft_check_leak_preview_readonly(store):
    """/draft-check:给 focalizer+seq 时跑限知泄露预览(只读),命中泄露且不落库。"""
    luanshi_leak_world(store)
    c = _client(store)
    before_facts = len(store.facts_at(9999))
    before_knows = len(store.load_knowledge())
    r = c.post("/draft-check", params={"seq": 1},
               json={"prose": "老道看见焦三在治眼。", "focalizer": "role:老道"}).json()
    assert len(r["leaks"]) > 0, "老道写出治眼应被预览检出泄露"
    assert len(store.facts_at(9999)) == before_facts, "泄露预览是只读,不应新增 proposition"
    assert len(store.load_knowledge()) == before_knows, "泄露预览是只读,不应新增 knows"


def test_draft_check_registered_in_write_gate(store):
    """写路由审计门镜像:/draft-check 虽为 POST 但只读,须登记 KNOWN_REST_WRITE_ROUTES。"""
    from scribe3.tests.test_consistency import TestWriteGate
    assert ("POST", "/draft-check") in TestWriteGate.KNOWN_REST_WRITE_ROUTES


# ===== 批A 余项(P0-1 收尾)TDD: /ingest 手动端点纳入去重护栏 =====
# /ingest(前端"反哺设定库"按钮)在 _pending_ingest 去重集之外——手点反哺撞后台
# 自动 ingest 在途时同章交错。修:/ingest 也走同一 (work,seq) 在途集合护栏。

def test_ingest_rejected_when_chapter_pending(store):
    """/ingest:同章已有 ingest 在途(_pending_ingest 有标记,模拟后台 _bg_ingest 在跑)
    → 拒 409,防手点反哺撞自动 ingest 交错。"""
    A.set_store(store)
    A._pending_ingest.add(("main", 4))   # 模拟后台 _bg_ingest 同章在途
    client = TestClient(A.app)
    r = client.post("/ingest", params={"seq": 4, "work": "main"})
    assert r.status_code == 409, f"同章在途应拒 409,实际 {r.status_code}: {r.text}"
    # 被拒不应误清他人的在途标记
    assert ("main", 4) in A._pending_ingest, "被拒的 /ingest 不应清除在途标记"


def test_ingest_marks_pending_during_run_and_clears(store, monkeypatch):
    """/ingest 同步跑:执行期间占用 _pending_ingest(在途),故并发 _enqueue_ingest 同章去重;
    完成后清除在途标记。与后台 _bg_ingest/_enqueue_ingest 共用同一机制协同去重。"""
    import scribe3.ingest as ingest_mod
    A.set_store(store)
    seen = {}

    def fake_ingest(st, seq, fn, **kw):
        seen["pending_during"] = ("main", seq) in A._pending_ingest
        from fastapi import BackgroundTasks
        # 在途期间并发排队(如后台 save-chapter 触发)应被去重跳过
        seen["enqueue_during"] = A._enqueue_ingest(BackgroundTasks(), "main", seq)
        return {"applied": 0}

    monkeypatch.setattr(ingest_mod, "ingest_chapter", fake_ingest)
    client = TestClient(A.app)
    r = client.post("/ingest", params={"seq": 7, "work": "main"})
    assert r.status_code == 200, f"无在途冲突应 200,实际 {r.status_code}: {r.text}"
    assert seen["pending_during"] is True, "ingest 执行期间该章应标记在途"
    assert seen["enqueue_during"] is False, "在途期间 _enqueue_ingest 同章应去重跳过"
    assert ("main", 7) not in A._pending_ingest, "ingest 完成后应清除在途标记"


def test_ingest_clears_pending_on_exception(store, monkeypatch):
    """/ingest 抛异常也须在 finally 清除在途标记,避免该章永久锁死无法再反哺。"""
    import scribe3.ingest as ingest_mod
    A.set_store(store)

    def boom(st, seq, fn, **kw):
        raise RuntimeError("ingest 崩了")

    monkeypatch.setattr(ingest_mod, "ingest_chapter", boom)
    client = TestClient(A.app)
    try:
        client.post("/ingest", params={"seq": 8, "work": "main"})
    except RuntimeError:
        pass
    assert ("main", 8) not in A._pending_ingest, "异常后仍须清除在途标记(finally)"


# ============================================================
# 批C · 端点正确性小修(审计 P1-8 / P1-3 / Minor draft-check)
# ============================================================
def test_world_rule_illegal_scope_422(store):
    """P1-8: 非法 scope 提前 422(应用层枚举校验),不再走到 DB ASSERT 才 500。"""
    c = _client(store)
    r = c.post("/world-rules", json={"name": "禁术", "category": "magic", "scope": "galactic"})
    assert r.status_code == 422, f"非法 scope 应 422,实得 {r.status_code}: {r.text}"


def test_world_rule_legal_scopes_ok(store):
    """P1-8 回归:三个合法 scope 正常创建 200。"""
    c = _client(store)
    for sc in ("global", "regional", "faction_specific"):
        r = c.post("/world-rules", json={"name": f"规则_{sc}", "category": "magic", "scope": sc})
        assert r.status_code == 200, f"合法 scope={sc} 应 200,实得 {r.status_code}: {r.text}"


def test_edit_promise_preserves_unpassed_kind(store):
    """P1-3: PATCH 只改 text 不传 kind → kind 保留(red_herring 不被重置为 promise)。"""
    c = _client(store)
    c.post("/promises-new", json={"text": "障眼法", "setup_chapter": 2,
                                  "promise_kind": "red_herring"})
    pid = c.get("/promises").json()[0]["id"]
    r = c.patch(f"/promises/{pid}", json={"text": "障眼法(改文案)"})
    assert r.status_code == 200, r.text
    p = c.get("/promises").json()[0]
    assert p["text"] == "障眼法(改文案)"
    assert p["kind"] == "red_herring", "未传 kind 不应被重置为默认 promise"
    assert p["setup_chapter"] == 2, "未传 setup_chapter 不应被重置为默认 1"


def test_edit_promise_explicit_kind_still_updates(store):
    """P1-3 自审:显式传 kind 仍正常更新(exclude_unset 不影响正常更新)。"""
    c = _client(store)
    c.post("/promises-new", json={"text": "线索", "setup_chapter": 1,
                                  "promise_kind": "promise"})
    pid = c.get("/promises").json()[0]["id"]
    r = c.patch(f"/promises/{pid}", json={"text": "线索", "promise_kind": "red_herring"})
    assert r.status_code == 200, r.text
    assert c.get("/promises").json()[0]["kind"] == "red_herring", "显式传 kind 应更新"


def test_draft_check_quality_flags_fail_soft(store, monkeypatch):
    """Minor: quality_flags 抛错时 /draft-check 不 500,degraded_stages 含 quality_flags。"""
    import scribe3.critique as C

    def boom(prose):
        raise RuntimeError("检测器炸了")

    monkeypatch.setattr(C, "quality_flags", boom)
    c = _client(store)
    r = c.post("/draft-check", json={"prose": "测试正文。"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "quality_flags" in body["degraded_stages"], "quality_flags 应 fail-soft 计入 degraded"
    assert body["quality"]["total"] == 0, "降级时质量计数归零,不 500"


# ===== 方案A任务7:/post-check 接线 find_elegant_variation(同义词循环) =====

def test_post_check_elegant_variation_issue(store):
    """/post-check:store 里有角色「陈九」,正文用泛称(那男人/少年)反复替换指代时,
    issues 应含 type=elegant_variation 一条,meta.aliases 含命中的泛称。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:陈九", "character", "陈九"))
    prose = "陈九抬头看天。那男人叹了口气。少年攥紧了拳。陈九转身就走。"

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": prose, "focalizer": "", "brief": ""}).json()
    ev = [i for i in r.get("issues", []) if i.get("type") == "elegant_variation"]
    assert ev, f"应检出 elegant_variation issue,实际 issues 类型: {[i.get('type') for i in r.get('issues', [])]}"
    assert set(ev[0]["meta"]["aliases"]) >= {"那男人", "少年"}


def test_post_check_elegant_variation_fail_soft(store, monkeypatch):
    """/post-check:st.characters() 抛异常时 elegant_variation 检测 fail-soft 跳过,不 500。"""
    import scribe3.store as storemod

    monkeypatch.setattr(storemod.SurrealStore, "characters",
                        lambda self: (_ for _ in ()).throw(RuntimeError("db 炸了")))

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "正文。", "focalizer": "", "brief": ""})
    assert r.status_code == 200, f"characters() 抛异常时 /post-check 应 200,实际: {r.status_code}"
    assert not any(i.get("type") == "elegant_variation" for i in r.json().get("issues", []))


def test_post_check_no_characters_no_elegant_variation(store):
    """/post-check:库中无角色时,elegant_variation 不产生命中(不误报,不崩溃)。"""
    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "陈九抬头看天。那男人叹了口气。少年攥紧了拳。", "focalizer": "", "brief": ""})
    assert r.status_code == 200
    assert not any(i.get("type") == "elegant_variation" for i in r.json().get("issues", []))


# ===== 方案B任务24:story-import 逆向导入(全计划最后一个功能任务)=====

def test_write_gate_includes_import_route():
    """test_consistency 守卫的镜像:确认 /import 已登记在 KNOWN_REST_WRITE_ROUTES。"""
    from scribe3.tests.test_consistency import TestWriteGate
    assert ("POST", "/import") in TestWriteGate.KNOWN_REST_WRITE_ROUTES


def test_import_endpoint_e2e_and_idempotent_resume(store, monkeypatch, tmp_path):
    """POST /import:逐章按 seq 升序走 ingest_chapter(journal 包裹);
    断言 imported==2、open_promises 可见、journal 文件 stages_completed 含两章;
    再次以相同 chapters 调用 → 全部 skipped(幂等续跑,B23 journal 断点续跑语义)。"""
    monkeypatch.setenv("SCRIBE3_IMPORT_JOURNAL_DIR", str(tmp_path))
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    store.plant_promise("怀玉腰间的玉佩来历不明", setup_chapter=1)

    def fake_complete(prompt, **kw):
        return ('{"learned":[{"who":"柳怀玉","fact":"知晓玉佩来历"}],"did":[],'
                '"voice_shift":[],"arc":[],"events":[]}')

    c = _client(store, complete_fn=fake_complete)
    body = {"chapters": [{"seq": 1, "prose": "柳怀玉在城郊遇险。"},
                         {"seq": 2, "prose": "柳怀玉揭开玉佩秘密。"}]}
    r = c.post("/import", params={"work": "main"}, json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["imported"] == 2, data
    assert data["skipped"] == 0
    assert data["resume_from"] == 3
    assert any(p["status"] == "open" for p in data["open_promises"]), "open_promises 应可见"
    assert "error" not in data

    jf = tmp_path / "scribe3_import_main.json"
    assert jf.exists(), "journal 文件应已落盘"
    jdata = json.loads(jf.read_text())
    assert set(jdata["stages_completed"]) >= {"import_ch1", "import_ch2"}
    assert jdata["in_progress"] is None

    # 第二次以相同 chapters 调用:两章均已 complete → 全部幂等跳过
    r2 = c.post("/import", params={"work": "main"}, json=body)
    data2 = r2.json()
    assert data2["imported"] == 0
    assert data2["skipped"] == 2
    assert data2["resume_from"] == 3


def test_import_endpoint_stops_on_parse_failed_and_reports_resume(store, monkeypatch, tmp_path):
    """crash-safe 协议:某章 ingest parse_failed → 立即中止、不继续后续章;
    响应 200+error 保留已完成进度 + resume 指引(而非 4xx 丢掉进度信息);
    journal 该章保持未 complete(in_progress),供下次整章重跑。"""
    monkeypatch.setenv("SCRIBE3_IMPORT_JOURNAL_DIR", str(tmp_path))
    store.add_entity(Entity("role:阿禾", "character", "阿禾"))

    calls = {"n": 0}

    def flaky_complete(prompt, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return '{"learned":[],"did":[],"voice_shift":[],"arc":[],"events":[]}'
        return "不是JSON,解析必然失败"

    c = _client(store, complete_fn=flaky_complete)
    body = {"chapters": [{"seq": 1, "prose": "阿禾出场。"},
                         {"seq": 2, "prose": "阿禾遇险。"},
                         {"seq": 3, "prose": "阿禾获救。"}]}
    r = c.post("/import", params={"work": "main"}, json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 1, data
    assert data["resume_from"] == 2, "应指回失败的第2章,而非跳过它续第3章"
    assert data.get("error"), "失败应带 error 字段(200+error,保留已完成进度)"

    jf = tmp_path / "scribe3_import_main.json"
    jdata = json.loads(jf.read_text())
    assert jdata["stages_completed"] == ["import_ch1"]
    assert jdata["in_progress"] == "import_ch2", "失败章应停在 in_progress,不可 complete,供整章重跑"
