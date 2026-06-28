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


# ===== S5 TDD: soak seed_words 进写作 prompt(无 LLM,传入才注入) =====

def test_soak_block_injects_seed_words_when_provided(store, monkeypatch):
    """_soak_block:request 传入 seed_words 时,instructions 应含种子词。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False):
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

    def fake_stream(msg, instructions, expect_proposal=False):
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

    def fake_stream(msg, instructions, expect_proposal=False):
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

    def fake_stream(msg, instructions, expect_proposal=False):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store).get("/chat/write", params={"msg": "续写第一章", "chapter": 1})
    instr = captured.get("instructions", "")
    assert "PROPOSAL" in instr, "instructions 应含 PROPOSAL 围栏提醒"
    assert "乱世铜炉" in instr, "instructions 应含乱世铜炉文风提醒"
    # 强化:提醒须在末尾(最后 200 字内)
    tail = instr[-200:]
    assert "PROPOSAL" in tail, "PROPOSAL 提醒应出现在 instructions 末尾 200 字内"
    assert "乱世铜炉" in tail, "乱世铜炉提醒应出现在 instructions 末尾 200 字内"


def test_final_reminder_in_post_chat_write(store, monkeypatch):
    """S7 Trim 2: POST /chat/write 组装的 instructions 末尾同样含 ⟦PROPOSAL⟧ + 乱世铜炉 提醒。"""
    import scribe3.app as appmod
    captured = {}

    def fake_stream(msg, instructions, expect_proposal=False):
        captured["instructions"] = instructions
        return iter([])

    monkeypatch.setattr(appmod, "_stream_write", fake_stream)
    _client(store).post("/chat/write", json={"msg": "帮我续写第一章", "chapter": 1})
    instr = captured.get("instructions", "")
    assert "PROPOSAL" in instr, "POST instructions 应含 PROPOSAL 围栏提醒"
    assert "乱世铜炉" in instr, "POST instructions 应含乱世铜炉文风提醒"
    tail = instr[-200:]
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
    """audit:payoff<setup(闭无开 deus ex machina)应被抓出,balanced=False。"""
    store.plant_promise("异常伏笔", setup_chapter=9, kind="promise")
    bad_pid = next(p["id"] for p in store.list_promises() if "异常" in p["text"])
    # 回收于第 3 章(< setup 9)——逻辑上凭空 payoff
    store.advance_promise(bad_pid, 3)
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


def test_patch_chapter_not_found(store):
    """PATCH /chapters/{seq} 章不存在 → 404。"""
    c = _client(store)
    r = c.patch("/chapters/9999", json={"synopsis": "不存在"})
    assert r.status_code == 404


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
    assert ("POST", "/chapters/reorder") in known
    assert ("PATCH", "/chapters/{seq}") in known
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
