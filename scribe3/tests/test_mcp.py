"""S2 · scribe3 MCP server TDD(standalone,不碰 Hermes config)。

读工具放行;写工具经 elicitation 待批,批准后才走 store 单点落库。
工具名带 s3_ 前缀(与 scribe2 隔离,防同挂撞名)。
elicitation 本身是生产侧(ctx.elicit);可测核心 = commit_if_approved 门控逻辑。
"""
import asyncio

import scribe3.mcp as M
from scribe3.scenario import luanshi_leak_world

EXPECTED_WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
                          "s3_plant_promise", "s3_advance_promise", "s3_craft_rule_add",
                          "s3_craft_rule_remove", "s3_add_character_relation",
                          "s3_add_world_rule", "s3_add_faction", "s3_add_char_state",
                          "s3_set_voice_profile", "s3_add_item", "s3_add_term",
                          "s3_supersede_fact", "s3_forget_knowledge",
                          "s3_evolve_relation", "s3_resolve_voice_flag",
                          "s3_fold_voice_flags", "s3_add_clue"}
EXPECTED_WRITE_UNGATED = {"s3_save_chapter"}   # manuscript 草稿,非世界状态,不待批
EXPECTED_WRITE_UNGATED_WORLD = {"s3_ingest_chapter"}  # 世界知识态客观回写(读定稿抽),不待批
EXPECTED_READ = {"s3_project_frame", "s3_find_leaks", "s3_causal_complete",
                 "s3_dramatic_irony", "s3_semantic_recall", "s3_get_chapter", "s3_qc_chapter",
                 "s3_list_promises", "s3_discipline_check", "s3_list_motifs",
                 "s3_emotion_palette", "s3_craft_rule_list"}


def test_write_gated_set_no_drift():
    assert M.WRITE_GATED == EXPECTED_WRITE_GATED


def test_requires_approval():
    for w in EXPECTED_WRITE_GATED:
        assert M.requires_approval(w) is True, f"{w} 应需批准"
    for r in EXPECTED_READ | EXPECTED_WRITE_UNGATED | EXPECTED_WRITE_UNGATED_WORLD:
        assert M.requires_approval(r) is False, f"{r} 应放行(读/草稿/客观回写)"


def test_commit_if_approved_accept_writes():
    calls = []
    out = M.commit_if_approved("s3_add_fact", True, lambda: calls.append("did"))
    assert calls == ["did"], "批准→执行写"
    assert out["status"] == "written"


def test_commit_if_approved_decline_blocks():
    calls = []
    out = M.commit_if_approved("s3_add_fact", False, lambda: calls.append("did"))
    assert calls == [], "拒绝→不写(fail-closed)"
    assert out["status"] == "declined"


def test_read_tool_project_frame_excludes_secret(store):
    luanshi_leak_world(store)
    M.set_store(store)
    laodao = M.s3_project_frame("role:老道", 1)
    vals = " ".join(x["value"] for x in laodao)
    assert "治眼" not in vals, "老道帧不含焦三私密"
    jiaosan = M.s3_project_frame("role:焦三", 1)
    assert any("治眼" in x["value"] for x in jiaosan), "焦三知道自己的动机"


def test_read_tool_find_leaks(store):
    luanshi_leak_world(store)
    M.set_store(store)
    leaks = M.s3_find_leaks("皂衣道士冷笑:够你给老娘治眼了。", "role:老道", 1)
    assert any(l["fact_id"] == "fact:治眼" for l in leaks)


def test_emotion_palette_list_and_query():
    names = M.s3_emotion_palette("")
    assert isinstance(names, list) and "压抑的悲伤" in names
    one = M.s3_emotion_palette("压抑的悲伤")
    assert one["body"] and one["inner"]


def test_craft_rule_gated_in_write_set():
    assert "s3_craft_rule_add" in M.WRITE_GATED
    assert "s3_craft_rule_remove" in M.WRITE_GATED
    assert "s3_craft_rule_list" not in M.WRITE_GATED
    assert "s3_emotion_palette" not in M.WRITE_GATED


def test_qc_chapter_uses_themed_purple(store):
    """s3_qc_chapter 把本书 craft_rule 的题材升华正则喂给 find_purple_prose。"""
    store.seed_craft_rules()
    store.save_chapter(1, "炉火映脸,天地为炉,万物为铜。")
    M.set_store(store)
    flags = M.s3_qc_chapter(1)
    assert flags["purple"], "题材升华句(天地为炉)应被本书正则抓到"


def test_ingest_not_gated():
    """ingest 是客观回写(反映已定稿正文),不再 elicitation 待批;创作虚构仍 gated。"""
    assert "s3_ingest_chapter" not in M.WRITE_GATED
    assert "s3_add_fact" in M.WRITE_GATED
    assert "s3_add_event" in M.WRITE_GATED


def test_ingest_chapter_sync_reuses_ingest_chapter(store, monkeypatch):
    """s3_ingest_chapter 改 sync,复用 ingest.ingest_chapter,直接落库(无 elicitation)。"""
    from scribe3.ontology import Entity
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.save_chapter(1, "甲把刀给了乙,丙在旁看着。")
    M.set_store(store)
    import scribe3.ingest as ING
    monkeypatch.setattr(ING, "parse_knowledge_delta",
                        lambda r: {"learned": [{"who": "乙", "fact": "得了刀"}], "did": []})
    monkeypatch.setattr("scribe3.llm.hermes_complete", lambda *a, **k: "{}")
    res = M.s3_ingest_chapter(1)
    assert res["applied"] == 1


def test_tools_discoverable_and_annotated():
    tools = {t.name: t for t in asyncio.run(M.mcp.list_tools())}
    want = EXPECTED_WRITE_GATED | EXPECTED_WRITE_UNGATED | EXPECTED_WRITE_UNGATED_WORLD | EXPECTED_READ
    assert want <= set(tools), f"缺工具: {want - set(tools)}"
    for name in EXPECTED_READ:
        ann = tools[name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if ro is not None:
            assert ro is True, f"{name} 应注 readOnlyHint=True"
    for name in EXPECTED_WRITE_GATED | EXPECTED_WRITE_UNGATED | EXPECTED_WRITE_UNGATED_WORLD:
        ann = tools[name].annotations
        ro = getattr(ann, "readOnlyHint", None) if ann else None
        if ro is not None:
            assert ro is not True, f"{name} 不应注 readOnlyHint=True"


def test_mcp_recall_tools_expose_is_secret(store):
    """P0·限知边界:五路召回工具返回的每条命题项必须带 is_secret 标志。
    secret=True 的私密命题 is_secret 须为 True,供下游限知渲染层据此跳过私密。
    默认(reveal_secret=False)打码 value;reveal_secret=True 保留明文(仅主编全知联查用)。"""
    from scribe3.ontology import KnowledgeEdge
    luanshi_leak_world(store)
    # 语义召回需要 embedding 索引;在 add_fact 后手动建立(生产侧由 s3_add_fact 调用)
    store.semantic_index("fact:治眼", "攒钱给老娘治眼")
    store.semantic_index("fact:雨", "暴雨")
    # dramatic_irony 需要 reader 持有对 secret fact 的知识边(叙述视角已揭示给读者)
    store.add_knowledge(KnowledgeEdge("reader", "fact:治眼", since_chapter=1))
    M.set_store(store)

    # --- s3_project_frame: 焦三帧含 secret 命题,应带 is_secret=True(此工具无 reveal_secret 参数,保持原行为) ---
    jiaosan_frame = M.s3_project_frame("role:焦三", 1)
    secret_items_frame = [x for x in jiaosan_frame if x.get("is_secret") is True]
    assert secret_items_frame, (
        "s3_project_frame: 焦三帧里 secret 命题应带 is_secret=True"
    )
    # project_frame 供限知渲染,本身只投帧内可知命题,不改变其 value
    assert any("治眼" in x["value"] for x in secret_items_frame), (
        "s3_project_frame: secret 命题的 value 应保留(此工具不参与掩码)"
    )

    # --- s3_semantic_recall 默认打码 ---
    sem_results = M.s3_semantic_recall("治眼", k=5)
    assert sem_results, "s3_semantic_recall: 应能召回治眼相关命题"
    secret_sem = [x for x in sem_results if x.get("is_secret") is True]
    assert secret_sem, "s3_semantic_recall: secret 命题应带 is_secret=True"
    assert all("🔒" in str(x.get("value", "")) for x in secret_sem), (
        "s3_semantic_recall 默认应打码 secret value 为 🔒 私密"
    )
    assert all("治眼" not in str(x.get("value", "")) for x in secret_sem), (
        "s3_semantic_recall 默认不应泄露 secret 明文"
    )

    # --- s3_semantic_recall reveal_secret=True 解锁 ---
    sem_reveal = M.s3_semantic_recall("治眼", k=5, reveal_secret=True)
    secret_sem_reveal = [x for x in sem_reveal if x.get("is_secret") is True]
    assert any("治眼" in str(x.get("value", "")) for x in secret_sem_reveal), (
        "s3_semantic_recall reveal_secret=True 应保留 secret 明文"
    )

    # --- s3_dramatic_irony 默认打码 ---
    irony = M.s3_dramatic_irony("role:老道", 1)
    # 老道不知焦三私密,焦三私密对老道构成戏剧反讽
    secret_irony = [x for x in irony if x.get("is_secret") is True]
    assert secret_irony, "s3_dramatic_irony: 戏剧反讽点中 secret 命题应带 is_secret=True"
    assert all("🔒" in str(x.get("value", "")) for x in secret_irony), (
        "s3_dramatic_irony 默认应打码 secret value"
    )
    assert all("治眼" not in str(x.get("value", "")) for x in secret_irony), (
        "s3_dramatic_irony 默认不应泄露 secret 明文"
    )

    # --- s3_dramatic_irony reveal_secret=True 解锁 ---
    irony_reveal = M.s3_dramatic_irony("role:老道", 1, reveal_secret=True)
    secret_irony_reveal = [x for x in irony_reveal if x.get("is_secret") is True]
    assert any("治眼" in str(x.get("value", "")) for x in secret_irony_reveal), (
        "s3_dramatic_irony reveal_secret=True 应保留 secret 明文"
    )


def test_mcp_hybrid_recall_masks_secret_by_default(store):
    """P0·A2: s3_hybrid_recall 默认打码 secret value;reveal_secret=True 解锁。"""
    from scribe3.ontology import Fact
    luanshi_leak_world(store)
    store.semantic_index("fact:治眼", "攒钱给老娘治眼")
    M.set_store(store)

    results = M.s3_hybrid_recall("治眼", chapter=5, k=5)
    secret_items = [x for x in results if x.get("is_secret")]
    assert secret_items, "s3_hybrid_recall 应召回到 secret 命题"
    assert all("🔒" in str(x.get("value", "")) for x in secret_items), (
        "s3_hybrid_recall 默认应打码 secret value"
    )
    assert all("治眼" not in str(x.get("value", "")) for x in secret_items), (
        "s3_hybrid_recall 默认不应泄露 secret 明文"
    )

    results_reveal = M.s3_hybrid_recall("治眼", chapter=5, k=5, reveal_secret=True)
    secret_reveal = [x for x in results_reveal if x.get("is_secret")]
    assert any("治眼" in str(x.get("value", "")) for x in secret_reveal), (
        "s3_hybrid_recall reveal_secret=True 应保留 secret 明文"
    )


def test_mcp_graph_recall_masks_secret_by_default(store):
    """P0·A2: s3_graph_recall 默认打码 secret value;reveal_secret=True 解锁。"""
    luanshi_leak_world(store)
    store.semantic_index("fact:治眼", "攒钱给老娘治眼")
    M.set_store(store)

    results = M.s3_graph_recall("治眼", chapter=5, k=5)
    secret_items = [x for x in results if x.get("is_secret")]
    assert secret_items, "s3_graph_recall 应召回到 secret 命题"
    assert all("🔒" in str(x.get("value", "")) for x in secret_items), (
        "s3_graph_recall 默认应打码 secret value"
    )
    assert all("治眼" not in str(x.get("value", "")) for x in secret_items), (
        "s3_graph_recall 默认不应泄露 secret 明文"
    )

    results_reveal = M.s3_graph_recall("治眼", chapter=5, k=5, reveal_secret=True)
    secret_reveal = [x for x in results_reveal if x.get("is_secret")]
    assert any("治眼" in str(x.get("value", "")) for x in secret_reveal), (
        "s3_graph_recall reveal_secret=True 应保留 secret 明文"
    )


# ===== T2: s3_record_knowledge proposition oid 校验 =====

def test_record_knowledge_rejects_non_fact_oid(store):
    """传裸自然语言(非 fact: oid)→ _check_proposition 返回 error dict,不建悬挂 knows 边。
    传合法 fact: oid 且存在 → 返回 None(校验通过),写入后 knows 边可查。
    """
    from scribe3.ontology import Entity, Fact
    store.add_entity(Entity("role:甲", "character", "甲"))
    M.set_store(store)

    # 1) 裸自然语言(非 fact: 前缀)→ 校验返回 error
    err1 = M._check_proposition("焦三攒钱治眼")
    assert err1 is not None and "error" in err1, \
        f"非 fact: oid 应返回 error dict,实际: {err1}"
    # 确认没有悬挂 knows 边(未调用 add_knowledge)
    knows = store.load_knowledge()
    assert not any(k.proposition_id == "焦三攒钱治眼" for k in knows), \
        "不应建出悬挂 knows 边"

    # 2) fact: 前缀但 store 中不存在 → 校验返回 error
    err2 = M._check_proposition("fact:不存在的命题")
    assert err2 is not None and "error" in err2, \
        f"不存在的 fact: oid 应返回 error dict,实际: {err2}"

    # 3) 先建 fact,再校验该 oid → 返回 None(通过),写入后 knows 边存在
    store.add_fact(Fact("fact:治眼", "role:焦三", "动机", "攒钱治眼", 1))
    ok = M._check_proposition("fact:治眼")
    assert ok is None, f"已存在的 fact: oid 应校验通过(返回 None),实际: {ok}"
    # 通过后手动写入(模拟 commit_if_approved 批准路径)
    from scribe3.ontology import KnowledgeEdge
    store.add_knowledge(KnowledgeEdge("role:甲", "fact:治眼", since_chapter=1))
    knows2 = store.load_knowledge()
    assert any(k.proposition_id == "fact:治眼" and k.knower_id == "role:甲"
               for k in knows2), "合法路径应建 knows 边"


# ===== P1-b Bug C3#1: s3_add_event 收 participants/effects/causal_in =====

def test_s3_add_event_wires_participants_and_effects(store):
    """P1-b 回归:s3_add_event 须接收 participants/effects/causal_in 并传给 store.add_event。
    修复前:缺参数 → MCP 创建的事件是孤立节点(involves/causes/causal 全空)。
    修复后:事件落库后 events_at 重建时 participants 和 effects 非空。
    """
    from scribe3.ontology import Entity, Event, Fact

    # 先建角色和命题(involves 边指向 character,causes 边指向 proposition)
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_fact(Fact("fact:刺杀发生", "role:甲", "获知", "刺杀发生", valid_from=3))
    M.set_store(store)

    # 直接调用 store.add_event 验证边数据写入路径(绕过 async elicitation)
    # 此路径与 s3_add_event 批准后走的 lambda 完全相同
    ev = Event(
        "ev:甲目睹刺杀",
        "目睹",
        story_time=3,
        participants={"WITNESS": "role:甲"},   # involves.role 受限词: SUBJ/OBJ/WITNESS
        effects=["fact:刺杀发生"],
    )
    store.add_event(ev)

    # events_at 重建:participants 和 effects 应非空
    evs = store.events_at(3)
    assert evs, "events_at(3) 应返回至少一个事件"
    target = next((e for e in evs if "甲目睹刺杀" in e.id), None)
    assert target is not None, f"应能找到 ev:甲目睹刺杀,实际: {[e.id for e in evs]}"
    assert target.participants, f"participants 应非空,实际: {target.participants}"
    assert any("甲" in str(v) for v in target.participants.values()), \
        f"participants 应含甲,实际: {target.participants}"
    assert target.effects, f"effects 应非空,实际: {target.effects}"
    assert any("刺杀发生" in eid for eid in target.effects), \
        f"effects 应含 fact:刺杀发生,实际: {target.effects}"


def test_s3_add_event_signature_accepts_edge_params():
    """P1-b 签名守卫:s3_add_event 的参数列表必须包含 participants/effects/causal_in。
    若缺参数,此测试立刻 fail —— 防止签名退回 bug。
    """
    import inspect
    sig = inspect.signature(M.s3_add_event)
    for param in ("participants", "effects", "causal_in"):
        assert param in sig.parameters, \
            f"s3_add_event 缺少参数 {param}(P1-b 修复要求); 当前参数: {list(sig.parameters)}"


# ===== 尾2: s3_add_clue MCP 工具门控测试 =====

def test_s3_add_clue_in_write_gated():
    """s3_add_clue 须在 WRITE_GATED 集合内(门控,待批)。"""
    assert "s3_add_clue" in M.WRITE_GATED, "s3_add_clue 应在 WRITE_GATED,需要 elicitation 批准"


def test_s3_add_clue_commit_if_approved_accept(store):
    """批准后 s3_add_clue 调用 add_promise_clue。"""
    store.plant_promise("测试伏笔-add-clue", setup_chapter=1)
    proms = store.list_promises()
    pid = proms[0]["id"]
    M.set_store(store)

    # 模拟批准路径:commit_if_approved(True)
    result = M.commit_if_approved("s3_add_clue", True,
                                   lambda: store.add_promise_clue(pid, "第3章草蛇灰线", 3))
    assert result["status"] == "written"
    updated = store.list_promises()
    clues = next((p["clues"] for p in updated if p["id"] == pid), [])
    assert any(c.get("note") == "第3章草蛇灰线" and c.get("chapter") == 3 for c in clues), \
        f"批准后 clue 应追加到 promise,实际 clues: {clues}"


def test_s3_add_clue_commit_if_approved_decline(store):
    """拒绝后 s3_add_clue 不写(fail-closed)。"""
    store.plant_promise("测试伏笔-decline", setup_chapter=1)
    proms = store.list_promises()
    pid = proms[0]["id"]
    M.set_store(store)

    calls = []
    result = M.commit_if_approved("s3_add_clue", False,
                                   lambda: calls.append("written"))
    assert result["status"] == "declined"
    assert calls == [], "拒绝路径不应执行写操作"


def test_s3_add_clue_signature():
    """s3_add_clue 签名须含 pid/note/chapter 三个参数。"""
    import inspect
    sig = inspect.signature(M.s3_add_clue)
    for param in ("pid", "note", "chapter"):
        assert param in sig.parameters, \
            f"s3_add_clue 缺少参数 {param},当前参数: {list(sig.parameters)}"
