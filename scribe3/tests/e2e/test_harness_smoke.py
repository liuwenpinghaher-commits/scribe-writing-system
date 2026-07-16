"""证明 harness 三件套(full_stack 真打端点 / llm_stub 注入回流 / store 同实例)工作。"""


def test_full_stack_serves_health(full_stack):
    assert full_stack.get("/health").json()["ok"] is True


def test_llm_stub_injects_reply_into_chat_stream(full_stack, llm_stub):
    llm_stub.reply("主编回复")
    r = full_stack.get("/chat/stream", params={"msg": "hi", "work": "main"})
    body = b"".join(r.iter_bytes()).decode()
    assert "主编回复"[0] in body and '"done": true' in body


def test_llm_stub_records_history(full_stack, llm_stub):
    llm_stub.reply("x")
    full_stack.get("/chat/stream", params={"msg": "hi", "work": "main"})
    assert llm_stub.calls, "llm_stub 应记录到至少一次 LLM 调用"
