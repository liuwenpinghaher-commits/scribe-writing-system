"""写作层移植 Phase4:验证生成走 Hermes 的 OpenAI 兼容端点(mock httpx,无需 hermes 在跑)。"""
import scribe2.llm as llm


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": "渡叔立于船头,独眼望浊浪。"}}]}


def test_hermes_complete_routes_to_chat_completions(monkeypatch):
    captured = {}

    def fake_post(url, **kw):
        captured["url"] = url
        captured["json"] = kw["json"]
        captured["headers"] = kw["headers"]
        return _FakeResp()

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    out = llm.hermes_complete("写渡叔夜渡一段", system="你是古典小说主笔")
    assert out == "渡叔立于船头,独眼望浊浪。"
    # 走 hermes 网关的 OpenAI 兼容端点(非直连火山)
    assert captured["url"].endswith("/chat/completions")
    assert "8642" in captured["url"]
    assert captured["json"]["messages"][0]["role"] == "system"
    assert captured["json"]["messages"][-1]["content"] == "写渡叔夜渡一段"
    assert captured["headers"]["Authorization"].startswith("Bearer ")
