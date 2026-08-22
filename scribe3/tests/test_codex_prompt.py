"""CX-Task 6 · 设定进 prompt(注册表驱动 + 限知门控)+ faction 一致性校验。

背景(计划 `docs/superpowers/plans/2026-07-14-codex-layer-redesign.md` Task 6;
spec `docs/superpowers/specs/2026-07-14-codex-layer-redesign.md` §4):
`_codex_block` 注入势力时此前只取 `name + ideology[:18]`(app.py 旧实现)——作者精心写的
~25 个注册表字段(origin/key_figures/artifacts/internal_factions/structure/...)写作时
一个字都用不上。本文件验证:

① 势力段改为按 `codex_schema.prompt_keys('faction')` 注册表驱动注入(不再只有
   name+ideology[:18]);
② secret_capable 字段经【既有】限知链门控——命题桥(codex_secret_bridge)生成的
   proposition 被 `knowledge.project_frame` 投影消费,不是另建一套判断;用真桥接
   命题验证,不 mock;
   🚨 关键红线(U-003 三档可见性,2026-07-15):fail-closed 现在只是【生成/限知续写
   路径】(for_generation=True)的性质——拿不到 focalizer 时一律不注入,即便
   reveal=True(作者全知视角,历史上这个开关只对角色 backstory 生效)也不例外。
   作者/主编对话路径(for_generation=False,_codex_block 默认值)不受此约束:
   作者自己标记的势力秘密在对话里直接可见,这不是"泄露给读者",是"跟作者商量剧情"
   (旧版不分场合都走 focalizer 知情判据,过钝地把主编自己也挡在门外)。
③ 单势力注入长度预算,超出截断标注"…(略)";
④ 该势力的 entity_relation 摘要进块:perception_a/b 两档都注入;truth(主编独知)
   只在生成路径(for_generation=True)永不注入,作者/主编对话路径(False)会注入;
⑤ `validate_faction_consistency` 的三条(+1 可选)结构化一致性断言,只读不落库;
⑥ 端到端接线:真实生成入口 `_editor_write_system` 与真实作者对话入口 `_editor_system`
   默认调用方式,各自对 chief_only 字段的取舍与 `_codex_block` 单元测试结论一致——
   不只测函数单元,还测两个真实调用点(仓库教训:每新开一个注入点都泄露过一次)。
"""
from scribe3.app import _codex_block, _editor_system, _editor_write_system
from scribe3.codex_secret_bridge import sync_faction_secrets
from scribe3.codex_validate import validate_faction_consistency
from scribe3.ontology import Entity, Event, Fact, KnowledgeEdge


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
    block = _codex_block(store, reveal=True, request_text="衔尾蛇秘会")
    assert "衔尾蛇秘会" in block
    assert "长老议事" in block, "旧实现只有 name+ideology[:18],新实现须结构化注入 structure 字段"
    assert "金字塔" in block, "structure.type 应被结构化注入"
    assert "摄魂" in block, "key_figures[].known_abilities 应被结构化注入"


def test_codex_block_faction_backward_compatible_for_legacy_minimal_row(store):
    """向后兼容:只有 name+ideology 的老势力,注入效果不应退化(至少不比旧实现差)。"""
    store.add_faction("光明会", ideology="启蒙众生")
    block = _codex_block(store, reveal=True, request_text="光明会")
    assert "光明会" in block
    assert "启蒙众生" in block


# ============================================================
# ② secret 字段经限知门控(真桥接命题 + project_frame,不 mock)
# ============================================================

FACTION = "衔尾蛇秘会"
ENTITY_ID = f"faction:{FACTION}"


def test_codex_block_hides_secret_field_from_focalizer_who_does_not_know(store):
    """② 焦点角色帧外(无 KnowledgeEdge)→ 桥接命题对应的字段不注入。

    2026-07-15(U-003 三档可见性):这条 fail-closed 规则现在只是【生成/限知续写路径】
    (for_generation=True)的性质,须显式传入——作者/主编对话路径(for_generation=False,
    默认值)不受 focalizer 知情与否影响,见 test_codex_prompt_adversarial.py 里
    secret_agenda/author-dialogue 对照测试。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)

    block = _codex_block(store, reveal=False, focalizer="role:不知情的旁观者", chapter=5,
                         for_generation=True, request_text=FACTION)
    assert "源自前朝遗族的复国密谋" not in block, "焦点者无 KnowledgeEdge,秘密不应注入"


def test_codex_block_shows_secret_field_when_focalizer_knows(store):
    """② 反例:焦点者确有 KnowledgeEdge(project_frame 帧内)→ 该字段正常注入
    (生成/限知续写路径,for_generation=True)。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "origin")
    store.add_entity(Entity("role:知情人", "character", "知情人"))   # P3-b:knower 须真实存在
    store.add_knowledge(KnowledgeEdge("role:知情人", fact_id, since_chapter=1))

    block = _codex_block(store, reveal=False, focalizer="role:知情人", chapter=5,
                         for_generation=True, request_text=FACTION)
    assert "源自前朝遗族的复国密谋" in block, "焦点者知情(project_frame 帧内)应注入该字段"


def test_codex_block_fail_closed_when_focalizer_missing_even_if_reveal_true(store):
    """🚨 红线证据(生成/限知续写路径,for_generation=True):拿不到 focalizer 时,
    一律不注入势力 secret_capable 字段——即便 reveal=True(作者全知视角,历史上这个
    开关会放行角色 backstory)也不例外。

    这是新引入的势力 secret 字段与既有角色 backstory 掩码逻辑唯一不同之处:
    backstory 的掩码开关是 reveal;势力 secret 字段(生成路径)的掩码开关是"能否证明
    focalizer 知情"(project_frame 投影),reveal 对它不生效——宁可少给也不能泄密。

    2026-07-15 修订(U-003 三档可见性):
    - 显式传 for_generation=True——"fail-closed" 现在只是生成/限知续写路径的性质,
      作者/主编对话路径(for_generation=False,函数默认值)不再受此约束,见
      test_codex_block_secret_capable_visible_in_author_dialogue_without_focalizer。
    - 字段从 secret_agenda 换成 origin:secret_agenda 现在是 chief_only(仅主编可见),
      走的是独立的结构性名单门控(不依赖 focalizer/knows 边),专门测试见
      test_codex_prompt_adversarial.py 的 secret_agenda 回归锚。"""
    store.add_faction(FACTION, origin="连核心层都不知道的真相", origin_secret=True)
    _sync(store, FACTION)

    block_reveal_true = _codex_block(store, reveal=True, focalizer="", chapter=5,
                                     for_generation=True, request_text=FACTION)
    assert "连核心层都不知道的真相" not in block_reveal_true, (
        "生成路径:没有可验证身份的 focalizer 时,即便 reveal=True 也不得注入 secret 字段"
        "(fail-closed)")

    block_reveal_false = _codex_block(store, reveal=False, focalizer="", chapter=5,
                                      for_generation=True, request_text=FACTION)
    assert "连核心层都不知道的真相" not in block_reveal_false

    # 老调用方式(不传 focalizer/chapter),但仍显式钉住生成路径:
    block_default_call = _codex_block(store, for_generation=True)
    assert "连核心层都不知道的真相" not in block_default_call


def test_codex_block_secret_capable_visible_in_author_dialogue_without_focalizer(store):
    """U-003 三档可见性的另一半(与上一测试对照):作者/主编对话
    (for_generation=False,_codex_block 的默认值)里,即便没有 focalizer,作者自己
    标记的 secret_capable 字段也直接可见——这不是"泄露给读者",是"跟作者商量剧情"。
    旧版不分场合都走 focalizer 知情判据,把主编自己也挡在了门外,是过钝的实现。"""
    store.add_faction(FACTION, origin="连核心层都不知道的真相", origin_secret=True)
    _sync(store, FACTION)

    block = _codex_block(store, reveal=True, focalizer="", chapter=5, request_text=FACTION)
    assert "连核心层都不知道的真相" in block, (
        "作者/主编对话(for_generation=False)应直接看到作者自己标记的势力秘密")


def test_codex_block_non_secret_fields_unaffected_by_gating(store):
    """门控只应约束 secret_capable 且标记为真的字段;普通字段不受 focalizer 影响
    (作者/主编对话路径,for_generation 默认 False)。"""
    store.add_faction(FACTION, motto="尾衔其首,生生不息")
    block = _codex_block(store, reveal=False, focalizer="role:任何人", chapter=1,
                         request_text=FACTION)
    assert "尾衔其首,生生不息" in block, "非 secret 字段不应被限知门控误伤"


def test_codex_block_public_fields_still_injected_in_generation_path(store):
    """U-003 三档 × 两路径矩阵补齐第 2 格:公开字段(非 secret_capable、非 chief_only)
    在**生成/限知续写路径**(for_generation=True)也应正常注入——for_generation 只应
    影响 secret_capable/chief_only 两类字段的门控分支,不能连累普通字段被误伤为"也要
    等 focalizer 知情证据"。"""
    store.add_faction(FACTION, motto="尾衔其首,生生不息", leader="老祖")
    block = _codex_block(store, reveal=False, focalizer="role:任何人", chapter=1,
                         for_generation=True, request_text=FACTION)
    assert "尾衔其首,生生不息" in block, "公开字段在生成路径也应正常注入"
    assert "老祖" in block, "公开字段(领袖)在生成路径也应正常注入"


# ============================================================
# ③ 长度预算:单势力注入超上限时截断
# ============================================================

def test_codex_block_truncates_faction_over_length_budget(store):
    long_text = "极" * 600
    store.add_faction("长舌势力", ideology=long_text, public_face=long_text)

    unnamed = _codex_block(store, reveal=True)
    assert "长舌势力" in unnamed
    assert long_text not in unnamed, "未点名势力只留名片，禁止再走 400+长档"

    block = _codex_block(store, reveal=True, request_text="长舌势力")
    section = _faction_section(block)
    assert "长舌势力" in section
    assert long_text in section or section.count("极") >= 500
    assert len(section) <= 2600, "点名势力走 clip_for(faction_public)=2500，不再 400+…(略)"
    assert "…(略)" not in section


# ============================================================
# ④ 关系网注入:perception_a/b 进块,truth 永不注入
# ============================================================

def test_codex_block_injects_relation_perception_but_never_truth_in_generation_path(store):
    """④ 关系网注入:perception_a/b 两档都进块;truth(主编独知)在**生成/限知续写
    路径**(for_generation=True)永不注入——U-003 三档可见性:truth 不是给生成模型
    看的。作者/主编对话路径(for_generation=False)truth 会注入,与
    codex_schema.chief_only 字段同级,见下一测试。"""
    store.add_faction("秘会")
    store.add_faction("天龙座")
    store.add_entity_relation(
        a="faction:秘会", b="faction:天龙座", relation_type="臣服",
        perception_a="虚与委蛇,视为台阶",
        perception_b="视其为地球代理人",
        truth="秘会实为寄生外星文明的傀儡", since_chapter=1)

    block = _codex_block(store, reveal=True, chapter=5, for_generation=True,
                         request_text="秘会 天龙座")
    assert "虚与委蛇" in block, "perception_a 应注入"
    assert "地球代理人" in block, "perception_b 应注入"
    assert "寄生外星文明的傀儡" not in block, "truth 是主编独知的真相,生成路径永不注入 prompt"


def test_codex_block_injects_relation_truth_in_author_dialogue_path(store):
    """U-003:truth 在作者/主编对话(for_generation=False,_codex_block 默认值)里会
    注入——这是本次修订相对旧版的行为变化(旧版无论何种场合都不注入 truth,过钝地把
    主编自己也挡在了外面)。"""
    store.add_faction("秘会乙")
    store.add_faction("天龙座乙")
    store.add_entity_relation(
        a="faction:秘会乙", b="faction:天龙座乙", relation_type="臣服",
        truth="秘会乙实为寄生外星文明的傀儡", since_chapter=1)

    block = _codex_block(store, reveal=True, chapter=5, request_text="秘会乙 天龙座乙")
    assert "寄生外星文明的傀儡" in block, "作者/主编对话应能看到主编独知的关系真相"


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


# ============================================================
# ⑥ 端到端接线:真实生成入口 _editor_write_system vs 真实作者对话入口 _editor_system
#    默认调用方式——不只测 _codex_block 单元,还测两个真实调用点没有漏传 for_generation。
# ============================================================

def test_editor_write_system_excludes_chief_only_field_end_to_end(store):
    """_editor_write_system 是唯一的生成/限知续写入口(内部恒调用
    _editor_system(..., for_generation=True))。secret_agenda(chief_only)不得出现在
    真实续写 instructions 里,即便该势力没有其它任何遮挡内容。"""
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)

    instructions = _editor_write_system(store, focalizer="", chapter=1)
    assert "连核心层都不知道的真相" not in instructions, (
        "真实生成入口 _editor_write_system 不得泄露 chief_only 字段")


def test_editor_system_default_includes_chief_only_field_for_author_dialogue(store):
    """_editor_system 默认(for_generation=False)是作者/主编对话入口——chat_stream/
    chat_agentic_stream 均以此方式调用(不传 for_generation)。同一份数据,这条路径
    应看得到 secret_agenda——这正是"仅主编可见"的字面含义。"""
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)

    sysmsg = _editor_system(store, request_text=FACTION)
    assert "连核心层都不知道的真相" in sysmsg, (
        "作者/主编对话入口点名后应看到 secret_agenda(仅主编可见 = 主编看得见)")


def test_editor_write_system_excludes_bridge_mirror_in_gated_injection_branch(store):
    """U-003 补洞:M6 全知转储有**两条分支**,上面两测只覆盖了 fallback 那条。

    `_editor_system` 的作者全知视角(focalizer 空)会把 facts 全量转储进 prompt。它的
    lines 有两个来源:
      · fallback 分支(本书从未配 injection_mode)→ app._line(f) 渲染;
      · 门控态分支(本书有 ≥1 条 fact 配了 injection_mode)→ brief._fact_inject_line(f) 渲染。
    命题桥把势力 secret 字段镜像成 proposition,两条分支都会把它裸转储出来
    ("- faction:X · secret_agenda:明文(私密/伏线)"),绕过 _faction_prompt_block 的三档门控。

    本测试专打**门控态分支**:给本书随便一条 fact 配上 injection_mode(assemble_injection
    就不再 fallback),再确认生成路径仍不泄露。修法是在 **Fact 层**过滤(结构判据:
    entity_id 以 "faction:" 开头 + attribute ∈ secret_capable_keys,与命题桥创建时的谓词
    同源),不赌两个渲染函数的字符串格式永远一致。
    """
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True,
                      origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)

    # 让本书进入"门控态"(fallback=False):给一条普通命题显式配 injection_mode。
    store.add_entity(Entity("role:某人", "character", "某人"))
    store.add_fact(Fact("fact:普通事实", "role:某人", "职业", "铜匠", 1))
    store._execute_write(
        "UPDATE proposition SET injection_mode='always' WHERE attribute='职业'", {})

    from scribe3.brief import assemble_injection
    assert assemble_injection(store, 1)["fallback"] is False, (
        "前置条件:本测试必须走门控态分支(chosen),否则测的还是 fallback,白测")

    instructions = _editor_write_system(store, focalizer="", chapter=1)
    for leak in ("连核心层都不知道的真相", "源自前朝遗族的复国密谋"):
        assert leak not in instructions, (
            f"门控态分支(chosen)泄露了桥接镜像:{leak!r}\ninstructions={instructions!r}")

    # 反向:非桥接的普通事实照常转储(别把全知视角一起削没了)
    assert "铜匠" in instructions, "普通(非桥接)事实在全知视角应照常注入,过滤不能误伤"
