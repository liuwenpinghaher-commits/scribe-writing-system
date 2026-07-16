"""矩阵⑥:两轮对话,第二轮模型能看见第一轮(history 真注入),非失忆(U-009/U-005)。"""


def test_second_turn_sees_first_turn_in_history(full_stack, llm_stub):
    """第一轮主编给方案 → 第二轮 llm_stub 收到的 history 含第一轮 assistant 内容。"""
    llm_stub.reply("方案A或方案B")
    r1 = full_stack.get("/chat/stream", params={"msg": "给我两个方案", "work": "main"})
    b"".join(r1.iter_bytes())                 # 消费第一轮(触发落痕)

    llm_stub.reply("好的选A")
    r2 = full_stack.get("/chat/stream", params={"msg": "选A", "work": "main"})
    b"".join(r2.iter_bytes())

    hist = llm_stub.last_history
    assert hist, "第二轮必须带 history(非失忆)"
    joined = " ".join(str(m.get("content", "")) for m in hist)
    assert "方案A或方案B" in joined, f"第二轮 history 应含第一轮主编回复,实际={hist!r}"
    assert "给我两个方案" in joined, "第二轮 history 应含第一轮用户提问"


def test_thread_isolation_no_cross_thread_history_bleed(full_stack, llm_stub, store):
    """P0a 对抗:A 线程聊过的内容,B 线程的 LLM history 绝不可见(串台=多会话新失效模式)。
    顺序:先落 A(active 默认线程),再建 B——防 B 即最早 active 的恒真。"""
    llm_stub.reply("A线程回复")
    r1 = full_stack.get("/chat/stream", params={"msg": "A线程的机密讨论", "work": "main"})
    b"".join(r1.iter_bytes())                      # 落 active(默认)线程

    t_b = store.create_editorial_thread("main", "author")
    llm_stub.reply("B线程回复")
    r2 = full_stack.get("/chat/stream", params={"msg": "B线程新话题", "work": "main",
                                                "thread": t_b["thread_id"]})
    assert r2.status_code == 200
    b"".join(r2.iter_bytes())

    hist = llm_stub.last_history or []
    joined = " ".join(str(m.get("content", "")) for m in hist)
    assert "A线程的机密讨论" not in joined, f"跨线程历史串台:{hist!r}"
    assert "A线程回复" not in joined
