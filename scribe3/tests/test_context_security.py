"""统一上下文与记忆系统 · Task 16-A(安全隔离子集):跨 work 隔离 + 秘密屏蔽 + trace redactor。

硬红线(长篇写作台一库多书 + 限知宪法):
  ① 跨 work 数据泄漏 0——context/thread/memory/trace/run 每个 surface,book-a 建的资源
     用 book-b 声明去读一律被拒(存在但越权→409 context_work_mismatch;不存在→404);
  ② 秘密 value 泄漏 0——focalized envelope 组装绝不含私密真值,被屏蔽源留痕 masked=True;
     ai_run_trace 落库前统一 redactor 抹掉认证头(Authorization/Bearer/api_key)与秘密真值。

隔离底座:per-work db(SurrealStore(db=work));?work= 只是前端【声明】,权威 work 以记录
落库值为准。thread_id 内嵌 work(ethread:<work>:<uuid>),故 thread surface 越权可判 409;
context_session/memory_trace 记录带 work 字段;run 隔离靠库 + Hermes session_key,跨 work→404。

memory surface 现无 /memory/* REST(Task 12 才建),此处在 store 层验隔离(检索恒过滤 work)。

测试绝不真调 LLM/Hermes:只用 store 直写 + 内存 SurrealDB(conftest store 夹具同一 server 起多 db)。
"""
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import scribe3.app as A
from scribe3.context_assembler import ContextAssembler
from scribe3.context_models import ContextFocus, ContextSnapshot
from scribe3.memory_retrieval import MemoryRetriever
from scribe3.ontology import Entity, Fact, KnowledgeEdge
from scribe3.store import SurrealStore

WORK_A = "book-a"
WORK_B = "book-b"


class _Resp:
    """store 层探针的响应垫片(memory surface 无 REST,用 status_code 表达隔离结果)。"""

    def __init__(self, status_code: int):
        self.status_code = status_code


@pytest.fixture()
def two_works(store):
    """同一内存 SurrealDB server 上起两本书(book-a / book-b 各一 db),注入 app 两个 work 键。

    复用 conftest `store` 夹具已起的 server(store.url),避免再起子进程。两 store 各是独立 db
    (真 per-work 隔离);把它们注入 A._stores 后,HTTP 请求按 ?work= 命中对应库。"""
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


def _request_surface(client, store_a, store_b, surface):
    """在 book-a 建资源,再用 book-b 声明去读 → 返回响应(带 .status_code)。

    each surface 用其代表端点:context=会话读、thread=线程消息、trace=记忆溯源、
    run=Hermes run 审计;memory 无 REST → store 层检索探针(book-b 检索不到 book-a 记忆)。"""
    if surface == "context":
        sid = store_a.create_context_session(WORK_A, "author", "dev")["session_id"]
        return client.get(f"/context/sessions/{sid}?work={WORK_B}")
    if surface == "thread":
        tid = store_a.get_or_create_editorial_thread(WORK_A, "author")["thread_id"]
        store_a.add_chat_message(1, "draft", "user", "甲书密谈", thread_id=tid)
        return client.get(f"/chat/threads/{tid}/messages?work={WORK_B}")
    if surface == "trace":
        store_a.save_memory_trace({
            "trace_id": "tr-xwork", "work": WORK_A,
            "thread_id": f"ethread:{WORK_A}:1", "context_session_id": "sess-xwork",
            "snapshot_revision": 2, "query": "身份",
            "selected": [], "rejected": [],
        })
        return client.get(f"/context/sessions/sess-xwork/trace/2?work={WORK_B}")
    if surface == "run":
        store_a.upsert_ai_run_trace("run-xwork", status="created",
                                    input_text="整理甲书设定")
        return client.get(f"/ai/runs/run-xwork/trace?work={WORK_B}")
    if surface == "memory":
        # 无 /memory/* REST(Task 12):store 层验隔离——book-a 的记忆,book-b 检索不到。
        store_a.add_memory_item(WORK_A, "episodic", "甲书专属的隐秘往事",
                                source_type="turn", source_id="mem-xwork-1")
        cands = MemoryRetriever(store_b).retrieve(WORK_B, {}, "隐秘往事", 24)
        leaked = any("甲书专属的隐秘往事" in (getattr(c, "text", "") or "") for c in cands)
        return _Resp(200 if leaked else 404)
    raise AssertionError(f"未知 surface: {surface}")


# ---------------------------------------------------------------------------
# Step 1(TDD):每个 surface 跨 work 被拒 + focalized envelope 秘密 value 零泄漏
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("surface", ["context", "thread", "memory", "trace", "run"])
def test_every_surface_rejects_cross_work(two_works, surface):
    """跨 work 硬红线:每个 surface 用他书声明读本书资源都被拒。

    计划 Task 16 ① 协调:期望放宽为 {403,404,409}——存在但越权→409 context_work_mismatch
    (thread 落库 work 内嵌 id,可判越权);不存在/跨 db 不可达→404(per-work db 天然隔离)。
    绝不放水:任意 <400 视为泄漏。"""
    client, store_a, store_b = two_works
    resp = _request_surface(client, store_a, store_b, surface)
    assert resp.status_code in {403, 404, 409}, \
        f"surface={surface} 跨 work 未被拒绝(status={resp.status_code})"


def _focalized_snapshot(store):
    """限知焦点者快照:焦点者七王子【知道】自己的秘密真名(fact 落在其知识帧内)。"""
    store.add_entity(Entity("role:qi", "character", "七王子"))
    store.add_fact(Fact("fact:realname", "role:qi", "真名", "王子真名",
                        valid_from=1, secret=True))
    store.add_knowledge(KnowledgeEdge("role:qi", "fact:realname", since_chapter=1))
    return ContextSnapshot(
        session_id="s-foc", work="book-a", revision=1, thread_id="ethread:book-a:1",
        entry="chapter", directory_path=("chapter:2",),
        focus=ContextFocus(type="character", id="role:qi", label="七王子"),
        detail_route="chapter:2", chapter=2, phase="draft",
        focalizer="role:qi", previous_revision=0, navigation_id="nav-foc",
        captured_at=datetime.now(timezone.utc), context_hash="",
    ).with_hash()


def test_focalized_context_never_contains_secret_value(store):
    """限知红线(宪法级):focalized envelope 组装绝不含秘密真值,被屏蔽源留痕 masked=True。

    验证 assembler C1 屏蔽在 focalized 路径真实生效(不新造,验既有 _canonical_from_store)。"""
    snapshot = _focalized_snapshot(store)
    envelope = ContextAssembler(store).assemble(snapshot, "他知道什么", "discussion")
    assert "王子真名" not in envelope.model_dump_json()
    assert any(source.masked for block in envelope.blocks for source in block.sources)


# ---------------------------------------------------------------------------
# Step 2:统一 work 绑定校验——记录落库 work ≠ 请求 ?work= → 409 context_work_mismatch
# 用「同一 store 注入两个 work 键」逼出「记录存在但越权」的 409(区别于跨 db 的 404)。
# ---------------------------------------------------------------------------

def _dual_key_client(store):
    """把同一 store 同时注入 book-a / book-b:记录物理可达,但 work 字段权威判越权→409。"""
    A.set_store(store, WORK_A)
    A.set_store(store, WORK_B)
    A.set_complete_fn(lambda *a, **k: "x")
    return TestClient(A.app)


def test_context_session_declared_wrong_work_returns_409(store):
    client = _dual_key_client(store)
    sid = store.create_context_session(WORK_A, "author", "dev")["session_id"]
    r = client.get(f"/context/sessions/{sid}?work={WORK_B}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "context_work_mismatch"


def test_thread_messages_declared_wrong_work_returns_409(store):
    client = _dual_key_client(store)
    tid = store.get_or_create_editorial_thread(WORK_A, "author")["thread_id"]
    r = client.get(f"/chat/threads/{tid}/messages?work={WORK_B}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "context_work_mismatch"


def test_thread_fork_declared_wrong_work_returns_409(store):
    client = _dual_key_client(store)
    tid = store.get_or_create_editorial_thread(WORK_A, "author")["thread_id"]
    r = client.post(f"/chat/threads/{tid}/fork?work={WORK_B}", json={"title": "越权支线"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "context_work_mismatch"


def test_memory_trace_declared_wrong_work_returns_409(store):
    client = _dual_key_client(store)
    store.save_memory_trace({
        "trace_id": "tr-mismatch", "work": WORK_A,
        "thread_id": f"ethread:{WORK_A}:1", "context_session_id": "sess-mm",
        "snapshot_revision": 1, "query": "身份", "selected": [], "rejected": [],
    })
    r = client.get(f"/context/sessions/sess-mm/trace/1?work={WORK_B}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "context_work_mismatch"


def test_thread_missing_parent_still_404_not_409(store):
    """非 ethread 命名/不存在 → 无法判 work → 不误判 409,仍走 404(not-found 语义)。"""
    client = _dual_key_client(store)
    r = client.post(f"/chat/threads/thread:legacy/fork?work={WORK_A}", json={})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Step 2:ai_run_trace 落库前统一 redactor——认证头 + 秘密真值绝不入库(at-rest 不变量)
# ---------------------------------------------------------------------------

def test_run_trace_redactor_strips_auth_headers_and_secret_values(store):
    """tool_outputs/raw_events 里的 Authorization/Bearer/api_key 与秘密事实真值,
    落库前被 redactor 抹掉;直查 DB 行断言明文不入库,只留屏蔽占位。"""
    store.add_entity(Entity("role:qi", "character", "七王子"))
    store.add_fact(Fact("fact:realname", "role:qi", "真名", "王子真名",
                        valid_from=1, secret=True))
    store.upsert_ai_run_trace(
        "run-red", status="streaming",
        tool_outputs=[{
            "call_id": "c1", "tool": "http_get",
            "output": "Authorization: Bearer sk-" + "supersecrettoken12345 泄漏真名=王子真名",
            "headers": {"Authorization": "Bearer sk-" + "abc123def456ghi"},
        }],
        raw_events=[{"api_key": "sk-" + "topsecretkey99999", "note": "王子真名 混进原始事件"}],
    )
    row = store.get_ai_run_trace("run-red")
    blob = json.dumps(row, ensure_ascii=False)
    # 认证头/令牌明文一律不入库
    assert ("sk-" + "supersecrettoken12345") not in blob
    assert ("sk-" + "abc123def456ghi") not in blob
    assert ("sk-" + "topsecretkey99999") not in blob
    assert "Bearer sk-" not in blob
    # 秘密事实真值不入库
    assert "王子真名" not in blob
    # 屏蔽留痕(可审计"这里曾有认证头/秘密")
    assert "已屏蔽·认证" in blob
    assert "秘密事实已屏蔽" in blob


def test_run_trace_redactor_masks_string_embedded_bearer_basic_proxy(store):
    """C-1:字符串内嵌认证头(Bearer sk-ant 带连字符 / Basic base64 / Proxy-Authorization)
    落库无明文——旧正则顺序缺陷会把方案词吃掉致真凭据留明文,此处实测 at-rest 无明文。"""
    store.upsert_ai_run_trace(
        "run-c1", status="failed",
        tool_outputs=[
            {"call_id": "c1", "output": "curl 回显 Authorization: Bearer sk-" + "ant-api03-LIVEKEYabcdef123 done"},
            {"call_id": "c2", "output": "HTTP 头 Authorization: Basic " + "dXNlcjpwYXNzd29yZA== end"},
            {"call_id": "c3", "output": "上游 Proxy-Authorization: Bearer " + "proxyTok987zzz reject"},
        ],
        raw_events=[{"note": "裸令牌 Bearer sk-" + "ant-api03-BARETOKEN9988 也要抹"}],
    )
    blob = json.dumps(store.get_ai_run_trace("run-c1"), ensure_ascii=False)
    for leak in ("sk-" + "ant-api03-LIVEKEYabcdef123", "dXNlcjpwYXNzd29yZA==",
                 "proxyTok987zzz", "sk-" + "ant-api03-BARETOKEN9988"):
        assert leak not in blob, f"认证凭据明文入库: {leak}"
    assert "Bearer sk-" not in blob and ("Basic " + "dXNlcjp") not in blob
    assert "已屏蔽·认证" in blob


def test_run_trace_redactor_masks_error_field(store):
    """C-2:error 字段直取上游 HTTP 文本(常回显认证头),必须纳入 redactor。"""
    store.upsert_ai_run_trace(
        "run-c2", status="approval_failed",
        error="Hermes approval failed: 401 {\"detail\":\"bad Authorization: Bearer sk-" + "ant-api03-ERRLEAK7777\"}")
    blob = json.dumps(store.get_ai_run_trace("run-c2"), ensure_ascii=False)
    assert ("sk-" + "ant-api03-ERRLEAK7777") not in blob
    assert "Bearer sk-" not in blob
    assert "已屏蔽·认证" in blob


def test_run_trace_redactor_masks_single_char_secret_in_bounded_context(store):
    """I-1:单字秘密真名("禹")在名讳上下文里屏蔽(而非全文裸替换,防误伤正文同字用法)。"""
    store.add_entity(Entity("role:emperor", "character", "无名帝"))
    store.add_fact(Fact("fact:truename", "role:emperor", "真名", "禹",
                        valid_from=1, secret=True))
    store.upsert_ai_run_trace(
        "run-i1", status="streaming",
        tool_outputs=[
            {"call_id": "n1", "output": "经查其真名就是禹,乃上古之名。"},   # 名讳上下文 → 抹
            {"call_id": "n2", "output": "大禹治水泽被后世,与本案无关。"},   # 普通正文同字 → 不抹
        ])
    row = store.get_ai_run_trace("run-i1")
    o1 = row["tool_outputs"][0]["output"]
    o2 = row["tool_outputs"][1]["output"]
    assert "禹" not in o1, "名讳上下文里的单字秘密真值必须屏蔽"
    assert "秘密事实已屏蔽" in o1
    assert "大禹治水" in o2, "普通正文同字不得被裸替换(有界屏蔽的取舍)"


def test_run_trace_redactor_masks_cookie_string(store):
    """I-2:字符串内嵌 Cookie: <值> 抹到行尾(此前只 dict 键命中,字符串形式漏)。"""
    store.upsert_ai_run_trace(
        "run-i2", status="streaming",
        tool_outputs=[{"call_id": "k1",
                       "output": "响应头 Cookie: session=abc123secretvalue; theme=dark"}])
    blob = json.dumps(store.get_ai_run_trace("run-i2"), ensure_ascii=False)
    assert "abc123secretvalue" not in blob
    assert "已屏蔽·认证" in blob


# ---------------------------------------------------------------------------
# 安全指标:cross_work_rejections 计数(供 Task 16-B 的 runtime-status 消费)
# ---------------------------------------------------------------------------

def test_cross_work_rejections_metric_increments(store):
    client = _dual_key_client(store)
    sid = store.create_context_session(WORK_A, "author", "dev")["session_id"]
    before = A.get_security_metrics()["cross_work_rejections"]
    r = client.get(f"/context/sessions/{sid}?work={WORK_B}")
    assert r.status_code == 409
    after = A.get_security_metrics()["cross_work_rejections"]
    assert after == before + 1


def test_memory_surface_isolated_at_store_layer(store):
    """memory surface(无 REST,Task 12 才建):检索恒过滤 work——book-b 检索不到 book-a 记忆。"""
    store_a = SurrealStore(url=store.url, ns="scribe3", db="mem_a")
    store_a.apply_schema()
    store_b = SurrealStore(url=store.url, ns="scribe3", db="mem_b")
    store_b.apply_schema()
    try:
        store_a.add_memory_item(WORK_A, "episodic", "甲书专属的隐秘往事",
                                source_type="turn", source_id="mem-iso-1")
        cands = MemoryRetriever(store_b).retrieve(WORK_B, {}, "隐秘往事", 24)
        assert all("甲书专属的隐秘往事" not in (getattr(c, "text", "") or "")
                   for c in cands), "跨 work 记忆检索不得返回他书内容"
    finally:
        store_a.close()
        store_b.close()
