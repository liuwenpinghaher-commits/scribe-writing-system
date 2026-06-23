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
