"""U-005:主编【讨论 / agentic】对话留痕补齐 + 防复发门禁。

真机实证(2026-07-15):三条 SSE 对话路径此前只有 POST /chat/write(动稿)留痕;
chat_stream(速答讨论)/ chat_agentic_stream(agentic 联查/审批)从不落库——《印迹》
批准写入 15 世界规则 + 6 势力的整场讨论凭空消失。本文件:
  ① _ChatTurnLog 单元行为(user 开流前落 / assistant 流尽落 / 流断落部分 / 全空不落);
  ② 两条 SSE 端点经真实路由落库(红→绿:修前 0 条,修后 user+assistant);
  ③ 门禁——枚举所有 /chat SSE 端点,每个要么留痕要么显式豁免(防"每新开一条路就漏")。

只用 conftest 临时 SurrealDB,绝不碰生产库 ~/.scribe2-surreal/data.db。
"""
import inspect
import json

import pytest
from fastapi.testclient import TestClient

from scribe3 import app as A


# store fixture 用 conftest 的(已 apply_schema;端点会读 intent/editorial_thread 等多表)


@pytest.fixture
def client(store):
    A.set_store(store)   # work=main 注入活 store(否则命中别的测试遗留死连接)
    return TestClient(A.app)


def _thread_id(store):
    return store.get_or_create_editorial_thread("main", "author")["thread_id"]


# ============================================================
# ① _ChatTurnLog 单元行为
# ============================================================

def test_chatturnlog_persists_user_and_assistant_paired(store):
    tid = _thread_id(store)
    with A._ChatTurnLog(store, user_text="秘会跟天龙座什么关系?", chapter=3,
                        stage="discuss", thread_id=tid) as clog:
        clog.feed("秘会")
        clog.feed("表面臣服")
        clog.set_response_id("resp_abc")
    msgs = store.list_thread_messages(tid)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["text"] == "秘会跟天龙座什么关系?"
    assert msgs[1]["text"] == "秘会表面臣服"            # feed 累积拼接
    assert msgs[0]["turn"] == msgs[1]["turn"] != ""     # 同轮配对
    assert msgs[1]["response_id"] == "resp_abc"


def test_chatturnlog_user_persisted_before_stream_even_if_body_never_runs(store):
    """开流前即落 user:哪怕 with 体一个字都没产出(流开头就崩),问话也已在库。"""
    tid = _thread_id(store)
    with pytest.raises(RuntimeError):
        with A._ChatTurnLog(store, user_text="问了但会崩", chapter=1,
                            stage="discuss", thread_id=tid):
            raise RuntimeError("模拟流开头即崩")
    msgs = store.list_thread_messages(tid)
    assert [m["role"] for m in msgs] == ["user"]        # user 在;assistant 因全空未落
    assert msgs[0]["text"] == "问了但会崩"


def test_chatturnlog_persists_partial_assistant_on_midstream_break(store):
    """流中断(已产出部分):assistant 落已累积的部分——有一个字也比凭空消失强。"""
    tid = _thread_id(store)
    with pytest.raises(RuntimeError):
        with A._ChatTurnLog(store, user_text="q", chapter=1,
                            stage="discuss", thread_id=tid) as clog:
            clog.feed("已经说了一半")
            raise RuntimeError("模拟流中途断")
    msgs = store.list_thread_messages(tid)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["text"] == "已经说了一半"


def test_chatturnlog_skips_empty_assistant(store):
    """assistant 完全空(连一个字都没产出且正常退出)→ 不落 assistant 噪声。"""
    tid = _thread_id(store)
    with A._ChatTurnLog(store, user_text="q", chapter=1,
                        stage="discuss", thread_id=tid):
        pass   # 没有 feed
    msgs = store.list_thread_messages(tid)
    assert [m["role"] for m in msgs] == ["user"]


def test_chatturnlog_persist_failure_is_best_effort(store, monkeypatch):
    """落库失败只告警,绝不抛(对话主链路 SSE 已在飞,不能因留痕副作用崩)。"""
    tid = _thread_id(store)

    def boom(*a, **k):
        raise RuntimeError("DB 掉线")
    monkeypatch.setattr(store, "add_chat_message", boom)
    # 不抛即通过
    with A._ChatTurnLog(store, user_text="q", chapter=1,
                        stage="discuss", thread_id=tid) as clog:
        clog.feed("x")


# ============================================================
# ② 两条 SSE 端点经真实路由落库(红→绿)
# ============================================================

def _consume(resp):
    b"".join(resp.iter_bytes())


def test_chat_stream_endpoint_persists_discussion(client, store, monkeypatch):
    """GET /chat/stream:修前 0 条留痕(bug),修后 user+assistant 落到主编线程。"""
    monkeypatch.setattr("scribe3.llm.hermes_complete_stream",
                        lambda msg, system=None, **_kw: iter(["主编", "回复", "内容"]))
    r = client.get("/chat/stream", params={"msg": "讨论一下秘会", "work": "main", "seq": 2})
    assert r.status_code == 200
    _consume(r)
    tid = _thread_id(store)
    msgs = store.list_thread_messages(tid)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["text"] == "讨论一下秘会"
    assert msgs[1]["text"] == "主编回复内容"
    assert msgs[0]["stage"] == "discuss"


def test_chat_agentic_stream_endpoint_persists_discussion(client, store, monkeypatch):
    """GET /chat/agentic-stream:同样落库,且工具/审批帧不进对话留痕(只留最终文本)。"""
    def fake_events(message, instructions, model=None, **_kw):
        # 模拟 Hermes 事件流:工具调用 + 文本 + 完成(签名/事件形状同 test_app.py 既有 agentic 测试)
        yield {"type": "response.output_item.added",
               "item": {"type": "function_call", "name": "s3_list_factions", "arguments": "{}"}}
        yield {"type": "response.output_text.delta", "delta": "根据"}
        yield {"type": "response.output_text.delta", "delta": "工具查询"}
        yield {"type": "response.completed", "response": {"id": "resp_xyz"}}
    monkeypatch.setattr(A, "_responses_events", fake_events)
    r = client.get("/chat/agentic-stream", params={"msg": "秘会有哪些人?", "work": "main", "seq": 2})
    assert r.status_code == 200
    _consume(r)
    tid = _thread_id(store)
    msgs = store.list_thread_messages(tid)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["text"] == "秘会有哪些人?"
    assert "工具查询" in msgs[1]["text"]
    # 工具/审批不该混进对话文本
    assert "tool" not in msgs[1]["text"].lower()


# ============================================================
# ③ 门禁:所有 /chat SSE 端点必须留痕或显式豁免(防复发)
# ============================================================

def test_all_chat_sse_endpoints_persist_or_are_exempt():
    """自动发现所有 /chat SSE 端点,逐个断言:源码里含留痕(add_chat_message /
    _ChatTurnLog),否则必须在 EXEMPT 集并注明原因。

    这是本仓既有纪律模式(KNOWN_REST_WRITE_ROUTES 台账 / _LIVE_TABLES 门禁)的同款:
    U-002(漏订阅表)/ U-003(漏注入点)/ U-005(漏留痕)是同一类病——"每新开一条路
    就漏一个横切关注点"。以后再加第四条对话路径,忘了留痕就过不了这条测试。
    """
    # 显式豁免:名字 → 原因(不留痕是有意的,必须写清楚为什么)
    EXEMPT = {
        # GET /chat/write:D-005 兼容端点,无生产调用方,POST 版才是真写作留痕路径。
        "chat_write": "D-005 兼容端点,无生产调用方,不落库(POST 版才留痕)",
    }
    sse = []
    for route in A.app.routes:
        path = getattr(route, "path", "")
        fn = getattr(route, "endpoint", None)
        if not path.startswith("/chat/") or fn is None:
            continue
        try:
            src = inspect.getsource(fn)
        except OSError:
            continue
        if "text/event-stream" in src:
            sse.append((fn.__name__, src))

    assert sse, "没发现任何 /chat SSE 端点——枚举逻辑坏了(路由结构变了?)"
    names = {n for n, _ in sse}
    # 至少覆盖当前已知的三条(防有人把端点删了导致门禁空转)
    assert {"chat_stream", "chat_agentic_stream", "chat_write_post"} <= names, (
        f"已知 SSE 对话端点缺失,实际发现: {names}")

    for name, src in sse:
        if name in EXEMPT:
            continue
        assert ("add_chat_message" in src) or ("_ChatTurnLog" in src), (
            f"/chat SSE 端点 {name} 既不留痕也不在 EXEMPT——主编对话会凭空消失(U-005)。"
            f"要么接 _ChatTurnLog,要么显式加入 EXEMPT 并注明原因。")


# ============================================================
# ⑥ U-009 对话连续性:留痕反哺为模型的对话记忆(修"主编每轮失忆")
# ============================================================

def _fake_stream_factory(captured, reply):
    def fake(msg, system=None, history=None, **_kw):
        captured.append({"msg": msg, "history": list(history or [])})
        yield from reply
    return fake


def test_chat_stream_two_turns_model_sees_its_own_prior_options(client, store, monkeypatch):
    """两轮端到端:主编第一轮给出方向A/B/C,第二轮作者说"选方向C"——模型的 history
    里必须有第一轮的 user 与 assistant 原文(修前 history 概念不存在,主编反问
    "方向C是什么")。"""
    captured = []
    monkeypatch.setattr("scribe3.llm.hermes_complete_stream",
                        _fake_stream_factory(captured, ["方向A:守火人线;方向B:天穹线;", "方向C:烛照碎片线"]))
    _consume(client.get("/chat/stream", params={"msg": "给我三个展开方向", "work": "main"}))
    assert captured[0]["history"] == [], "第一轮之前无历史"

    monkeypatch.setattr("scribe3.llm.hermes_complete_stream",
                        _fake_stream_factory(captured, ["好,方向C展开如下…"]))
    _consume(client.get("/chat/stream", params={"msg": "选方向C", "work": "main"}))

    h = captured[1]["history"]
    assert {"role": "user", "content": "给我三个展开方向"} in h
    assert any(m["role"] == "assistant" and "方向C:烛照碎片线" in m["content"] for m in h), (
        f"模型没看到自己上一轮给的选项,history={h}")
    # 当前这句只在 prompt 里,不得在 history 里重复出现
    assert captured[1]["msg"] == "选方向C"
    assert not any(m["content"] == "选方向C" for m in h), "本轮消息在 history 里重复"


def test_chat_history_budget_truncates_long_and_caps_count(store):
    """预算:超长消息截断(印迹回填里有整篇世界观全案)、条数封顶最近 max_msgs。"""
    tid = _thread_id(store)
    store.add_chat_message(chapter=0, stage="discuss", role="user",
                           text="超长设定" * 500, thread_id=tid)   # 2000 字
    for i in range(20):
        store.add_chat_message(chapter=0, stage="discuss",
                               role="assistant" if i % 2 else "user",
                               text=f"第{i}条", thread_id=tid)
    h = A._thread_history_for_prompt(store, tid, max_msgs=12, max_chars_each=600)
    assert len(h) <= 12
    assert all(len(m["content"]) <= 600 + 12 for m in h)   # +截断标记
    assert h[-1]["content"] == "第19条", "应取【最近】的 N 条(旧的被挤出)"


def test_chat_history_failure_now_fails_loud_with_real_cause(client, store, monkeypatch):
    """U-011 行为变更(推翻本测试旧断言):取历史失败此前静默回 []——那是主编无声失忆
    (U-009 症状借降级复发)。现在 fail-loud:SSE error 帧携带【异常原文】给前端内联显示,
    LLM 不被调用(不带残缺上下文继续),流以 done 优雅收尾(非 500 裸断)。"""
    def boom(*a, **k):
        raise RuntimeError("DB 掉线")
    monkeypatch.setattr(store, "list_thread_messages", boom)
    captured = []
    monkeypatch.setattr("scribe3.llm.hermes_complete_stream",
                        _fake_stream_factory(captured, ["ok"]))
    r = client.get("/chat/stream", params={"msg": "hi", "work": "main"})
    assert r.status_code == 200            # SSE 已开流,错误经 error 帧而非 HTTP 码
    body = b"".join(r.iter_bytes()).decode()
    assert '"error"' in body and "DB 掉线" in body, (
        f"取历史失败必须以 error 帧携带真实原因,而非静默空历史(body={body!r})")
    assert '"done": true' in body          # 流优雅收尾
    assert captured == [], "上下文组装失败后不得再调 LLM(不带残缺上下文继续)"


def test_chat_history_last_assistant_keeps_tail_where_options_live(store):
    """P1 修正(U-009 补):作者短回复"选C"的指代对象在上一条主编消息的【尾部】
    ("方向C:…"惯常收尾)。修前砍尾留头,超 600 字的选项消息会把方向C 的定义截掉,
    失忆复发。修后最后一条 assistant 拿大预算(2400)且超长时头尾各留。"""
    tid = _thread_id(store)
    store.add_chat_message(chapter=0, stage="discuss", role="user",
                           text="给我三个展开方向", thread_id=tid)
    long_options = ("方案铺垫论证。" * 400) + "方向C:烛照碎片线,代价是誊抄人暴露。"   # ~2800字,C 在最尾
    store.add_chat_message(chapter=0, stage="discuss", role="assistant",
                           text=long_options, thread_id=tid)

    h = A._thread_history_for_prompt(store, tid)
    asst = [m for m in h if m["role"] == "assistant"][-1]
    assert "烛照碎片线" in asst["content"], "最后一条 assistant 的尾部(被指代的选项)必须保住"
    assert "中段截断" in asst["content"], "超长时应头尾各留而非砍尾"
    assert len(asst["content"]) <= 2400 + 30


def test_chat_history_non_last_assistant_still_head_truncated(store):
    """非最后的 assistant 仍走小预算头部截断(大预算只给最可能被指代的那一条)。"""
    tid = _thread_id(store)
    store.add_chat_message(chapter=0, stage="discuss", role="assistant",
                           text="旧方案" * 500, thread_id=tid)      # 1500字,非最后
    store.add_chat_message(chapter=0, stage="discuss", role="user",
                           text="换个思路", thread_id=tid)
    store.add_chat_message(chapter=0, stage="discuss", role="assistant",
                           text="新方案很短", thread_id=tid)         # 最后一条 assistant
    h = A._thread_history_for_prompt(store, tid)
    old = h[0]
    assert old["role"] == "assistant" and "后文截断" in old["content"]
    assert len(old["content"]) <= 600 + 12
    assert h[-1]["content"] == "新方案很短"


# ---- P0a 多会话:thread 参数贯通(零降级:无效 404 / 归档 409 / 跨 work 409,绝不回落)----

def test_chat_stream_thread_param_routes_messages(client, store, monkeypatch):
    """P0a 核心:传 thread → 消息落指定线程,不落 active 线程。
    注意顺序:先建 default(get_or_create 取最早 active),再建 t2——否则 default==t2 恒真。"""
    default = store.get_or_create_editorial_thread("main", "author")
    t2 = store.create_editorial_thread("main", "author")
    assert t2["thread_id"] != default["thread_id"]
    captured = []
    monkeypatch.setattr("scribe3.llm.hermes_complete_stream",
                        _fake_stream_factory(captured, ["好"]))
    r = client.get("/chat/stream", params={"msg": "落到新会话", "work": "main",
                                           "thread": t2["thread_id"]})
    assert r.status_code == 200
    b"".join(r.iter_bytes())
    msgs = store.list_thread_messages(t2["thread_id"])
    assert any("落到新会话" in (m.get("text") or "") for m in msgs)
    assert not any("落到新会话" in (m.get("text") or "")
                   for m in store.list_thread_messages(default["thread_id"]))


def test_chat_stream_invalid_thread_404_archived_409_no_fallback(client, store, monkeypatch):
    """零降级:无效/已归档/跨 work thread 绝不静默回落 active——404/409 抛。"""
    monkeypatch.setattr("scribe3.llm.hermes_complete_stream",
                        lambda *a, **k: iter(["x"]))
    r = client.get("/chat/stream", params={"msg": "hi", "work": "main",
                                           "thread": "ethread:main:nope"})
    assert r.status_code == 404
    t = store.create_editorial_thread("main", "author")
    store.update_editorial_thread_meta(t["thread_id"], status="archived")
    r2 = client.get("/chat/stream", params={"msg": "hi", "work": "main",
                                            "thread": t["thread_id"]})
    assert r2.status_code == 409   # 已归档:存在但不可写
    r3 = client.get("/chat/stream", params={"msg": "hi", "work": "other",
                                            "thread": t["thread_id"]})
    assert r3.status_code == 409   # 跨 work


def test_chat_agentic_thread_param_routes_messages(client, store, monkeypatch):
    """agentic 同样贯通:传 thread → 留痕落指定线程(先建 default 防 t2 即最早 active 的恒真)。"""
    import scribe3.app as A
    default = store.get_or_create_editorial_thread("main", "author")
    t2 = store.create_editorial_thread("main", "author")
    monkeypatch.setattr(A, "_responses_events",
                        lambda *a, **k: iter([{"type": "response.output_text.delta", "delta": "答"},
                                              {"type": "response.completed", "response": {"id": "r1"}}]))
    r = client.get("/chat/agentic-stream", params={"msg": "agentic落新会话", "work": "main",
                                                   "thread": t2["thread_id"]})
    assert r.status_code == 200
    b"".join(r.iter_bytes())
    msgs = store.list_thread_messages(t2["thread_id"])
    assert any("agentic落新会话" in (m.get("text") or "") for m in msgs)
    assert not any("agentic落新会话" in (m.get("text") or "")
                   for m in store.list_thread_messages(default["thread_id"]))


def test_chat_stream_no_thread_param_byte_compatible(client, store, monkeypatch):
    """不传 thread=文档化默认(active 线程)——旧调用方行为字节不变。"""
    captured = []
    monkeypatch.setattr("scribe3.llm.hermes_complete_stream",
                        _fake_stream_factory(captured, ["好"]))
    r = client.get("/chat/stream", params={"msg": "旧调用", "work": "main"})
    assert r.status_code == 200
    b"".join(r.iter_bytes())
    default = store.get_or_create_editorial_thread("main", "author")
    assert any("旧调用" in (m.get("text") or "")
               for m in store.list_thread_messages(default["thread_id"]))
