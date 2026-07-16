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
