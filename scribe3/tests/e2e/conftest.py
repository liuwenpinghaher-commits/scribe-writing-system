"""e2e 确定性档夹具:真打端点全链路,只 LLM 边界是可编程替身。

复用上级 conftest 的 store/_isolated_llm_ledger/_clear_context_caches(autouse)。
本文件只加 LLM 替身 + 绑好 store 的 TestClient。
"""
import pytest
from fastapi.testclient import TestClient


class LlmStub:
    """可编程 LLM 边界替身。默认正常回流;可注入故障测 fail-loud;记录每次调用(含 history)。"""

    def __init__(self):
        self._reply_deltas = ["好", "的"]
        self._exc = None
        self._events = []
        self.calls = []  # 每次 LLM 调用的 kwargs 快照,含 history/system

    def reply(self, text):
        """设定下一次流式回流的文本(按字符切成 deltas)。"""
        self._reply_deltas = list(text)
        self._exc = None

    def fail(self, exc):
        """设定下一次 LLM 调用抛出的异常(测 fail-loud)。"""
        self._exc = exc

    def responses(self, events):
        """设定 agentic 事件流(hermes_responses_events 的产出)。"""
        self._events = list(events)
        self._exc = None

    def hermes_complete_stream(self, msg, system=None, history=None, **kw):
        self.calls.append({"msg": msg, "system": system, "history": history, **kw})
        if self._exc:
            raise self._exc
        return iter(self._reply_deltas)

    complete_stream = hermes_complete_stream

    def hermes_responses_events(self, message, instructions, **kwargs):
        self.calls.append({"message": message, "instructions": instructions, **kwargs})
        if self._exc:
            raise self._exc
        return iter(self._events)

    responses_events = hermes_responses_events

    @property
    def last_history(self):
        return self.calls[-1].get("history") if self.calls else None


@pytest.fixture()
def llm_stub(monkeypatch):
    stub = LlmStub()
    import scribe3.llm as llm
    monkeypatch.setattr(llm, "hermes_complete_stream", stub.complete_stream)
    monkeypatch.setattr(llm, "hermes_responses_events", stub.responses_events)
    return stub


@pytest.fixture()
def full_stack(store, llm_stub):
    """绑好临时 store + LLM 替身的 TestClient。测试再请求 store/llm_stub 拿同实例。"""
    import scribe3.app as A
    A.set_store(store)
    return TestClient(A.app)
