"""统一上下文与记忆系统 · Task 12:可选 scribe3-memory Hermes provider 适配层。

覆盖两层:
  1. provider 生命周期(纯 FakeApi,不需真 Hermes/真网络)——
     · prefetch work-scoped(URL 带 work=、块内不串他书);
     · sync_turn 非阻塞(daemon 后台捕获,主调用 <0.05s 立即返回);
     · is_available 靠 SCRIBE3_API_BASE 门控;parse_scribe_session_id 解 work/thread;
     · on_pre_compress/on_session_end 触发 flush;get_tool_schemas 只读白名单。
  2. /memory/* REST(TestClient + 两本书真 store)——
     · prefetch 返回组装好的记忆块文本且 work 隔离;
     · capture-turn 幂等(同 event_id 二次→idempotent);flush 固化线程;
     · 跨 work 声明(book-a 线程 + ?work=book-b)→ 409 context_work_mismatch;
     · provider 关(SCRIBE3_API_BASE 未设)时主路不受影响(REST 独立于 provider)。

测试绝不真调 LLM/Hermes:provider 用 FakeApi;REST 用内存 SurrealDB(conftest store 夹具)。
"""
import importlib.util
import pathlib
import time

import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.ontology import Fact
from scribe3.store import SurrealStore

# --- 以文件路径加载 hyphenated 插件目录里的 provider 模块(Hermes 加载 out-of-tree 插件同理)---
_PLUGIN = (pathlib.Path(__file__).resolve().parents[1]
           / "hermes_plugins" / "scribe3-memory" / "__init__.py")


def _load_plugin():
    spec = importlib.util.spec_from_file_location("scribe3_memory_plugin", _PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pmod = _load_plugin()

WORK_A = "book-a"
WORK_B = "book-b"
SESSION_A = "scribe3|work:book-a|thread:t1"


# ======================================================================
# 1) provider 生命周期 —— FakeApi,不触网
# ======================================================================
class _Req:
    def __init__(self, url, body):
        self.url = url
        self.body = body


class FakeApi:
    """记 last_request.url,返回 work-scoped 假数据(块内绝不含他书 slug)。"""

    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.last_request = None
        self.captured = []
        self.flushed = []

    def prefetch(self, *, work, thread_id, query):
        if self.delay:
            time.sleep(self.delay)
        self.last_request = _Req(
            f"http://fake/memory/prefetch?work={work}&thread_id={thread_id}",
            {"query": query})
        return {"context": f"[work={work}] 记忆块:{query}", "work": work}

    def capture_turn(self, work, thread_id, payload):
        if self.delay:
            time.sleep(self.delay)
        self.last_request = _Req(f"http://fake/memory/capture-turn?work={work}", payload)
        self.captured.append((work, thread_id, payload))
        return {"status": "complete"}

    def flush(self, work, thread_id, *, reason):
        if self.delay:
            time.sleep(self.delay)
        self.last_request = _Req(f"http://fake/memory/flush?work={work}", {"reason": reason})
        self.flushed.append((work, thread_id, reason))
        return {"status": "flushed"}


def _make_provider(api, session=SESSION_A):
    """预接线 provider(注入 FakeApi,绕过真 ScribeMemoryApi 构造)。"""
    p = pmod.Scribe3MemoryProvider()
    p.api = api
    p.session_id = session
    p.work, p.thread_id = pmod.parse_scribe_session_id(session)
    p._sync_thread = None
    return p


@pytest.fixture()
def api():
    return FakeApi()


@pytest.fixture()
def slow_api():
    return FakeApi(delay=0.3)


@pytest.fixture()
def provider(api):
    return _make_provider(api)


def test_provider_prefetch_is_work_scoped(provider, api):
    block = provider.prefetch("伏笔进展", session_id=SESSION_A)
    assert "work=book-a" in api.last_request.url
    assert "book-b" not in block


def test_sync_turn_returns_without_waiting_for_network(slow_api):
    provider = _make_provider(slow_api)
    started = time.perf_counter()
    provider.sync_turn("u", "a", session_id=SESSION_A)
    elapsed = time.perf_counter() - started
    assert elapsed < 0.05, f"sync_turn 阻塞了 {elapsed:.3f}s(应 <0.05s)"
    # 后台线程最终确实捕获(证明不是丢弃而是异步)
    provider._sync_thread.join(timeout=2)
    assert slow_api.captured and slow_api.captured[0][0] == "book-a"


def test_initialize_constructs_work_scoped_api(monkeypatch, api):
    monkeypatch.setenv("SCRIBE3_API_BASE", "http://fake")
    monkeypatch.setattr(pmod, "ScribeMemoryApi", lambda base, **kw: api)
    p = pmod.Scribe3MemoryProvider()
    p.initialize(SESSION_A, hermes_home="/tmp/hermes")
    assert p.api is api
    assert p.work == "book-a" and p.thread_id == "t1"


def test_is_available_gated_by_env(monkeypatch, provider):
    monkeypatch.delenv("SCRIBE3_API_BASE", raising=False)
    assert provider.is_available() is False
    monkeypatch.setenv("SCRIBE3_API_BASE", "http://127.0.0.1:3320")
    assert provider.is_available() is True


def test_parse_scribe_session_id():
    assert pmod.parse_scribe_session_id(SESSION_A) == ("book-a", "t1")
    assert pmod.parse_scribe_session_id(
        "scribe3|work:book-a|thread:ethread:book-a:xy") == ("book-a", "ethread:book-a:xy")
    # 缺省/畸形容错:work 退 main、thread 退 None,不抛
    w, t = pmod.parse_scribe_session_id("garbage")
    assert w == "main" and t is None
    assert pmod.parse_scribe_session_id("") == ("main", None)


def test_flush_hooks_call_api(provider, api):
    provider.on_pre_compress([{"role": "user", "content": "x"}])
    provider.on_session_end([])
    reasons = [r for (_w, _t, r) in api.flushed]
    assert reasons == ["pre_compress", "session_end"]
    assert all(w == "book-a" for (w, _t, _r) in api.flushed)


def test_tool_schemas_are_read_only(provider):
    names = {t["name"] for t in provider.get_tool_schemas()}
    assert names == {"scribe_memory_search", "scribe_memory_trace", "scribe_context_current"}
    # 无任何直写设定/事实工具(Step 4:写入走产品审批,不在 provider 落库)
    assert not any("add" in n or "write" in n or "set" in n for n in names)


# ======================================================================
# 2) /memory/* REST —— TestClient + 两本书真 store(work-scoped 硬红线)
# ======================================================================
@pytest.fixture()
def two_works(store):
    """同一内存 SurrealDB server 上起两本书,注入 app 两个 work 键(复用 conftest store 夹具)。"""
    store_a = SurrealStore(url=store.url, ns="scribe3", db="book_a")
    store_a.apply_schema()
    store_b = SurrealStore(url=store.url, ns="scribe3", db="book_b")
    store_b.apply_schema()
    A.set_store(store_a, WORK_A)
    A.set_store(store_b, WORK_B)
    A.set_complete_fn(lambda *a, **k: "渲染的散文。")
    client = TestClient(A.app)
    try:
        yield client, store_a, store_b
    finally:
        for st in (store_a, store_b):
            try:
                st.close()
            except Exception:
                pass


def _thread_of(store, work):
    return store.get_or_create_editorial_thread(work, "author")["thread_id"]


def test_memory_prefetch_rest_returns_work_scoped_context(two_works):
    client, store_a, _store_b = two_works
    # book-a 独有一条 canonical 命题(讨论模式 facts_at 无条件出 canonical 块)
    store_a.add_fact(Fact(id="fact:zz1", entity_id="char:jia", attribute="身份",
                          value="书甲独有命题ZZTOKEN", valid_from=1))
    tid = _thread_of(store_a, WORK_A)
    r = client.post(f"/memory/prefetch?work={WORK_A}",
                    json={"thread_id": tid, "query": "身份"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["work"] == WORK_A
    assert "ZZTOKEN" in body["context"]


def test_memory_prefetch_does_not_cross_work(two_works):
    client, store_a, store_b = two_works
    store_a.add_fact(Fact(id="fact:zz2", entity_id="char:jia", attribute="身份",
                          value="书甲独有命题CROSSTOKEN", valid_from=1))
    tid_b = _thread_of(store_b, WORK_B)
    r = client.post(f"/memory/prefetch?work={WORK_B}",
                    json={"thread_id": tid_b, "query": "身份"})
    assert r.status_code == 200, r.text
    assert "CROSSTOKEN" not in r.json()["context"]


def test_memory_capture_turn_rest_idempotent(two_works):
    client, store_a, _store_b = two_works
    tid = _thread_of(store_a, WORK_A)
    payload = {"thread_id": tid, "event_id": "prov-evt-1",
               "user": "书甲角色做了一个决定", "assistant": "好的，我记下了"}
    r1 = client.post(f"/memory/capture-turn?work={WORK_A}", json=payload)
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "complete"
    # 同 event_id 二次 → 幂等,不重复落库
    r2 = client.post(f"/memory/capture-turn?work={WORK_A}", json=payload)
    assert r2.status_code == 200, r2.text
    assert r2.json().get("idempotent") is True


def test_memory_flush_rest(two_works):
    client, store_a, _store_b = two_works
    tid = _thread_of(store_a, WORK_A)
    client.post(f"/memory/capture-turn?work={WORK_A}",
                json={"thread_id": tid, "event_id": "prov-evt-2",
                      "user": "确定本章目标是揭开身世", "assistant": "收到"})
    r = client.post(f"/memory/flush?work={WORK_A}",
                    json={"thread_id": tid, "reason": "pre_compress"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "flushed" and body["reason"] == "pre_compress"
    assert "through_turn" in body


@pytest.mark.parametrize("path,extra", [
    ("/memory/prefetch", {"query": "身份"}),
    ("/memory/capture-turn", {"event_id": "x", "user": "越权写入"}),
    ("/memory/flush", {"reason": "session_end"}),
])
def test_memory_rest_cross_work_rejected(two_works, path, extra):
    """book-a 线程 + ?work=book-b 声明 → 409 context_work_mismatch(跨 work 越权)。"""
    client, store_a, _store_b = two_works
    tid_a = _thread_of(store_a, WORK_A)   # ethread:book-a:<uuid>
    r = client.post(f"{path}?work={WORK_B}", json={"thread_id": tid_a, **extra})
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "context_work_mismatch"
