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
    - chapter 死列 qc_at 已删除,qc_word_count 保留
    - Phase0-BE1(047)起 qc_issues/qc_causal 复活为 LIVE 缓存列(save_chapter 真写,quality 真读),
      不再是死列——故此处断言它们【存在】(与 038 的删除相反,因审计后已赋予真实读写路径)。
    - place 027 死字段(geography/first_visit_chapter/political_affiliation/notable_events) 已删除
    - 设定表(faction/item/term/world_rule).name UNIQUE 索引已建(delete-before-create 幂等安全)
    """
    # --- chapter 字段检查 ---
    chap_info = store._query("INFO FOR TABLE chapter")
    # INFO FOR TABLE 返回一个 dict 或单元素 list 包含 dict
    if isinstance(chap_info, list):
        chap_info = chap_info[0] if chap_info else {}
    chap_fields = chap_info.get("fields", {})
    assert "qc_at" not in chap_fields, "qc_at 仍应为已删除的死列"
    assert "qc_word_count" in chap_fields, "qc_word_count 是 LIVE 字段,应保留"
    # 047 复活:qc_issues/qc_causal 现为 LIVE 缓存列,应存在
    assert "qc_issues" in chap_fields, "qc_issues 047 起为 LIVE 缓存列,应存在"
    assert "qc_causal" in chap_fields, "qc_causal 047 起为 LIVE 缓存列,应存在"
    assert "scene_count" in chap_fields, "scene_count 缓存列应存在"

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


# ── F-04 · 进度统计与码字激励 ────────────────────────────────────────────────

def test_daily_progress_table_exists(store):
    """迁移后 daily_progress 表存在且 SCHEMAFULL 字段正常写入。"""
    store._execute_write(
        "UPSERT type::record('daily_progress', '2026-01-01') SET "
        "date='2026-01-01', words_written=100, words_total=100, "
        "chapters_touched=[1], save_count=1, updated_at=time::now()", {})
    rows = store._query("SELECT date, words_written FROM daily_progress WHERE date='2026-01-01'")
    assert rows and rows[0]["words_written"] == 100


def test_save_chapter_records_daily_delta(store):
    """save_chapter 后 daily_progress 当日行正确累加。"""
    today = "2099-01-01"   # 固定日期避免与真实日混淆
    # 第一章 ~1000 字(用较长字符串,口径: len("".join(prose.split())))
    prose1 = "甲" * 1000
    store.save_chapter(1, prose1, title="一", _today=today)
    rows = store._query("SELECT words_written, words_total, save_count, chapters_touched "
                        "FROM daily_progress WHERE date=$d", {"d": today})
    assert rows, "save_chapter 后应有当日 daily_progress 行"
    r = rows[0]
    assert r["words_written"] == 1000, f"words_written={r['words_written']} 期望 1000"
    assert r["words_total"] == 1000
    assert r["save_count"] == 1
    assert 1 in r["chapters_touched"]

    # 同日再存第 2 章 800 字 → 累加
    prose2 = "乙" * 800
    store.save_chapter(2, prose2, title="二", _today=today)
    rows2 = store._query("SELECT words_written, words_total, save_count, chapters_touched "
                         "FROM daily_progress WHERE date=$d", {"d": today})
    r2 = rows2[0]
    assert r2["words_written"] == 1800, f"两章后 words_written={r2['words_written']} 期望 1800"
    assert r2["words_total"] == 1800
    assert r2["save_count"] == 2
    assert 1 in r2["chapters_touched"] and 2 in r2["chapters_touched"]


# ── P2-a TDD: 6 项后端清债 ────────────────────────────────────────────────────

def test_forget_knowledge_does_not_overwrite_closed_edge(store):
    """P2-a Fix2: forget_knowledge 仅更新开区间边——已闭合边(until_chapter 已设)不被覆写。"""
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:秘1", "role:甲", "秘密", "旧秘密", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:甲", "fact:秘1", since_chapter=1, until_chapter=5))
    # 原始已闭合 until_chapter=5,再次 forget 设 10 不应生效
    store.forget_knowledge("role:甲", "fact:秘1", 10)
    rows = store._query(
        "SELECT until_chapter FROM knows WHERE in=type::record('character','甲') "
        "AND out=type::record('proposition','秘1')")
    assert rows, "knows 边应存在"
    assert rows[0]["until_chapter"] == 5, \
        f"已闭合边(until_chapter=5)不应被 forget 覆写为 10,实际: {rows[0]['until_chapter']}"


def test_forget_knowledge_updates_open_edge(store):
    """P2-a Fix2(正向):开区间边 forget 后 until_chapter 正确写入。"""
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_fact(Fact("fact:秘2", "role:乙", "秘密", "新秘密", valid_from=1))
    store.add_knowledge(KnowledgeEdge("role:乙", "fact:秘2", since_chapter=1))  # until_chapter=None
    store.forget_knowledge("role:乙", "fact:秘2", 7)
    rows = store._query(
        "SELECT until_chapter FROM knows WHERE in=type::record('character','乙') "
        "AND out=type::record('proposition','秘2')")
    assert rows and rows[0]["until_chapter"] == 7, \
        f"开区间边 forget 后 until_chapter 应为 7,实际: {rows}"


def test_purge_ingest_clears_unverified(store):
    """P2-a Fix5: 重 ingest 后 purge_ingest 清除本章 ingest_unverified,不累积 pending。"""
    store.add_unverified_ref("路过甲", 3, "saw")
    store.add_unverified_ref("路过乙", 3, "heard")
    # 确认已登记
    rows_before = store._query("SELECT * FROM ingest_unverified WHERE seq=3")
    assert len(rows_before) == 2, f"purge 前应有 2 条,实际: {len(rows_before)}"
    # 再次 ingest 前先 purge
    store.purge_ingest(3)
    rows_after = store._query("SELECT * FROM ingest_unverified WHERE seq=3")
    assert len(rows_after) == 0, \
        f"purge_ingest 后本章 ingest_unverified 应清零,实际: {len(rows_after)}"


def test_purge_ingest_unverified_no_cross_chapter_leak(store):
    """P2-a Fix5(隔离):purge_ingest(seq=3) 不删除其他章的 ingest_unverified。"""
    store.add_unverified_ref("路过丙", 3, "saw")
    store.add_unverified_ref("路过丁", 5, "told")
    store.purge_ingest(3)
    rows_ch5 = store._query("SELECT * FROM ingest_unverified WHERE seq=5")
    assert len(rows_ch5) == 1, \
        f"purge_ingest(seq=3) 不应删除 seq=5 的 unverified,实际: {len(rows_ch5)}"


def test_reorder_chapters_large_volume_no_collision(store):
    """P2-a Fix4: 卷基址 *100000(原 *1000)→ 相邻卷的 sort_order 区间不相交,
    单卷支持至多 10万章而不跨卷撞号。

    旧 *1000 下:卷一(sort_order=1)基址 1000,满 1001 章占 1000..2000,正好撞上
    卷二(sort_order=2)基址 2000 → 撞号。新 *100000 把每卷可容纳量抬到 10万,
    realistic 章数下相邻卷区间恒不相交。此处用 2 卷各 2 章验区间与基址即可证明机制。
    """
    v1 = store.add_volume("卷一", sort_order=1)
    v2 = store.add_volume("卷二", sort_order=2)
    store.save_chapter(1, "甲", title="一·1")
    store.save_chapter(2, "乙", title="一·2")
    store.save_chapter(3, "丙", title="二·1")
    store.save_chapter(4, "丁", title="二·2")
    store.reorder_chapters(v1, [1, 2])
    store.reorder_chapters(v2, [3, 4])
    rows = store._query("SELECT seq, sort_order FROM chapter ORDER BY sort_order")
    by_seq = {r["seq"]: r["sort_order"] for r in rows}
    # 卷一基址 1*100000=100000;卷二基址 2*100000=200000
    assert by_seq[1] == 100000 and by_seq[2] == 100001, f"卷一 sort_order 应为 100000/100001: {by_seq}"
    assert by_seq[3] == 200000 and by_seq[4] == 200001, f"卷二 sort_order 应为 200000/200001: {by_seq}"
    # 全局唯一 + 卷一最大 < 卷二基址(区间不相交,即便卷一有近 10万章也不撞卷二)
    orders = list(by_seq.values())
    assert len(orders) == len(set(orders)), f"sort_order 应全局唯一: {orders}"
    assert max(by_seq[1], by_seq[2]) < 200000, "卷一区间须落在卷二基址之下(不撞号)"


def test_daily_progress_no_negative_delta(store):
    """把某章改短 → 当日 words_written 不应被倒扣(max(0,delta))。
    第一次 save:+1000(全书从 0 增至 1000) → words_written=1000
    第二次 save(改短至 600):delta=600-1000=-400 → max(0,-400)=0,不倒扣
    words_written 应仍为 1000,不为负,不为 600。
    words_total 快照如实更新为 600(不受影响)。
    """
    today = "2099-01-02"
    store.save_chapter(1, "甲" * 1000, title="一", _today=today)
    rows_after_first = store._query(
        "SELECT words_written, words_total FROM daily_progress WHERE date=$d", {"d": today})
    assert rows_after_first[0]["words_written"] > 0, "第一次 save 后 words_written 应 > 0"

    # 改短为 600 字(全书总字数缩水)
    store.save_chapter(1, "甲" * 600, title="一", _today=today)
    rows = store._query(
        "SELECT words_written, words_total FROM daily_progress WHERE date=$d", {"d": today})
    ww = rows[0]["words_written"]
    wt = rows[0]["words_total"]
    # 核心断言:缩写不倒扣,当日累计写入量不降、不为负
    assert ww >= 0, f"words_written 不应为负,实际={ww}"
    assert ww >= rows_after_first[0]["words_written"], (
        f"缩写后 words_written 不应减少:before={rows_after_first[0]['words_written']}, after={ww}")
    # words_total 快照应如实反映当前全书总字数(可缩)
    assert wt < rows_after_first[0]["words_total"], (
        f"改短后 words_total 快照应减少,实际 before={rows_after_first[0]['words_total']}, after={wt}")


def test_record_daily_progress_failsoft(store, monkeypatch):
    """记账内部异常时 save_chapter 主写仍成功落库(fail-soft)。"""
    original = store._record_daily_progress

    def boom(*args, **kwargs):
        raise RuntimeError("模拟记账炸了")

    monkeypatch.setattr(store, "_record_daily_progress", boom)
    # 即使记账方法炸了,章节仍应成功落库
    store.save_chapter(1, "正文内容", title="测")
    ch = store.get_chapter(1)
    assert ch is not None and ch.get("prose") == "正文内容", \
        "记账异常不应阻断 save_chapter"


def test_intent_word_goals_roundtrip(store):
    """set_intent 写入 total_word_goal/daily_word_goal 后 get_intent 回读一致。"""
    store.set_intent({"reader_feeling": "沉浸", "total_word_goal": 100000, "daily_word_goal": 2000})
    got = store.get_intent()
    assert got["total_word_goal"] == 100000
    assert got["daily_word_goal"] == 2000

    # 不设时键不存在不报错
    store.set_intent({"reader_feeling": "平静"})
    got2 = store.get_intent()
    assert "total_word_goal" not in got2 or got2.get("total_word_goal") is None


def test_progress_returns_correct_structure(store):
    """progress() 返回结构含必要键,且 total_words 与 stats 一致。"""
    today = "2099-01-03"
    store.save_chapter(1, "甲" * 500, title="一", _today=today)
    p = store.progress(today=today)
    assert "today" in p and "total_words" in p and "daily" in p
    assert p["total_words"] == store.stats()["word_count"], "total_words 口径须与 stats 一致"
    assert len(p["daily"]) >= 1
    assert p["daily"][0]["words"] == 500


def test_progress_streak(store):
    """两天连续达标 → current_streak=2;断一天后 → current=0 from today。"""
    from scribe3.store import _compute_streaks
    rows = [
        {"date": "2099-02-01", "words_written": 1000},
        {"date": "2099-02-02", "words_written": 1000},
        # 2099-02-03 缺失(断)
        {"date": "2099-02-04", "words_written": 1000},
    ]
    cur, longest = _compute_streaks(rows, "2099-02-04", daily_goal=None)
    assert cur == 1, f"断后 current_streak 应=1,实际={cur}"
    assert longest == 2, f"最长连续段应=2,实际={longest}"

    # 今天还没写(today=2099-02-05),从昨天算
    cur2, _ = _compute_streaks(rows, "2099-02-05", daily_goal=None)
    assert cur2 == 1, "today 无写入时从前一天起算"

    # daily_goal=2000,某天 1000 不达标 → 不计入 streak
    cur3, long3 = _compute_streaks(rows, "2099-02-04", daily_goal=2000)
    assert cur3 == 0 and long3 == 0, "低于 daily_goal 不达标"


# ── 完整期:window + weekday_histogram + 理想线 ──────────────────────────────

def test_progress_window_filters_daily(store):
    """progress(window='30') 仅返回近30天的 daily 序列;heatmap 不受影响。"""
    # 写两天数据:一条远在100天前,一条3天前
    far_day = "2099-03-01"
    near_day = "2099-07-10"
    today = "2099-07-12"
    store.save_chapter(1, "甲" * 500, title="一", _today=far_day)
    store.save_chapter(2, "乙" * 300, title="二", _today=near_day)
    # window=30:只返回 near_day(3天前),不含 far_day(超出30天)
    p30 = store.progress(today=today, window="30")
    assert p30["window"] == "30"
    dates_30 = [r["date"] for r in p30["daily"]]
    assert far_day not in dates_30, f"window=30 不应含 {far_day}"
    assert near_day in dates_30, f"window=30 应含 {near_day}"
    # heatmap 须含两条(全量)
    heatmap_dates = [r["date"] for r in p30["heatmap"]]
    assert far_day in heatmap_dates, "heatmap 应含全量数据(不受 window 影响)"


def test_progress_window_all(store):
    """progress(window='all') 与不传 window 等价,返回全量 daily。"""
    today = "2099-04-05"
    store.save_chapter(1, "甲" * 400, title="一", _today="2099-01-01")
    store.save_chapter(2, "乙" * 400, title="二", _today=today)
    p_all = store.progress(today=today, window="all")
    p_none = store.progress(today=today)
    assert len(p_all["daily"]) == len(p_none["daily"]), "window=all 与默认等价"
    assert p_all["window"] == "all"


def test_progress_weekday_histogram(store):
    """progress() 返回 weekday_histogram 含7个槽 + best_weekday。
    2099-05-04=周一(weekday=0), 2099-05-05=周二(weekday=1)。"""
    today = "2099-05-07"
    # 写周一(5-04)和周二(5-05)
    store.save_chapter(1, "甲" * 1000, title="一", _today="2099-05-04")  # 周一(weekday=0)
    store.save_chapter(2, "乙" * 600,  title="二", _today="2099-05-05")  # 周二(weekday=1)
    p = store.progress(today=today)
    hist = p.get("weekday_histogram")
    assert hist is not None and len(hist) == 7, f"应有7个星期槽,实际={len(hist) if hist else None}"
    # 周一(weekday=0)总字数=1000,周二(weekday=1)=600
    mon = next(h for h in hist if h["weekday"] == 0)
    tue = next(h for h in hist if h["weekday"] == 1)
    assert mon["total_words"] == 1000, f"周一总字={mon['total_words']}"
    assert mon["avg_words"] == 1000, f"周一均字={mon['avg_words']}"
    assert tue["total_words"] == 600, f"周二总字={tue['total_words']}"
    # best_weekday 应是周一(1000>600)
    assert p.get("best_weekday") == "周一", f"最高产星期几={p.get('best_weekday')}"


def test_progress_ideal_line(store):
    """设了 total_word_goal 后,daily 每条有 ideal_cumulative 字段且单调递增。"""
    today = "2099-06-10"
    store.set_intent({"total_word_goal": 10000, "reader_feeling": "沉浸"})
    store.save_chapter(1, "甲" * 500, title="一", _today="2099-06-08")
    store.save_chapter(2, "乙" * 300, title="二", _today="2099-06-09")
    p = store.progress(today=today)
    daily = p.get("daily", [])
    assert daily, "daily 不应为空"
    # 每条都有 ideal_cumulative
    for row in daily:
        assert "ideal_cumulative" in row, f"日期 {row['date']} 缺 ideal_cumulative"
    # ideal_cumulative 单调递增
    ideals = [r["ideal_cumulative"] for r in daily]
    assert ideals == sorted(ideals), f"ideal_cumulative 应单调递增: {ideals}"
    # 最终值不超过 total_word_goal
    assert ideals[-1] <= 10000, f"理想线末值不应超目标: {ideals[-1]}"
    # ideal_daily_rate 字段存在
    assert p.get("ideal_daily_rate") is not None


def test_progress_no_goal_no_ideal_line(store):
    """未设 total_word_goal 时,daily 行不含 ideal_cumulative。"""
    today = "2099-07-01"
    store.save_chapter(1, "甲" * 200, title="一", _today=today)
    p = store.progress(today=today)
    for row in p.get("daily", []):
        assert "ideal_cumulative" not in row, "无目标时不应有 ideal_cumulative"
    assert p.get("ideal_daily_rate") is None


# ===== F-01 大纲/卷章树手稿支(后端数据层) =====

from scribe3.store import _split_scenes


class TestSplitScenes:
    """_split_scenes 纯函数:按 SceneBreak 约定切段。"""

    def test_no_separator_single_scene(self):
        prose = "焦三扛着镇煞钉走进奈何谷。"
        scenes = _split_scenes(prose)
        assert len(scenes) == 1
        assert scenes[0]["chars"] == len("焦三扛着镇煞钉走进奈何谷。")

    def test_two_separators_three_scenes(self):
        prose = "第一段文字。\n* * *\n第二段文字。\n* * *\n第三段文字。"
        scenes = _split_scenes(prose)
        assert len(scenes) == 3

    def test_dash_separator(self):
        prose = "段落A。\n---\n段落B。"
        scenes = _split_scenes(prose)
        assert len(scenes) == 2

    def test_title_truncated_to_24(self):
        long_line = "A" * 30
        scenes = _split_scenes(long_line)
        assert len(scenes[0]["title"]) <= 24

    def test_chars_excludes_whitespace(self):
        prose = "文 字 计 数"   # 去空白后 4 字
        scenes = _split_scenes(prose)
        assert scenes[0]["chars"] == 4

    def test_empty_prose_returns_empty(self):
        assert _split_scenes("") == []

    def test_only_separator_returns_empty(self):
        # 仅有分隔行,无实质内容
        assert _split_scenes("* * *") == []


class TestVolumeCRUD:
    """volume 表增删改查。"""

    def test_add_and_list_volumes(self, store):
        vid = store.add_volume("第一卷·镇煞", sort_order=1, color="#5b8c6e")
        vols = store.list_volumes()
        assert any(v["id"] == vid for v in vols)
        target = next(v for v in vols if v["id"] == vid)
        assert target["title"] == "第一卷·镇煞"
        assert target["color"] == "#5b8c6e"

    def test_update_volume(self, store):
        vid = store.add_volume("临时标题", sort_order=0)
        store.update_volume(vid, {"title": "新标题", "sort_order": 5})
        vols = store.list_volumes()
        target = next(v for v in vols if v["id"] == vid)
        assert target["title"] == "新标题"
        assert target["sort_order"] == 5

    def test_delete_volume_unlinks_chapters(self, store):
        """删卷:该卷下的章 volume 置 NONE,章本身不删。"""
        vid = store.add_volume("待删之卷", sort_order=0)
        # 建章并归入该卷
        store.save_chapter(10, "第十章正文", title="测试章")
        store.update_chapter_meta(10, {"volume": vid})
        # 确认章已关联到卷
        ch_before = store._query(
            "SELECT meta::id(volume) AS vol FROM type::record('chapter', 10)")
        assert ch_before and ch_before[0]["vol"] is not None
        # 删卷
        store.delete_volume(vid)
        # 章仍存在,volume 变 NONE
        ch_after = store.get_chapter(10)
        assert ch_after is not None, "章不应被删除"
        # 用 outline 验证:删卷后章应在 unassigned_chapters
        outline = store.outline()
        assert 10 in outline["unassigned_chapters"], "删卷后章应出现在 unassigned_chapters"
        # 卷本身已不存在
        vols = store.list_volumes()
        assert not any(v["id"] == vid for v in vols)


class TestOutline:
    """outline() 聚合 + sort_order≠seq 纪律。"""

    def test_outline_returns_structure(self, store):
        """outline() 返回 volumes/chapters/unassigned_chapters 三键。"""
        result = store.outline()
        assert "volumes" in result
        assert "chapters" in result
        assert "unassigned_chapters" in result

    def test_outline_with_volume_and_synopsis(self, store):
        """建卷+章,关联,设 synopsis → outline 正确聚合。"""
        vid = store.add_volume("第一卷", sort_order=1)
        store.save_chapter(1, "焦三走进奈何谷。\n* * *\n他看见了镇煞钉。", title="楔子")
        store.save_chapter(2, "第二章正文。", title="入派")
        # 关联章到卷
        store.update_chapter_meta(1, {"volume": vid, "synopsis": "楔子梗概"})
        store.update_chapter_meta(2, {"synopsis": "入派梗概"})

        result = store.outline()
        # 卷存在
        assert any(v["id"] == vid for v in result["volumes"])
        # 第1章属于卷
        ch1 = next(c for c in result["chapters"] if c["seq"] == 1)
        assert ch1["volume"] == vid
        assert ch1["synopsis"] == "楔子梗概"
        # scene_count: 正文有 * * * 分两段 → 2
        assert ch1["scene_count"] == 2
        # 第2章无卷 → 在 unassigned_chapters
        assert 2 in result["unassigned_chapters"]

    def test_outline_chapters_sorted_by_sort_order(self, store):
        """章按 sort_order 排序,而非 seq。"""
        store.save_chapter(1, "第一章", title="一")
        store.save_chapter(2, "第二章", title="二")
        store.save_chapter(3, "第三章", title="三")
        # 把 seq=3 的章 sort_order 设为 0(排最前)
        store.reorder_chapters(None, [3, 1, 2])
        result = store.outline()
        seqs = [c["seq"] for c in result["chapters"]]
        assert seqs[0] == 3, f"sort_order 最小的章应排第一,实际顺序: {seqs}"

    def test_outline_word_count_from_qc_cache(self, store):
        """outline 返回 word_count 来自 qc_word_count 缓存。"""
        store.save_chapter(5, "五字五字五字五字五字", title="五")
        result = store.outline()
        ch5 = next((c for c in result["chapters"] if c["seq"] == 5), None)
        assert ch5 is not None
        # save_chapter 会写 qc_word_count
        assert ch5.get("word_count") is not None


class TestReorderChapters:
    """sort_order≠seq 守卫:reorder 只改 sort_order,seq 永不变。"""

    def test_reorder_changes_sort_order_not_seq(self, store):
        """核心守卫:reorder 后 seq 完全不变。"""
        store.save_chapter(1, "一", title="一")
        store.save_chapter(2, "二", title="二")
        store.save_chapter(3, "三", title="三")

        store.reorder_chapters(None, [3, 1, 2])

        # seq 不变:三章仍存在于各自 seq 位置
        for s in [1, 2, 3]:
            ch = store.get_chapter(s)
            assert ch is not None, f"chapter:{s} 应仍存在"
            assert ch["seq"] == s, f"seq 不应被改动,chapter:{s} seq={ch['seq']}"

        # sort_order 已按 reorder 顺序改变
        rows = store._query("SELECT seq, sort_order FROM chapter ORDER BY sort_order")
        seq_order = [r["seq"] for r in rows]
        assert seq_order[0] == 3, f"reorder 后 sort_order 最小的应是 seq=3,实际: {seq_order}"

    def test_reorder_does_not_affect_facts_at(self, store):
        """reorder 后,facts_at(以 seq 为参数的读路径)不受影响。"""
        from scribe3.ontology import Entity, Fact
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:test_reorder", "role:甲", "属性", "测试值", valid_from=2))
        store.save_chapter(1, "一", title="一")
        store.save_chapter(2, "二", title="二")

        before = {f.id for f in store.facts_at(2)}
        store.reorder_chapters(None, [2, 1])
        after = {f.id for f in store.facts_at(2)}

        assert before == after, (
            f"reorder 后 facts_at(2) 结果不应变化\n"
            f"before={before}\nafter={after}")

    def test_reorder_with_volume(self, store):
        """带卷重排:volume 字段同步更新。"""
        vid = store.add_volume("卷A", sort_order=1)
        store.save_chapter(10, "十", title="十")
        store.save_chapter(11, "十一", title="十一")

        store.reorder_chapters(vid, [11, 10])

        rows = store._query(
            "SELECT seq, meta::id(volume) AS vol, sort_order "
            "FROM chapter WHERE seq IN [10, 11] ORDER BY sort_order")
        assert rows[0]["seq"] == 11, "sort_order 更小的应是 seq=11"
        for r in rows:
            assert r["vol"] == vid, f"chapter:{r['seq']} volume 应更新为 {vid}"


class TestUpdateChapterMeta:
    """update_chapter_meta:白名单字段更新,不碰 prose。"""

    def test_patch_synopsis_does_not_touch_prose(self, store):
        store.save_chapter(7, "七章正文内容", title="七")
        store.update_chapter_meta(7, {"synopsis": "七章梗概"})
        ch = store.get_chapter(7)
        assert ch["prose"] == "七章正文内容", "patch synopsis 不应改动 prose"
        rows = store._query("SELECT synopsis FROM type::record('chapter', 7)")
        assert rows[0]["synopsis"] == "七章梗概"

    def test_patch_nonexistent_chapter_returns_false(self, store):
        result = store.update_chapter_meta(9999, {"synopsis": "不存在的章"})
        assert result is False

    def test_patch_volume_assignment(self, store):
        vid = store.add_volume("归属卷", sort_order=0)
        store.save_chapter(8, "八章", title="八")
        store.update_chapter_meta(8, {"volume": vid})
        rows = store._query(
            "SELECT meta::id(volume) AS vol FROM type::record('chapter', 8)")
        assert rows[0]["vol"] == vid

    def test_patch_label_valid(self, store):
        store.save_chapter(6, "六章", title="六")
        store.update_chapter_meta(6, {"label": "done"})
        rows = store._query("SELECT label FROM type::record('chapter', 6)")
        assert rows[0]["label"] == "done"

    def test_patch_ignores_non_whitelist_fields(self, store):
        store.save_chapter(4, "四章正文", title="四")
        # 尝试写 prose(非白名单)→ 应被忽略
        store.update_chapter_meta(4, {"prose": "篡改正文", "synopsis": "合法梗概"})
        ch = store.get_chapter(4)
        assert ch["prose"] == "四章正文", "非白名单字段 prose 不应被改写"


# ===== M3 validate_cross_chapter_consistency 单元测试 =====
class TestValidateCrossChapter:
    """M3: 跨章一致性检测。"""

    def test_numeric_inconsistency_via_term(self, store):
        """术语专名绑定不同数字 → numeric_inconsistency。"""
        from scribe3.store import SurrealStore
        store.add_term("灵龙镇", category="地名")
        store.save_chapter(3, "灵龙镇煞钉三百六十枚,镇住了万年阴气。", title="第三章")
        store.save_chapter(5, "灵龙镇煞钉七十二枚,哪里够用。", title="第五章")
        hints = store.validate_cross_chapter_consistency()
        ni = [h for h in hints if h["type"] == "numeric_inconsistency"]
        assert ni, f"灵龙镇数字矛盾(360 vs 72)应报 numeric_inconsistency,实际 hints: {hints}"
        assert any("灵龙镇" in h.get("entity", "") or "灵龙镇" in h.get("description", "")
                   for h in ni), f"应指向「灵龙镇」,实际: {ni}"
        # evidence 应含两处冲突章号
        assert all("evidence" in h for h in ni), "numeric_inconsistency 应含 evidence"

    def test_numeric_same_no_hint(self, store):
        """同一专名同一数字多次出现 → 不报矛盾。"""
        store.add_term("灵龙镇", category="地名")
        store.save_chapter(3, "灵龙镇煞钉三百六十枚。", title="第三章")
        store.save_chapter(5, "灵龙镇煞钉三百六十枚依旧。", title="第五章")
        hints = store.validate_cross_chapter_consistency()
        ni = [h for h in hints if h["type"] == "numeric_inconsistency"]
        assert not ni, f"数字一致不应报矛盾,实际: {ni}"

    def test_no_chapters_no_crash(self, store):
        """无章时返回空列表,不崩溃。"""
        hints = store.validate_cross_chapter_consistency()
        assert isinstance(hints, list)

    def test_numeric_different_unit_no_false_positive(self, store):
        """数字单位不同时不报矛盾——修复滥报。

        章1「柳三更三十出头的年纪」→ 数字"三十",单位"出头"(无标准量词)
        章2「柳三更二十年前离家」  → 数字"二十",单位"年"
        量词单位不同("出头" vs "年"),不应触发 numeric_inconsistency。
        """
        store.add_term("柳三更", category="人名")
        store.save_chapter(1, "柳三更三十出头的年纪,面容清癯。", title="第一章")
        store.save_chapter(2, "柳三更二十年前离家,如今重返。", title="第二章")
        hints = store.validate_cross_chapter_consistency()
        ni = [h for h in hints if h["type"] == "numeric_inconsistency"
              and "柳三更" in h.get("entity", "")]
        assert not ni, (
            f"年龄(三十出头)vs时间(二十年前)不同单位,不应报矛盾,实际: {ni}"
        )

    def test_numeric_same_unit_inconsistency_reported(self, store):
        """同单位不同数字 → 应报 numeric_inconsistency。

        章1「潭家二十七口尽死」(单位:口)
        章2「潭家三百一十七口皆是百姓」(单位:口)
        同一量词单位"口"但数字不同 → 应报。
        """
        store.add_faction("潭家")
        store.save_chapter(1, "潭家二十七口尽死,无一生还。", title="第一章")
        store.save_chapter(2, "潭家三百一十七口皆是百姓,岂能枉死。", title="第二章")
        hints = store.validate_cross_chapter_consistency()
        ni = [h for h in hints if h["type"] == "numeric_inconsistency"
              and "潭家" in h.get("entity", "")]
        assert ni, (
            f"潭家「二十七口」vs「三百一十七口」同单位口,应报 numeric_inconsistency,实际: {hints}"
        )

    def test_unregistered_name_not_flooding(self, store):
        """正常正文不应产生大量 unregistered_name 假阳性(≤5条)。

        收紧后:只报 ≥5次 且 与已知专名共享≥2个连续字(别名漂移)的词,
        普通词汇和独立新词不报。
        """
        store.add_term("柳三更", category="人名")
        store.add_faction("潭家")
        # 普通正文:有常用词,有专名,有新词但频次低
        normal_prose = (
            "柳三更走过街道,看见潭家的门楼紧闭。"
            "他回头望了望,这里的百姓已经不多。"
            "夜色渐深,月光照在石板路上。"
            "柳三更想起往日的事情,心中五味杂陈。"
            "潭家的人早已逃散,只留下一座空院。"
        )
        store.save_chapter(1, normal_prose * 3, title="第一章")
        store.save_chapter(2, normal_prose * 3, title="第二章")
        hints = store.validate_cross_chapter_consistency()
        un = [h for h in hints if h["type"] == "unregistered_name"]
        assert len(un) <= 5, (
            f"正常正文 unregistered_name 应≤5条(收紧后),实际 {len(un)} 条: "
            + str([h['entity'] for h in un])
        )


# ===== Phase0-BE1 千万字可扩展基座 =====

from scribe3.ontology import Entity, Fact, KnowledgeEdge, Event
from scribe3.store import backfill_scalability_caches


class TestSceneCountCache:
    """outline() 停拉全文 —— scene_count/scene_meta 缓存列(头号病灶)。"""

    def test_save_chapter_writes_scene_count(self, store):
        """save_chapter 落库时算好 scene_count 存列。"""
        store.save_chapter(1, "第一场。\n* * *\n第二场。\n* * *\n第三场。", title="一")
        rows = store._query(
            "SELECT scene_count FROM type::record('chapter', 1)")
        assert rows and rows[0]["scene_count"] == 3

    def test_save_chapter_writes_scene_meta(self, store):
        """scene_meta 缓存每场景 title+char_count(JSON串),供 project_tree 免拉正文建树。"""
        import json
        store.save_chapter(2, "甲段。\n* * *\n乙段乙段。", title="二")
        rows = store._query("SELECT scene_meta FROM type::record('chapter', 2)")
        meta = json.loads(rows[0]["scene_meta"])
        assert isinstance(meta, list) and len(meta) == 2
        assert meta[0]["title"] and meta[0]["char_count"] == 3   # "甲段。" 按字符数=3

    def test_outline_sql_does_not_select_prose(self):
        """自证:outline() 源码 SQL 不再 SELECT prose(停拉全书正文)。
        只看可执行代码行(剥离 docstring/注释),docstring 里提及 prose 不算。"""
        import inspect
        import ast
        from scribe3.store import SurrealStore
        src = inspect.getsource(SurrealStore.outline)
        tree = ast.parse(src.strip())
        func = tree.body[0]
        # 剥离首条 docstring 表达式
        body = func.body[1:] if (func.body and isinstance(func.body[0], ast.Expr)
                                 and isinstance(getattr(func.body[0], "value", None), ast.Constant)) else func.body
        code_strings = [n.value for n in ast.walk(ast.Module(body=body, type_ignores=[]))
                        if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        joined = " ".join(code_strings)
        assert "prose" not in joined, f"outline() 可执行 SQL 不应引用 prose: {joined}"

    def test_outline_scene_count_matches_split(self, store):
        """outline 返回的 scene_count 与 _split_scenes 直算一致(对拍)。"""
        prose = "焦三夜行。\n* * *\n他看见镇煞钉。\n---\n第三场。"
        store.save_chapter(3, prose, title="三")
        out = store.outline()
        ch3 = next(c for c in out["chapters"] if c["seq"] == 3)
        assert ch3["scene_count"] == len(_split_scenes(prose)) == 3
        # scenes 详情来自缓存,长度对齐
        assert len(ch3["scenes"]) == 3

    def test_backfill_populates_scene_count(self, store):
        """存量章(直接写 prose 绕过 save_chapter 缓存)backfill 后有 scene_count。"""
        # 模拟存量:直接 UPSERT prose,不走 save_chapter(无 scene_count)
        store._execute_write(
            "UPSERT type::record('chapter', 7) SET seq=7, title='存量', "
            "prose='第一场。\n* * *\n第二场。', qc_word_count=10", {})
        # 回填前 scene_count 为空
        pre = store._query("SELECT scene_count FROM type::record('chapter', 7)")
        assert not pre[0].get("scene_count")
        n = backfill_scalability_caches(store)
        assert n >= 1
        post = store._query("SELECT scene_count FROM type::record('chapter', 7)")
        assert post[0]["scene_count"] == 2


class TestQualityCache:
    """quality 缓存列:qc_issues/qc_causal 在 save_chapter 落库,outline 聚合不重算。"""

    def test_save_chapter_writes_qc_issues(self, store):
        store.save_chapter(1, "一段正常的志怪内容。", title="一")
        rows = store._query("SELECT qc_issues, qc_causal FROM type::record('chapter', 1)")
        assert rows[0]["qc_issues"] is not None
        assert rows[0]["qc_causal"] is not None

    def test_qc_causal_reflects_event_violations(self, store):
        """有缺目标事件的章,qc_causal 缓存应记录违规数。"""
        store.add_event(Event("ev:逃", "逃", story_time=4))   # 缺 motivated_by_goal
        store.save_chapter(4, "第四章正文。", title="四")
        rows = store._query("SELECT qc_causal FROM type::record('chapter', 4)")
        assert rows[0]["qc_causal"] >= 1

    def test_outline_exposes_qc_caches(self, store):
        store.save_chapter(5, "正文五。", title="五")
        out = store.outline()
        ch5 = next(c for c in out["chapters"] if c["seq"] == 5)
        assert "qc_issues" in ch5 and "qc_causal" in ch5


class TestGraphEgoAndLimit:
    """graph(focus=...) ego 子图;graph() 无 focus 硬上限 limit。"""

    def test_graph_focus_returns_ego_subgraph(self, store):
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_entity(Entity("role:乙", "character", "乙"))
        store.add_entity(Entity("role:丙", "character", "丙"))
        store.add_fact(Fact("fact:f1", "role:甲", "属性", "甲知道的事", valid_from=1))
        store.add_fact(Fact("fact:f2", "role:乙", "属性", "乙知道的事", valid_from=1))
        store.add_knowledge(KnowledgeEdge("role:甲", "fact:f1", since_chapter=1))
        store.add_knowledge(KnowledgeEdge("role:乙", "fact:f2", since_chapter=1))
        g = store.graph(focus="role:甲", chapter=5)
        node_ids = {n["id"] for n in g["nodes"]}
        assert "role:甲" in node_ids
        assert "fact:f1" in node_ids          # 甲的邻居命题在
        assert "fact:f2" not in node_ids       # 乙的命题不在 ego 邻域

    def test_graph_no_focus_respects_limit(self, store):
        store.add_entity(Entity("role:主", "character", "主"))
        for i in range(50):
            fid = f"fact:p{i}"
            store.add_fact(Fact(fid, "role:主", "属性", f"命题{i}", valid_from=1))
            store.add_knowledge(KnowledgeEdge("role:主", fid, since_chapter=1))
        g = store.graph(limit=10)
        assert len(g["nodes"]) <= 10, f"无 focus 节点数应 ≤ limit=10,实际 {len(g['nodes'])}"

    def test_graph_backward_compatible_default(self, store):
        """无新参数调用仍返回 nodes/edges 结构。"""
        store.add_entity(Entity("role:甲", "character", "甲"))
        store.add_fact(Fact("fact:x", "role:甲", "属性", "某值", valid_from=1))
        store.add_knowledge(KnowledgeEdge("role:甲", "fact:x", since_chapter=1))
        g = store.graph(5)
        assert "nodes" in g and "edges" in g
        assert any(n["id"] == "role:甲" for n in g["nodes"])


class TestTimelineWindow:
    """timeline 总 items 上限(防一次返上万)。"""

    def test_timeline_respects_limit(self, store):
        for i in range(1, 40):
            store.add_event(Event(f"ev:e{i}", "action", story_time=i,
                                  motivated_by_goal="g", causal_in=[("ev:e1", "enables")]))
        items = store.timeline(ch_from=1, ch_to=100, limit=10)
        assert len(items) <= 10, f"timeline items 应被 limit 截断,实际 {len(items)}"

    def test_timeline_default_unlimited_backcompat(self, store):
        """不传 limit 时不截断(向后兼容,全部返回)。"""
        for i in range(1, 6):
            store.add_event(Event(f"ev:e{i}", "action", story_time=i,
                                  motivated_by_goal="g", causal_in=[("ev:e1", "enables")]))
        items = store.timeline(ch_from=1, ch_to=100)
        assert len(items) >= 5


# ===== Phase0-BE2 四阶段写作:beats / draft / chapter_version 扩字段 =====

def test_chapter_beats_roundtrip(store):
    """节拍 beats 读写往返:写 JSON 串数组,get_chapter 解析还原为 list。"""
    store.save_chapter(1, "正文。", title="第一章")
    beats = [{"text": "开场:潭家满门遭屠", "done": True}, {"text": "焦三登场"}]
    assert store.update_chapter_meta(1, {"beats": beats}) is True
    ch = store.get_chapter(1)
    assert ch.get("beats") == beats


def test_chapter_beats_default_empty(store):
    """未写过 beats 的章:get_chapter 返回 beats=[](字段恒在,向后兼容)。"""
    store.save_chapter(2, "正文。", title="第二章")
    ch = store.get_chapter(2)
    assert ch.get("beats") == []


def test_chapter_draft_roundtrip(store):
    """草稿 draft 与正文 prose 分离:save_draft 写 draft,get_chapter 取回,prose 不受影响。"""
    store.save_chapter(3, "这是定稿正文。", title="第三章")
    store.save_chapter_draft(3, "这是草稿正文。")
    ch = store.get_chapter(3)
    assert ch.get("draft") == "这是草稿正文。"
    assert ch.get("prose") == "这是定稿正文。"


def test_chapter_version_stage_fields(store):
    """chapter_version 新增 stage/summary/stats;list/get 带上。"""
    import json
    vid = store.add_chapter_version(
        4, "草稿正文。", label="v1", kind="checkpoint",
        stage="draft", summary="第一稿", stats={"words": 5, "avg_sentence": 5, "dialog_count": 0})
    rows = store.list_chapter_versions(4)
    assert rows and rows[0]["id"] == vid
    assert rows[0]["stage"] == "draft"
    assert rows[0]["summary"] == "第一稿"
    got = store.get_chapter_version(vid)
    assert got["stage"] == "draft"
    assert json.loads(got["stats"])["words"] == 5


def test_chapter_version_stage_defaults_final(store):
    """向后兼容:add_chapter_version 不传 stage → 默认 'final'。"""
    vid = store.add_chapter_version(5, "正文。", kind="checkpoint")
    got = store.get_chapter_version(vid)
    assert got["stage"] == "final"


def test_latest_draft_version(store):
    """latest_draft_version 取该章最新 draft 版(忽略 final 版)。"""
    store.add_chapter_version(6, "草稿A。", stage="draft", summary="A")
    store.add_chapter_version(6, "正文定稿。", stage="final")
    store.add_chapter_version(6, "草稿B。", stage="draft", summary="B")
    latest = store.latest_draft_version(6)
    assert latest is not None
    assert latest["prose"] == "草稿B。"
    assert latest["stage"] == "draft"


def test_latest_draft_version_none(store):
    """无 draft 版时 latest_draft_version 返回 None。"""
    store.add_chapter_version(7, "正文定稿。", stage="final")
    assert store.latest_draft_version(7) is None


def test_chapter_deduction_fields_roundtrip(store):
    """scene_truth / involved_characters / deductions 三字段 patch→get 往返。"""
    store.save_chapter(1, "", title="第1章")
    store.update_chapter_meta(1, {
        "scene_truth": "客观真相:借命正在发生。",
        "involved_characters": ["role:柳怀玉", "role:苏纸鸢"],
        "deductions": [{"character_id": "role:柳怀玉", "character_name": "柳怀玉", "prose": "看到:纸人动。"}],
    })
    ch = store.get_chapter(1)
    assert ch["scene_truth"] == "客观真相:借命正在发生。"
    assert ch["involved_characters"] == ["role:柳怀玉", "role:苏纸鸢"]
    assert ch["deductions"][0]["character_name"] == "柳怀玉"
