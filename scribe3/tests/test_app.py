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
    """Fix 1: intent 设置 overdue_threshold 时覆盖默认 OVERDUE_SLACK。"""
    import scribe3.app as A
    # 设置 intent.overdue_threshold = 10(宽松)
    store.set_intent({"reader_feeling": "", "emotional_arc": "", "red_lines": "",
                      "overdue_threshold": 10})
    store.plant_promise("宽松伏笔", setup_chapter=1, kind="promise")
    # max_chapter = 1+3+1 = 5,远小于 threshold=10 → 不应超期
    store.add_event(Event("ev:ov2", "action", story_time=5))
    c = _client(store)
    q = c.get("/quality").json()
    proms = q["foreshadow"].get("promises", [])
    p = next((x for x in proms if "宽松" in x.get("text", "")), None)
    assert p is not None
    assert p["overdue"] is False, f"threshold=10 时 max_ch=5 不应超期: {p}"


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


def test_post_check_leaks_detected(store):
    """/post-check:有 focalizer 且散文含泄露时,leaks 非空。"""
    luanshi_leak_world(store)

    def fake_complete(prompt, **kw):
        return '{"ok": true, "violations": [], "cut_after": ""}'

    c = _client(store, complete_fn=fake_complete)
    r = c.post("/post-check", params={"seq": 1},
               json={"prose": "老道看见焦三在治眼。", "focalizer": "role:老道"}).json()
    assert len(r["leaks"]) > 0, "老道写出治眼应被检出泄露"


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

    def fake_stream(msg, instructions, expect_proposal=False):
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

    def fake_stream(msg, instructions, expect_proposal=False):
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
