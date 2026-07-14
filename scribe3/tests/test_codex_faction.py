"""CX-Task 2 · faction 表扩字段 + store CONTENT/MERGE 驱动改造。

背景:codex_schema.py(Task 1)已把 faction 的字段权威源收拢成 ~28 键的声明式注册表;
本任务把 migration 逐字段落到 SurrealDB SCHEMAFULL(漏一个字段就落库被拒),并把
store.add_faction 从"DELETE+CREATE 整行覆盖"改成"UPSERT ... MERGE 部分更新"——
未传字段不再被销毁,前端/API 层不必再靠 pick() 手工回填全部字段才敢调用。
"""
import pathlib
import shutil

import pytest

from scribe3.codex_schema import all_storage_keys

MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent / "migrations"
MIGRATION_083 = MIGRATIONS_DIR / "083_faction_expand.surql"


def _apply_migrations_before_083(store, tmp_path):
    """把 001~082 拷进临时目录后应用——模拟"跑到 082、从未见过 083"的真实生产表。"""
    staged = tmp_path / "migrations_upto_082"
    staged.mkdir()
    for f in sorted(MIGRATIONS_DIR.glob("*.surql")):
        if f.stem < "083":
            shutil.copy(f, staged / f.name)
    store.apply_schema(str(staged))


def test_migration_083_on_real_legacy_row(unmigrated_store, tmp_path):
    """【P0 回归】真老行(而非 CREATE 出来的假老行)跑 083 —— 审查复现的生产事故。

    假绿陷阱:用已应用全部 migration 的 `store` 夹具 CREATE 一行来冒充老行,CREATE 会自动
    填上 DEFAULT,恰好绕开"老行 bool 字段为 NONE"这个触发条件。必须从未应用 083 的表起。

    修复前的真实症状(已在临时库实证):
      · SurrealDB 的 DEFAULT 不回填已有老行 → 老行 5 个新 `_secret` 字段是 NONE;
      · 而写入时 SurrealDB 校验【整条记录】→ 083 末尾的数据迁移 UPDATE 当场 coercion 报错
        (Expected `bool` but found `NONE`),拷贝根本没发生;
      · 且此后对该老行的任何写(含 add_faction 的 MERGE)永久 500 → 《印迹》6 个真实势力
        再也编辑不了。
    """
    st = unmigrated_store
    _apply_migrations_before_083(st, tmp_path)

    # 裸 SQL 造真老行:只有 9 个老字段、随机 record id(不经 add_faction,不填任何新字段)。
    st._raw_query(
        "CREATE faction SET name=$n, ideology=$i, status='active', leader=$l, "
        "known_members=$km, public_face=$pf, private_operation=$po, "
        "first_mention_chapter=1, private_operation_secret=true",
        {"n": "衔尾蛇秘会", "i": "复国", "l": "首席", "km": ["甲"],
         "pf": "商会", "po": "遗产运作+对外操纵全挤在这"})

    # 现在才跑 083(整文件一次多语句调用,与 apply_schema 的执行方式一致)。
    st._raw_query(MIGRATION_083.read_text(encoding="utf-8"))

    row = st.get_faction("衔尾蛇秘会")
    # ① 拷贝真的发生了(修复前:静默失败,这里是 None)
    assert row["artifact_operation"] == "遗产运作+对外操纵全挤在这", \
        f"private_operation 应已拷进 artifact_operation,实际: {row.get('artifact_operation')!r}"
    assert row["artifact_operation_secret"] is True, "secret 旗标应一并迁移"
    # ② 老行其余字段一字不变
    assert row["ideology"] == "复国"
    assert row["leader"] == "首席"
    assert row["known_members"] == ["甲"]
    assert row["public_face"] == "商会"
    assert row["first_mention_chapter"] == 1
    assert row["private_operation"] == "遗产运作+对外操纵全挤在这", "老字段本身不应被清空"
    # 老行的新 bool 旗标应已从 NONE 回填为 false(不是 None)
    assert row["origin_secret"] is False
    assert row["secret_agenda_secret"] is False

    # ④ 跑完 083 后老行仍可写(修复前:永久 500)
    st.add_faction("衔尾蛇秘会", motto="尾衔其首")
    assert st.get_faction("衔尾蛇秘会")["motto"] == "尾衔其首"

    # ③ 迁移重放不覆盖作者已手动分流的内容(幂等)
    st.add_faction("衔尾蛇秘会", artifact_operation="作者已手动分流的新内容")
    st._raw_query(MIGRATION_083.read_text(encoding="utf-8"))
    row2 = st.get_faction("衔尾蛇秘会")
    assert row2["artifact_operation"] == "作者已手动分流的新内容", "重放不应覆盖已有内容"
    assert row2["motto"] == "尾衔其首", "重放不应动其它字段"



def test_faction_full_new_fields_roundtrip(store):
    """① add_faction 传入新字段(含 array<object>/object 嵌套)→ list_factions() 回读一致。"""
    store.add_faction(
        "衔尾蛇秘会",
        origin="源自前朝遗族的复国密谋",
        key_figures=[
            {"name": "老祖", "generation": 1, "status": "active",
             "known_abilities": "摄魂"},
            {"name": "二当家", "generation": 2, "status": "dissipated",
             "known_abilities": "御火"},
        ],
        structure={"type": "金字塔", "core_size": 7,
                   "decision_mechanism": "长老议事", "succession": "血脉"},
    )
    factions = store.list_factions()
    f = next(x for x in factions if x["name"] == "衔尾蛇秘会")
    assert f["origin"] == "源自前朝遗族的复国密谋"
    assert f["structure"] == {"type": "金字塔", "core_size": 7,
                              "decision_mechanism": "长老议事", "succession": "血脉"}
    assert f["key_figures"] == [
        {"name": "老祖", "generation": 1, "status": "active", "known_abilities": "摄魂"},
        {"name": "二当家", "generation": 2, "status": "dissipated", "known_abilities": "御火"},
    ], f"array<object> 嵌套应保真,不被压平,实际: {f['key_figures']}"


def test_faction_partial_update_preserves_other_fields(store):
    """② store 层 MERGE 部分更新:再传 motto 一个字段 → 其余先前字段不丢。"""
    store.add_faction(
        "衔尾蛇秘会",
        origin="源自前朝遗族的复国密谋",
        key_figures=[{"name": "老祖", "generation": 1, "status": "active",
                      "known_abilities": "摄魂"}],
        structure={"type": "金字塔", "core_size": 7,
                   "decision_mechanism": "长老议事", "succession": "血脉"},
    )
    store.add_faction("衔尾蛇秘会", motto="尾衔其首,生生不息")

    factions = [f for f in store.list_factions() if f["name"] == "衔尾蛇秘会"]
    assert len(factions) == 1, f"同名应只剩一行(MERGE 不应新建重复记录),实际 {len(factions)}"
    f = factions[0]
    assert f["motto"] == "尾衔其首,生生不息"
    assert f["origin"] == "源自前朝遗族的复国密谋", "只改 motto 不应销毁 origin"
    assert f["structure"]["core_size"] == 7, "只改 motto 不应销毁 structure"
    assert f["key_figures"] and f["key_figures"][0]["name"] == "老祖", \
        "只改 motto 不应销毁 key_figures"


def test_faction_secret_companion_flag(store):
    """③ secret 伴生字段:{key}_secret 独立落库/回读,不受其它字段影响。"""
    store.add_faction("天龙座", origin="秘不可宣", origin_secret=True)
    f = next(x for x in store.list_factions() if x["name"] == "天龙座")
    assert f["origin"] == "秘不可宣"
    assert f["origin_secret"] is True

    # 只改别的字段,origin_secret 应保持 True(未传不动)。
    store.add_faction("天龙座", motto="星辰不熄")
    f2 = next(x for x in store.list_factions() if x["name"] == "天龙座")
    assert f2["origin_secret"] is True, "未传 origin_secret 时不应被重置"
    assert f2["origin"] == "秘不可宣", "未传 origin 时不应被销毁"


def test_faction_legacy_row_survives_new_schema(store):
    """⑤ 旧数据兼容:只有 9 个老字段的行,list_factions() 不崩,新字段读出 None/[]。"""
    # 模拟 migration 083 之前、只按老 9 字段建的行(不经 add_faction,直接走底层写入路径)。
    store._execute_write(
        "CREATE faction SET name=$n, ideology=$i, status=$s, leader=$l, "
        "known_members=$km, public_face=$pf, private_operation=$po, "
        "first_mention_chapter=$fmc",
        {"n": "老门派", "i": "守旧", "s": "active", "l": "老掌门",
         "km": ["甲"], "pf": "武馆", "po": "私下囤粮", "fmc": 1})

    factions = store.list_factions()  # 不应抛异常
    f = next(x for x in factions if x["name"] == "老门派")
    assert f["ideology"] == "守旧"
    # 新字段无值时按 schema 默认/NONE 读出,不崩、不是 KeyError。
    assert f.get("origin") in (None, ""), f"新 option<string> 字段应为 None,实际: {f.get('origin')}"
    assert f.get("key_figures") in (None, [], "" ), \
        f"新 array<object> 字段应为空/None,实际: {f.get('key_figures')}"
    assert f.get("aliases") == [], f"array<string> DEFAULT [] 字段应为空列表,实际: {f.get('aliases')}"
    assert f.get("origin_secret") is False, "新 secret 旗标应默认 False"


def test_private_operation_migration_copies_to_artifact_operation(store):
    """⑥ private_operation → artifact_operation 迁移(幂等,只在目标为空时拷贝)。"""
    # 模拟老行:只写 private_operation(+ secret 旗标),不写 artifact_operation。
    store._execute_write(
        "CREATE faction SET name=$n, private_operation=$po, private_operation_secret=$pos",
        {"n": "旧垃圾桶门", "po": "遗产运作+对外操纵+加速手段全挤在这", "pos": True})

    # 重放本迁移(apply_schema 已在 store fixture 建库时跑过一次;此处再跑一次验证幂等)。
    import pathlib
    migration_path = (pathlib.Path(__file__).parent.parent
                      / "migrations" / "083_faction_expand.surql")
    store._raw_query(migration_path.read_text(encoding="utf-8"))

    f = next(x for x in store.list_factions() if x["name"] == "旧垃圾桶门")
    assert f["artifact_operation"] == "遗产运作+对外操纵+加速手段全挤在这"
    assert f["artifact_operation_secret"] is True
    assert f["private_operation"] == "遗产运作+对外操纵+加速手段全挤在这", "老字段本身不应被清空"

    # 幂等:作者之后手动改了 artifact_operation,再重放迁移不应覆盖回老值。
    store.add_faction("旧垃圾桶门", artifact_operation="作者已手动分流的新内容")
    store._raw_query(migration_path.read_text(encoding="utf-8"))
    f2 = next(x for x in store.list_factions() if x["name"] == "旧垃圾桶门")
    assert f2["artifact_operation"] == "作者已手动分流的新内容", \
        "迁移重放不应覆盖作者已手动分流的 artifact_operation"


def test_add_faction_rejects_unknown_field(store):
    """白名单拒绝语义(store.add_faction 抛 ValueError,而非静默丢弃/落库脏字段)。"""
    with pytest.raises(ValueError):
        store.add_faction("未知门", not_a_real_field="乱写")


def test_get_faction_by_name(store):
    """新增 get_faction(name):按名精确取单个势力(供 REST/桥接/一致性校验按名查询)。"""
    store.add_faction("求真堂", origin="求真为本", motto="唯真不破")
    f = store.get_faction("求真堂")
    assert f is not None
    assert f["motto"] == "唯真不破"
    assert store.get_faction("不存在的门派") is None


def test_all_storage_keys_faction_writable(store):
    """codex_schema.all_storage_keys('faction') 白名单里的每个 key,store 层都接受(冒烟)。
    防止注册表新增字段却忘了在 store 白名单/migration 里同步接住。"""
    keys = all_storage_keys("faction")
    assert "artifact_operation_secret" in keys
    assert "origin_secret" in keys
    # 逐个当作单字段更新调用一次(仅验证不抛 ValueError/不炸;值类型随意用字符串占位,
    # 除 known_members/aliases 等 array 字段外用其原生 Python 类型近似即可)。
    sample_arrays = {"known_members", "aliases"}
    sample_array_objs = {"internal_factions", "key_figures", "artifacts",
                         "goals", "world_rule_affinity", "timeline"}
    for k in keys:
        if k == "name":
            continue
        if k in sample_arrays:
            store.add_faction("白名单探针", **{k: ["x"]})
        elif k in sample_array_objs:
            store.add_faction("白名单探针", **{k: [{"a": 1}]})
        elif k == "structure":
            store.add_faction("白名单探针", **{k: {"type": "扁平"}})
        elif k.endswith("_secret"):
            store.add_faction("白名单探针", **{k: True})
        elif k == "first_mention_chapter":
            store.add_faction("白名单探针", **{k: 3})
        elif k == "status":
            store.add_faction("白名单探针", **{k: "dormant"})
        else:
            store.add_faction("白名单探针", **{k: "占位值"})
    # 全部走完不炸即通过。
    assert store.get_faction("白名单探针") is not None


# ============================================================
# CX-Task 3:faction REST/MCP 按注册表通用化(secret 自动配对,堵掩码回写陷阱)
# ============================================================
import asyncio
import inspect

from fastapi.testclient import TestClient

import scribe3.app as A
import scribe3.mcp as M
from scribe3.codex_schema import all_storage_keys as _all_keys
from scribe3.codex_schema import fields_for as _fields_for


def _client(store):
    A.set_store(store)
    return TestClient(A.app)


class _AcceptCtx:
    """假 elicitation 上下文:恒批准,供 MCP 写工具测试用(与 test_mcp.py 同款)。"""
    async def elicit(self, message, schema):
        return type("_R", (), {"action": "accept"})()


# ---- ① GET /factions 通用掩码:全部 secret_capable 字段都应被掩码,不只 private_operation ----
def test_get_factions_masks_all_secret_capable_fields(store):
    """现状(修复前)GET /factions 只裹了 private_operation 一个字段的掩码循环;
    origin/artifact_operation/external_manipulation/acceleration_methods/secret_agenda
    这五个新 secret 字段标了 *_secret=True 后,GET 默认应一并掩码——逐字段断言。"""
    store.add_faction(
        "赤霄盟",
        origin="秘密起源:前朝余孽", origin_secret=True,
        artifact_operation="遗产暗中运作", artifact_operation_secret=True,
        external_manipulation="操纵他人门派", external_manipulation_secret=True,
        acceleration_methods="加速夺权手段", acceleration_methods_secret=True,
        secret_agenda="真正野心是颠覆", secret_agenda_secret=True,
    )
    c = _client(store)
    masked = next(f for f in c.get("/factions").json() if f["name"] == "赤霄盟")
    for key in ("origin", "artifact_operation", "external_manipulation",
                "acceleration_methods", "secret_agenda"):
        assert masked[key] == "🔒 私密", f"{key} 应被掩码,实际: {masked[key]!r}"

    revealed = next(f for f in c.get("/factions", params={"reveal_secret": True}).json()
                    if f["name"] == "赤霄盟")
    assert revealed["origin"] == "秘密起源:前朝余孽"
    assert revealed["artifact_operation"] == "遗产暗中运作"
    assert revealed["external_manipulation"] == "操纵他人门派"
    assert revealed["acceleration_methods"] == "加速夺权手段"
    assert revealed["secret_agenda"] == "真正野心是颠覆"


# ---- ②【关键·防数据毁灭】POST /factions 掩码哨兵通用循环 ----
def test_post_factions_masked_secret_field_not_overwritten(store):
    """现状(修复前)POST /factions 只 pop 了 private_operation 一个掩码哨兵。
    前端典型行为:GET 拿到整行(含掩码占位符)→ 只改其中一个无关字段 → 原样 POST 回传。
    若 origin 没有同款哨兵,掩码字符串 "🔒 私密" 会被当成真值直接落库,永久销毁原文——
    这条测试证明该陷阱;修复前必须失败(红)。"""
    store.add_faction("赤火盟", origin="真实起源:前朝余孽复仇", origin_secret=True,
                      motto="旧格言")
    c = _client(store)
    masked = next(f for f in c.get("/factions").json() if f["name"] == "赤火盟")
    assert masked["origin"] == "🔒 私密"   # 先确认落库真值确实被 GET 掩码

    r = c.post("/factions", json={
        "name": "赤火盟",
        "origin": "🔒 私密",        # 前端整行回传,origin 未被作者编辑,仍是掩码占位符
        "origin_secret": True,
        "motto": "新格言",          # 这次真正想改的字段
    })
    assert r.status_code == 200, r.text

    row = next(f for f in c.get("/factions", params={"reveal_secret": True}).json()
               if f["name"] == "赤火盟")
    assert row["origin"] == "真实起源:前朝余孽复仇", (
        f"掩码字符串不应覆盖真值——现状陷阱复现:实际 {row['origin']!r}")
    assert row["motto"] == "新格言", "motto 应正常更新"


# ---- ③ GET /codex-schema/{kind}:只读元数据端点 ----
def test_get_codex_schema_faction_returns_metadata(store):
    c = _client(store)
    r = c.get("/codex-schema/faction")
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list) and len(data) == len(_fields_for("faction")), (
        f"schema_for('faction') 条目数应与注册表字段数一致,实际 {len(data)} 条")
    by_key = {f["key"]: f for f in data}
    assert "origin" in by_key and by_key["origin"]["secret_capable"] is True
    assert "key_figures" in by_key and by_key["key_figures"]["item_schema"], \
        "array<object> 字段应带非空 item_schema"
    assert by_key["status"]["enum"] == ["active", "dissolved", "dormant", "reformed"]


def test_get_codex_schema_unknown_kind_404(store):
    c = _client(store)
    r = c.get("/codex-schema/not_a_real_kind")
    assert r.status_code == 404, r.text


# ---- ④ enum 非法值 → 422 ----
def test_post_factions_illegal_status_enum_422(store):
    c = _client(store)
    r = c.post("/factions", json={"name": "乱序门", "status": "not_a_real_status"})
    assert r.status_code == 422, f"非法 status 应 422,实际: {r.status_code} {r.text}"
    assert not any(f["name"] == "乱序门" for f in c.get("/factions").json()), \
        "非法枚举不应落库"


def test_post_factions_illegal_nested_enum_best_effort_422(store):
    """嵌套子字段 enum(key_figures[].status)尽力而为校验:SurrealDB FLEXIBLE 子字段
    DB 层不校验,app 层是唯一防线。"""
    c = _client(store)
    r = c.post("/factions", json={
        "name": "乱序门二",
        "key_figures": [{"name": "甲", "generation": 1, "status": "not_a_real_status"}],
    })
    assert r.status_code == 422, f"非法嵌套 status 应 422,实际: {r.status_code} {r.text}"


# ---- FactionIn 字段集钉子:防两处漂移 ----
def test_faction_in_fields_match_registry_storage_keys():
    assert set(A.FactionIn.model_fields.keys()) == set(_all_keys("faction")), (
        "FactionIn 字段集应与 codex_schema.all_storage_keys('faction') 完全一致;"
        f"多余: {set(A.FactionIn.model_fields.keys()) - set(_all_keys('faction'))}; "
        f"缺失: {set(_all_keys('faction')) - set(A.FactionIn.model_fields.keys())}")


# ---- ⑤ MCP s3_list_factions:按 _secret 后缀通用掩码,不硬编码字段名 ----
def test_mcp_s3_list_factions_masks_by_suffix_generically(store):
    M.set_store(store)
    store.add_faction("影卫", origin="来路不明", origin_secret=True)
    factions = M.s3_list_factions()
    f = next(x for x in factions if x["name"] == "影卫")
    assert f["origin"] == "🔒 私密", f"origin 应按 origin_secret 后缀自动掩码,实际: {f['origin']!r}"
    revealed = next(x for x in M.s3_list_factions(reveal_secret=True) if x["name"] == "影卫")
    assert revealed["origin"] == "来路不明"


# ---- ⑥ MCP s3_add_faction:关键字实参 + 支持新字段 ----
def test_mcp_s3_add_faction_supports_new_fields_keyword(store):
    M.set_store(store)
    res = asyncio.run(M.s3_add_faction(
        _AcceptCtx(), name="鸿蒙会",
        origin="创会秘辛", origin_secret=True,
        key_figures=[{"name": "甲", "generation": 1, "status": "active",
                      "known_abilities": "御风"}],
        structure={"type": "扁平", "core_size": 3},
    ))
    assert res["status"] == "written"
    f = store.get_faction("鸿蒙会")
    assert f["origin"] == "创会秘辛"
    assert f["origin_secret"] is True
    assert f["key_figures"][0]["name"] == "甲"
    assert f["structure"]["type"] == "扁平"


def test_mcp_s3_add_faction_signature_covers_all_registry_fields():
    """签名守卫:s3_add_faction 必须暴露 codex_schema.all_storage_keys('faction') 里
    的每一个字段(关键字实参),防止注册表新增字段却忘了在 MCP 层同步接住。"""
    sig = inspect.signature(M.s3_add_faction)
    missing = set(_all_keys("faction")) - set(sig.parameters.keys())
    assert not missing, f"s3_add_faction 缺少参数: {missing}"


def test_mcp_s3_add_faction_partial_update_does_not_clobber_unset_fields(store):
    """回归(审查实测复现的现状 bug):第二次调用只传 leader,ideology/known_members 等
    先前字段不应被静默清空为 None(旧实现:MCP 层新老字段一律用具体默认值而非哨兵,
    每次调用都会把未传字段重置,known_members 甚至会因写 NONE 进非 optional array 而
    直接 500)。"""
    M.set_store(store)
    res1 = asyncio.run(M.s3_add_faction(_AcceptCtx(), name="探测门",
                                        ideology="复古", leader="甲",
                                        known_members=["甲"], public_face="药铺"))
    assert res1["status"] == "written"

    res2 = asyncio.run(M.s3_add_faction(_AcceptCtx(), name="探测门", leader="乙"))
    assert res2["status"] == "written"

    f = store.get_faction("探测门")
    assert f["leader"] == "乙", "leader 应更新"
    assert f["ideology"] == "复古", "未传字段不应被清空"
    assert f["known_members"] == ["甲"], "未传字段不应被清空"
    assert f["public_face"] == "药铺", "未传字段不应被清空"


# ---- ⑦(审查追加)未知字段 → 422 不是 500 ----
def test_post_factions_unknown_field_422_not_500(store):
    c = _client(store)
    r = c.post("/factions", json={"name": "笔误门", "nonexistent_field_xyz": "abc"})
    assert r.status_code == 422, f"未知字段应 422 而非裸 500,实际: {r.status_code} {r.text}"


# ---- ⑧(审查追加)并发同名 → 409 不是 500 ----
def test_post_factions_concurrent_duplicate_name_409_not_500(store, monkeypatch):
    """确定性复现 TOCTOU 竞态(而非依赖真线程,避免测试 flaky):monkeypatch store._query,
    让 add_faction 内部"该名字是否已存在"的探测查询恒回空,强迫它走 CREATE 分支——
    即便该名字已存在——从而真实撞上 uniq_faction_name UNIQUE 索引(migration 038)。
    实测(本仓 surrealdb Python SDK 2.0.0 + surreal 服务端 3.2.0):该冲突抛的是
    `surrealdb.errors.InternalError`(message 含 "already contains"),而非 QueryError。"""
    c = _client(store)
    r1 = c.post("/factions", json={"name": "并发门"})
    assert r1.status_code == 200, r1.text

    orig_query = store._query

    def _fake_query(surql, vars=None):
        if surql.startswith("SELECT id FROM faction WHERE name=$n"):
            return []
        return orig_query(surql, vars)

    monkeypatch.setattr(store, "_query", _fake_query)

    r2 = c.post("/factions", json={"name": "并发门", "motto": "抢建"})
    assert r2.status_code == 409, f"并发同名应 409 而非裸 500,实际: {r2.status_code} {r2.text}"


# ============================================================
# CX-Task 3 追修(审查 P2×2):畸形输入必须转干净 4xx,不得裸 500。
# 上面 ⑦ 只覆盖了"普通未知字段名";还有两类畸形输入会绕过校验一路走到底层炸成 500。
# ============================================================

# ---- P2-1:字段名撞 Python 保留字 "self" → 曾裸 500(TypeError,不被 except ValueError 接住)----
def test_post_factions_field_named_self_422_not_500(store):
    """`st.add_faction(name, **sent)` 里若 sent 含键 "self",展开后与绑定方法的隐式 self
    实参打架 → TypeError(不是 ValueError,躲过异常映射)→ 裸 500。
    根治:app 层前置白名单过滤,未知键(含 "self")当场 422 并列出键名,压根不让它进
    `**sent` 展开——顺带也堵住未来 store 方法签名变化引入的新保留字冲突。"""
    c = _client(store)
    r = c.post("/factions", json={"name": "保留字门", "self": "x"})
    assert r.status_code == 422, f"字段名 'self' 应 422 而非裸 500,实际: {r.status_code} {r.text}"
    assert "self" in r.text, f"detail 应列出未知键名,实际: {r.text}"


# ---- P2-2:array<object> 字段传非 dict 元素 → 曾裸 500(6 个字段全中)----
@pytest.mark.parametrize("field", ["internal_factions", "key_figures", "artifacts",
                                   "goals", "world_rule_affinity", "timeline"])
def test_post_factions_array_object_non_dict_element_422_not_500(store, field):
    """校验器(当时叫 _enum_violations,现 _field_violations)原来对非 dict 元素静默
    continue,畸形数据(如 goals=["纯字符串"])
    一路走到 DB:migration 083 把这些字段的 `.*` 子字段定义为 `TYPE object FLEXIBLE`,
    字符串元素无法 coerce 成 object → InternalError(message 不含 "already contains",
    躲过 409 分支)→ 原样 re-raise → 裸 500。全部 6 个 array<object> 字段逐个钉。"""
    c = _client(store)
    r = c.post("/factions", json={"name": f"畸形门_{field}", field: ["我不是对象"]})
    assert r.status_code == 422, (
        f"{field} 传非 dict 元素应 422 而非裸 500,实际: {r.status_code} {r.text}")
    assert field in r.text, f"detail 应指出是哪个字段,实际: {r.text}"


# ---- P2-2 同类洞(本次追查发现):array<string> 字段传非字符串元素 → 曾同样裸 500 ----
@pytest.mark.parametrize("field", ["known_members", "aliases"])
@pytest.mark.parametrize("bad_element", [{"a": 1}, 123])
def test_post_factions_array_string_non_str_element_422_not_500(store, field, bad_element):
    """与 array<object> 完全同型:DB 类型是 `array<string>`,传 dict/int 元素 coercion
    失败 → 裸 500(已实测复现)。pydantic 拦不住(FactionIn 里是裸 `list`,元素不带类型),
    app 层同样是唯一防线。"""
    c = _client(store)
    r = c.post("/factions", json={"name": f"畸形串门_{field}", field: [bad_element]})
    assert r.status_code == 422, (
        f"{field} 传非字符串元素应 422 而非裸 500,实际: {r.status_code} {r.text}")
    assert field in r.text, f"detail 应指出是哪个字段,实际: {r.text}"
