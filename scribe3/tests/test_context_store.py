"""Task 3:context_session / context_snapshot 的 SurrealDB 原子存储测试。

覆盖三条合同:
1. create_context_session 返回 revision=0 的完整初始快照(entry/focus 默认值);
2. advance_context 是单事务 CAS——revision 失配抛 StaleContextError,绝不自动覆盖;
3. 幂等重放:同 navigation_id 重复提交返回同一快照;并发窗口下撞
   UNIQUE(session_id, navigation_id) 索引必须转为"读回已有快照"而非抛错。
"""
import pytest

from scribe3.context_models import ContextFocus, NavigationIntent, StaleContextError


def nav(expected_revision, navigation_id, focus_id, *, reason="item"):
    """构造最小可用 NavigationIntent(测试专用 helper)。"""
    return NavigationIntent(
        navigation_id=navigation_id,
        expected_revision=expected_revision,
        entry="manuscript",
        directory_path=["manuscript", "chapter:1"],
        focus=ContextFocus(type="character", id=focus_id, label="焦点角色"),
        detail_route=focus_id,
        chapter=1,
        phase="draft",
        reason=reason,
    )


def test_create_context_session_returns_initial_snapshot(store):
    s = store.create_context_session("book-a", "author", "browser-a")
    assert s["revision"] == 0
    assert s["work"] == "book-a"
    assert s["entry"] == "manuscript"
    assert s["focus"]["type"] == "entry"
    assert s["focus"]["id"] == "entry:manuscript"
    assert s["detail_route"] == "entry:manuscript"
    assert s["navigation_id"] == "init"
    assert s["reason"] == "restore"
    # Task 6:thread_id 取自正式主编线程(ethread 命名空间),不再是占位 thread:*_default
    assert s["thread_id"].startswith("ethread:book-a:")
    assert len(s["context_hash"]) == 64
    # 初始快照与 session 同事务落库,立即可读回
    got = store.get_context_snapshot(s["session_id"])
    assert got["revision"] == 0
    assert got["context_hash"] == s["context_hash"]


def test_session_thread_id_matches_editorial_thread_and_backfill(store):
    """I-1 端到端锁:create_context_session 的 thread_id ==
    get_or_create_editorial_thread == backfill 归档目标(三等式)——命名空间不再断裂。
    并验证:旧消息(不带 thread_id)经 backfill 后,能用 session 的 thread_id 读回。

    用 store.db_name 作 work:生产里一书一 store(db==work),create_context_session、
    backfill(用 self.db_name)、get_or_create_editorial_thread 三者 work 恒一致。"""
    work = store.db_name
    # 存量旧消息:无 thread_id(升级前写入)
    store.add_chat_message(1, "draft", "user", "旧对话不得消失")
    # session 与正式线程共用同一 ethread id
    s = store.create_context_session(work, "author", "browser-a")
    thread = store.get_or_create_editorial_thread(work, "author")
    assert s["thread_id"] == thread["thread_id"], "session 与正式线程必须同 id"
    # backfill 归档目标 = 同一线程;旧消息经 session.thread_id 读得回(UI 真实路径)
    store.backfill_thread_ids()
    msgs = store.list_thread_messages(s["thread_id"])
    assert any(m["text"] == "旧对话不得消失" for m in msgs), \
        "session.thread_id 必须能读到 backfill 归档的旧消息(否则 UI 上凭空消失)"


def test_advance_context_is_atomic_and_idempotent(store):
    first = store.create_context_session("book-a", "author", "browser-a")
    intent = nav(expected_revision=first["revision"], navigation_id="nav-1", focus_id="role:a")
    advanced = store.advance_context(first["session_id"], intent.model_dump())
    repeated = store.advance_context(first["session_id"], intent.model_dump())
    assert repeated["revision"] == advanced["revision"] == 1
    assert repeated["context_hash"] == advanced["context_hash"]


def test_advance_context_rejects_stale_revision(store):
    session = store.create_context_session("book-a", "author", "browser-a")
    store.advance_context(session["session_id"], nav(0, "nav-1", "role:a").model_dump())
    with pytest.raises(StaleContextError):
        store.advance_context(session["session_id"], nav(0, "nav-2", "role:b").model_dump())


def test_stale_error_carries_expected_actual_latest(store):
    """StaleContextError 必须带 expected/actual/latest,前端凭 latest 直接对齐。"""
    s = store.create_context_session("book-a", "author", "browser-a")
    store.advance_context(s["session_id"], nav(0, "nav-1", "role:a").model_dump())
    with pytest.raises(StaleContextError) as ei:
        store.advance_context(s["session_id"], nav(0, "nav-2", "role:b").model_dump())
    assert ei.value.expected == 0
    assert ei.value.actual == 1
    assert ei.value.latest and ei.value.latest["revision"] == 1
    # CAS 失败绝不落新快照:current 仍指向 nav-1
    assert store.get_context_snapshot(s["session_id"])["navigation_id"] == "nav-1"


def test_advance_chain_and_get_by_revision(store):
    s = store.create_context_session("book-a", "author", "browser-a")
    sid = s["session_id"]
    a1 = store.advance_context(sid, nav(0, "nav-1", "role:a").model_dump())
    a2 = store.advance_context(sid, nav(1, "nav-2", "role:b").model_dump())
    assert a2["revision"] == 2
    assert a2["previous_revision"] == 1
    # revision=None → current(最新)
    cur = store.get_context_snapshot(sid)
    assert cur["revision"] == 2 and cur["navigation_id"] == "nav-2"
    # 指定 revision → 历史版本
    old = store.get_context_snapshot(sid, revision=1)
    assert old["navigation_id"] == "nav-1"
    assert old["context_hash"] == a1["context_hash"]
    # 不存在的 revision / session → None
    assert store.get_context_snapshot(sid, revision=9) is None
    assert store.get_context_snapshot("no-such-session") is None


def test_advance_context_unknown_session_raises(store):
    with pytest.raises(ValueError):
        store.advance_context("no-such-session", nav(0, "nav-1", "role:a").model_dump())


def test_unique_index_blocks_duplicate_navigation(store):
    """验证 UNIQUE(session_id, navigation_id) 索引真实存在:绕过 store 方法
    手工 CREATE 一条同键快照,必须被索引拒绝(IndexExists 形状的错误)。"""
    s = store.create_context_session("book-a", "author", "browser-a")
    sid = s["session_id"]
    store.advance_context(sid, nav(0, "nav-1", "role:a").model_dump())
    with pytest.raises(Exception) as ei:
        store._raw_query(
            "CREATE context_snapshot SET session_id=$sid, work='book-a', revision=77, "
            "previous_revision=NONE, navigation_id='nav-1', "
            "thread_id='thread:book-a_default', entry='manuscript', directory_path=[], "
            "focus={type:'character', id:'role:x', label:''}, detail_route='role:x', "
            "chapter=NONE, phase=NONE, focalizer=NONE, reason='item', "
            "context_hash='deadbeef'",
            {"sid": sid})
    msg = str(ei.value)
    assert ("context_snapshot_navigation" in msg) or ("already contains" in msg)


def test_unique_conflict_converted_to_idempotent_replay(store, monkeypatch):
    """并发窗口模拟:快照隔离下两个重放可能同时通过"先查 navigation_id"预查,
    后到者由 UNIQUE 索引兜底。这里把第一次预查短路(模拟预查发生在另一提交前),
    让 CREATE 真撞唯一索引——实现必须捕获冲突并读回已有快照返回,不得抛给前端。"""
    s = store.create_context_session("book-a", "author", "browser-a")
    sid = s["session_id"]
    first = store.advance_context(sid, nav(0, "nav-1", "role:a").model_dump())

    orig = store._find_context_snapshot_by_navigation
    calls = {"n": 0}

    def fake(session_id, navigation_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # 短路预查:模拟并发写入者尚未提交
        return orig(session_id, navigation_id)

    monkeypatch.setattr(store, "_find_context_snapshot_by_navigation", fake)
    # expected=1 通过 CAS 检查,CREATE 撞 navigation 唯一索引 → 读回 nav-1 已有快照
    replay = store.advance_context(sid, nav(1, "nav-1", "role:a").model_dump())
    assert replay["revision"] == first["revision"] == 1
    assert replay["context_hash"] == first["context_hash"]
    assert calls["n"] >= 2  # 冲突捕获路径确实走了读回


def test_stale_throw_with_existing_navigation_returns_replay(store, monkeypatch, caplog):
    """I-1(真实并发形状):对方已提交后,同 navigation 重放的事务撞的是
    stale THROW(IF 判定在 CREATE 之前,轮不到唯一索引)——必须先按 navigation
    读回、幂等返回旧快照,不得给重放请求喂假 409。payload 不一致仅 warning。"""
    import logging
    s = store.create_context_session("book-a", "author", "browser-a")
    sid = s["session_id"]
    first = store.advance_context(sid, nav(0, "nav-1", "role:a").model_dump())

    orig = store._find_context_snapshot_by_navigation
    calls = {"n": 0}

    def fake(session_id, navigation_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # 短路预查:模拟预查发生在对方提交之前
        return orig(session_id, navigation_id)

    monkeypatch.setattr(store, "_find_context_snapshot_by_navigation", fake)
    # 与真实竞态一致:重放仍带 expected=0(对方已推到 1)→ 事务抛 stale THROW
    # 故意换 focus payload,顺带验证 M-1:忽略新 payload、log warning
    with caplog.at_level(logging.WARNING, logger="scribe3.store"):
        replay = store.advance_context(sid, nav(0, "nav-1", "role:b").model_dump())
    assert replay["revision"] == first["revision"] == 1
    assert replay["context_hash"] == first["context_hash"]
    assert replay["focus"]["id"] == "role:a"  # 以先落库者为准,新 payload 被忽略
    assert calls["n"] >= 2  # stale 分支确实走了 navigation 读回
    assert any("payload 与已落库快照不一致" in r.message for r in caplog.records)


def test_advance_rejects_ended_session(store):
    """I-2:ended 守卫——已结束的会话拒绝推进(end 方法后续任务才建,先手工置)。"""
    s = store.create_context_session("book-a", "author", "browser-a")
    sid = s["session_id"]
    store._raw_query(
        "UPDATE type::thing('context_session', $sid) SET status='ended'",
        {"sid": sid})
    with pytest.raises(ValueError, match="已结束"):
        store.advance_context(sid, nav(0, "nav-1", "role:a").model_dump())
    # 守卫在事务内 CREATE 之前,不落任何新快照
    assert store.get_context_snapshot(sid)["revision"] == 0


def test_classify_context_tx_error_text_injection():
    """I-3:错误分流函数的单元级文本注入测试(真提交层冲突难稳定复现)。"""
    from scribe3.store import SurrealStore
    c = SurrealStore._classify_context_tx_error
    assert c("An error occurred: stale_revision:5") == "stale"
    assert c("An error occurred: context_session_missing") == "session_missing"
    assert c("An error occurred: context_session_ended") == "session_ended"
    assert c("Database index `context_snapshot_navigation` already contains "
             "['x', 'nav-1'], with record `context_snapshot:abc`") == "unique_conflict"
    assert c("Failed to commit transaction due to a read or write conflict. "
             "This transaction can be retried") == "commit_conflict"
    assert c("The table 'context_session' does not exist") == "unknown"


def test_revision_unique_conflict_without_navigation_raises_stale(store):
    """M-4:撞的是 revision 唯一键且无同 navigation 快照(版本号被并发抢走)
    → 语义等价 CAS 失配,转 StaleContextError 而非裸 RuntimeError。"""
    s = store.create_context_session("book-a", "author", "browser-a")
    sid = s["session_id"]
    store.advance_context(sid, nav(0, "nav-1", "role:a").model_dump())
    # 手工占住 (sid, revision=2),模拟并发写入者抢走了下一个版本号
    store._raw_query(
        "CREATE context_snapshot SET session_id=$sid, work='book-a', revision=2, "
        "previous_revision=1, navigation_id='ghost-nav', "
        "thread_id='thread:book-a_default', entry='manuscript', directory_path=[], "
        "focus={type:'character', id:'role:x', label:''}, detail_route='role:x', "
        "chapter=NONE, phase=NONE, focalizer=NONE, reason='item', "
        "context_hash='deadbeef'",
        {"sid": sid})
    with pytest.raises(StaleContextError):
        store.advance_context(sid, nav(1, "nav-2", "role:b").model_dump())


def test_get_snapshot_falls_back_when_current_id_dangling(store):
    """M-4:current_snapshot_id 悬空时,get_context_snapshot 兜底取最大 revision。"""
    s = store.create_context_session("book-a", "author", "browser-a")
    sid = s["session_id"]
    a1 = store.advance_context(sid, nav(0, "nav-1", "role:a").model_dump())
    store._raw_query(
        "UPDATE type::thing('context_session', $sid) SET "
        "current_snapshot_id='no-such-snapshot'",
        {"sid": sid})
    got = store.get_context_snapshot(sid)
    assert got is not None
    assert got["revision"] == 1
    assert got["context_hash"] == a1["context_hash"]
