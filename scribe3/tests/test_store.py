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
    rows = store._query("SELECT character, seq, trigger_chapter, reason FROM voice_evolution_flag")
    assert rows and rows[0]["trigger_chapter"] == 7 and rows[0]["seq"] == 7
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
    """P1-b 回归:max_chapter 须读 story_chapter(双写真源),不能只查 valid_from。
    修复前:只查 valid_from → 外部/ingest 路径只写 story_chapter 不写 valid_from 的事件被遗漏。
    修复后:取 MAX(story_chapter, valid_from) → 正确返回最大章号。

    直接用 _execute_write 绕过 add_event 插入「只有 story_chapter、valid_from=NONE」的事件
    来模拟 ingest/外部写入路径,这正是只查 valid_from 时会遗漏的场景。
    """
    # 通过 add_event 正常路径写一个章号较小的事件(valid_from=story_chapter=5)
    store.add_event(Event("ev:普通事件", "普通", story_time=5))
    assert store.max_chapter() == 5

    # 直接写入 story_chapter=17、valid_from=0 的事件(模拟 ingest/外部路径:真实章号在 story_chapter)
    # valid_from=0 是"未设置"语义;只查 valid_from 时该事件最大章号仍为 5,不会是 17
    store._execute_write(
        "CREATE type::record('event', 'only_story_ch') SET etype='ingest写入', event_type='ingest写入', "
        "story_chapter=17, valid_from=0, motivated_by_goal=NONE, location=NONE, preconditions=[]",
        {})

    result = store.max_chapter()
    assert result >= 17, (
        f"max_chapter 应 >= 17(story_chapter=17,valid_from=0 的事件),实际: {result}。"
        f"Bug:只查 valid_from 时该事件被遗漏。"
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
