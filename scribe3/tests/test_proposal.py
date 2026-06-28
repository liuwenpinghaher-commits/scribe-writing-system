import scribe3.app as A
from scribe3.proposal import ProposalParser


def test_plain_delta():
    p = ProposalParser()
    assert p.feed("主编回话") == [("delta", "主编回话")]   # 无疑似标记 → 立即吐
    assert p.flush() == []


def test_holds_partial_marker_tail():
    p = ProposalParser()
    assert p.feed("文字⟦PROP") == [("delta", "文字")]   # ⟦PROP 可能是标记前缀,留住
    assert p.flush() == [("delta", "⟦PROP")]            # 终究不是真标记,flush 吐出


def test_proposal_block_whole():
    p = ProposalParser()
    ev = p.feed("好的：⟦PROPOSAL scope=selection⟧新散文⟦/PROPOSAL⟧收工") + p.flush()
    assert ("delta", "好的：") in ev
    assert ("proposal_open", "selection") in ev
    assert ("proposal_delta", "新散文") in ev
    assert ("proposal_close", None) in ev
    assert ev[-1] == ("delta", "收工")


def test_split_marker_across_chunks():
    p = ProposalParser()
    out = []
    for c in ["前文⟦PROPO", "SAL scope=chapter⟧整章", "草稿⟦/PRO", "POSAL⟧尾"]:
        out += p.feed(c)
    out += p.flush()
    assert ("proposal_open", "chapter") in out
    assert ("proposal_close", None) in out
    txt = "".join(t for k, t in out if k == "proposal_delta")
    assert txt == "整章草稿"
    assert ("delta", "前文") in out and ("delta", "尾") in out


# ── G2a: proposal 围栏兜底(fallback)测试 ───────────────────────────────────


def test_stream_write_fallback_wraps_fenceless_prose(monkeypatch):
    """模型忘写围栏,但散文足够长(≥120字) → 在流末尾自动包成 chapter 提案(带 fallback=true)。"""
    prose = "老乌头守着铁炉坐了半宿。" * 12   # >120 chars
    assert len(prose) >= 120, "前置断言:prose 须足够长"

    def fake_events(msg, instructions, model=None):
        yield {"type": "response.output_text.delta", "delta": prose}

    monkeypatch.setattr(A, "_responses_events", fake_events)
    events = list(A._stream_write("帮我写本章", "instr", expect_proposal=True))
    blob = "".join(events)
    assert '"proposal"' in blob, "应有 proposal 事件"
    assert '"scope": "chapter"' in blob, "scope 应为 chapter"
    assert '"fallback": true' in blob, "应标注 fallback=true"
    # 确认 delta 照常推送(用户能看到文本流)
    assert '"delta"' in blob


def test_stream_write_no_fallback_when_fence_present(monkeypatch):
    """模型正确输出围栏 → 只有 1 个 proposal 事件,不再追加兜底事件(无双发)。"""
    def fake_events(msg, instructions, model=None):
        yield {"type": "response.output_text.delta",
               "delta": "思路：⟦PROPOSAL scope=chapter⟧正文正文正文⟦/PROPOSAL⟧"}

    monkeypatch.setattr(A, "_responses_events", fake_events)
    events = list(A._stream_write("写", "instr", expect_proposal=True))
    blob = "".join(events)
    # 正好 1 个 proposal,不能有兜底第 2 个
    assert blob.count('"proposal"') == 1, f"应只有 1 个 proposal,实际: {blob.count('\"proposal\"')}"
    assert '"fallback"' not in blob, "真围栏路径不应含 fallback 字段"


def test_stream_write_no_fallback_for_short_discussion(monkeypatch):
    """短回复(讨论句式,<120字) + expect_proposal=False → 不应产生任何 proposal 事件。"""
    def fake_events(msg, instructions, model=None):
        yield {"type": "response.output_text.delta", "delta": "我觉得可以。"}

    monkeypatch.setattr(A, "_responses_events", fake_events)
    events = list(A._stream_write("你觉得呢", "instr", expect_proposal=False))
    blob = "".join(events)
    assert '"proposal"' not in blob, "短讨论不应有 proposal 事件"


def test_stream_write_no_fallback_short_prose_with_write_intent(monkeypatch):
    """即使 expect_proposal=True,若散文 <120 字,也不应触发兜底(防把短确认误包成草稿)。"""
    def fake_events(msg, instructions, model=None):
        yield {"type": "response.output_text.delta", "delta": "好的,我来写。"}

    monkeypatch.setattr(A, "_responses_events", fake_events)
    events = list(A._stream_write("帮我写", "instr", expect_proposal=True))
    blob = "".join(events)
    assert '"proposal"' not in blob, "短文本不应有 proposal 事件"


def test_is_write_intent_detection():
    """_is_write_intent 应正确识别含写作动词的用户消息。"""
    assert A._is_write_intent("帮我写本章") is True
    assert A._is_write_intent("续写到天亮") is True
    assert A._is_write_intent("把这段改得冷一点") is True
    assert A._is_write_intent("本章节奏如何") is True
    assert A._is_write_intent("重写这里") is True
    assert A._is_write_intent("你觉得节奏怎么样") is False
    assert A._is_write_intent("这章结构好吗") is False
