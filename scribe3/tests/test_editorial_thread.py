"""统一上下文与记忆系统 · Task 6:主编历史 = 一 work 一连续线程 + 每轮焦点标签。

契约:
- get_or_create_editorial_thread(work, actor):幂等取/建本 work 的活跃主编线程;
- add_chat_message(..., thread_id=, context_revision=, focus=, ...):线程稳定,焦点只做每轮标签;
- list_thread_messages(thread_id):按线程拉全部消息(ts 升序);
- 隔离:别的 work 的 store 读不到本 work 的 thread(per-work db);
- backfill_thread_ids():存量无 thread_id 的旧消息全部归入默认线程,幂等,不增不减总数;
- fork:parent_thread_id 建新线程(显式分支)。
"""
import os
import shutil
import socket
import subprocess
import time

import pytest

from scribe3.store import SurrealStore

SURREAL_BIN = (os.environ.get("SURREAL_BIN") or shutil.which("surreal")
               or os.path.expanduser("~/.surrealdb/surreal"))


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture()
def surreal_server():
    """起一个临时内存 SurrealDB server,供同 url 下多 db(多 work)共用。"""
    port = _free_port()
    clean_env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
                 "HOME": os.path.expanduser("~"), "PWD": "/tmp"}
    proc = subprocess.Popen(
        [SURREAL_BIN, "start", "--no-banner", "--bind", f"127.0.0.1:{port}",
         "--user", "root", "--pass", "root", "memory"],
        cwd="/tmp", env=clean_env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        if proc.poll() is not None:
            raise RuntimeError(f"surreal 子进程启动失败,退出码 {proc.returncode}")
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.2)
    url = f"ws://127.0.0.1:{port}/rpc"
    stores: list[SurrealStore] = []

    def make(db: str) -> SurrealStore:
        st = SurrealStore(url=url, ns="scribe3", db=db)
        st.apply_schema()
        stores.append(st)
        return st

    try:
        yield make
    finally:
        for st in stores:
            try:
                st.close()
            except Exception:
                pass
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture()
def store_a(surreal_server):
    return surreal_server("book-a")


@pytest.fixture()
def store_b(surreal_server):
    return surreal_server("book-b")


def test_get_or_create_editorial_thread_is_idempotent(store):
    a = store.get_or_create_editorial_thread(store.db_name, "author")
    b = store.get_or_create_editorial_thread(store.db_name, "author")
    assert a["thread_id"] and a["thread_id"] == b["thread_id"], "一 work 一线程:重复取应同 id"
    assert a["work"] == store.db_name
    assert a["status"] == "active"


def test_update_thread_response_id_is_idempotent_and_safe(store):
    """Task 11:一轮 Responses 完成后回写续接锚(previous_response_id/conversation)。

    幂等 + fail-soft 契约(掉链是常态,回写不得误伤):
    - 空 response_id 不覆盖已有锚(不擦成 NONE);缺省 conversation_id 不动;线程不存在 no-op 不抛。
    """
    tid = store.get_or_create_editorial_thread(store.db_name, "author")["thread_id"]
    # 初始锚为空(建线程时 previous_response_id=NONE)
    assert not store._get_editorial_thread(tid).get("previous_response_id")

    store.update_thread_response_id(tid, "resp-1")
    assert store._get_editorial_thread(tid)["previous_response_id"] == "resp-1"

    # 空 response_id(None / "")都不覆盖已有锚
    store.update_thread_response_id(tid, None)
    store.update_thread_response_id(tid, "")
    assert store._get_editorial_thread(tid)["previous_response_id"] == "resp-1"

    # 缺省 conversation_id 不动(仍为空)
    assert not store._get_editorial_thread(tid).get("hermes_conversation_id")

    # 带 conversation_id 才写(与 response id 同轮更新)
    store.update_thread_response_id(tid, "resp-2", conversation_id="conv-9")
    row = store._get_editorial_thread(tid)
    assert row["previous_response_id"] == "resp-2"
    assert row["hermes_conversation_id"] == "conv-9"

    # 线程不存在 → UPDATE 空操作,不抛(调用方 fail-soft)
    store.update_thread_response_id("ethread:test:nonexistent", "resp-x")


def test_editorial_thread_is_stable_across_focus(store):
    """焦点切换(role→promise)只改每轮的 focus 标签,线程不变、消息累积。"""
    thread = store.get_or_create_editorial_thread(store.db_name, "author")
    store.add_chat_message(3, "draft", "user", "甲", thread_id=thread["thread_id"],
                           context_revision=1, focus={"id": "role:a"})
    store.add_chat_message(3, "draft", "user", "乙", thread_id=thread["thread_id"],
                           context_revision=2, focus={"id": "promise:b"})
    msgs = store.list_thread_messages(thread["thread_id"])
    assert len(msgs) == 2
    assert [m["text"] for m in msgs] == ["甲", "乙"]
    assert msgs[0]["focus"]["id"] == "role:a"
    assert msgs[1]["focus"]["id"] == "promise:b"
    assert msgs[1]["context_revision"] == 2


def test_add_chat_message_is_backward_compatible(store):
    """扩展签名全默认 None:旧调用方一字不改仍能落库(向后兼容铁律)。"""
    store.add_chat_message(1, "draft", "user", "旧式调用")
    msgs = store.list_chat_messages(chapter=1)
    assert msgs[0]["text"] == "旧式调用"
    assert msgs[0].get("thread_id") in (None, "")


def test_thread_cannot_be_read_from_another_work(store_a, store_b):
    """work 隔离:book-a 建的线程,book-b 的 store 读不到任何消息(per-work db)。"""
    thread = store_a.get_or_create_editorial_thread("book-a", "author")
    store_a.add_chat_message(1, "draft", "user", "甲书的话", thread_id=thread["thread_id"])
    assert store_b.list_thread_messages(thread["thread_id"]) == []
    assert len(store_a.list_thread_messages(thread["thread_id"])) == 1


def test_backfill_assigns_default_thread_to_legacy_messages(store):
    """升级后旧对话不得从 UI 消失:无 thread_id 的存量消息归入默认线程。"""
    store.add_chat_message(1, "draft", "user", "旧消息")
    store.backfill_thread_ids()
    tid = store.get_or_create_editorial_thread(store.db_name, "author")["thread_id"]
    msgs = store.list_thread_messages(tid)
    assert any(m["text"] == "旧消息" for m in msgs), "升级后旧对话不得从 UI 消失"


def test_backfill_is_idempotent_and_preserves_total(store):
    """幂等 + 守恒:再跑不改变任何消息,回填前后 chat_message 总数相等。"""
    store.add_chat_message(1, "draft", "user", "m1")
    store.add_chat_message(2, "draft", "assistant", "m2")
    before = len(store.list_chat_messages())
    store.backfill_thread_ids()
    tid = store.get_or_create_editorial_thread(store.db_name, "author")["thread_id"]
    once = len(store.list_thread_messages(tid))
    store.backfill_thread_ids()   # 再跑
    twice = len(store.list_thread_messages(tid))
    assert once == twice == before, "回填幂等,总数守恒"
    assert len(store.list_chat_messages()) == before


def test_fork_creates_child_thread(store):
    """显式分支:fork 写 parent_thread_id 建新线程(新 id,活跃)。"""
    parent = store.get_or_create_editorial_thread(store.db_name, "author")
    child = store.fork_editorial_thread(parent["thread_id"], title="支线讨论")
    assert child["thread_id"] != parent["thread_id"]
    assert child["parent_thread_id"] == parent["thread_id"]
    assert child["title"] == "支线讨论"
    assert child["status"] == "active"


def test_list_editorial_threads_returns_work_threads(store):
    """列本 work 全部线程(含分支)。"""
    parent = store.get_or_create_editorial_thread(store.db_name, "author")
    store.fork_editorial_thread(parent["thread_id"])
    threads = store.list_editorial_threads(store.db_name)
    ids = {t["thread_id"] for t in threads}
    assert parent["thread_id"] in ids
    assert len(threads) >= 2


# ---- /chat/threads 端点族(app.py)----

def test_chat_threads_endpoint_lists_and_bootstraps_default(store):
    """GET /chat/threads:首次访问即建默认线程并返回。"""
    from .test_app import _client
    r = _client(store).get("/chat/threads")
    assert r.status_code == 200
    threads = r.json()["threads"]
    assert len(threads) == 1
    assert threads[0]["status"] == "active" and threads[0]["thread_id"]


def test_chat_thread_messages_endpoint(store):
    """GET /chat/threads/{id}/messages:按线程拉消息。"""
    from .test_app import _client
    c = _client(store)
    tid = c.get("/chat/threads").json()["threads"][0]["thread_id"]
    store.add_chat_message(1, "draft", "user", "端点消息", thread_id=tid,
                           context_revision=3, focus={"id": "role:x"})
    data = c.get(f"/chat/threads/{tid}/messages").json()
    assert [m["text"] for m in data] == ["端点消息"]
    assert data[0]["context_revision"] == 3
    assert data[0]["focus"]["id"] == "role:x"


def test_fork_thread_endpoint(store):
    """POST /chat/threads/{id}/fork:显式分支建子线程。"""
    from .test_app import _client
    c = _client(store)
    parent = c.get("/chat/threads").json()["threads"][0]["thread_id"]
    r = c.post(f"/chat/threads/{parent}/fork", json={"title": "支线"})
    assert r.status_code == 200
    child = r.json()
    assert child["parent_thread_id"] == parent and child["title"] == "支线"


def test_fork_missing_parent_returns_404(store):
    from .test_app import _client
    r = _client(store).post("/chat/threads/ethread:nope/fork", json={})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "thread_not_found"


# ---- P0a 多会话:显式新建 / 改名归档 / fork 继承 summary(store 层)----

def test_create_editorial_thread_explicit(store):
    """显式新建:不复用 active 线程,每次新建一条;默认标题「新会话」。"""
    w = store.db_name
    t1 = store.get_or_create_editorial_thread(w, "author")
    t2 = store.create_editorial_thread(w, "author")
    t3 = store.create_editorial_thread(w, "author", title="门派设定讨论")
    assert t2["thread_id"] != t1["thread_id"] and t3["thread_id"] != t2["thread_id"]
    assert t2["title"] == "新会话" and t3["title"] == "门派设定讨论"
    assert t2["status"] == "active"


def test_update_editorial_thread_meta_rename_archive(store):
    t = store.create_editorial_thread(store.db_name, "author")
    store.update_editorial_thread_meta(t["thread_id"], title="改个名")
    assert store._get_editorial_thread(t["thread_id"])["title"] == "改个名"
    store.update_editorial_thread_meta(t["thread_id"], status="archived")
    row = store._get_editorial_thread(t["thread_id"])
    assert row["status"] == "archived" and row["title"] == "改个名"   # 只改传入字段


def test_fork_inherits_parent_summary(store):
    """P0a(spec 审核修正#4):fork 继承父 summary,分支不失忆。"""
    parent = store.get_or_create_editorial_thread(store.db_name, "author")
    store._execute_write(
        "UPDATE editorial_thread SET summary=$s WHERE thread_id=$tid RETURN NONE",
        {"s": "早期讨论:主角设定为风水师。", "tid": parent["thread_id"]})
    child = store.fork_editorial_thread(parent["thread_id"], title="支线")
    assert child["summary"] == "早期讨论:主角设定为风水师。"


# ---- P0a 多会话:POST /chat/threads(新建)+ PATCH /chat/threads/{id}(改名/归档)----

def test_post_chat_threads_creates_new(store):
    from .test_app import _client
    c = _client(store)
    r = c.post("/chat/threads", json={"title": "新支线"})
    assert r.status_code == 200
    row = r.json()
    assert row["title"] == "新支线" and row["status"] == "active"
    r2 = c.post("/chat/threads", json={})
    assert r2.status_code == 200
    assert r2.json()["thread_id"] != row["thread_id"]   # 每次都新建
    assert r2.json()["title"] == "新会话"


def test_patch_chat_thread_rename_archive_and_guards(store):
    from .test_app import _client
    c = _client(store)
    tid = c.post("/chat/threads", json={}).json()["thread_id"]
    assert c.patch(f"/chat/threads/{tid}", json={"title": "改名"}).status_code == 200
    r = c.patch(f"/chat/threads/{tid}", json={"status": "archived"})
    assert r.status_code == 200 and r.json()["status"] == "archived"
    assert r.json()["title"] == "改名"
    # 非法 status → 422
    assert c.patch(f"/chat/threads/{tid}", json={"status": "deleted"}).status_code == 422
    # 不存在 → 404
    assert c.patch("/chat/threads/ethread:main:nope", json={"title": "x"}).status_code == 404
    # 跨 work → 409(_assert_work_binding 既有语义)
    assert c.patch(f"/chat/threads/{tid}", params={"work": "other"},
                   json={"title": "x"}).status_code == 409


# ---- P0a:首条消息自动命名 ----

def test_autotitle_on_first_user_message(store):
    t = store.create_editorial_thread(store.db_name, "author")            # title=新会话
    store.maybe_autotitle_thread(t["thread_id"], "帮我把门派体系理一遍,从青叶门开始梳理脉络")
    assert store._get_editorial_thread(t["thread_id"])["title"] == \
        "帮我把门派体系理一遍,从青叶门开始梳理脉络"[:24]
    # 已非默认标题 → 不再改(幂等)
    store.maybe_autotitle_thread(t["thread_id"], "第二句话")
    assert store._get_editorial_thread(t["thread_id"])["title"] != "第二句话"


def test_autotitle_via_chat_stream_endpoint(store, monkeypatch):
    """端点整合:新会话发首条消息 → 线程标题自动变成消息前 24 字。"""
    from .test_app import _client
    c = _client(store)
    monkeypatch.setattr("scribe3.llm.hermes_complete_stream",
                        lambda msg, system=None, **_kw: iter(["回"]))
    tid = c.post("/chat/threads", json={}).json()["thread_id"]            # title=新会话
    r = c.get("/chat/stream", params={"msg": "给主角起个带金属感的名字", "work": "main",
                                      "thread": tid})
    assert r.status_code == 200
    b"".join(r.iter_bytes())
    assert store._get_editorial_thread(tid)["title"] == "给主角起个带金属感的名字"


# ---- P0b:分页 / 增量摘要 / 注入 L2 / 导出 / maintenance ----

def test_list_thread_messages_before_ts_pagination(store):
    tid = store.get_or_create_editorial_thread(store.db_name, "author")["thread_id"]
    for i in range(5):
        store.add_chat_message(1, "discuss", "user", f"m{i}", thread_id=tid)
    recent = store.list_thread_messages(tid, limit=2)
    assert [m["text"] for m in recent] == ["m3", "m4"]
    earlier = store.list_thread_messages(tid, limit=2, before_ts=recent[0]["ts"])
    assert [m["text"] for m in earlier] == ["m1", "m2"]
    earliest = store.list_thread_messages(tid, limit=10, before_ts=earlier[0]["ts"])
    assert [m["text"] for m in earliest] == ["m0"]


def test_set_thread_summary_and_error_roundtrip(store):
    tid = store.create_editorial_thread(store.db_name, "author")["thread_id"]
    store.set_thread_summary(tid, "早期要点", "2026-07-16T00:00:00Z")
    row = store._get_editorial_thread(tid)
    assert row["summary"] == "早期要点" and row["summarized_upto_ts"] == "2026-07-16T00:00:00Z"
    assert not row.get("summary_error")
    store.set_thread_summary_error(tid, "LLM 超时")
    row = store._get_editorial_thread(tid)
    assert row["summary_error"] == "LLM 超时" and row["summary"] == "早期要点"   # 旧摘要保留
    store.set_thread_summary(tid, "新要点", "2026-07-16T01:00:00Z")
    assert not store._get_editorial_thread(tid).get("summary_error")   # 成功即清红字


def test_maybe_summarize_thread_and_history_injection(store, monkeypatch):
    """增量摘要:阈值触发→summary 落库+游标推进;二次调用 skipped;
    _thread_history_for_prompt 把 summary 作首条记忆块注入(L2)。"""
    import scribe3.app as A
    A.set_store(store)
    tid = store.get_or_create_editorial_thread("main", "author")["thread_id"]
    for i in range(4):
        store.add_chat_message(1, "discuss", "user" if i % 2 == 0 else "assistant",
                               f"讨论内容{i}", thread_id=tid)
    monkeypatch.setattr(A, "_complete_fn", lambda p: "压缩摘要:主角定为风水师;伏笔待收。")
    r = A._maybe_summarize_thread("main", tid, threshold=3)
    assert r["status"] == "summarized" and r["new_count"] == 4
    row = store._get_editorial_thread(tid)
    assert "风水师" in row["summary"] and row["summarized_upto_ts"]
    # 幂等:游标之后无新消息 → skipped
    assert A._maybe_summarize_thread("main", tid, threshold=3)["status"] == "skipped"
    # L2 注入:history 首条=摘要块
    hist = A._thread_history_for_prompt(store, tid)
    assert hist and "早期摘要" in hist[0]["content"] and "风水师" in hist[0]["content"]
    # 失败路径:error 落 summary_error,旧摘要保留
    def boom(p):
        raise RuntimeError("网关超时")
    monkeypatch.setattr(A, "_complete_fn", boom)
    store.add_chat_message(1, "discuss", "user", "又来了几条", thread_id=tid)
    store.add_chat_message(1, "discuss", "assistant", "回复", thread_id=tid)
    store.add_chat_message(1, "discuss", "user", "再来", thread_id=tid)
    r2 = A._maybe_summarize_thread("main", tid, threshold=3)
    assert r2["status"] == "error"
    row2 = store._get_editorial_thread(tid)
    assert "网关超时" in (row2.get("summary_error") or "") and "风水师" in row2["summary"]


def test_thread_export_md_jsonl_and_guards(store):
    from .test_app import _client
    import json as _j
    c = _client(store)
    tid = c.post("/chat/threads", json={"title": "导出测试"}).json()["thread_id"]
    store.add_chat_message(1, "discuss", "user", "问一句", thread_id=tid)
    store.add_chat_message(1, "discuss", "assistant", "答一句", thread_id=tid)
    md = c.get(f"/chat/threads/{tid}/export?format=md")
    assert md.status_code == 200 and "问一句" in md.text and "答一句" in md.text
    assert "attachment" in md.headers.get("content-disposition", "")
    jl = c.get(f"/chat/threads/{tid}/export?format=jsonl")
    rows = [_j.loads(x) for x in jl.text.splitlines() if x.strip()]
    assert [r["role"] for r in rows] == ["user", "assistant"]
    assert set(rows[0].keys()) == {"role", "text", "ts"}   # 泄密面最小:无工具输出
    assert c.get(f"/chat/threads/{tid}/export?format=pdf").status_code == 422
    assert c.get("/chat/threads/ethread:main:nope/export").status_code == 404


def test_maintenance_summarize_threads_endpoint(store, monkeypatch):
    from .test_app import _client
    import scribe3.app as A
    c = _client(store)
    tid = store.get_or_create_editorial_thread("main", "author")["thread_id"]
    for i in range(3):
        store.add_chat_message(1, "discuss", "user", f"x{i}", thread_id=tid)
    monkeypatch.setattr(A, "_complete_fn", lambda p: "兜底摘要")
    r = c.post("/maintenance/summarize-threads?threshold=2")
    assert r.status_code == 200
    d = r.json()
    assert d["summarized"] >= 1 and d["errors"] == {}


# ---- P2:每日摘报 ----

def test_daily_digest_writes_row_and_inbox_shows_it(store):
    from .test_app import _client
    c = _client(store)
    r = c.post("/maintenance/daily-digest")
    assert r.status_code == 200
    d = r.json()
    assert "字数" in d["body"] and "等你决策" in d["body"] and "伏笔" in d["body"]
    row = store.latest_chief_digest()
    assert row and row["day"] == d["day"] and row["body"] == d["body"]
    # 重跑覆盖(一天一行)
    c.post("/maintenance/daily-digest")
    assert store.latest_chief_digest()["day"] == d["day"]
    # 收件箱消费
    inbox = c.get("/inbox").json()
    dg = [it for it in inbox["items"] if it["kind"] == "daily_digest"]
    assert dg and d["day"] in dg[0]["message"]


def test_daily_digest_partial_source_failure_is_loud(store, monkeypatch):
    """零降级:某源失败 → error 字段如实带出(收件箱红字),不产假完整摘报。"""
    from .test_app import _client
    monkeypatch.setattr(store, "progress",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("progress 表崩")))
    r = _client(store).post("/maintenance/daily-digest")
    assert r.status_code == 200
    d = r.json()
    assert d["error"] and "progress" in d["error"]
    assert "等你决策" in d["body"]   # 其余源仍产出
