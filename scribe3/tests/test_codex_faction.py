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
