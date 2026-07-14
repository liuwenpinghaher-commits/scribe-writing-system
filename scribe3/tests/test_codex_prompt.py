"""CX-Task 6 · 设定进 prompt(注册表驱动 + 限知门控)+ faction 一致性校验。

背景(计划 `docs/superpowers/plans/2026-07-14-codex-layer-redesign.md` Task 6;
spec `docs/superpowers/specs/2026-07-14-codex-layer-redesign.md` §4):
`_codex_block` 注入势力时此前只取 `name + ideology[:18]`(app.py 旧实现)——作者精心写的
~25 个注册表字段(origin/key_figures/artifacts/internal_factions/structure/...)写作时
一个字都用不上。本文件验证:

① 势力段改为按 `codex_schema.prompt_keys('faction')` 注册表驱动注入(不再只有
   name+ideology[:18]);
② secret_capable 字段经【既有】限知链门控——命题桥(codex_secret_bridge)生成的
   proposition 被 `knowledge.project_frame` 投影 + `context_assembler._secret_fact_ids`
   权威判定消费,不是另建一套判断;用真桥接命题验证,不 mock;
   🚨 关键红线:拿不到 focalizer 时 fail-closed(宁可少给也不能泄密)——即便
   reveal=True(作者全知视角,历史上这个开关只对角色 backstory 生效)也不例外;
③ 单势力注入长度预算,超出截断标注"…(略)";
④ 该势力的 entity_relation 摘要进块,只含 perception_a/b,truth(主编独知)永不注入;
⑤ `validate_faction_consistency` 的三条(+1 可选)结构化一致性断言,只读不落库。
"""
from scribe3.app import _codex_block
from scribe3.codex_secret_bridge import sync_faction_secrets
from scribe3.codex_validate import validate_faction_consistency
from scribe3.ontology import Entity, Event, KnowledgeEdge


def _sync(store, name: str) -> dict:
    """回读势力行后跑命题桥(与 app.py POST /factions 落库后的调用方式一致,
    见 test_codex_secret_bridge.py 同款辅助——不重新发明,直接复用同一套装配顺序)。"""
    row = store.get_faction(name)
    assert row is not None, f"测试前置条件:势力 {name!r} 应已存在"
    return sync_faction_secrets(store, name, row)


def _bridge_fact_id(store, entity_id: str, attribute: str) -> str:
    """裸查桥接命题的 fact id(`fact:{local}`),供测试直接给它挂 KnowledgeEdge。"""
    rows = store._query(
        "SELECT meta::id(id) AS local FROM proposition "
        "WHERE entity_id=$eid AND attribute=$attr AND source='codex_bridge' LIMIT 1",
        {"eid": entity_id, "attr": attribute})
    assert rows, f"未找到桥接命题: {entity_id}/{attribute}(先调用 _sync)"
    return f"fact:{rows[0]['local']}"


def _faction_section(block: str) -> str:
    """从整块设定圣经文本里摘出「〔势力〕」这一段(到下一个〔…〕之前或结尾)。"""
    start = block.index("〔势力〕")
    rest = block[start:]
    nxt = rest.find("〔", 1)
    return rest if nxt == -1 else rest[:nxt]


# ============================================================
# ① 注册表驱动注入(不再只有 name+ideology[:18])
# ============================================================

def test_codex_block_injects_registry_fields_not_just_name_ideology(store):
    store.add_faction(
        "衔尾蛇秘会", ideology="尾衔其首", status="active", leader="老祖",
        known_members=["二当家", "三使者"],
        structure={"type": "金字塔", "core_size": 7,
                   "decision_mechanism": "长老议事", "succession": "血脉相承"},
        key_figures=[{"name": "老祖", "generation": 1, "status": "active",
                     "known_abilities": "摄魂"}],
    )
    block = _codex_block(store, reveal=True)
    assert "衔尾蛇秘会" in block
    assert "长老议事" in block, "旧实现只有 name+ideology[:18],新实现须结构化注入 structure 字段"
    assert "金字塔" in block, "structure.type 应被结构化注入"
    assert "摄魂" in block, "key_figures[].known_abilities 应被结构化注入"


def test_codex_block_faction_backward_compatible_for_legacy_minimal_row(store):
    """向后兼容:只有 name+ideology 的老势力,注入效果不应退化(至少不比旧实现差)。"""
    store.add_faction("光明会", ideology="启蒙众生")
    block = _codex_block(store, reveal=True)
    assert "光明会" in block
    assert "启蒙众生" in block


# ============================================================
# ② secret 字段经限知门控(真桥接命题 + project_frame,不 mock)
# ============================================================

FACTION = "衔尾蛇秘会"
ENTITY_ID = f"faction:{FACTION}"


def test_codex_block_hides_secret_field_from_focalizer_who_does_not_know(store):
    """② 焦点角色帧外(无 KnowledgeEdge)→ 桥接命题对应的字段不注入。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)

    block = _codex_block(store, reveal=False, focalizer="role:不知情的旁观者", chapter=5)
    assert "源自前朝遗族的复国密谋" not in block, "焦点者无 KnowledgeEdge,秘密不应注入"


def test_codex_block_shows_secret_field_when_focalizer_knows(store):
    """② 反例:焦点者确有 KnowledgeEdge(project_frame 帧内)→ 该字段正常注入。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "origin")
    store.add_entity(Entity("role:知情人", "character", "知情人"))   # P3-b:knower 须真实存在
    store.add_knowledge(KnowledgeEdge("role:知情人", fact_id, since_chapter=1))

    block = _codex_block(store, reveal=False, focalizer="role:知情人", chapter=5)
    assert "源自前朝遗族的复国密谋" in block, "焦点者知情(project_frame 帧内)应注入该字段"


def test_codex_block_fail_closed_when_focalizer_missing_even_if_reveal_true(store):
    """🚨 红线证据:拿不到 focalizer 时,一律不注入势力 secret 字段——
    即便 reveal=True(作者全知视角,历史上这个开关会放行角色 backstory)也不例外。

    这是新引入的势力 secret 字段与既有角色 backstory 掩码逻辑唯一不同之处:
    backstory 的掩码开关是 reveal;势力 secret 字段的掩码开关是"能否证明 focalizer
    知情"(project_frame 投影),reveal 对它不生效——宁可少给也不能泄密。"""
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)

    block_reveal_true = _codex_block(store, reveal=True, focalizer="", chapter=5)
    assert "连核心层都不知道的真相" not in block_reveal_true, (
        "没有可验证身份的 focalizer 时,即便 reveal=True 也不得注入 secret 字段(fail-closed)")

    block_reveal_false = _codex_block(store, reveal=False, focalizer="", chapter=5)
    assert "连核心层都不知道的真相" not in block_reveal_false

    block_default_call = _codex_block(store)   # 调用方完全不传 focalizer/chapter(老调用方式)
    assert "连核心层都不知道的真相" not in block_default_call


def test_codex_block_non_secret_fields_unaffected_by_gating(store):
    """门控只应约束 secret_capable 且标记为真的字段;普通字段不受 focalizer 影响。"""
    store.add_faction(FACTION, motto="尾衔其首,生生不息")
    block = _codex_block(store, reveal=False, focalizer="role:任何人", chapter=1)
    assert "尾衔其首,生生不息" in block, "非 secret 字段不应被限知门控误伤"


# ============================================================
# ③ 长度预算:单势力注入超上限时截断
# ============================================================

def test_codex_block_truncates_faction_over_length_budget(store):
    long_text = "极" * 600
    store.add_faction("长舌势力", ideology=long_text, public_face=long_text)

    block = _codex_block(store, reveal=True)
    section = _faction_section(block)
    assert "长舌势力" in section
    assert "…(略)" in section, "超预算应截断并标注省略,不炸 prompt"
    assert len(section) < len(long_text), "截断后长度应远小于原始超长字段"


# ============================================================
# ④ 关系网注入:perception_a/b 进块,truth 永不注入
# ============================================================

def test_codex_block_injects_relation_perception_but_never_truth(store):
    store.add_faction("秘会")
    store.add_faction("天龙座")
    store.add_entity_relation(
        a="faction:秘会", b="faction:天龙座", relation_type="臣服",
        perception_a="虚与委蛇,视为台阶",
        perception_b="视其为地球代理人",
        truth="秘会实为寄生外星文明的傀儡", since_chapter=1)

    block = _codex_block(store, reveal=True, chapter=5)
    assert "虚与委蛇" in block, "perception_a 应注入"
    assert "地球代理人" in block, "perception_b 应注入"
    assert "寄生外星文明的傀儡" not in block, "truth 是主编独知的真相,永不注入 prompt"


# ============================================================
# ⑤ validate_faction_consistency:三条(+1 可选)结构化一致性断言
# ============================================================

def test_validate_faction_consistency_empty_when_consistent(store):
    """基线:互不冲突的势力 → 空列表,不误报。"""
    store.add_faction("甲盟", structure={"core_size": 3},
                      key_figures=[{"name": "甲", "status": "active"}])
    assert validate_faction_consistency(store) == []


def test_validate_faction_consistency_detects_relation_contradiction(store):
    """A 说敌对 B,B 侧独立一条边说结盟 A(两条独立边,非同边内认知不对称)→ 报冲突。"""
    store.add_faction("甲盟")
    store.add_faction("乙盟")
    store.add_entity_relation(a="faction:甲盟", b="faction:乙盟", relation_type="敌对")
    store.add_entity_relation(a="faction:乙盟", b="faction:甲盟", relation_type="结盟")

    issues = validate_faction_consistency(store)
    hit = next((i for i in issues if i["kind"] == "relation_contradiction"), None)
    assert hit is not None, f"应检出关系矛盾,实际: {issues}"
    assert hit["severity"]
    assert "甲盟" in hit["detail"] and "乙盟" in hit["detail"]


def test_validate_faction_consistency_allows_asymmetric_perception_same_edge(store):
    """同一条边内 perception_a/b 不对称是合法的错误认知,不应触发冲突。"""
    store.add_faction("甲盟")
    store.add_faction("乙盟")
    store.add_entity_relation(a="faction:甲盟", b="faction:乙盟", relation_type="臣服",
                              perception_a="虚与委蛇", perception_b="真心臣服")
    issues = validate_faction_consistency(store)
    assert not any(i["kind"] == "relation_contradiction" for i in issues)


def test_validate_faction_consistency_ignores_time_evolved_relation(store):
    """已被 until_chapter 终止的旧关系代表时间演化(关系破裂后重归于好之类),
    不是同时矛盾,不应误报。"""
    store.add_faction("甲盟")
    store.add_faction("乙盟")
    store.add_entity_relation(a="faction:甲盟", b="faction:乙盟", relation_type="敌对",
                              since_chapter=1)
    store.end_entity_relation("faction:甲盟", "faction:乙盟", until_chapter=5)
    store.add_entity_relation(a="faction:甲盟", b="faction:乙盟", relation_type="结盟",
                              since_chapter=5)

    issues = validate_faction_consistency(store)
    assert not any(i["kind"] == "relation_contradiction" for i in issues)


def test_validate_faction_consistency_detects_key_figures_exceed_core_size(store):
    """key_figures 里 status=active 的人数 > structure.core_size → 报冲突。"""
    store.add_faction(
        "甲盟",
        structure={"type": "扁平", "core_size": 1},
        key_figures=[
            {"name": "甲", "status": "active"},
            {"name": "乙", "status": "active"},
            {"name": "丙", "status": "dead"},
        ])
    issues = validate_faction_consistency(store)
    hit = next((i for i in issues if i["kind"] == "key_figures_exceed_core_size"), None)
    assert hit is not None, f"应检出核心圈超编,实际: {issues}"
    assert hit["faction"] == "甲盟"
    assert "2" in hit["detail"] and "1" in hit["detail"]


def test_validate_faction_consistency_detects_artifact_transfer_beyond_max_chapter(store):
    """artifacts 的 last_transfer_chapter > 当前最大章 → 报冲突。"""
    store.add_event(Event("ev:普通事件", "普通", story_time=5))  # max_chapter() == 5
    store.add_faction(
        "甲盟",
        artifacts=[{"artifact_name": "回煞炉", "artifact_type": "邪器",
                   "current_power_level": "强", "decay_rate": "缓慢",
                   "last_transfer_chapter": 99}])
    issues = validate_faction_consistency(store)
    hit = next((i for i in issues if i["kind"] == "artifact_transfer_beyond_max_chapter"), None)
    assert hit is not None, f"应检出信物传承章超前,实际: {issues}"
    assert hit["faction"] == "甲盟"
    assert "99" in hit["detail"]


def test_validate_faction_consistency_flags_power_share_over_100_percent(store):
    """(可选)internal_factions 的 power_share 总和明显 >100% → 报提示。"""
    store.add_faction(
        "甲盟",
        internal_factions=[
            {"name": "鹰派", "power_share": "70%"},
            {"name": "鸽派", "power_share": "60%"},
        ])
    issues = validate_faction_consistency(store)
    assert any(i["kind"] == "power_share_over_total" for i in issues)


def test_faction_consistency_endpoint_readonly(store):
    """GET /faction-consistency:只读端点,不落库,直接暴露 validate_faction_consistency。"""
    import scribe3.app as A
    from fastapi.testclient import TestClient

    A.set_store(store)
    client = TestClient(A.app)
    store.add_faction("甲盟")
    store.add_faction("乙盟")
    store.add_entity_relation(a="faction:甲盟", b="faction:乙盟", relation_type="敌对")
    store.add_entity_relation(a="faction:乙盟", b="faction:甲盟", relation_type="结盟")

    r = client.get("/faction-consistency")
    assert r.status_code == 200
    body = r.json()
    assert any(i["kind"] == "relation_contradiction" for i in body)
