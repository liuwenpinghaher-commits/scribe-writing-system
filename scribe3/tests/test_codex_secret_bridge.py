"""CX-Task 4 · 命题桥:faction secret 字段真正接入限知体系。

背景:codex_schema.py 的 `{key}_secret` 目前只是【界面掩码】(app._mask_field,只在 GET
/POST 掩盖/还原字符串)——它完全不经过既有限知体系:project_frame(knowledge.py)、
_secret_fact_ids(context_assembler.py,prompt 门控权威判定)、_secret_guard_block
(app.py,泄露检测)、_secret_proposition_values(store.py,证据链 trace 脱敏)全部只认
`proposition.secret`,与 faction 表的 `{key}_secret` 毫无关系。所以"标了 secret 的字段"
从未真正被这条限知链保护/消费过——顶多是列表接口不回显明文而已。

本文件验证 `codex_secret_bridge.sync_faction_secrets` 把字段级 secret 同步成一条
`proposition(secret=True, source='codex_bridge')`,从而被【既有】限知链自动消费——
不是又建一套平行的假机制。② 号测试(_secret_fact_ids 命中)是本任务成败的关键断言。
"""
from scribe3.codex_secret_bridge import SOURCE, sync_faction_secrets
from scribe3.context_assembler import _secret_fact_ids
from scribe3.knowledge import project_frame


def _sync(store, name: str) -> dict:
    """辅助:回读势力行(与 app.py POST /factions 落库后的调用方式一致)后跑桥接。"""
    row = store.get_faction(name)
    assert row is not None, f"测试前置条件:势力 {name!r} 应已存在"
    return sync_faction_secrets(store, name, row)


def _bridge_rows(store, entity_id: str, attribute: str | None = None) -> list:
    """裸查桥接命题(不 LIMIT——刻意让重复行有机会被测出来,不是只看幂等后的表象)。"""
    q = ("SELECT meta::id(id) AS local, entity_id, attribute, value, secret, source "
         "FROM proposition WHERE entity_id=$eid AND source=$src")
    vars_ = {"eid": entity_id, "src": SOURCE}
    if attribute is not None:
        q += " AND attribute=$attr"
        vars_["attr"] = attribute
    return store._query(q, vars_)


FACTION = "衔尾蛇秘会"
ENTITY_ID = f"faction:{FACTION}"


def test_secret_field_generates_bridge_proposition(store):
    """① 写 faction 带 origin_secret=True → 自动生成 proposition,
    entity_id/attribute/secret/source 均正确。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)

    counts = _sync(store, FACTION)
    assert counts == {"created": 1, "updated": 0, "deleted": 0}

    rows = _bridge_rows(store, ENTITY_ID, "origin")
    assert len(rows) == 1, f"应恰好生成一条桥接命题,实际: {rows}"
    r = rows[0]
    assert r["entity_id"] == ENTITY_ID
    assert r["attribute"] == "origin"
    assert r["secret"] is True
    assert r["source"] == SOURCE
    assert r["value"] == "源自前朝遗族的复国密谋"


def test_bridge_proposition_consumed_by_secret_fact_ids(store):
    """② 关键断言(本任务成败所系):该命题必须被既有限知链的权威判定函数
    `context_assembler._secret_fact_ids` 查到——证明真正接入了 prompt 门控,
    而不是又建一套自说自话、无人消费的平行机制。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)

    rows = _bridge_rows(store, ENTITY_ID, "origin")
    expected_fact_id = f"fact:{rows[0]['local']}"

    ids = _secret_fact_ids(store)
    assert expected_fact_id in ids, (
        f"桥接命题 {expected_fact_id} 未被 _secret_fact_ids 收录,"
        f"说明没有真正接入既有限知门控(ids={ids})")


def test_bridge_proposition_gated_by_project_frame(store):
    """(附加,超出最低 8 条但同一关键链路)project_frame 角色知情投影也应正确消费:
    全知视角('world')能看见;没有对应 KnowledgeEdge 的角色看不见(帧外物理屏蔽)。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    rows = _bridge_rows(store, ENTITY_ID, "origin")
    fact_id = f"fact:{rows[0]['local']}"

    omniscient = project_frame(store, "world", 999)
    assert omniscient.knows(fact_id), "全知视角应能看到桥接命题(它就是一条正常 secret proposition)"

    frame = project_frame(store, "role:不知情的旁观者", 999)
    assert not frame.knows(fact_id), "无 KnowledgeEdge 的角色不应'知道'桥接的秘密(帧外屏蔽)"


def test_bridge_sync_idempotent_no_duplicate(store):
    """③ 幂等:同内容重复调用 sync_faction_secrets → 不产生重复命题。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    counts2 = _sync(store, FACTION)

    rows = _bridge_rows(store, ENTITY_ID, "origin")
    assert len(rows) == 1, f"重复同步不应产生重复命题,实际 {len(rows)} 条: {rows}"
    assert counts2 == {"created": 0, "updated": 1, "deleted": 0}


def test_bridge_sync_updates_value_on_content_change(store):
    """④ 内容更新 → 命题 value 同步更新(原地更新同一条记录,不是新增一条)。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    local_before = _bridge_rows(store, ENTITY_ID, "origin")[0]["local"]

    store.add_faction(FACTION, origin="真相更劲爆:老祖尚在人间")
    _sync(store, FACTION)

    rows_after = _bridge_rows(store, ENTITY_ID, "origin")
    assert len(rows_after) == 1
    assert rows_after[0]["local"] == local_before, "应原地更新同一条命题,而非新建一条"
    assert rows_after[0]["value"] == "真相更劲爆:老祖尚在人间"


def test_bridge_removed_when_secret_flag_turned_off(store):
    """⑤ 取消 secret(origin_secret=False)→ 桥接命题被删除(不再限知)。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    assert len(_bridge_rows(store, ENTITY_ID, "origin")) == 1

    store.add_faction(FACTION, origin_secret=False)
    counts = _sync(store, FACTION)

    assert _bridge_rows(store, ENTITY_ID, "origin") == []
    assert counts == {"created": 0, "updated": 0, "deleted": 1}


def test_bridge_removed_when_field_cleared(store):
    """⑥ 字段清空(显式置空字符串)→ 命题删除。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋", origin_secret=True)
    _sync(store, FACTION)
    assert len(_bridge_rows(store, ENTITY_ID, "origin")) == 1

    store.add_faction(FACTION, origin="")
    counts = _sync(store, FACTION)

    assert _bridge_rows(store, ENTITY_ID, "origin") == []
    assert counts == {"created": 0, "updated": 0, "deleted": 1}


def test_non_secret_field_generates_no_proposition(store):
    """⑦ 非 secret 字段(未标 `{key}_secret`)不生成命题,不污染命题空间。"""
    store.add_faction(FACTION, origin="源自前朝遗族的复国密谋")  # 未标 origin_secret

    counts = _sync(store, FACTION)

    assert _bridge_rows(store, ENTITY_ID) == []
    assert counts == {"created": 0, "updated": 0, "deleted": 0}


def test_bridge_proposition_tagged_with_source_for_filtering(store):
    """⑧ 桥接命题带 source='codex_bridge' 标记,可与作者手写命题区分/过滤。"""
    store.add_faction(FACTION, secret_agenda="连核心层都不知道的真相",
                      secret_agenda_secret=True)
    _sync(store, FACTION)

    # 作者/主编手写的命题(不经桥接,直接 add_fact)source 应天然为 NONE。
    from scribe3.ontology import Fact
    store.add_fact(Fact("fact:human1", ENTITY_ID, "手写命题", "作者亲手写的秘密",
                        valid_from=1, secret=True))

    all_secret_rows = store._query(
        "SELECT attribute, source FROM proposition WHERE entity_id=$eid AND secret=true",
        {"eid": ENTITY_ID})
    bridge_rows = [r for r in all_secret_rows if r.get("source") == SOURCE]
    human_rows = [r for r in all_secret_rows if r.get("source") != SOURCE]
    assert len(bridge_rows) == 1 and bridge_rows[0]["attribute"] == "secret_agenda"
    assert len(human_rows) == 1 and human_rows[0]["attribute"] == "手写命题"


def test_sync_ignores_faction_without_any_secret_field(store):
    """边界:全新势力,一个 secret 字段都没标 → 全部计数为 0,不报错。"""
    store.add_faction("光明会", ideology="启蒙")

    counts = _sync(store, "光明会")

    assert counts == {"created": 0, "updated": 0, "deleted": 0}
    assert _bridge_rows(store, "faction:光明会") == []


def test_value_over_cap_is_truncated(store):
    """值上限(报告注明为 500 字):超长内容被截断而非整段落库,
    避免单条 proposition 过大拖慢全表扫描类查询(_secret_fact_ids 等)。"""
    long_text = "秘" * 800
    store.add_faction(FACTION, origin=long_text, origin_secret=True)

    _sync(store, FACTION)

    row = _bridge_rows(store, ENTITY_ID, "origin")[0]
    assert len(row["value"]) <= 501, f"应被截断到上限附近,实际长度 {len(row['value'])}"
    assert row["value"] != long_text
