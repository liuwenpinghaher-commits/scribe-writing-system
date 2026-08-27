"""限知帧 167 迁移的护栏：等价性 + 规模。

167 把 fn::knowledge_frame 从「IN 列表逐行重算」改成「按 record link 取」。
这里钉两件事：
1. 新实现与留档的 v1 结果集**逐条一致**（否则限知系统会静默漏事实或多给事实，
   比性能问题严重得多）。
2. 耗时不随知识边总数二次增长——旧实现在千万字量级实测 32.7 秒，是不可用的。
"""
from __future__ import annotations

import time


def _seed_edge_cases(store):
    """专攻边界：会不会多给、会不会漏给。"""
    store._query(
        "INSERT INTO character ["
        "{id: character:jiao3, name:'焦三', aliases:[]},"
        "{id: character:aqi, name:'阿七', aliases:[]}];")
    props = [
        ("p_ok", 1, "NONE", "false"),        # 正常：该给
        ("p_future", 99, "NONE", "false"),   # 命题还没生效
        ("p_expired", 1, "5", "false"),      # 命题已失效
        ("p_arch", 1, "NONE", "true"),       # 已归档
        ("p_neg", 1, "NONE", "false"),       # 边 polarity=false（误信）
        ("p_until", 1, "NONE", "false"),     # 边 until_chapter 已过（忘了）
        ("p_late", 1, "NONE", "false"),      # 边 since_chapter 还没到（还不知道）
        ("p_other", 1, "NONE", "false"),     # 别人的边
    ]
    store._query("INSERT INTO proposition [%s];" % ",".join(
        "{id: proposition:%s, entity_id:'e', attribute:'a', value:'v', valid_from:%d, "
        "valid_to:%s, secret:false, leak_markers:[], archived:%s}" % p for p in props))
    edges = [
        ("jiao3", "p_ok", 1, "NONE", "true"),
        ("jiao3", "p_future", 1, "NONE", "true"),
        ("jiao3", "p_expired", 1, "NONE", "true"),
        ("jiao3", "p_arch", 1, "NONE", "true"),
        ("jiao3", "p_neg", 1, "NONE", "false"),
        ("jiao3", "p_until", 1, "3", "true"),
        ("jiao3", "p_late", 50, "NONE", "true"),
        ("aqi", "p_other", 1, "NONE", "true"),
    ]
    store._query("INSERT RELATION INTO knows [%s];" % ",".join(
        "{in: character:%s, out: proposition:%s, since_chapter:%d, until_chapter:%s, "
        "polarity:%s, acquired_via:'given'}" % e for e in edges))


def _locals(rows):
    return sorted((r or {}).get("local", "") for r in (rows or []))


def _frame(store, fn, who, ch):
    return _locals(store._query(f"RETURN fn::{fn}($k, $c);", {"k": who, "c": ch}))


def test_knowledge_frame_matches_legacy(store):
    """新实现与 v1 留档在所有边界上返回同一集合。"""
    _seed_edge_cases(store)
    cases = [
        ("jiao3", 10), ("role:jiao3", 10),   # 带不带 role: 前缀都要认
        ("aqi", 10), ("nobody", 10),         # 别人的 / 不存在的角色
        ("jiao3", 1), ("jiao3", 4), ("jiao3", 100),
    ]
    for who, ch in cases:
        assert _frame(store, "knowledge_frame", who, ch) == \
            _frame(store, "knowledge_frame_v1", who, ch), f"{who}@{ch} 与 v1 不一致"

    # 顺带钉住语义本身，别让两个实现一起错
    assert _frame(store, "knowledge_frame", "jiao3", 10) == ["p_ok"]
    assert _frame(store, "knowledge_frame", "jiao3", 1) == ["p_expired", "p_ok", "p_until"]
    assert _frame(store, "knowledge_frame", "nobody", 10) == []


def test_knowledge_frame_dedups_multiple_edges(store):
    """同一命题被多条边指向（重复获知 / 重复 ingest）时只算一次。

    新实现展开的是边而不是命题行，少一个 array::distinct 就会重复计数。
    """
    store._query("INSERT INTO character [{id: character:dup, name:'重', aliases:[]}];")
    store._query("INSERT INTO proposition [{id: proposition:pd, entity_id:'e', attribute:'a', "
                 "value:'v', valid_from:1, valid_to:NONE, secret:false, leak_markers:[]}];")
    store._query("INSERT RELATION INTO knows [%s];" % ",".join(
        "{in: character:dup, out: proposition:pd, since_chapter:%d, until_chapter:NONE, "
        "polarity:true, acquired_via:'told'}" % ch for ch in (1, 2, 3)))

    assert _frame(store, "knowledge_frame", "dup", 10) == ["pd"]


def test_project_frame_returns_all_known_facts(store):
    """限知帧要返回**全部**已知事实，不是第一条。

    真书里灌了 24 条命题后才暴露：`_project_frame_db` 原先 `raw = rows[0]`，
    把驱动返回的拍平行列表当成了嵌套数组，于是每个角色永远只知道一件事。
    单测数据每人恰好一条命题，所以一直没抓到——这个用例故意给三条。
    """
    from scribe3.knowledge import project_frame

    store._query("INSERT INTO character [{id: character:many, name:'多', aliases:[]}];")
    store._query("INSERT INTO proposition [%s];" % ",".join(
        "{id: proposition:m%d, entity_id:'e%d', attribute:'a%d', value:'v%d', "
        "valid_from:1, valid_to:NONE, secret:false, leak_markers:[]}" % (i, i, i, i)
        for i in range(3)))
    store._query("INSERT RELATION INTO knows [%s];" % ",".join(
        "{in: character:many, out: proposition:m%d, since_chapter:1, until_chapter:NONE, "
        "polarity:true, acquired_via:'saw'}" % i for i in range(3)))

    facts = list(project_frame(store, "role:many", 10).facts)
    assert sorted(f.id for f in facts) == ["fact:m0", "fact:m1", "fact:m2"], \
        f"限知帧只返回了 {len(facts)} 条，应为 3 条"


def test_normalize_frame_rows_accepts_both_shapes():
    """驱动的解包行为不该由我们赌——拍平和嵌套两种都要认。"""
    from scribe3.knowledge import _normalize_frame_rows

    flat = [{"local": "a"}, {"local": "b"}]
    assert _normalize_frame_rows(flat) == flat
    assert _normalize_frame_rows([flat]) == flat
    assert _normalize_frame_rows({"local": "a"}) == [{"local": "a"}]
    assert _normalize_frame_rows([]) == []


def test_reader_frame_reads_its_own_table(store):
    """读者帧存在 reader_knows（另一张表），不在 knows 里。

    169 之前 `fn::knowledge_frame('reader', ...)` 查 knows 必然空集，
    dramatic_irony 拿不到读者帧、静默回退 Python 全表扫。
    """
    from scribe3.knowledge import dramatic_irony, project_frame

    store._query("INSERT INTO character [{id: character:foc, name:'视角', aliases:[]}];")
    store._query("INSERT INTO proposition [%s];" % ",".join(
        "{id: proposition:r%d, entity_id:'e', attribute:'a%d', value:'v%d', "
        "valid_from:1, valid_to:NONE, secret:false, leak_markers:[]}" % (i, i, i)
        for i in range(3)))
    # 读者知道三条，视角角色只知道第一条 → 后两条是反讽点
    store._query("INSERT INTO reader_knows [%s];" % ",".join(
        "{proposition:'fact:r%d', since_chapter:1}" % i for i in range(3)))
    store._query(
        "INSERT RELATION INTO knows [{in: character:foc, out: proposition:r0, "
        "since_chapter:1, until_chapter:NONE, polarity:true, acquired_via:'saw'}];")

    reader = list(project_frame(store, "reader", 10).facts)
    assert sorted(f.id for f in reader) == ["fact:r0", "fact:r1", "fact:r2"], \
        f"读者帧应有 3 条，实得 {len(reader)}"

    irony = dramatic_irony(store, "role:foc", 10)
    assert sorted(f.id for f in irony) == ["fact:r1", "fact:r2"]


def test_reader_frame_respects_chapter_gate(store):
    """读者也得按章知道，不能提前。"""
    from scribe3.knowledge import project_frame

    store._query(
        "INSERT INTO proposition [{id: proposition:late, entity_id:'e', attribute:'a', "
        "value:'v', valid_from:1, valid_to:NONE, secret:false, leak_markers:[]}];")
    store._query("INSERT INTO reader_knows [{proposition:'fact:late', since_chapter:50}];")

    assert [f.id for f in project_frame(store, "reader", 10).facts] == []
    assert [f.id for f in project_frame(store, "reader", 50).facts] == ["fact:late"]


def test_knowledge_frame_scale(store):
    """耗时不随边总数二次增长。

    旧实现在 3000 章 / 3 万命题 / 15 万边下实测 32.7 秒（主角 8000 边）。
    这里用 1/5 规模让 CI 跑得动；阈值放得很宽，抓的是复杂度回潮而不是几十毫秒抖动。
    """
    n_char, n_prop, n_edge, hero = 80, 6_000, 30_000, 3_000

    rows = ["{id: character:c%d, name:'角色%d', aliases:[]}" % (i, i) for i in range(n_char)]
    for k in range(0, len(rows), 500):
        store._query("INSERT INTO character [%s];" % ",".join(rows[k:k + 500]))

    rows = ["{id: proposition:p%d, entity_id:'c%d', attribute:'attr%d', value:'值', "
            "valid_from:%d, valid_to:NONE, secret:false, leak_markers:[]}"
            % (i, i % n_char, i, (i % 600) + 1) for i in range(n_prop)]
    for k in range(0, len(rows), 400):
        store._query("INSERT INTO proposition [%s];" % ",".join(rows[k:k + 400]))

    rows = ["{in: character:c%d, out: proposition:p%d, since_chapter:%d, until_chapter:NONE, "
            "polarity:true, acquired_via:'given'}"
            % (0 if i < hero else i % n_char, (i * 7919) % n_prop, (i % 600) + 1)
            for i in range(n_edge)]
    for k in range(0, len(rows), 400):
        store._query("INSERT RELATION INTO knows [%s];" % ",".join(rows[k:k + 400]))

    t0 = time.perf_counter()
    got = _frame(store, "knowledge_frame", "c0", 600)
    elapsed = time.perf_counter() - t0

    assert got, "主角限知帧不该为空"
    assert elapsed < 3.0, (
        f"主角限知帧耗时 {elapsed:.1f}s（{len(got)} 条 / {n_edge} 边）。"
        "167 之前的实现在此规模约需十秒级，超阈说明二次复杂度回潮了。"
    )
