"""scribe3 · CX-Task 5:通用实体关系表(双向认知 + 主编独知 truth + 时态)。

背景(计划 `docs/superpowers/plans/2026-07-14-codex-layer-redesign.md` Task 5;
spec `docs/superpowers/specs/2026-07-14-codex-layer-redesign.md` §3):
既有 `020_character_relation.surql` 是 character→character 的 `TYPE RELATION` 边表,
锁死了两端必须是真实存在的 character 记录。作者的核心诉求是"秘会看天龙座(虚与委蛇/
视为台阶)vs 天龙座看秘会(视其为地球代理人),而且对方的认知可能是错的"——单向碎片
不是关系网,需要双方各自认知(可不对称/可错)+ 主编独知的客观真相(truth)+ 任意实体
类型(不锁 faction/character/item)。新表 `entity_relation` 与 020 并存,020 零改动。

实体引用格式核实(见任务报告):`codex_secret_bridge.py` 已确认全仓 `entity_id` 惯例是
`"{table_prefix}:{local_name}"`,character 的前缀是 **"role"**(如 `role:焦三`),不是
"character"——`store._split`/`ONT2TBL` 把 "role" 映射到 SurrealDB 的 `character` 表。
本文件按此**实测确认过的**惯例写 `role:焦三`,而非任务描述里字面出现但与本仓实际用法
不符的 "character:role:焦三" 三段式。
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
import scribe3.mcp as M
from scribe3.codex_schema import ENTITY_RELATION_TYPES
from scribe3.ontology import Entity


def _client(store):
    A.set_store(store)
    return TestClient(A.app)


class _AcceptCtx:
    """假 elicitation 上下文:恒批准,供 MCP 写工具测试用(与 test_codex_faction.py 同款)。"""
    async def elicit(self, message, schema):
        return type("_R", (), {"action": "accept"})()


# ============================================================
# ① 双方认知不对称回读(store 层)
# ============================================================
def test_add_entity_relation_asymmetric_perception_roundtrip(store):
    store.add_faction("衔尾蛇秘会")
    store.add_faction("天龙座")
    store.add_entity_relation(
        a="faction:衔尾蛇秘会", b="faction:天龙座", relation_type="臣服",
        perception_a="虚与委蛇,视为台阶",
        perception_b="视其为地球代理人",
        truth="秘会实为寄生", since_chapter=1)

    rows = store.list_entity_relations(entity="faction:衔尾蛇秘会")
    assert len(rows) == 1, f"应恰好一条关系,实际: {rows}"
    row = rows[0]
    assert row["a"] == "faction:衔尾蛇秘会"
    assert row["b"] == "faction:天龙座"
    assert row["relation_type"] == "臣服"
    assert row["perception_a"] == "虚与委蛇,视为台阶"
    assert row["perception_b"] == "视其为地球代理人"
    assert row["perception_a"] != row["perception_b"], "双方认知应可不对称(这是作者的核心诉求)"
    assert row["truth"] == "秘会实为寄生", "truth 应独立于双方认知回读"


# ============================================================
# ② 时态过滤:entity_relations_at(chapter)
# ============================================================
def test_entity_relations_at_temporal_filter(store):
    store.add_entity_relation(a="faction:甲盟", b="faction:乙盟", relation_type="敌对",
                              since_chapter=1)
    store.add_entity_relation(a="faction:丙盟", b="faction:丁盟", relation_type="结盟",
                              since_chapter=10)

    at5 = {(r["a"], r["b"]) for r in store.entity_relations_at(5)}
    assert ("faction:甲盟", "faction:乙盟") in at5
    assert ("faction:丙盟", "faction:丁盟") not in at5, "since_chapter=10 > 5,尚未生效不应返回"

    at15 = {(r["a"], r["b"]) for r in store.entity_relations_at(15)}
    assert ("faction:丙盟", "faction:丁盟") in at15, "第15章时该关系已生效"


# ============================================================
# ③ end_entity_relation:关边(until_chapter 之后不返回;until 侧过滤一并验证)
# ============================================================
def test_end_entity_relation_closes_window(store):
    store.add_entity_relation(a="faction:戊盟", b="faction:己盟", relation_type="共生",
                              since_chapter=1)
    store.end_entity_relation("faction:戊盟", "faction:己盟", until_chapter=5)

    rows = store.list_entity_relations(entity="faction:戊盟")
    row = next(r for r in rows if r["b"] == "faction:己盟")
    assert row["until_chapter"] == 5

    before = {(r["a"], r["b"]) for r in store.entity_relations_at(3)}
    assert ("faction:戊盟", "faction:己盟") in before, "until_chapter 之前仍应返回"

    after = {(r["a"], r["b"]) for r in store.entity_relations_at(6)}
    assert ("faction:戊盟", "faction:己盟") not in after, "until_chapter 之后不应返回"


# ============================================================
# ④ 任意实体类型:不锁类型,不做存在性校验
# ============================================================
def test_add_entity_relation_arbitrary_entity_types(store):
    """faction↔character(role 前缀)、character↔item 都能存;且 a/b 引用的实体
    刻意不预先建档(不像 character_relation 的 RELATE 那样要求两端真实存在)——
    证明本表通用、不锁实体类型。"""
    store.add_entity_relation(a="faction:秘会", b="role:焦三", relation_type="渗透",
                              since_chapter=2)
    store.add_entity_relation(a="role:焦三", b="item:碎片", relation_type="利用",
                              since_chapter=2)

    rows = store.list_entity_relations(entity="role:焦三")
    pairs = {(r["a"], r["b"], r["relation_type"]) for r in rows}
    assert ("faction:秘会", "role:焦三", "渗透") in pairs
    assert ("role:焦三", "item:碎片", "利用") in pairs


# ============================================================
# ⑤ 非法 relation_type → 拒(store ValueError / app 422)
# ============================================================
def test_add_entity_relation_illegal_relation_type_raises(store):
    with pytest.raises(ValueError):
        store.add_entity_relation(a="faction:X", b="faction:Y",
                                  relation_type="不存在的关系类型")


def test_post_entity_relations_illegal_relation_type_422(store):
    c = _client(store)
    r = c.post("/entity-relations", json={
        "a": "faction:X", "b": "faction:Y", "relation_type": "不存在的关系类型",
    })
    assert r.status_code == 422, f"非法 relation_type 应 422,实际: {r.status_code} {r.text}"
    assert not any(row["a"] == "faction:X" for row in
                   c.get("/entity-relations", params={"entity": "faction:X"}).json()), \
        "非法枚举不应落库"


def test_relation_type_vocabulary_single_source_of_truth():
    """codex_schema.ENTITY_RELATION_TYPES 是 store/app 共用的唯一权威词表(防两处漂移)。"""
    assert ENTITY_RELATION_TYPES == ("臣服", "敌对", "渗透", "无视", "共生", "结盟", "利用", "未知")


# ============================================================
# ⑥ truth 掩码(GET 默认掩,reveal 才见)+ POST 回传掩码不覆盖真值
# ============================================================
def test_get_entity_relations_masks_truth_by_default(store):
    store.add_entity_relation(a="faction:密盟", b="faction:显盟", relation_type="臣服",
                              truth="不可告人的真相", truth_secret=True, since_chapter=1)
    c = _client(store)

    masked = next(r for r in c.get("/entity-relations",
                  params={"entity": "faction:密盟"}).json() if r["b"] == "faction:显盟")
    assert masked["truth"] == A._SECRET_MASK, f"GET 默认应掩码 truth,实际: {masked['truth']!r}"

    revealed = next(r for r in c.get("/entity-relations",
                    params={"entity": "faction:密盟", "reveal_secret": True}).json()
                    if r["b"] == "faction:显盟")
    assert revealed["truth"] == "不可告人的真相"


def test_post_entity_relations_masked_truth_not_overwritten(store):
    """【关键·防数据毁灭】前端典型行为:GET 拿到整行(truth 已是掩码占位符)→
    只改 perception_a → 原样 POST 回传 → 若无掩码哨兵,"🔒 私密" 会被当成真值
    落库,永久销毁原文(Task 3 的血泪教训,同一陷阱在此表复现)。"""
    c = _client(store)
    r = c.post("/entity-relations", json={
        "a": "faction:秘会3", "b": "faction:天龙座3", "relation_type": "臣服",
        "perception_a": "虚与委蛇,视为台阶", "perception_b": "视其为地球代理人",
        "truth": "秘会实为寄生", "truth_secret": True, "since_chapter": 1,
    })
    assert r.status_code == 200, r.text

    masked = next(r for r in c.get("/entity-relations",
                  params={"entity": "faction:秘会3"}).json() if r["b"] == "faction:天龙座3")
    assert masked["truth"] == A._SECRET_MASK, "先确认落库真值确实被 GET 掩码"

    r2 = c.post("/entity-relations", json={
        "a": "faction:秘会3", "b": "faction:天龙座3", "relation_type": "臣服",
        "perception_a": "新的认知:发现台阶另有隐情",   # 这次真正想改的字段
        "truth": A._SECRET_MASK,                      # 前端整行回传,未被作者编辑
        "since_chapter": 1,
    })
    assert r2.status_code == 200, r2.text

    row = next(r for r in c.get("/entity-relations",
               params={"entity": "faction:秘会3", "reveal_secret": True}).json()
               if r["b"] == "faction:天龙座3")
    assert row["truth"] == "秘会实为寄生", (
        f"掩码字符串不应覆盖真值——现状陷阱复现:实际 {row['truth']!r}")
    assert row["perception_a"] == "新的认知:发现台阶另有隐情", "perception_a 应正常更新"


# ============================================================
# ⑦ 既有 character_relation 零回归(完整回归见 test_store.py 等既有套件;
#    这里只做最小烟雾验证:新表不影响旧表)
# ============================================================
def test_character_relation_unaffected_by_new_entity_relation_table(store):
    store.add_entity(Entity("role:甲", "character", "甲"))
    store.add_entity(Entity("role:乙", "character", "乙"))
    store.add_character_relation("role:甲", "role:乙", "盟友", since_chapter=1)

    # 同时也写一条 entity_relation,证明两表互不干扰
    store.add_entity_relation(a="faction:无关势力", b="role:甲", relation_type="无视",
                              since_chapter=1)

    rels = store.relations_at(5)
    assert any(r["src"] == "甲" and r["dst"] == "乙" and r["relation"] == "盟友"
              for r in rels), "character_relation 既有功能应不受影响"


# ============================================================
# ⑧ REST / MCP 端点
# ============================================================
def test_rest_entity_relations_get_post_delete_roundtrip(store):
    c = _client(store)
    r = c.post("/entity-relations", json={
        "a": "faction:REST甲", "b": "faction:REST乙", "relation_type": "结盟",
        "perception_a": "共同御敌", "since_chapter": 3,
    })
    assert r.status_code == 200, r.text

    got = c.get("/entity-relations", params={"entity": "faction:REST甲"}).json()
    assert any(row["b"] == "faction:REST乙" and row["relation_type"] == "结盟" for row in got)

    d = c.delete("/entity-relations", params={"a": "faction:REST甲", "b": "faction:REST乙"})
    assert d.status_code == 200, d.text
    got_after = c.get("/entity-relations", params={"entity": "faction:REST甲"}).json()
    assert not any(row["b"] == "faction:REST乙" for row in got_after), "DELETE 后不应再查到"


def test_rest_entity_relations_get_with_chapter_filters_temporally(store):
    c = _client(store)
    c.post("/entity-relations", json={
        "a": "faction:时态甲", "b": "faction:时态乙", "relation_type": "敌对",
        "since_chapter": 20,
    })
    early = c.get("/entity-relations", params={"entity": "faction:时态甲", "chapter": 5}).json()
    assert not any(row["b"] == "faction:时态乙" for row in early), "chapter=5 时尚未生效"

    late = c.get("/entity-relations", params={"entity": "faction:时态甲", "chapter": 25}).json()
    assert any(row["b"] == "faction:时态乙" for row in late), "chapter=25 时应已生效"


def test_mcp_s3_add_entity_relation_is_write_gated():
    assert "s3_add_entity_relation" in M.WRITE_GATED, "写工具必须进 WRITE_GATED(待批)"


def test_mcp_s3_add_entity_relation_writes_after_accept(store):
    M.set_store(store)
    res = asyncio.run(M.s3_add_entity_relation(
        _AcceptCtx(), a="faction:MCP甲", b="faction:MCP乙", relation_type="利用",
        perception_a="单方面认为对方可被驱使", since_chapter=7))
    assert res["status"] == "written"
    rows = store.list_entity_relations(entity="faction:MCP甲")
    assert any(r["b"] == "faction:MCP乙" and r["relation_type"] == "利用" for r in rows)


def test_mcp_s3_add_entity_relation_declined_does_not_write(store):
    M.set_store(store)

    class _DeclineCtx:
        async def elicit(self, message, schema):
            return type("_R", (), {"action": "decline"})()

    res = asyncio.run(M.s3_add_entity_relation(
        _DeclineCtx(), a="faction:拒批甲", b="faction:拒批乙", relation_type="敌对"))
    assert res["status"] == "declined"
    assert store.list_entity_relations(entity="faction:拒批甲") == []


def test_mcp_s3_list_entity_relations_masks_truth_by_default(store):
    M.set_store(store)
    store.add_entity_relation(a="faction:MCP密", b="faction:MCP显", relation_type="臣服",
                              truth="MCP真相", truth_secret=True, since_chapter=1)
    rows = M.s3_list_entity_relations(entity="faction:MCP密")
    row = next(r for r in rows if r["b"] == "faction:MCP显")
    assert row["truth"] == "🔒 私密"

    revealed = next(r for r in M.s3_list_entity_relations(entity="faction:MCP密",
                                                          reveal_secret=True)
                    if r["b"] == "faction:MCP显")
    assert revealed["truth"] == "MCP真相"
