"""S0/S1 · SurrealStore TDD —— 证限知范式在【真库 NS=scribe3】上照样成立。

纵切片的 knowledge.project_frame 不改一行,直接跑在
SurrealStore 上(鸭子兼容)。老道帧仍排除焦三私密 → 范式不依赖存储后端。
"""
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge
from scribe3.scenario import luanshi_leak_world
from scribe3.knowledge import project_frame
from scribe3.verify import causal_complete


def test_schema_and_entity_roundtrip(store):
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    assert store.entity("role:焦三").name == "焦三"


def test_fact_roundtrip_and_secret(store):
    store.add_entity(Entity("place:乱岗", "place", "乱葬岗"))
    store.add_fact(Fact("fact:治眼", "role:焦三", "私密动机", "攒钱给老娘治眼",
                        valid_from=1, secret=True, leak_markers=["治眼"]))
    store.add_fact(Fact("fact:雨", "place:乱岗", "天气", "暴雨", valid_from=1))
    assert {f.id for f in store.facts_at(1)} == {"fact:治眼", "fact:雨"}
    assert store.fact("fact:治眼").secret is True
    assert store.fact("fact:治眼").leak_markers == ["治眼"]


def test_knowledge_edge_roundtrip(store):
    store.add_entity(Entity("role:焦三", "character", "焦三"))
    store.add_fact(Fact("fact:治眼", "role:焦三", "私密动机", "攒钱给老娘治眼", valid_from=1, secret=True))
    store.add_knowledge(KnowledgeEdge("role:焦三", "fact:治眼", since_chapter=1, acquired_via="given"))
    edges = store.knowledge
    assert any(e.knower_id == "role:焦三" and e.proposition_id == "fact:治眼" for e in edges)


def test_persisted_paradigm_holds(store):
    """范式证明(真库):老道帧排除焦三私密"""
    luanshi_leak_world(store)                      # canonical 场景落到 NS=scribe3
    laodao = project_frame(store, "role:老道", 1)
    assert not laodao.knows("fact:治眼"), "老道不该知道焦三私密动机"
    assert laodao.knows("fact:雨"), "公开事实老道应知道"
    assert project_frame(store, "role:焦三", 1).knows("fact:治眼"), "焦三知道自己的动机"


def test_causal_complete_runs_against_store(store):
    """回归:causal_complete 须能跑在 SurrealStore 上(agentic 冒烟揪出的 .events bug)。"""
    assert causal_complete(store, 1) == [], "空库无事件→无违规"
    store.add_event(Event("ev:逃", "逃", story_time=1))   # 无 motivated_by_goal
    assert any(v.event_id == "ev:逃" for v in causal_complete(store, 1)), "应flag缺目标"


def test_chapter_version_table_exists(store):
    # 迁移已在 store 夹具的 apply_schema 中跑过;直接 CREATE 应成功
    store._execute_write(
        "CREATE chapter_version SET seq=1, prose='初稿', label='测试', "
        "kind='checkpoint', qc={}, created_at=time::now()", {})
    rows = store._query("SELECT seq, label, kind FROM chapter_version WHERE seq=1")
    assert rows and rows[0]["label"] == "测试" and rows[0]["kind"] == "checkpoint"


def test_chapter_version_crud(store):
    vid = store.add_chapter_version(2, "正文A", label="重写结尾前",
                                    kind="checkpoint", qc={"repetition": 3})
    assert isinstance(vid, str) and vid
    store.add_chapter_version(2, "正文B", label="定稿", kind="final", qc={})
    lst = store.list_chapter_versions(2)
    assert len(lst) == 2
    assert lst[0]["label"] == "定稿"          # created_at DESC,最新在前
    assert "prose" not in lst[0]               # 列表不回传全文(省带宽)
    one = store.get_chapter_version(vid)
    assert one["prose"] == "正文A" and one["qc"]["repetition"] == 3


def test_chapter_version_kind_default_applies(store):
    # 迁移守卫:SCHEMAFULL 的 DEFAULT 只有在 032 迁移真正落库时才生效。
    # 直接 CREATE 不带 kind → 应默认 'checkpoint'(若表是 schemaless 自动建的则不会有默认值)。
    store._execute_write("CREATE chapter_version SET seq=9, prose='x', created_at=time::now()", {})
    rows = store._query("SELECT kind FROM chapter_version WHERE seq=9")
    assert rows and rows[0]["kind"] == "checkpoint"


def test_add_voice_flag_sets_trigger_chapter(store):
    # 回归:add_voice_flag 必须显式写入 trigger_chapter,否则旧库(必填 int)ingest 崩。
    store.add_voice_flag("role:甲", 7, "声音突变")
    rows = store._query("SELECT character, trigger_chapter, reason FROM voice_evolution_flag")
    assert rows and rows[0]["trigger_chapter"] == 7
    flags = store.list_voice_flags("open")
    assert any(f["reason"] == "声音突变" for f in flags)


def test_graph_recall_returns_secret_flag(store):
    luanshi_leak_world(store)
    # graph_recall 依赖向量索引;luanshi_leak_world 内 add_fact 现已自动建 embedding,
    # 此处显式调用 semantic_index 保持幂等(覆盖写等价,不影响正确性)
    store.semantic_index("fact:治眼", "攒钱给老娘治眼")
    store.semantic_index("fact:雨", "暴雨")
    res = store.graph_recall("治眼", 9999, k=5)
    assert res, "应召回到结果"
    # graph_recall 返回的 dict 列表中每一项必须含 secret 字段
    for item in res:
        assert isinstance(item, dict), f"graph_recall 每项应为 dict,实为: {type(item)}"
        assert "secret" in item, f"graph_recall 返回项缺少 secret 字段: {item}"
    # 召回中应包含 fact:治眼(secret=True)
    secret_items = [item for item in res if item.get("secret") is True]
    assert secret_items, "应有至少一条 secret=True 的召回命题(fact:治眼)"


# --- P0 Task 7: 设定 CRUD 幂等(add_* 同名覆盖)---

def test_add_faction_idempotent_by_name(store):
    store.add_faction("青叶门", ideology="复辟", leader="甲")
    store.add_faction("青叶门", ideology="改良", leader="乙")  # 同名再写=覆盖
    facs = [f for f in store.list_factions() if f.get("name") == "青叶门"]
    assert len(facs) == 1, f"同名应只剩一行,实际 {len(facs)}"
    assert facs[0].get("ideology") == "改良"  # 取最新值


def test_add_world_rule_idempotent_by_name(store):
    store.add_world_rule("断契", category="magic", source="a")
    store.add_world_rule("断契", category="social", source="b")
    rs = [r for r in store.list_world_rules() if r.get("name") == "断契"]
    assert len(rs) == 1 and rs[0].get("category") == "social"


def test_add_item_idempotent_by_name(store):
    store.add_item("镇煞钉", category="法器")
    store.add_item("镇煞钉", category="凶器")
    its = [i for i in store.list_items() if i.get("name") == "镇煞钉"]
    assert len(its) == 1 and its[0].get("category") == "凶器"


def test_graph_includes_relation_edges(store):
    """graph() 应把 character_relation 边也纳入,端点带 role: 前缀对齐节点 id。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_character_relation("role:甲", "role:乙", "ally", since_chapter=1)
    g = store.graph(5)
    rel = [e for e in g["edges"] if e.get("rel") == "ally"]
    assert rel, f"应含 ally 关系边: {g['edges']}"
    assert rel[0]["src"] == "role:甲" and rel[0]["dst"] == "role:乙", \
        f"端点应带 role: 前缀对齐节点 id: {rel[0]}"
    # 每条边都有 rel 键(knows 边也应该有)
    assert all("rel" in e for e in g["edges"])


def test_add_term_idempotent_by_name(store):
    store.add_term("镇煞", category="术语")
    store.add_term("镇煞", category="法术")
    ts = [t for t in store.list_terms() if t.get("name") == "镇煞"]
    assert len(ts) == 1 and ts[0].get("category") == "法术"


# --- P1 Task 3: add_fact 写入后自动建 embedding ---

def test_add_fact_is_semantically_recallable(store):
    """P1 回归:store.add_fact 写入后命题应可被 semantic_recall 召回。
    修复前:add_fact 不建 embedding → semantic_recall 永远找不到该命题。
    修复后:add_fact 内部调用 semantic_index → REST/ingest 路径与 MCP s3_add_fact 对齐。
    """
    store.add_fact(Fact("fact:t1", "role:甲", "获知", "焦三在乱葬岗埋了一坛酒", valid_from=1))
    hits = store.semantic_recall("乱葬岗 酒", k=5)
    assert any(getattr(f, "id", None) == "fact:t1" for f in hits), \
        "新命题应可被语义召回(add_fact 须自动调 semantic_index)"


# --- P2 F2: char_state after_state 接通 ---

def test_char_state_after_state_snapshot(store):
    """P2 F2:store 层 after_state 应进入 char_state_at 快照。
    修复前:写路径不传 after_state → char_state_at abilities/relations/personality 恒空。
    修复后:add_char_state 接收并持久化 after_state → char_state_at 正确聚合快照。
    """
    store.add_char_state(character_id="role:甲", chapter=3, change_type="ability",
                         summary="习得御剑",
                         after_state={"ability_snapshot": {"御剑": "初成"}})
    snap = store.char_state_at("role:甲", 5)
    assert snap and snap.get("abilities"), f"快照 abilities 应非空: {snap}"
    assert "御剑" in str(snap["abilities"]), f"快照应含 after_state 中的御剑: {snap}"


# --- P1-b Bug C3#3: max_chapter 读 story_chapter 真源 ---

def test_max_chapter_reads_story_chapter(store):
    """P1-b + P3-e2 回归:max_chapter 读 story_chapter(唯一真源,valid_from 退场方已删)。
    验证直接写入 story_chapter=17 的事件能被 max_chapter 正确识别。
    """
    # 通过 add_event 正常路径写一个章号较小的事件
    store.add_event(Event("ev:普通事件", "普通", story_time=5))
    assert store.max_chapter() == 5

    # 直接写入 story_chapter=17 的事件(模拟外部/ingest 写入路径)
    store._execute_write(
        "CREATE type::record('event', 'only_story_ch') SET event_type='ingest写入', "
        "story_chapter=17, motivated_by_goal=NONE, location=NONE, preconditions=[]",
        {})

    result = store.max_chapter()
    assert result >= 17, (
        f"max_chapter 应 >= 17(story_chapter=17 的事件),实际: {result}。"
    )


def test_char_state_after_state_relation_snapshot(store):
    """P2 F2 补充:relation 类型 after_state 应进入 relations 快照。"""
    store.add_char_state(character_id="role:乙", chapter=2, change_type="relation",
                         summary="结盟白鹤堂",
                         after_state={"relation_snapshot": {"白鹤堂": "盟友"}})
    snap = store.char_state_at("role:乙", 4)
    assert "白鹤堂" in str(snap.get("relations") or ""), f"relations 快照应含白鹤堂: {snap}"


def test_char_state_after_state_personality_snapshot(store):
    """P2 F2 补充:personality 类型 after_state 应进入 personality 快照。"""
    store.add_char_state(character_id="role:丙", chapter=1, change_type="personality",
                         summary="心境转变",
                         after_state={"personality_snapshot": "冷峻内敛"})
    snap = store.char_state_at("role:丙", 3)
    assert snap.get("personality") == "冷峻内敛", f"personality 快照应为冷峻内敛: {snap}"


def test_schema_cleanup_034_removes_dead_artifacts(store):
    # word_stats 视图已删(023 遗留)
    db_info = store._query("INFO FOR DB")  # 返回 dict
    tables = (db_info.get("tables") if isinstance(db_info, dict) else {}) or {}
    assert "word_stats" not in tables, f"word_stats 视图应已删除: {list(tables)[:20]}"
    # character.traits / motivation 孤儿列已删(027,与 Entity.traits 撞车)
    tbl = store._query("INFO FOR TABLE character")  # 返回 dict
    fields = (tbl.get("fields") if isinstance(tbl, dict) else {}) or {}
    assert "traits" not in fields, f"character.traits 应已删除: {list(fields)}"
    assert "motivation" not in fields, f"character.motivation 应已删除: {list(fields)}"


# --- P1-c: 双时态右端——supersede / forget / certainty ---

def test_supersede_fact_closes_prior(store):
    """supersede_fact 须关闭旧命题右端,旧值在关闭章前有效、关闭章后失效。"""
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:o", "role:甲", "状态", "重伤", valid_from=1))
    store.supersede_fact("role:甲", "状态", "痊愈", since_chapter=5)
    # 第3章仍在 valid_to(=5) 之前,应看到重伤
    at3 = {f.value for f in store.facts_at(3)}
    assert "重伤" in at3, f"第3章应仍有重伤(prior 尚未关闭): {at3}"
    # 第7章超过 valid_to,旧值应消失、新值出现
    at7 = {f.value for f in store.facts_at(7)}
    assert "痊愈" in at7, f"第7章应有痊愈(新命题 valid_from=5): {at7}"
    assert "重伤" not in at7, f"第7章重伤应已超越失效: {at7}"


def test_forget_knowledge_closes_edge(store):
    """forget_knowledge 须令 until_chapter 生效:该章前知道、该章及以后不知道。"""
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:f1", "role:乙", "秘密", "藏宝", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:乙", "fact:f1", since_chapter=1, acquired_via="given"))
    # 尚未 forget:第3章应知道
    from scribe3.knowledge import project_frame
    assert project_frame(store, "role:乙", 3).knows("fact:f1"), "forget 前第3章应知道"
    # 设置遗忘:第5章起忘记
    store.forget_knowledge("role:乙", "fact:f1", until_chapter=5)
    # 第3章仍在 until_chapter 之前,应还知道
    assert project_frame(store, "role:乙", 3).knows("fact:f1"), "forget 后第3章(仍在有效期内)应知道"
    # 第5章起不知道(until_chapter=5 → chapter >= 5 时 until_chapter > chapter 不满足)
    assert not project_frame(store, "role:乙", 5).knows("fact:f1"), "第5章起应已忘记"
    assert not project_frame(store, "role:乙", 7).knows("fact:f1"), "第7章应已忘记"


def test_knows_certainty_roundtrips(store):
    """add_knowledge 写入 certainty=0.5,load_knowledge 读回时 certainty 应与写入值一致。"""
    store.add_entity(Entity("role:丙", "character", "丙"))
    store.add_fact(Fact("fact:k", "role:丙", "x", "v", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:丙", "fact:k", since_chapter=1,
                                      acquired_via="told", certainty=0.5))
    edges = store.load_knowledge()
    matched = [e for e in edges if e.knower_id == "role:丙" and e.proposition_id == "fact:k"]
    assert matched, "应能找到新建的知识边"
    assert abs(matched[0].certainty - 0.5) < 1e-6, \
        f"certainty 应约等于 0.5,实际: {matched[0].certainty}"


# --- P2-D1: affects_voice 自动触发声音演变 flag ---

def test_affects_voice_triggers_flag(store):
    """affects_voice=True 的 char_state 应自动创建 voice_evolution_flag。"""
    store.add_char_state(character_id="role:甲", chapter=3, change_type="personality",
                         summary="由怯转狠", affects_voice=True)
    flags = store.list_voice_flags("open")
    assert any(f.get("character") == "role:甲" for f in flags), \
        f"affects_voice=True 应自动生成 flag: {flags}"


def test_affects_voice_false_no_flag(store):
    """affects_voice=False 不应创建 voice_evolution_flag。"""
    store.add_char_state(character_id="role:乙", chapter=3, change_type="ability",
                         summary="习剑", affects_voice=False)
    flags = store.list_voice_flags("open")
    assert not any(f.get("character") == "role:乙" for f in flags), \
        f"affects_voice=False 不应生成 flag: {flags}"


def test_affects_voice_none_no_flag(store):
    """affects_voice=None(默认)不应创建 voice_evolution_flag(不破坏旧调用)。"""
    store.add_char_state(character_id="role:丙", chapter=2, change_type="ability",
                         summary="习武")
    flags = store.list_voice_flags("open")
    assert not any(f.get("character") == "role:丙" for f in flags), \
        f"affects_voice=None 不应生成 flag: {flags}"


def test_resolve_voice_flag(store):
    """resolve_voice_flag 应将 flag 状态从 open 改为 done。"""
    store.add_voice_flag("role:甲", 5, "声调突变")
    flags_open = store.list_voice_flags("open")
    assert flags_open, "前置条件:应有 open flag"
    fid = flags_open[0]["id"]

    store.resolve_voice_flag(fid)

    open_after = store.list_voice_flags("open")
    done_after = store.list_voice_flags("done")
    assert not any(f["id"] == fid for f in open_after), "resolve 后 flag 不应在 open 列表"
    assert any(f["id"] == fid for f in done_after), "resolve 后 flag 应在 done 列表"


# ===== P3-b: knower 防悬挂边 =====

def test_add_knowledge_rejects_unknown_knower(store):
    """P3-b: add_knowledge 若 knower 不存在(非 reader)应拒绝,不创建悬挂边。
    修复前:只验证 proposition 端 → knower 不存在时静默写入,留下悬挂边。
    修复后:knower != 'reader' 时先用 entity() 检查,不存在则抛 ValueError。
    """
    import pytest
    store.add_fact(Fact("fact:p1", "role:甲", "属性", "值", valid_from=1))
    with pytest.raises((ValueError, Exception)):
        store.add_knowledge(KnowledgeEdge("role:不存在的人", "fact:p1", since_chapter=1))
    # 确认没有边被写入
    edges = store.load_knowledge()
    assert not any(
        e.knower_id == "role:不存在的人" and e.proposition_id == "fact:p1"
        for e in edges
    ), "拒绝后不应有悬挂边写入"


def test_add_knowledge_allows_reader_knower(store):
    """P3-b: knower='reader' 是虚拟 knower(无实体行),应被放行,不抛错。"""
    store.add_fact(Fact("fact:p2", "role:甲", "属性", "值", valid_from=1))
    # 不应抛错
    store.add_knowledge(KnowledgeEdge("reader", "fact:p2", since_chapter=1))
    edges = store.load_knowledge()
    assert any(
        e.knower_id == "reader" and e.proposition_id == "fact:p2"
        for e in edges
    ), "reader knower 应被写入 reader_knows"


def test_add_knowledge_allows_existing_knower(store):
    """P3-b: knower 实体存在时应正常写入 knows 边。"""
    store.add_entity(Entity("role:存在者", "character", "存在者"))
    store.add_fact(Fact("fact:p3", "role:存在者", "属性", "值", valid_from=1))
    # 不应抛错
    store.add_knowledge(KnowledgeEdge("role:存在者", "fact:p3", since_chapter=1))
    edges = store.load_knowledge()
    assert any(
        e.knower_id == "role:存在者" and e.proposition_id == "fact:p3"
        for e in edges
    ), "存在的 knower 应正常写入 knows 边"


def test_p3c_schema_cleanup(store):
    """P3-c: schema 清债验证
    - chapter 死列(qc_issues/qc_causal/qc_at) 已删除,qc_word_count 保留
    - place 027 死字段(geography/first_visit_chapter/political_affiliation/notable_events) 已删除
    - 设定表(faction/item/term/world_rule).name UNIQUE 索引已建(delete-before-create 幂等安全)
    """
    # --- chapter 字段检查 ---
    chap_info = store._query("INFO FOR TABLE chapter")
    # INFO FOR TABLE 返回一个 dict 或单元素 list 包含 dict
    if isinstance(chap_info, list):
        chap_info = chap_info[0] if chap_info else {}
    chap_fields = chap_info.get("fields", {})
    assert "qc_issues" not in chap_fields, "qc_issues 应已从 chapter 删除"
    assert "qc_causal" not in chap_fields, "qc_causal 应已从 chapter 删除"
    assert "qc_at" not in chap_fields, "qc_at 应已从 chapter 删除"
    assert "qc_word_count" in chap_fields, "qc_word_count 是 LIVE 字段,应保留"

    # --- place 字段检查 ---
    place_info = store._query("INFO FOR TABLE place")
    if isinstance(place_info, list):
        place_info = place_info[0] if place_info else {}
    place_fields = place_info.get("fields", {})
    assert "geography" not in place_fields, "geography 应已从 place 删除"
    assert "first_visit_chapter" not in place_fields, "first_visit_chapter 应已从 place 删除"
    assert "political_affiliation" not in place_fields, "political_affiliation 应已从 place 删除"
    assert "notable_events" not in place_fields, "notable_events 应已从 place 删除"

    # --- faction UNIQUE:同名两次仅保留最后一条(delete-before-create)---
    store.add_faction("唯一门", ideology="a")
    store.add_faction("唯一门", ideology="b")
    matches = [x for x in store.list_factions() if x["name"] == "唯一门"]
    assert len(matches) == 1, f"同名势力应只有1条,实际{len(matches)}条"
    assert matches[0]["ideology"] == "b", "第二次写入(ideology=b)应覆盖"


def test_event_table_lacks_dead_taxonomy_columns(store):
    """P3-f Fix2: 041_tail_cleanup 应从 event 表移除死列 event_category/event_subtype。
    这两列由 024_taxonomy.surql 引入,但无任何生产代码读写,属死 taxonomy。
    """
    # INFO FOR TABLE 直接返回 dict(不是 list)
    info = store._query("INFO FOR TABLE event")
    # SurrealDB 3.x: info 是 dict,fields 键的值是字段名→定义的 dict
    fields = info.get("fields", {}) if isinstance(info, dict) else {}
    assert "event_category" not in fields, \
        "event.event_category 应已被 041_tail_cleanup 移除"
    assert "event_subtype" not in fields, \
        "event.event_subtype 应已被 041_tail_cleanup 移除"


# --- S8: fold_voice_flags 半自动声音演变消化 ---

def test_fold_voice_flags_updates_profile_and_resolves(store):
    """S8 主流程:fold 把 open flag 折叠进 profile,并 resolve 所有已处理 flag。"""
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.set_voice_profile("role:甲", {"style_summary": "怯懦结巴"})
    # add_char_state with affects_voice=True 自动创建 open flag
    store.add_char_state(character_id="role:甲", chapter=5, change_type="personality",
                         summary="由怯转狠", affects_voice=True)
    # 确认 flag 已创建
    assert store.list_voice_flags("open"), "add_char_state(affects_voice=True) 应自动创建 open flag"

    def fake_complete(prompt):
        return '{"style_summary":"由怯转狠后,语气转冷硬决绝"}'

    res = store.fold_voice_flags("role:甲", fake_complete)
    assert res["folded"] >= 1, f"应有至少 1 条 flag 被折叠,实际: {res}"
    updated_profile = store.get_voice_profile("role:甲")
    assert updated_profile is not None, "fold 后 voice_profile 应存在"
    assert "冷硬" in updated_profile["style_summary"], \
        f"profile 应反映演变后声音,实际: {updated_profile['style_summary']}"
    # 所有 role:甲 的 flag 应已 resolve(不再出现在 open 列表)
    remaining = [f for f in store.list_voice_flags("open") if f.get("character") == "role:甲"]
    assert not remaining, f"fold 后 role:甲 的 open flag 应全部 resolve,仍有: {remaining}"


def test_fold_voice_flags_none_open(store):
    """S8 空路:无 open flag 时直接返回 {folded:0},不调 LLM。"""
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.set_voice_profile("role:乙", {"style_summary": "x"})
    called = {"n": 0}

    def fake_complete(prompt):
        called["n"] += 1
        return "{}"

    res = store.fold_voice_flags("role:乙", fake_complete)
    assert res["folded"] == 0, f"无 flag 应返回 folded=0,实际: {res}"
    assert called["n"] == 0, "无 flag 时不应调用 complete_fn"


def test_fold_voice_flags_degraded_on_bad_json(store):
    """S8 fail-soft:LLM 返回非法 JSON → degraded=True,profile 不被污染。"""
    store.add_entity(Entity("role:丙", "character", "丙"))
    store.set_voice_profile("role:丙", {"style_summary": "原样"})
    store.add_char_state(character_id="role:丙", chapter=2, change_type="personality",
                         summary="x", affects_voice=True)

    res = store.fold_voice_flags("role:丙", lambda p: "非法JSON")
    assert res.get("degraded") is True, f"坏 JSON 应返回 degraded=True,实际: {res}"
    # 现有 profile 不应被修改
    profile = store.get_voice_profile("role:丙")
    assert profile is not None, "profile 应仍然存在"
    assert profile["style_summary"] == "原样", \
        f"坏 JSON 时 profile 不应被修改,实际: {profile['style_summary']}"
