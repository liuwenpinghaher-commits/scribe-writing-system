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
