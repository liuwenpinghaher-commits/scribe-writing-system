"""对抗审查 · commit 03a3bb2(设定进 prompt:注册表驱动+限知门控 + faction 一致性校验)。

本文件不是功能回归测试,是**证伪**测试——默认假设 03a3bb2 的限知门控有洞,逐条尝试
用真实(或高度写实的模拟失败)输入让 secret 字段泄进 prompt。凡本文件里断言失败的用例,
即是实锤的安全问题;凡断言通过的,是"已尝试攻破、未攻破"的安全证据。

只用 conftest.py 的 `store` fixture(临时内存 SurrealDB 子进程,每测试独立端口),
绝不触碰生产库 ~/.scribe2-surreal/data.db。
"""
import json

import pytest

from scribe3.app import _codex_block
from scribe3.codex_secret_bridge import sync_faction_secrets
from scribe3.codex_validate import validate_faction_consistency
from scribe3.ontology import Entity, KnowledgeEdge

FACTION = "衔尾蛇秘会"
ENTITY_ID = f"faction:{FACTION}"


def _sync(store, name: str) -> dict:
    row = store.get_faction(name)
    assert row is not None
    return sync_faction_secrets(store, name, row)


def _bridge_fact_id(store, entity_id: str, attribute: str) -> str:
    rows = store._query(
        "SELECT meta::id(id) AS local FROM proposition "
        "WHERE entity_id=$eid AND attribute=$attr AND source='codex_bridge' LIMIT 1",
        {"eid": entity_id, "attr": attribute})
    assert rows, f"未找到桥接命题: {entity_id}/{attribute}(先调用 _sync)"
    return f"fact:{rows[0]['local']}"


# ============================================================
# P0 候选①:_secret_fact_ids 失败/返回空集时,是否反而放行(fail-open)?
# ============================================================

def test_P0_secret_leaks_when_secret_fact_ids_returns_empty(store, monkeypatch):
    """结构性证伪:_faction_prompt_block 的门控写法是

        if fid is None or (fid in secret_ids and fid not in known_ids):
            continue  # 跳过注入

    只有当 fid 命中 secret_ids 时,"focalizer 是否知情"才生效。若 secret_ids
    因任何原因(DB 抖动、查询异常、store 变体缺方法……)算成空集,则
    `fid in secret_ids` 恒 False,整个门控被短路——不管 focalizer 知不知情,
    只要桥接命题(fid)存在就直接注入明文。这与 context_assembler 里"或"结构的
    姐妹判据(`mask = secret_ids 命中 or 帧外`)不同:后者失败时还有"帧外"这条独立
    保险;这里没有第二道防线。

    这里直接让权威判定函数返回空集(它自己的文档就承诺"fail-soft:任何查询异常
    退回空集"——本用例只是真实触发这个已声明的退化路径),验证调用方是否安全。
    """
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)

    import scribe3.context_assembler as ca
    monkeypatch.setattr(ca, "_secret_fact_ids", lambda st: set())

    # focalizer 明确不知情:没有对应 KnowledgeEdge。for_generation=True:这是生成/限知
    # 续写路径的性质(U-003 三档可见性,2026-07-15)——作者/主编对话路径不做此判定。
    block = _codex_block(store, reveal=False, focalizer="role:不知情的旁观者", chapter=5,
                         for_generation=True)
    assert "源自前朝遗族的复国密谋" not in block, (
        "P0:_secret_fact_ids 返回空集时,已建桥的 secret 字段绕过限知门控直接注入明文"
        f"(实际 block: {block!r})")


def test_P0_secret_store_failure_now_fails_loud_not_silent(store, monkeypatch):
    """U-011(2026-07-15,作者要 fail-loud)行为变更:store 的秘密判定查询失败时,
    此前 `_secret_fact_ids` 退空集(fail-soft)、靠下游门 fail-closed 兜住不泄露——
    现在改为**直接抛**(fail-loud)。安全属性反而更强:崩了就啥都不产出,定义上更
    不可能泄露,而且作者能在前端看见"限知判定失败,本章生成中止",不会被静默降级躲过。

    本测试:让 `WHERE secret = true` 宽扫查询失败 → _codex_block 必须【抛】,而不是
    静默返回一个碰巧没泄露的块。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)

    real_query = store._query

    def fake_query(surql, vars=None):
        if "secret = true" in surql:
            raise RuntimeError("模拟:秘密判定宽扫查询超时/失败")
        return real_query(surql, vars)

    monkeypatch.setattr(store, "_query", fake_query)

    # for_generation=True:生成/限知续写路径。秘密判据查询失败 → 直接抛(fail-loud),
    # 不再静默退空集把泄密风险躲过去。
    with pytest.raises(Exception):
        _codex_block(store, reveal=False, focalizer="role:不知情的旁观者", chapter=5,
                     for_generation=True)


# ============================================================
# secret_agenda:是否比其他 secret_capable 字段多一层保护?
# ============================================================

def test_secret_agenda_never_injected_in_generation_path_even_with_a_knows_edge(store):
    """P1-1 回归锚(2026-07-14 对抗审查发现,已修;2026-07-15 U-003 三档可见性重构后
    行为再调整,断言随之更新——别按 commit 里的旧注释办事)。

    codex_schema.py 原话:secret_agenda = "连势力核心层都不知道的真相,仅主编可见"。
    这比"限知"更强一档:限知字段还能靠 knows 边授予某个角色,而它**没有任何角色该知道**。
    修前它和 origin/artifact_operation 走同一套 secret_capable + knows 边判据,一条
    误建的边就能捅穿这条红线。

    上一版修复用 in_prompt=False 把它整个关出 prompt_keys('faction')——结果连"仅主编"
    的"主编"都看不见它了,太钝。现在改为 chief_only=True + in_prompt=True(恢复默认):
    它确实出现在 prompt_keys('faction') 里(见下方断言),但生成/限知续写路径
    (for_generation=True)由 app.py `_faction_prompt_block` 按 `chief_only_keys()`
    结构性名单拦截——不看任何 knows 边、不看 focalizer;作者/主编对话路径
    (for_generation=False)才注入,这就是"仅主编可见"的字面意思,见下一测试。

    本测试构造最恶劣的情形——一条(误建的)KnowledgeEdge 把 secret_agenda 的桥接命题
    直接挂给某角色,且以该角色为焦点——**生成路径**仍必须一个字都不进 prompt。"""
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "secret_agenda")
    store.add_entity(Entity("role:意外知情者", "character", "意外知情者"))
    store.add_knowledge(KnowledgeEdge("role:意外知情者", fact_id, since_chapter=1))

    for reveal in (False, True):   # 全知模式(reveal=True)也不例外
        block = _codex_block(store, reveal=reveal, focalizer="role:意外知情者", chapter=5,
                             for_generation=True)
        assert "连核心层都不知道的真相" not in block, (
            f"P1-1 回归(reveal={reveal}):secret_agenda 是主编独知,生成路径即便存在"
            f"knows 边也绝不可进 prompt(实际 block: {block!r})")

    from scribe3.codex_schema import chief_only_keys, prompt_keys
    assert "secret_agenda" in prompt_keys("faction"), (
        "secret_agenda 现在 in_prompt=True(恢复默认)——它会出现在作者/主编对话的"
        "prompt 里,这是'仅主编可见'的字面意思,不是'谁都看不见'")
    assert "secret_agenda" in chief_only_keys("faction"), (
        "secret_agenda 必须 chief_only=True——这是它在生成路径结构性不进 prompt 的"
        "保证,别退回成'靠 knows 边把关'或'靠 in_prompt=False 一关了之'")


def test_secret_agenda_visible_in_author_dialogue_even_without_any_knows_edge(store):
    """U-003 三档可见性的另一半:作者/主编对话(for_generation=False,_codex_block
    默认值)里,secret_agenda 直接可见——即便**没有**任何 KnowledgeEdge、也没有传
    focalizer。"仅主编可见"就是"主编看得见",不是"谁都看不见"(旧版 in_prompt=False
    的失误,详见上一测试的 docstring)。"""
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)
    # 特意不建任何 KnowledgeEdge、不传 focalizer——纯作者/主编讨论场景。

    block = _codex_block(store, reveal=True, focalizer="", chapter=5, request_text=FACTION)
    assert "连核心层都不知道的真相" in block, (
        "作者/主编对话(for_generation=False)应看到 secret_agenda——它不走 knows 边判据")


# ============================================================
# 声明式"解密"(作者主动取消 secret 标记):应安全,且不留残余桥接命题
# ============================================================

def test_unflagging_secret_cleanly_deletes_bridge_and_reveals_plaintext(store):
    store.add_faction(FACTION, origin="曾经的秘密,现已解密", origin_secret=True)
    _sync(store, FACTION)
    _bridge_fact_id(store, ENTITY_ID, "origin")   # 前置:桥接命题确已存在

    store.add_faction(FACTION, origin_secret=False)   # 作者显式取消 secret 标记
    counts = _sync(store, FACTION)
    assert counts["deleted"] == 1, "取消 secret 标记且重新同步后,残留桥接命题应被删除"

    rows = store._query(
        "SELECT meta::id(id) AS local FROM proposition "
        "WHERE entity_id=$eid AND attribute='origin' AND source='codex_bridge'",
        {"eid": ENTITY_ID})
    assert rows == [], "解密后不应残留桥接命题"

    block = _codex_block(store, reveal=False, focalizer="", chapter=5, request_text=FACTION)
    assert "曾经的秘密,现已解密" in block, "作者显式取消 secret 后,字段应正常明文注入(声明式解密,非 bug)"


def test_unflagging_secret_without_resync_is_still_safe_because_flag_gates_first(store):
    """更贴近真实前端 bug 场景:add_faction 把 origin_secret 改成 False,但调用方
    这次**没有**跟着重新调用 sync_faction_secrets(桥接命题残留、未删)。
    验证:即便桥接命题(secret=true 的 proposition)还在库里没清理,门控代码本身
    先看 row 上的 `{key}_secret` 位——False 就完全跳过秘密门控分支,直接明文注入。
    这是"当前实现" (非某种隐藏漏洞):字段级 secret 位是唯一权威开关,桥接命题只是
    它的派生投影,不反向指挥它。"""
    store.add_faction(FACTION, origin="曾经的秘密,现已解密", origin_secret=True)
    _sync(store, FACTION)   # 桥接命题创建,fid 存在且 secret=true

    store.add_faction(FACTION, origin_secret=False)   # 只改标志位,不重新 sync

    row = store.get_faction(FACTION)
    assert row.get("origin_secret") is False
    assert row.get("origin") == "曾经的秘密,现已解密"   # 值本身未变

    block = _codex_block(store, reveal=False, focalizer="", chapter=5, request_text=FACTION)
    assert "曾经的秘密,现已解密" in block, (
        "row.origin_secret=False 时直接明文注入,不受残留桥接命题影响——"
        "字段级 secret 位是唯一权威开关")


# ============================================================
# chapter 缺省(None → eff_chapter=1):应是保守方向(漏注入),不是泄露方向
# ============================================================

def test_chapter_default_direction_is_conservative_not_leaky(store):
    """for_generation=True:章号缺省的保守方向是生成/限知续写路径的性质(U-003 三档
    可见性)——作者/主编对话路径不做 knows 边时态判定,不受此约束。"""
    store.add_faction(FACTION, origin="迟到的秘密", origin_secret=True)
    _sync(store, FACTION)
    fact_id = _bridge_fact_id(store, ENTITY_ID, "origin")
    store.add_entity(Entity("role:后来知情", "character", "后来知情"))
    store.add_knowledge(KnowledgeEdge("role:后来知情", fact_id, since_chapter=5))

    # 老调用方式:不传 chapter(内部 eff_chapter 落到 1),但显式钉住生成路径。
    block_no_chapter = _codex_block(store, reveal=False, focalizer="role:后来知情",
                                    for_generation=True)
    assert "迟到的秘密" not in block_no_chapter, (
        "eff_chapter 缺省落到 1 < since_chapter=5:应判定为尚不知情——"
        "方向是漏注入(保守),不是泄露")

    block_with_chapter = _codex_block(store, reveal=False, focalizer="role:后来知情", chapter=5,
                                      for_generation=True, request_text=FACTION)
    assert "迟到的秘密" in block_with_chapter, "传入真实章号后,该知情的应正常可见"


# ============================================================
# validate_faction_consistency:动态验证只读 + 不携带 secret 字段原文
# ============================================================

def test_validate_faction_consistency_never_calls_execute_write(store, monkeypatch):
    """动态证明只读:把 store._execute_write 换成"一调用就报错",
    确认 validate_faction_consistency 全程不触发它(而不仅是静态读代码判断)。
    monkeypatch 必须在测试数据建好【之后】才打(建数据本身当然要写库),
    只包住真正要验证的那一次调用。"""
    store.add_faction(
        "甲盟", structure={"core_size": 1},
        key_figures=[{"name": "甲", "status": "active"}, {"name": "乙", "status": "active"}])
    store.add_faction("乙盟")
    store.add_entity_relation(a="faction:甲盟", b="faction:乙盟", relation_type="敌对")
    store.add_entity_relation(a="faction:乙盟", b="faction:甲盟", relation_type="结盟")

    def _boom(*a, **kw):
        raise AssertionError("validate_faction_consistency 不应发起任何写操作")
    monkeypatch.setattr(store, "_execute_write", _boom)

    validate_faction_consistency(store)   # 若内部有任何写操作,上面的 _boom 会抛出


def test_faction_consistency_output_never_contains_secret_field_text(store):
    store.add_faction(
        "甲盟", structure={"core_size": 1},
        key_figures=[{"name": "甲", "status": "active"}, {"name": "乙", "status": "active"}],
        origin="绝密来源文本ABC123", origin_secret=True,
        secret_agenda="绝密议程XYZ789", secret_agenda_secret=True,
        artifacts=[{"artifact_name": "回煞炉", "last_transfer_chapter": 999}])
    issues = validate_faction_consistency(store)
    dump = json.dumps(issues, ensure_ascii=False)
    assert "绝密来源文本ABC123" not in dump
    assert "绝密议程XYZ789" not in dump


def test_faction_consistency_endpoint_no_reveal_gating_but_structurally_cannot_leak(store):
    """GET /faction-consistency 端点本身没有 focalizer/reveal 门控(纯结构诊断,
    非叙事视角)。这只在"校验函数确实永不触碰 secret_capable 字段内容"的前提下
    才安全——上面两个测试已验证该前提;这里额外过一遍真实 HTTP 端点,确认端到端
    结论一致。"""
    import scribe3.app as A
    from fastapi.testclient import TestClient

    A.set_store(store)
    client = TestClient(A.app)
    store.add_faction(FACTION, origin="绝密来源文本ABC123", origin_secret=True,
                      secret_agenda="绝密议程XYZ789", secret_agenda_secret=True)
    r = client.get("/faction-consistency")
    assert r.status_code == 200
    body_text = json.dumps(r.json(), ensure_ascii=False)
    assert "绝密来源文本ABC123" not in body_text
    assert "绝密议程XYZ789" not in body_text


# ============================================================
# 旁路①(跨模块,超出 03a3bb2 本身但与其安全承诺直接相关):
# secret_agenda 桥接命题一旦存在,能否绕过 _codex_block 完全不管,
# 直接被 hybrid_recall(关键词路)检索到,从而被 s3_hybrid_recall(_RO,
# 无需批准)这类 agentic 工具在“限知写作”过程中直接查到?
# ============================================================

def test_bridge_fact_discoverable_via_keyword_recall_bypassing_codex_gate(store):
    """codex_secret_bridge.py 自己的模块 docstring 承认:桥接命题不走 store.add_fact,
    因此【没有 embedding】——语义召回(semantic_recall/向量路)确实碰不到它。
    但 hybrid_recall 还有一条关键词路(_keyword_search_propositions),直接对
    proposition.value 做 jieba 分词关键词匹配,不检查 source 字段、不依赖 embedding、
    不做任何"是否为 codex_bridge 桥接命题"的排除。若 agentic 主编工具
    (mcp.py s3_hybrid_recall,只读、无需 _ask 批准)在【限知写作】过程中被模型
    自主调用且 reveal_secret=True,可以完全绕开 _codex_block/_faction_prompt_block
    这整套限知门控,直接拿到 secret_agenda 明文。

    本测试只验证链条的第一环(store 层是否真的把桥接命题交给关键词召回),
    不依赖 mcp/Hermes 网关。"""
    store.add_faction(FACTION, secret_agenda="衔尾蛇秘会真正听命于寄生外星文明母舰",
                      secret_agenda_secret=True)
    _sync(store, FACTION)

    # 语义召回(向量路):桥接命题没有 embedding,应该(且确实)找不到——这一条不是洞。
    semantic_hits = store.semantic_recall("寄生外星文明母舰", k=10)
    assert not any("寄生外星文明母舰" in (f.value or "") for f in semantic_hits), (
        "预期:桥接命题无 embedding,语义召回不该命中(用于对照关键词路的差异)")

    # 混合召回(关键词路会扫全表 value 字段做 jieba 分词匹配,不看 source/是否桥接):
    hybrid_hits = store.hybrid_recall("寄生外星文明母舰", chapter=5, k=10)
    hit = next((f for f in hybrid_hits if "寄生外星文明母舰" in (f.value or "")), None)
    assert hit is not None, (
        "旁路证据:hybrid_recall 的关键词路径能直接检索到 secret_agenda 的桥接命题明文,"
        "完全绕开 _codex_block/_faction_prompt_block 的限知门控(此路径对 mcp.py 的 "
        "s3_hybrid_recall 只读、免批准工具同样成立)")
    assert hit.secret is True   # 至少 is_secret 标志还在,调用方若检查它可自行掩码——
                                 # 但 mcp.s3_hybrid_recall 的 reveal_secret=True 会照样解锁明文


# ============================================================
# 显式补全 item②前半:标了 secret 但桥接同步从未跑过(sync 失败/未调用)
# ============================================================

def test_flagged_secret_without_any_bridge_sync_is_fail_closed(store):
    """作者勾了 origin_secret=True 并写入真值,但 sync_faction_secrets 从未被调用过
    (对应 app.py POST /factions 里 sync 被 try/except 吞掉那种场景的最终态:
    无论是首次同步失败,结果都是"没有桥接命题")。验证(生成/限知续写路径,
    for_generation=True):fid 恒为 None → 不注入,即便 reveal=True 也一样——这是
    fail-closed 的核心保证,不依赖任何 KnowledgeEdge。

    U-003 三档可见性(2026-07-15):这条 fail-closed 保证只对 for_generation=True 生效——
    作者/主编对话路径(for_generation=False)里,作者标记的 secret_capable 字段本就该
    直接可见(不必等桥接命题同步),不是本测试要证伪的场景。"""
    store.add_faction(FACTION, origin="从未被同步过的秘密", origin_secret=True)
    # 特意不调用 _sync(store, FACTION)。

    rows = store._query(
        "SELECT meta::id(id) AS local FROM proposition "
        "WHERE entity_id=$eid AND attribute='origin' AND source='codex_bridge'",
        {"eid": ENTITY_ID})
    assert rows == [], "前置条件:确认没有桥接命题存在"

    block_reveal_true = _codex_block(store, reveal=True, focalizer="", chapter=5,
                                     for_generation=True)
    assert "从未被同步过的秘密" not in block_reveal_true

    block_with_focalizer = _codex_block(store, reveal=False, focalizer="role:任何人", chapter=5,
                                        for_generation=True)
    assert "从未被同步过的秘密" not in block_with_focalizer
