"""S0/S1 · SurrealStore TDD —— 证限知范式在【真库 NS=scribe3】上照样成立。

纵切片的 knowledge.project_frame 不改一行,直接跑在
SurrealStore 上(鸭子兼容)。老道帧仍排除焦三私密 → 范式不依赖存储后端。
"""
import pytest

import scribe3.store as store_module
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge
from scribe3.scenario import luanshi_leak_world
from scribe3.knowledge import project_frame
from scribe3.verify import causal_complete


@pytest.mark.parametrize("bad", [True, 0, -1, 1.5, "1"])
def test_chapter_range_target_rejects_non_positive_ints(bad):
    target = getattr(store_module, "_chapter_range_target", None)
    assert target is not None, "store 应定义章节 record range 目标构造器"
    with pytest.raises((TypeError, ValueError)):
        target(start=bad, end=3)


def test_chapter_range_target_shapes():
    target = getattr(store_module, "_chapter_range_target", None)
    assert target is not None, "store 应定义章节 record range 目标构造器"
    assert target() == "chapter:.."
    assert target(end=5, end_inclusive=False) == "chapter:..5"
    assert target(start=1, end=10) == "chapter:1..=10"
    with pytest.raises(ValueError):
        target(start=10, end=1)


def test_chapter_range_semantics_preserve_gaps_and_archived_existence(store):
    store.save_chapter(1, "一章。", title="一")
    store.save_chapter(2, "二章。", title="二")
    store.save_chapter(4, "四章。", title="四")
    store.archive_chapter(2, "测试归档")

    assert hasattr(store, "chapter_seqs_in_range"), "store 应提供闭区间章节存在性读取"
    assert store.chapter_seqs_in_range(1, 4) == [1, 2, 4]
    assert [row["seq"] for row in store.list_chapters()] == [1, 4]


def test_recent_proses_range_keeps_exclusive_bound_archive_filter_and_order(store):
    store.save_chapter(1, "一章。", title="一")
    store.save_chapter(2, "二章。", title="二")
    store.save_chapter(4, "四章。", title="四")
    store.archive_chapter(2, "测试归档")

    rows = store.recent_proses(4, k=3)
    assert [row["seq"] for row in rows] == [1]


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


def test_add_voice_flag_normalizes_bare_name_to_role_prefix(store):
    """批D P1-11:裸名(ingest voice_shift 传 who 名)写入的 voice flag 应统一带 role: 前缀,
    否则 fold_voice_flags/前端按 role: id 匹配永远空操作。既有带前缀写入不被二次加前缀。"""
    store.add_voice_flag("胡不为", 3, "声音因恐惧发颤")            # 裸名(模拟 ingest voice_shift)
    store.add_voice_flag("role:赵芙南", 4, "声调转冷")             # 已带前缀
    chars = {f["character"] for f in store.list_voice_flags("open")}
    assert "role:胡不为" in chars, f"裸名应规范化为 role: 前缀: {chars}"
    assert "胡不为" not in chars, f"不应残留裸名: {chars}"
    assert "role:赵芙南" in chars and "role:role:赵芙南" not in chars, \
        f"带前缀写入不应二次加前缀: {chars}"


def test_bare_name_voice_flag_is_foldable(store):
    """批D P1-11:裸名写入的 flag 规范化后可被 fold_voice_flags(role: id)消化(此前空操作)。"""
    store.add_voice_flag("胡不为", 3, "声音因恐惧发颤")
    res = store.fold_voice_flags("role:胡不为",
                                 lambda p: '{"style_summary":"声音因恐惧而短促发颤"}')
    assert res.get("folded") == 1, f"裸名 flag 应被 role: id fold 到,实际: {res}"


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


# --- P0(2026-07-14):多语句脚本静默失败 ---

def test_raw_query_raises_on_any_failing_statement(store):
    """【P0】多语句脚本里**任何一条**语句失败都必须抛,不能只看第一条。

    surrealdb-py 的 `query()` 对多语句脚本只检查/返回 `result[0]`——后续语句报错被静默吞掉。
    migration 是"整个文件一次 query"的多语句调用,于是第 1 条 DEFINE 成功就足以让
    apply_schema 把整个 migration 标记为已应用,哪怕后面的数据迁移 UPDATE 全炸了,
    且此后永不重放。083 正是这样静默半成功的(实证)。所有历史 migration 都受此影响。
    """
    # 第 1 条必成功(DEFINE 一张 SCHEMAFULL 空表),第 2 条必失败(写一个未定义的字段)。
    script = ("DEFINE TABLE IF NOT EXISTS _silent_fail_probe SCHEMAFULL; "
              "CREATE _silent_fail_probe SET nonexistent_field = 1;")
    with pytest.raises(Exception) as ei:
        store._raw_query(script)
    assert "nonexistent_field" in str(ei.value), \
        f"应把第 2 条语句的真实错误抛出来,实际: {ei.value}"
    # 且失败语句确实没落库(不是"报错了但数据还是写进去了")
    assert store._query("SELECT * FROM _silent_fail_probe") == []


def test_raw_query_still_returns_first_statement_result(store):
    """回归护栏:逐条校验不得改变正常查询的返回形状(仍是第 1 条语句的 result)。"""
    # 单语句
    assert store._raw_query("RETURN 1 + 1") == 2
    # 正常多语句:返回值仍取第一条,后续语句照常执行(不因新校验而中断)
    out = store._raw_query("RETURN 'first'; DEFINE TABLE IF NOT EXISTS _ok_probe SCHEMALESS;")
    assert out == "first"


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

def test_semantic_index_retries_transient_transaction_conflict(store, monkeypatch):
    """向量 UPDATE 遇到 SurrealDB 短暂写冲突时，不能永久丢失语义召回。"""
    import scribe3.embed as embed_module
    monkeypatch.setattr(embed_module, "embed", lambda _texts: [[0.1, 0.2]])
    calls = []

    def write(_surql, _vars):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("Transaction write conflict")

    monkeypatch.setattr(store, "_execute_write", write)
    store.semantic_index("fact:retry", "可被召回的命题")
    assert len(calls) == 2

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
        "CREATE type::thing('event', 'only_story_ch') SET event_type='ingest写入', "
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
        "UPSERT type::thing('daily_progress', '2026-01-01') SET "
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
        "SELECT until_chapter FROM knows WHERE in=type::thing('character','甲') "
        "AND out=type::thing('proposition','秘1')")
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
        "SELECT until_chapter FROM knows WHERE in=type::thing('character','乙') "
        "AND out=type::thing('proposition','秘2')")
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
    """set_intent 写入 total_word_goal/daily_word_goal 后 get_intent 回读一致。

    P2-12:改 MERGE 后,局部更新(只传 reader_feeling)不再抹掉此前设的字数目标
    (旧行为 CONTENT 整替会静默清空未传字段——正是审计要修的 bug)。
    "未设时键不存在" 由全新库场景保证(见 test_intent_crud:GET 空库不含 word goal 键)。
    """
    store.set_intent({"reader_feeling": "沉浸", "total_word_goal": 100000, "daily_word_goal": 2000})
    got = store.get_intent()
    assert got["total_word_goal"] == 100000
    assert got["daily_word_goal"] == 2000

    # 只更新 reader_feeling 不传字数目标 → 目标保留(MERGE 非整替;不报错)
    store.set_intent({"reader_feeling": "平静"})
    got2 = store.get_intent()
    assert got2["reader_feeling"] == "平静"
    assert got2.get("total_word_goal") == 100000, "P2-12:未传字段应保留,不被抹空"
    assert got2.get("daily_word_goal") == 2000


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
            "SELECT meta::id(volume) AS vol FROM type::thing('chapter', 10)")
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

    def test_chapter_archive_hides_from_visible_outline_and_restore_returns_it(self, store):
        """归档章默认从手稿目录/统计隐藏,恢复后回到原 seq。"""
        store.save_chapter(1, "第一章正文。", title="一")
        store.save_chapter(2, "第二章正文。", title="二")

        assert store.archive_chapter(2, "删掉支线") is True

        outline = store.outline()
        assert [c["seq"] for c in outline["chapters"]] == [1]
        assert store.stats()["chapter_count"] == 1
        archived = store.get_chapter(2)
        assert archived and archived["archived"] is True
        assert archived["archive_reason"] == "删掉支线"

        created = store.create_chapter("新第三章")
        assert created["seq"] == 3, "新增章不得复用已归档的 seq=2"

        assert store.restore_chapter(2) is True
        outline2 = store.outline()
        assert [c["seq"] for c in outline2["chapters"]] == [1, 2, 3]


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
        rows = store._query("SELECT synopsis FROM type::thing('chapter', 7)")
        assert rows[0]["synopsis"] == "七章梗概"

    def test_patch_nonexistent_chapter_returns_false(self, store):
        result = store.update_chapter_meta(9999, {"synopsis": "不存在的章"})
        assert result is False

    def test_patch_volume_assignment(self, store):
        vid = store.add_volume("归属卷", sort_order=0)
        store.save_chapter(8, "八章", title="八")
        store.update_chapter_meta(8, {"volume": vid})
        rows = store._query(
            "SELECT meta::id(volume) AS vol FROM type::thing('chapter', 8)")
        assert rows[0]["vol"] == vid

    def test_patch_label_valid(self, store):
        store.save_chapter(6, "六章", title="六")
        store.update_chapter_meta(6, {"label": "done"})
        rows = store._query("SELECT label FROM type::thing('chapter', 6)")
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
            "SELECT scene_count FROM type::thing('chapter', 1)")
        assert rows and rows[0]["scene_count"] == 3

    def test_save_chapter_writes_scene_meta(self, store):
        """scene_meta 缓存每场景 title+char_count(JSON串),供 project_tree 免拉正文建树。"""
        import json
        store.save_chapter(2, "甲段。\n* * *\n乙段乙段。", title="二")
        rows = store._query("SELECT scene_meta FROM type::thing('chapter', 2)")
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
            "UPSERT type::thing('chapter', 7) SET seq=7, title='存量', "
            "prose='第一场。\n* * *\n第二场。', qc_word_count=10", {})
        # 回填前 scene_count 为空
        pre = store._query("SELECT scene_count FROM type::thing('chapter', 7)")
        assert not pre[0].get("scene_count")
        n = backfill_scalability_caches(store)
        assert n >= 1
        post = store._query("SELECT scene_count FROM type::thing('chapter', 7)")
        assert post[0]["scene_count"] == 2


class TestQualityCache:
    """quality 缓存列:qc_issues/qc_causal 在 save_chapter 落库,outline 聚合不重算。"""

    def test_save_chapter_writes_qc_issues(self, store):
        store.save_chapter(1, "一段正常的志怪内容。", title="一")
        rows = store._query("SELECT qc_issues, qc_causal FROM type::thing('chapter', 1)")
        assert rows[0]["qc_issues"] is not None
        assert rows[0]["qc_causal"] is not None

    def test_qc_causal_reflects_event_violations(self, store):
        """有缺目标事件的章,qc_causal 缓存应记录违规数。"""
        store.add_event(Event("ev:逃", "逃", story_time=4))   # 缺 motivated_by_goal
        store.save_chapter(4, "第四章正文。", title="四")
        rows = store._query("SELECT qc_causal FROM type::thing('chapter', 4)")
        assert rows[0]["qc_causal"] >= 1

    def test_outline_exposes_qc_caches(self, store):
        store.save_chapter(5, "正文五。", title="五")
        out = store.outline()
        ch5 = next(c for c in out["chapters"] if c["seq"] == 5)
        assert "qc_issues" in ch5 and "qc_causal" in ch5

    def test_qc_causal_no_event_data_sentinel(self, store):
        """批D P1-5 假绿止血:章无落库事件时 qc_causal=-1(无事件数据哨兵),
        区分'因果完整=0'与'根本没有事件可校验'。有事件的章仍写真实违规数(≥0)。"""
        store.save_chapter(7, "第七章正文,无任何落库事件。", title="七")
        rows = store._query("SELECT qc_causal FROM type::thing('chapter', 7)")
        assert rows[0]["qc_causal"] == -1, "空事件章应为 -1 哨兵而非 0"
        # 对照:有事件(缺目标违规)的章记录真实违规数,不被哨兵覆盖
        store.add_event(Event("ev:逃", "逃", story_time=7))   # 缺 motivated_by_goal
        store.save_chapter(7, "第七章正文,现有一个缺目标事件。", title="七")
        rows2 = store._query("SELECT qc_causal FROM type::thing('chapter', 7)")
        assert rows2[0]["qc_causal"] >= 1, "有事件时写真实违规数"


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
    assert ch.get("scene_truth_revision", 0) >= 1
    assert ch["deductions"][0].get("based_on_truth_rev") == ch["scene_truth_revision"]


def test_scene_truth_revision_bumps_and_marks_projection_stale(store):
    """真相实质改写 → revision +1；旧投影 based_on 落后 → is_stale。"""
    from scribe3.deduce_helpers import is_stale_deduction, soft_gate_issues

    store.save_chapter(2, "", title="第2章")
    store.update_chapter_meta(2, {
        "scene_truth": "第一版真相。",
        "involved_characters": ["role:哑姑", "哑姑"],  # 裸名与 role: 应归一
        "deductions": [{"character_id": "哑姑", "prose": "她听见井鸣。"}],
    })
    ch1 = store.get_chapter(2)
    assert ch1["involved_characters"] == ["role:哑姑"]
    rev1 = ch1["scene_truth_revision"]
    assert rev1 >= 1
    assert ch1["deductions"][0]["character_id"] == "role:哑姑"
    assert ch1["deductions"][0]["based_on_truth_rev"] == rev1
    assert is_stale_deduction(ch1["deductions"][0], rev1) is False

    store.update_chapter_meta(2, {"scene_truth": "第二版真相,借命已成。"})
    ch2 = store.get_chapter(2)
    assert ch2["scene_truth_revision"] == rev1 + 1
    assert is_stale_deduction(ch2["deductions"][0], ch2["scene_truth_revision"]) is True
    issues = soft_gate_issues(ch2)
    assert "role:哑姑" in issues["stale"]
    assert issues["needs_attention"] is True

    # 同文不 bump
    store.update_chapter_meta(2, {"scene_truth": "第二版真相,借命已成。"})
    assert store.get_chapter(2)["scene_truth_revision"] == rev1 + 1


def test_deductions_normalize_bare_vs_role_prefix(store):
    """同一角色裸名与 role: 写入不产生双条。"""
    store.save_chapter(3, "", title="第3章")
    store.update_chapter_meta(3, {
        "scene_truth": "真相。",
        "involved_characters": ["沈砚", "role:沈砚", "role:季棠"],
        "deductions": [
            {"character_id": "沈砚", "prose": "旧"},
            {"character_id": "role:沈砚", "prose": "新"},
            {"character_id": "role:季棠", "prose": "季棠投影"},
        ],
    })
    ch = store.get_chapter(3)
    assert ch["involved_characters"] == ["role:沈砚", "role:季棠"]
    by = {d["character_id"]: d for d in ch["deductions"]}
    assert set(by) == {"role:沈砚", "role:季棠"}
    assert by["role:沈砚"]["prose"] == "新"


def test_resave_deductions_does_not_clear_stale_on_unstamped_old_prose(store):
    """真相 bump 后全文重存：旧无 stamp prose 仍 stale；新角色 stamp 到当前 rev。"""
    from collections import OrderedDict
    from scribe3.deduce_helpers import is_stale_deduction, soft_gate_issues

    store.save_chapter(4, "", title="第4章")
    # 先写入真相 rev=1 + 一条「模拟旧数据」：直接写 JSON 无 based_on
    store.update_chapter_meta(4, {
        "scene_truth": "第一版真相",
        "involved_characters": ["role:哑姑"],
        "deductions": [{"character_id": "role:哑姑", "prose": "旧哑姑投影"}],
    })
    rev1 = store.get_chapter(4)["scene_truth_revision"]
    # 手工剥掉 based_on，模拟历史无 stamp 行
    import json
    store._execute_write(
        "UPDATE type::thing('chapter', $seq) SET deductions=$d",
        {"seq": 4, "d": json.dumps(
            [{"character_id": "role:哑姑", "prose": "旧哑姑投影"}], ensure_ascii=False)},
    )
    # 真相 bump
    store.update_chapter_meta(4, {"scene_truth": "第二版真相已变"})
    rev2 = store.get_chapter(4)["scene_truth_revision"]
    assert rev2 == rev1 + 1
    assert is_stale_deduction(store.get_chapter(4)["deductions"][0], rev2) is True

    # pilot/MCP 式全文重存：旧 prose 无 stamp + 新角色
    store.update_chapter_meta(4, {
        "deductions": [
            {"character_id": "role:哑姑", "prose": "旧哑姑投影"},
            {"character_id": "role:老范", "prose": "新老范投影"},
        ],
        "involved_characters": ["role:哑姑", "role:老范"],
    })
    ch = store.get_chapter(4)
    by = {d["character_id"]: d for d in ch["deductions"]}
    assert "based_on_truth_rev" not in by["role:哑姑"]
    assert is_stale_deduction(by["role:哑姑"], ch["scene_truth_revision"]) is True
    assert by["role:老范"]["based_on_truth_rev"] == ch["scene_truth_revision"]
    assert is_stale_deduction(by["role:老范"], ch["scene_truth_revision"]) is False
    issues = soft_gate_issues(ch)
    assert "role:哑姑" in issues["stale"]
    assert "role:老范" not in issues["stale"]


def test_scene_truth_and_deductions_order_independent_stamp(store):
    """fields 先 deductions 后 scene_truth 时，新投影仍 stamp 到 bump 后的 rev。"""
    from collections import OrderedDict
    from scribe3.deduce_helpers import is_stale_deduction

    store.save_chapter(5, "", title="第5章")
    store.update_chapter_meta(5, {"scene_truth": "旧真相"})
    rev0 = store.get_chapter(5)["scene_truth_revision"]

    fields = OrderedDict([
        ("deductions", [{"character_id": "role:沈砚", "prose": "同批新投影"}]),
        ("scene_truth", "同批新真相"),
        ("involved_characters", ["role:沈砚"]),
    ])
    store.update_chapter_meta(5, fields)
    ch = store.get_chapter(5)
    assert ch["scene_truth"] == "同批新真相"
    assert ch["scene_truth_revision"] == rev0 + 1
    d = ch["deductions"][0]
    assert d["based_on_truth_rev"] == ch["scene_truth_revision"]
    assert is_stale_deduction(d, ch["scene_truth_revision"]) is False


def test_motif_instance_roundtrip_and_purge(store):
    """add_motif_instance → list_motif_instances(章) 往返;purge_ingest 幂等清本章。"""
    store.add_motif("铜炉", theme="宿命", echoes="炉火/铜锈")
    mid = store.list_motifs()[0]["id"]
    store.add_motif_instance(mid, chapter=3, evidence="炉火忽明忽暗", ingest_seq=3)
    got = store.list_motif_instances(3)
    assert len(got) == 1
    assert got[0]["motif_id"] == mid
    assert got[0]["name"] == "铜炉"
    assert got[0]["evidence"] == "炉火忽明忽暗"
    assert store.list_motif_instances(4) == []
    store.purge_ingest(3)
    assert store.list_motif_instances(3) == []




def test_relation_touch_roundtrip_and_purge(store):
    """方案B任务12:add_relation_touch → list_relation_touches(a,b) 对称往返;
    purge_ingest 幂等清本章。a/b 是无序对——反过来传参也应命中同一条记录。"""
    store.add_relation_touch("role:柳怀玉", "role:阿禾", chapter=3, kind="冲突", note="正面对峙")
    got = store.list_relation_touches("role:柳怀玉", "role:阿禾")
    assert len(got) == 1
    assert got[0]["kind"] == "冲突"
    assert got[0]["note"] == "正面对峙"
    # 对称查询:反过来传参仍能命中
    got_rev = store.list_relation_touches("role:阿禾", "role:柳怀玉")
    assert len(got_rev) == 1
    # 单侧查询同样命中
    assert len(store.list_relation_touches(a="role:柳怀玉")) == 1
    assert len(store.list_relation_touches(b="role:阿禾")) == 1
    # 无关角色对查不到
    assert store.list_relation_touches("role:柳怀玉", "role:老李") == []
    store.purge_ingest(3)
    assert store.list_relation_touches("role:柳怀玉", "role:阿禾") == []


def test_promise_lifecycle_fields_and_window_state(store):
    """伏笔生命周期:tier 默认 chapter + 兑现窗口按层级自动推算;arc/book 窗口各异。"""
    store.plant_promise("窗台上的铜炉", setup_chapter=2)
    p = [x for x in store.list_promises() if x["text"] == "窗台上的铜炉"][0]
    assert p["tier"] == "chapter"
    assert p["payoff_min"] == 3 and p["payoff_max"] == 5
    store.plant_promise("судьба线", setup_chapter=1, tier="arc")
    store.plant_promise("书级主线", setup_chapter=1, tier="book")
    arc = [x for x in store.list_promises() if x["tier"] == "arc"][0]
    book = [x for x in store.list_promises() if x["tier"] == "book"][0]
    assert (arc["payoff_min"], arc["payoff_max"]) == (6, 16)
    assert book["payoff_min"] == 2 and book["payoff_max"] is None


def test_promise_window_state_pure():
    from scribe3.store import promise_window_state
    p = {"status": "open", "kind": "payoff", "setup_chapter": 2,
         "payoff_min": 3, "payoff_max": 7, "last_refresh_at": None, "tier": "chapter"}
    assert promise_window_state(p, max_chapter=1)["state"] == "pre_window"
    assert promise_window_state(p, max_chapter=2)["state"] == "in_window"
    assert promise_window_state(p, max_chapter=3)["state"] == "in_window"
    assert promise_window_state(p, max_chapter=5)["state"] == "over_half"
    assert promise_window_state(p, max_chapter=8)["state"] == "overdue"
    assert promise_window_state(p, max_chapter=5)["salience_gap"] == 3
    p2 = dict(p, last_refresh_at=5)
    assert promise_window_state(p2, max_chapter=5)["salience_gap"] == 0
    pb = dict(p, tier="book", payoff_max=None)
    assert promise_window_state(pb, max_chapter=99)["state"] == "in_window"
    assert promise_window_state(dict(p, status="closed"), 5)["state"] == "inactive"
    assert promise_window_state(dict(p, kind="red_herring"), 5)["state"] == "inactive"


def test_promise_touch_roundtrip_purge_and_lifecycle(store):
    """promise_touch 往返 + promises_with_lifecycle 派生刷新态 + purge 幂等清本章。"""
    store.plant_promise("井底的名字", setup_chapter=1)
    pid = [x for x in store.list_promises() if x["text"] == "井底的名字"][0]["id"]
    store.add_promise_touch(pid, chapter=3, evidence="她又梦见井", ingest_seq=3)
    store.add_promise_touch(pid, chapter=4, evidence="井绳断了", ingest_seq=4)
    touches = store.list_promise_touches(pid)
    assert [t["chapter"] for t in touches] == [3, 4]
    # promises_with_lifecycle 派生 refresh_count/last_refresh_at + window 计算态
    rows = store.promises_with_lifecycle(max_chapter=4)
    row = [r for r in rows if r["id"] == pid][0]
    assert row["refresh_count"] == 2 and row["last_refresh_at"] == 4
    # setup=1 → 窗口 2~4;max_chapter=4 → next_ch=5 > pmax=4 → overdue(输入确定,钉死)
    assert row["window"]["state"] == "overdue"
    assert row["window"]["salience_gap"] == 0
    # purge 幂等:重 ingest 第4章前清第4章触及
    store.purge_ingest(4)
    assert [t["chapter"] for t in store.list_promise_touches(pid)] == [3]


def test_update_promise_rejects_bad_tier_even_with_explicit_window(store):
    """Task2 跟进②:非法 tier + 显式窗口不得绕过 tier 校验(校验须在窗口分支之外)。"""
    import pytest
    store.plant_promise("井底的名字", setup_chapter=1)
    pid = [x for x in store.list_promises() if x["text"] == "井底的名字"][0]["id"]
    with pytest.raises(ValueError):
        store.update_promise(pid, {"tier": "saga", "payoff_min": 9})
    # 合法 tier + 显式窗口仍应通过且不被重算覆盖
    assert store.update_promise(pid, {"tier": "arc", "payoff_min": 9}) is True
    row = [x for x in store.list_promises() if x["id"] == pid][0]
    assert row["payoff_min"] == 9


def test_promise_legacy_row_fallback_and_resolution_default(store):
    """Task1 跟进⑤:旧行(裸 CREATE 无 052 字段)回退路径 + resolution 默认值。"""
    store._execute_write(
        "CREATE promise SET text=$t, setup_chapter=2, payoff_chapter=NONE, "
        "status='open', kind='promise'", {"t": "052前的旧伏笔"})
    old = [x for x in store.list_promises() if x["text"] == "052前的旧伏笔"][0]
    assert old["tier"] == "chapter"                              # tier 回退 chapter
    assert old["payoff_min"] == 3 and old["payoff_max"] == 5     # 窗口按 setup 补算
    assert old["clues"] == []
    assert old.get("resolution") is None
    store.plant_promise("新伏笔", setup_chapter=1)
    new = [x for x in store.list_promises() if x["text"] == "新伏笔"][0]
    assert new.get("resolution") is None                         # 052 起默认 NONE(未回收)


def test_plant_promise_resolution_persists(store):
    """B21 收尾清理批:plant_promise 新增可选 resolution 参数,应落库可读回;
    不传 resolution 时保持向后兼容(默认 None,行为不变)。"""
    store.plant_promise("镇魂器悬念", setup_chapter=1, tier="book",
                        resolution="铜炉本是镇魂器,终将反噬铸炉者")
    row = [x for x in store.list_promises() if x["text"] == "镇魂器悬念"][0]
    assert row["resolution"] == "铜炉本是镇魂器,终将反噬铸炉者"


def test_overdue_flag_window_alignment():
    """Task1 跟进①⑤:_overdue_flag 与 promise_window_state 同口径。
    有窗口:overdue = max_chapter+1 > payoff_max(首边界 pmax=7 → max_chapter=7 即超期);
    book 层 payoff_max=None 永不超期;无窗口旧行才走 legacy slack。"""
    from scribe3.store import _overdue_flag
    p = {"status": "open", "kind": "promise", "setup_chapter": 2,
         "payoff_min": 3, "payoff_max": 7, "tier": "chapter"}
    assert _overdue_flag(p, max_chapter=7, slack=3) is True    # next_ch=8 > pmax=7,首边界
    assert _overdue_flag(p, max_chapter=6, slack=3) is False   # next_ch=7 ≤ pmax,窗内
    assert _overdue_flag(p, max_chapter=7, slack=99) is True   # 有窗口时 slack 不参与判定
    book = {"status": "open", "kind": "promise", "setup_chapter": 1,
            "payoff_min": 2, "payoff_max": None, "tier": "book"}
    assert _overdue_flag(book, max_chapter=999, slack=3) is False  # 书级永不超期
    legacy = {"status": "open", "kind": "promise", "setup_chapter": 1}
    assert _overdue_flag(legacy, max_chapter=5, slack=3) is True    # 1+3 < 5
    assert _overdue_flag(legacy, max_chapter=5, slack=10) is False  # legacy 分支吃 slack


def test_plant_promise_invalid_tier_raises(store):
    """Task1 跟进③:非法 tier 不再静默回退 chapter,直接 ValueError。"""
    import pytest
    with pytest.raises(ValueError):
        store.plant_promise("坏层级", setup_chapter=1, tier="saga")


def test_promise_window_state_pmin_fallback_tier_aware():
    """Task1 跟进④:payoff_min 缺失时按 tier 查 _TIER_WINDOW 回退(非一律 setup+1);
    payoff_min=0 的 falsy 显式值不再被误判为缺失。"""
    from scribe3.store import promise_window_state
    arc = {"status": "open", "kind": "promise", "setup_chapter": 1,
           "payoff_min": None, "payoff_max": 16, "tier": "arc", "last_refresh_at": None}
    # arc 窗口 lo=5 → pmin 回退 6;max_chapter=3 → next_ch=4 < 6 → pre_window
    assert promise_window_state(arc, max_chapter=3)["state"] == "pre_window"
    zero = {"status": "open", "kind": "promise", "setup_chapter": 3,
            "payoff_min": 0, "payoff_max": 9, "tier": "chapter", "last_refresh_at": None}
    # pmin=0 是显式值(is None 判定):next_ch=1 ≥ 0 → in_window(旧代码误回退 setup+1=4 → pre_window)
    assert promise_window_state(zero, max_chapter=0)["state"] == "in_window"


def test_update_promise_recomputes_window(store):
    """Task1 跟进②:setup_chapter/tier 变更且未显式给窗口值时按 tier 重算 payoff_min/max。"""
    store.plant_promise("会挪位置的伏笔", setup_chapter=1)
    pid = [x for x in store.list_promises() if x["text"] == "会挪位置的伏笔"][0]["id"]
    store.update_promise(pid, {"setup_chapter": 4})
    p = [x for x in store.list_promises() if x["id"] == pid][0]
    assert p["payoff_min"] == 5 and p["payoff_max"] == 7
    store.update_promise(pid, {"tier": "book"})
    p = [x for x in store.list_promises() if x["id"] == pid][0]
    assert p["tier"] == "book"
    assert p["payoff_min"] == 5 and p["payoff_max"] is None  # book:hi=None → pmax 显式清空
    # 显式给窗口值时尊重调用方,不重算
    store.update_promise(pid, {"setup_chapter": 2, "payoff_min": 9, "payoff_max": 12})
    p = [x for x in store.list_promises() if x["id"] == pid][0]
    assert p["payoff_min"] == 9 and p["payoff_max"] == 12


def test_arc_anchor_and_plan_roundtrip(store):
    """Task4 弧光:静态锚(五要素)set/get + 局部更新不清空 + arc_plan 有序 + latest_lie_belief。"""
    store.add_entity(Entity("role:柳怀玉", "character", "柳怀玉"))
    cid = "role:柳怀玉"
    store.set_char_anchors(cid, {"lie": "官法大过阴律", "arc_type": "disillusionment",
                                 "private_agenda": "查清父亲卷宗"})
    a = store.char_anchors(cid)
    assert a["lie"] == "官法大过阴律" and a["arc_type"] == "disillusionment"
    # 局部更新:只传 want,不清空已设的 lie
    store.set_char_anchors(cid, {"want": "升迁刑名"})
    a2 = store.char_anchors(cid)
    assert a2["want"] == "升迁刑名" and a2["lie"] == "官法大过阴律"
    # 不存在的角色 → 空 dict
    assert store.char_anchors("role:不存在的角色") == {}
    # arc_plan 里程碑:按 target_chapter 升序
    store.add_arc_beat(cid, beat_name="midpoint", target_chapter=6, lie_belief_target=50,
                       trigger_event="判牍改命")
    store.add_arc_beat(cid, beat_name="third_plot_point", target_chapter=10, lie_belief_target=20)
    plan = store.list_arc_plan(cid)
    assert [b["beat_name"] for b in plan] == ["midpoint", "third_plot_point"]
    assert plan[0]["lie_belief_target"] == 50 and plan[0]["trigger_event"] == "判牍改命"
    # delete_arc_beat 后消失
    store.delete_arc_beat(plan[0]["id"])
    assert [b["beat_name"] for b in store.list_arc_plan(cid)] == ["third_plot_point"]
    # lie_belief 走 char_state:latest_lie_belief 取 chapter<=upto 且非空的最新一条
    store.add_char_state(character_id=cid, chapter=2, change_type="belief",
                         summary="初疑", lie_belief=70, ingest_seq=2)
    store.add_char_state(character_id=cid, chapter=3, change_type="belief",
                         summary="又退回", lie_belief=78, ingest_seq=3)
    assert store.latest_lie_belief(cid, upto_chapter=3) == 78
    assert store.latest_lie_belief(cid, upto_chapter=2) == 70
    assert store.latest_lie_belief(cid, upto_chapter=1) is None


def test_list_char_states_exposes_lie_belief(store):
    """craft:list_char_states 须投影 lie_belief(migration 054/T5 写入),
    GET /char-states 透传本方法——不暴露该列则前端弧光曲线(T10 LieBeliefSpark)
    取不到实测值,只能回退 arc_plan 计划轨迹。"""
    store.add_entity(Entity("role:江砚", "character", "江砚"))
    cid = "role:江砚"
    store.add_char_state(character_id=cid, chapter=4, change_type="belief",
                         summary="信念动摇", lie_belief=62)
    rows = store.list_char_states(cid)
    assert len(rows) == 1
    assert "lie_belief" in rows[0], "list_char_states 投影缺 lie_belief 列"
    assert rows[0]["lie_belief"] == 62


# ===== 方案B任务24:story-import 逆向导入——reverse_current_state（纯查询）=====

def test_reverse_current_state_no_history_returns_empty(store):
    """无 char_state 记录的角色:reverse_current_state 返回空 dict(与 char_state_at
    的"空历史仍给壳"不同——逆向导入只关心"有没有可用的当前状态",没有就是空)。"""
    store.add_entity(Entity("role:无名", "character", "无名"))
    assert store.reverse_current_state("role:无名") == {}


def test_reverse_current_state_takes_latest_per_change_type(store):
    """同一角色 3 章各类 state 后,快照应取每类的最新章值(而非最早/累加错乱)。
    ability 在第1、3章各写一次 → 应取第3章值；relation/personality 各写一次。"""
    store.add_entity(Entity("role:甲", "character", "甲"))
    cid = "role:甲"
    store.add_char_state(character_id=cid, chapter=1, change_type="ability",
                         summary="学会入门剑法",
                         after_state={"ability_snapshot": {"内力": "初窥"}})
    store.add_char_state(character_id=cid, chapter=3, change_type="ability",
                         summary="内力大成",
                         after_state={"ability_snapshot": {"内力": "大成"}})
    store.add_char_state(character_id=cid, chapter=2, change_type="relation",
                         summary="与阿萤结盟",
                         after_state={"relation_snapshot": {"阿萤": "盟友"}})
    store.add_char_state(character_id=cid, chapter=2, change_type="personality",
                         summary="心境转变",
                         after_state={"personality_snapshot": "冷峻内敛"})

    snap = store.reverse_current_state(cid)

    assert snap["ability"]["chapter"] == 3, f"ability 应取最新章(3): {snap}"
    assert snap["abilities"]["内力"] == "大成", f"abilities 快照应是第3章值: {snap}"
    assert snap["relation"]["chapter"] == 2
    assert snap["relations"]["阿萤"] == "盟友"
    assert snap["personality"] == "冷峻内敛"


def test_reverse_current_state_belief_included(store):
    """belief 类 change_type 应把最新 lie_belief 值合入快照(逆向续写需要知道
    角色当前对错误信念的信奉度)。"""
    store.add_entity(Entity("role:乙", "character", "乙"))
    cid = "role:乙"
    store.add_char_state(character_id=cid, chapter=1, change_type="belief",
                         summary="初疑", lie_belief=30)
    store.add_char_state(character_id=cid, chapter=4, change_type="belief",
                         summary="深信", lie_belief=85)
    snap = store.reverse_current_state(cid)
    assert snap["lie_belief"] == 85, f"应取最新章(4)的 lie_belief: {snap}"
    assert snap["belief"]["chapter"] == 4


def test_reverse_current_state_cross_type_chapter_order(store):
    """B24 审查发现的正确性 bug:composite 首现于早期章、其最新记录却晚于
    专项类型(ability)最新记录时,派生键(abilities 等)必须按 chapter 全局时间序
    合并——而不是先按 change_type 折叠(latest_by_type,dict 按首次插入序遍历)
    再合并,否则更早插入的专项类型会在遍历顺序上"后到"从而覆盖更新的 composite 值。

    时间线:ch1 composite{剑术:初级} / ch2 ability{剑术:精通} / ch10 composite{剑术:入圣}
    正确结果应为 chapter 序最新的 ch10 composite 值:剑术=入圣。"""
    store.add_entity(Entity("role:丙", "character", "丙"))
    cid = "role:丙"
    store.add_char_state(character_id=cid, chapter=1, change_type="composite",
                         summary="初学剑术",
                         after_state={"ability_snapshot": {"剑术": "初级"}})
    store.add_char_state(character_id=cid, chapter=2, change_type="ability",
                         summary="剑术精进",
                         after_state={"ability_snapshot": {"剑术": "精通"}})
    store.add_char_state(character_id=cid, chapter=10, change_type="composite",
                         summary="剑术通神",
                         after_state={"ability_snapshot": {"剑术": "入圣"}})

    snap = store.reverse_current_state(cid)

    assert snap["abilities"]["剑术"] == "入圣", (
        f"应取 chapter 全局最新(10)的 composite 值,而非按 change_type 分组遍历序覆盖: {snap}")


# ===== 块四a-1 素材库 material(非正典材料;不进图谱/不被 ingest)=====

def test_material_roundtrip(store):
    """建/列(kind 过滤+updated_at DESC)/取/局部改/删 全链往返。"""
    import time as _t
    mid1 = store.add_material("北宋纸扎工艺", body="纸人骨架用竹篾……",
                              kind="research", tags=["民俗", "纸扎"], source="县志影印本")
    _t.sleep(0.01)   # updated_at 排序需要可分辨的时间差
    mid2 = store.add_material("桥段:井底还魂", kind="snippet")
    assert mid1 and mid2 and mid1 != mid2
    # 全列:按 updated_at DESC(后建在前)
    rows = store.list_materials()
    assert [r["id"] for r in rows] == [mid2, mid1]
    # kind 过滤
    only_research = store.list_materials(kind="research")
    assert [r["id"] for r in only_research] == [mid1]
    assert store.list_materials(kind="note") == []
    # get:全字段
    m = store.get_material(mid1)
    assert m["title"] == "北宋纸扎工艺" and m["kind"] == "research"
    assert m["tags"] == ["民俗", "纸扎"] and m["source"] == "县志影印本"
    assert m["created_at"] is not None and m["updated_at"] is not None
    # 局部更新:只改 body,不动其他字段;updated_at 刷新 → 排序反转
    _t.sleep(0.01)
    assert store.update_material(mid1, {"body": "改:骨架用桑皮纸捻"}) is True
    m2 = store.get_material(mid1)
    assert m2["body"] == "改:骨架用桑皮纸捻" and m2["title"] == "北宋纸扎工艺"
    assert [r["id"] for r in store.list_materials()] == [mid1, mid2]
    # 非法 kind → ValueError(应用层 422 之下的 store 防线)
    import pytest as _pt
    with _pt.raises(ValueError):
        store.update_material(mid1, {"kind": "diary"})
    with _pt.raises(ValueError):
        store.add_material("x", kind="diary")
    # 删:存在 True / 不存在 False
    assert store.delete_material(mid2) is True
    assert store.delete_material(mid2) is False
    assert [r["id"] for r in store.list_materials()] == [mid1]
    store.delete_material(mid1)
    assert store.list_materials() == []


def test_material_not_in_knowledge(store):
    """负验证:素材操作对 ingest 相关表(proposition/knows)零感知。"""
    before_props = store._query("SELECT count() FROM proposition GROUP ALL")
    before_knows = store._query("SELECT count() FROM knows GROUP ALL")
    mid = store.add_material("灵感:灯影戏开场", body="他知道妹妹三年前死了。", kind="inspiration")
    store.update_material(mid, {"body": "改一版。"})
    store.delete_material(mid)
    assert store._query("SELECT count() FROM proposition GROUP ALL") == before_props
    assert store._query("SELECT count() FROM knows GROUP ALL") == before_knows


def test_material_kind_emotion_module(store):
    """方案B任务15:EM/RH/TR 情绪模式库统一挂 kind="emotion_module"(卡内 id 前缀
    EM-/RH-/TR- 自行区分,互引用 id 字符串);MATERIAL_KINDS 白名单须放行,
    add_material 校验通过并可正常列出/取回。"""
    from scribe3.store import MATERIAL_KINDS
    assert "emotion_module" in MATERIAL_KINDS
    mid = store.add_material(
        "憋屈反杀", body='{"id":"EM-001","emotion":"憋屈","trigger":"当众羞辱",'
                        '"escalation":"隐忍蓄力","release":"当众反杀"}',
        kind="emotion_module")
    assert mid
    m = store.get_material(mid)
    assert m["kind"] == "emotion_module" and m["title"] == "憋屈反杀"
    assert [r["id"] for r in store.list_materials(kind="emotion_module")] == [mid]
    store.delete_material(mid)


# ============================================================
# 批C · 后端正确性小修(审计 P1-7 / P2-12 / D-3)
# ============================================================
import pytest  # noqa: E402
from scribe3.store import _overdue_flag  # noqa: E402


def test_apply_schema_failed_migration_not_marked_and_retryable(store, tmp_path):
    """P1-7: 迁移抛异常 → 不写 _migration 记录并向上抛;成功的仍标记;失败者下次可重试。

    迁移全用 IF NOT EXISTS/OVERWRITE(幂等重放无害),故任何异常都是真失败,
    绝不能标记已应用(否则永久跳过、schema 静默漂移)。
    """
    (tmp_path / "001_cgood.surql").write_text(
        "DEFINE TABLE IF NOT EXISTS _mig_cgood SCHEMALESS;", encoding="utf-8")
    (tmp_path / "002_cbad.surql").write_text(
        "DEFINE TABLE IF NOT EXISTS _mig_cbad SCHEMALESS;", encoding="utf-8")
    # 打桩点是 query_raw:_raw_query 已改走它(逐条校验多语句结果,见
    # test_raw_query_raises_on_any_failing_statement),不再经 SDK 裸 query。
    orig = store._db.query_raw
    fail = {"on": True}

    def flaky(surql, *a, **k):
        if fail["on"] and "_mig_cbad" in surql:
            raise RuntimeError("模拟迁移失败(连接抖动/语法错)")
        return orig(surql, *a, **k)

    store._db.query_raw = flaky
    try:
        with pytest.raises(RuntimeError):
            store.apply_schema(migrations_dir=str(tmp_path))
        ids = {r["id"] for r in store._query("SELECT meta::id(id) AS id FROM _migration")}
        assert "002_cbad" not in ids, "失败迁移不得标记已应用"
        assert "001_cgood" in ids, "成功迁移应正常标记"
        # 修复后重试:该迁移应被应用并标记(未被永久跳过)
        fail["on"] = False
        store.apply_schema(migrations_dir=str(tmp_path))
        ids2 = {r["id"] for r in store._query("SELECT meta::id(id) AS id FROM _migration")}
        assert "002_cbad" in ids2, "修复后重试应成功应用并标记"
    finally:
        store._db.query_raw = orig


def test_apply_schema_normal_migrations_unaffected(store):
    """P1-7 自审:正常迁移全绿(conftest 已 apply_schema),重复调用幂等不抛。"""
    store.apply_schema()  # 再跑一次:全已应用 → 无操作、不抛
    ids = {r["id"] for r in store._query("SELECT meta::id(id) AS id FROM _migration")}
    assert "056_injection_mode" in ids, "真迁移应已全部标记"


def test_apply_schema_concurrent_initializers_share_one_migration_record(store, tmp_path):
    """API 与独立 MCP 同时首次打开同一作品时，迁移记录不能发生唯一键竞态。"""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from uuid import uuid4

    from scribe3.store import SurrealStore

    (tmp_path / "001_schema_race.surql").write_text(
        "DEFINE TABLE IF NOT EXISTS _schema_race_probe SCHEMALESS;", encoding="utf-8")
    work = f"schema_race_{uuid4().hex}"
    stores = [SurrealStore(url=store.url, ns="scribe3", db=work) for _ in range(2)]
    barrier = Barrier(2)
    originals = [target._raw_query for target in stores]

    def synchronized_raw_query(original):
        waited_for_initial_schema = False

        def wrapped(surql, vars=None):
            nonlocal waited_for_initial_schema
            if (not waited_for_initial_schema
                    and surql.startswith("DEFINE TABLE IF NOT EXISTS _migration")):
                waited_for_initial_schema = True
                barrier.wait(timeout=5)
            return original(surql, vars)
        return wrapped

    for target, original in zip(stores, originals):
        target._raw_query = synchronized_raw_query(original)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(target.apply_schema, str(tmp_path)) for target in stores]
            for future in futures:
                future.result(timeout=15)
        rows = stores[0]._query(
            "SELECT meta::id(id) AS id FROM _migration WHERE meta::id(id)='001_schema_race'"
        )
        assert rows == [{"id": "001_schema_race"}]
    finally:
        for target in stores:
            target.close()


def test_late_approval_resolution_backfills_completed_write_trace(store):
    """工具完成先于批准 HTTP 回写时，审计仍必须证明该 MCP 写入已获批准。"""
    run_id = "run_late_approval_trace"
    store.upsert_ai_run_trace(run_id, status="streaming")
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.started", "call_id": "call_late", "name": "s3_add_character",
        "arguments": '{"oid":"role:许棹"}',
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.requested", "call_id": "call_late", "approval_id": "ap_late",
        "message": "批准写入?新增角色 role:许棹=许棹",
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.output", "call_id": "call_late", "tool_name": "s3_add_character",
        "output": "",
    })

    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.resolved", "call_id": "call_late", "approval_id": "ap_late",
        "choice": "once",
    })

    trace = store.get_ai_run_trace(run_id)
    assert trace["tool_calls"][0]["result_status"] == "written"
    assert trace["tool_outputs"][0]["decision"] == "once"
    assert trace["tool_outputs"][0]["result_status"] == "written"


def test_approved_write_without_tool_output_stays_unverified(store):
    """审批成功不是落库成功：网关未给 MCP 返回值时审计不得假报 written。"""
    run_id = "run_approved_without_tool_output"
    store.upsert_ai_run_trace(run_id, status="streaming")
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.started", "call_id": "call_no_output",
        "name": "s3_add_character_relation",
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.requested", "call_id": "call_no_output", "approval_id": "ap_no_output",
        "message": "批准写入?添加角色关系 role:甲→role:乙 [ally](章1)",
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.output", "call_id": "call_no_output",
        "tool_name": "s3_add_character_relation", "output": "", "output_available": False,
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.resolved", "call_id": "call_no_output", "approval_id": "ap_no_output",
        "choice": "once",
    })

    trace = store.get_ai_run_trace(run_id)
    assert trace["tool_calls"][0]["result_status"] == "approved_unverified"
    assert trace["tool_outputs"][0]["result_status"] == "approved_unverified"


def test_completed_run_fails_closed_for_unresolved_write_approval(store):
    """Run 结束时未决的正典写审批必须明确归档为未写入，不能留下假成功空洞。"""
    run_id = "run_expired_approval_trace"
    store.upsert_ai_run_trace(run_id, status="streaming")
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.started", "call_id": "call_expired", "name": "s3_add_character",
        "arguments": '{"oid":"role:未决"}',
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.requested", "call_id": "call_expired", "approval_id": "ap_expired",
        "message": "批准写入?新增角色 role:未决=未决",
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.output", "call_id": "call_expired", "tool_name": "s3_add_character",
        "output": "",
    })
    store.append_ai_run_trace_event(run_id, {"kind": "run.completed"})

    trace = store.get_ai_run_trace(run_id)
    assert trace["status"] == "completed"
    assert trace["tool_calls"][0]["result_status"] == "expired"
    assert trace["tool_outputs"][0]["decision"] == "timeout"
    assert trace["tool_outputs"][0]["result_status"] == "expired"
    assert trace["approvals"][-1]["status"] == "expired"


def test_expired_approval_status_is_not_overwritten_by_late_streaming(store):
    """collector 竞态晚到的活跃态不得让过期审批重新冒充可点击。"""
    run_id = "run_expired_status_sticky"
    store.upsert_ai_run_trace(run_id, status="approval_expired", error="approval_not_active")
    store.upsert_ai_run_trace(run_id, status="streaming")

    trace = store.get_ai_run_trace(run_id)
    assert trace["status"] == "approval_expired"
    assert trace["error"] == "approval_not_active"

    store.upsert_ai_run_trace(run_id, status="completed")
    store.upsert_ai_run_trace(run_id, status="streaming")
    assert store.get_ai_run_trace(run_id)["status"] == "completed"


def test_late_approval_after_completed_run_reconciles_timeout_trace(store):
    """网关终态先抵达时，稍后真实批准必须覆盖临时超时判定。"""
    run_id = "run_completed_before_approval"
    store.upsert_ai_run_trace(run_id, status="streaming")
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.started", "call_id": "call_late_terminal", "name": "s3_add_character",
        "arguments": '{"oid":"role:迟到批准"}',
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.requested", "call_id": "call_late_terminal",
        "approval_id": "ap_late_terminal", "message": "批准写入?新增角色 role:迟到批准=迟到批准",
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.output", "call_id": "call_late_terminal", "tool_name": "s3_add_character",
        "output": "",
    })
    store.append_ai_run_trace_event(run_id, {"kind": "run.completed"})
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.resolved", "call_id": "call_late_terminal",
        "approval_id": "ap_late_terminal", "choice": "once",
    })

    trace = store.get_ai_run_trace(run_id)
    assert trace["tool_calls"][0]["result_status"] == "written"
    assert trace["tool_outputs"][0]["decision"] == "once"
    assert trace["tool_outputs"][0]["result_status"] == "written"
    assert trace["approvals"][-1]["status"] == "resolved"


def test_completed_run_does_not_expire_an_already_resolved_approval(store):
    """审批已决后才来的 run.completed 不能倒灌成 timeout。"""
    run_id = "run_approved_before_completed"
    store.upsert_ai_run_trace(run_id, status="streaming")
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.started", "call_id": "call_approved", "name": "s3_add_character",
        "arguments": '{"oid":"role:已批准"}',
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.requested", "call_id": "call_approved",
        "approval_id": "ap_approved", "message": "批准写入?新增角色 role:已批准=已批准",
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "approval.resolved", "call_id": "call_approved",
        "approval_id": "ap_approved", "choice": "once",
    })
    store.append_ai_run_trace_event(run_id, {
        "kind": "tool.output", "call_id": "call_approved", "tool_name": "s3_add_character",
        "output": "",
    })
    store.append_ai_run_trace_event(run_id, {"kind": "run.completed"})

    trace = store.get_ai_run_trace(run_id)
    assert trace["tool_outputs"][0]["decision"] == "once"
    assert trace["tool_outputs"][0]["result_status"] == "written"
    assert not any(row.get("status") == "expired" for row in trace["approvals"])


def test_set_intent_merge_preserves_unpassed_fields(store):
    """P2-12: 只 set reader_feeling 不传 emotional_arc → emotional_arc 保留(MERGE 非整替)。"""
    store.set_intent({"reader_feeling": "压抑见微光", "emotional_arc": "由怯到决",
                      "red_lines": "不洗白反派"})
    store.set_intent({"reader_feeling": "苦中带甜"})  # 仅传一字段
    got = store.get_intent()
    assert got["reader_feeling"] == "苦中带甜"
    assert got["emotional_arc"] == "由怯到决", "未传字段应保留,不被抹空"
    assert got["red_lines"] == "不洗白反派"


def test_set_intent_merge_preserves_thresholds(store):
    """P2-12: 局部更新不得抹掉此前设的 overdue_threshold / word goals。"""
    store.set_intent({"reader_feeling": "A", "emotional_arc": "B", "red_lines": "C",
                      "overdue_threshold": 7, "total_word_goal": 100000})
    store.set_intent({"reader_feeling": "A2"})
    got = store.get_intent()
    assert got.get("overdue_threshold") == 7, "未传阈值应保留"
    assert got.get("total_word_goal") == 100000, "未传字数目标应保留"


def test_timeline_promise_overdue_single_source(store):
    """D-3: timeline 伏笔泳道 overdue 走 _overdue_flag 单源(不再恒 False,与 /promises 一致)。"""
    store.plant_promise("早埋未收的伏笔", setup_chapter=1, tier="chapter")  # pmax=4
    store.add_event(Event("ev:推进", "act", story_time=8, motivated_by_goal="g"))  # max_chapter=8
    items = store.timeline(ch_from=1, ch_to=8)
    setups = [i for i in items if i["kind"] == "promise_setup"]
    assert setups, "应有伏笔埋点条目"
    assert setups[0]["refs"]["overdue"] is True, \
        "超期伏笔在 timeline 泳道应 overdue=True(与 /promises 一致)"
    p = store.list_promises()[0]
    assert setups[0]["refs"]["overdue"] == _overdue_flag(p, store.max_chapter(), 3), \
        "timeline overdue 必须与 _overdue_flag 单源一致"


def test_timeline_promise_overdue_book_tier_false(store):
    """D-3: book 级伏笔在 timeline 泳道永不超期(与单源一致)。"""
    store.plant_promise("书级悬念", setup_chapter=1, tier="book")  # payoff_max=None
    store.add_event(Event("ev:远推", "act", story_time=99, motivated_by_goal="g"))
    items = store.timeline(ch_from=1, ch_to=99)
    setups = [i for i in items if i["kind"] == "promise_setup"]
    assert setups and setups[0]["refs"]["overdue"] is False, "book 级伏笔不应标超期"
