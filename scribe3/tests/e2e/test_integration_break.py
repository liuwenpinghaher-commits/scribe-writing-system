"""矩阵⑤:外部依赖(LLM 网关)断裂 → SSE error 帧优雅收尾,前端拿到可显示错误而非 500 白屏
(U-008 网关 down→连接被拒)。"""
from scribe3.tests.e2e.asserts import assert_error_frame_carries_cause


def test_chat_stream_gateway_down_yields_error_frame_not_500(full_stack, llm_stub):
    """LLM 网关连接被拒 → /chat/stream 仍 200 开流,错误经 error 帧带原文 + done 收尾。"""
    llm_stub.fail(ConnectionError("网关 :8644 连接被拒"))
    r = full_stack.get("/chat/stream", params={"msg": "hi", "work": "main"})
    assert r.status_code == 200, "SSE 已开流,错误应走 error 帧而非 HTTP 码"
    assert_error_frame_carries_cause(r, "连接被拒")


def test_chat_agentic_gateway_down_yields_error_frame(full_stack, llm_stub):
    """agentic 端点同样:网关 down → error 帧,不裸崩。"""
    llm_stub.fail(ConnectionError("网关 :8643 连接被拒"))
    r = full_stack.get("/chat/agentic-stream", params={"msg": "hi", "work": "main"})
    assert r.status_code == 200
    assert_error_frame_carries_cause(r, "连接被拒")
