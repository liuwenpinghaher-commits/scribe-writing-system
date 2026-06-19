"""C3-3 编排状态机 自检:合法转移、非法拒绝、持久化、终态。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.orchestrator import (Orchestrator, legal_transition, STATES, INITIAL,  # noqa: E402
                                     TERMINAL)


def test_transition_rules():
    assert len(STATES) == 15
    assert legal_transition("PLANNING", "OUTLINED")
    assert legal_transition("DRAFTING", "DRAFTED")
    assert not legal_transition("PLANNING", "DONE")       # 不能跳过
    assert not legal_transition("DONE", "DRAFTING")       # 终态不出
    assert "DONE" in TERMINAL


def test_persist_and_advance():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    o = Orchestrator(d)
    t = o.ensure(w, 1)
    assert t["status"] == INITIAL
    # 合法链路
    o.advance(w, 1, "OUTLINED")
    o.advance(w, 1, "DRAFTING")
    o.advance(w, 1, "DRAFTED")
    o.advance(w, 1, "REVIEWING")
    o.advance(w, 1, "CONSISTENCY_CHECK")
    o.advance(w, 1, "MEMORY_UPDATE")
    t = o.advance(w, 1, "DONE")
    assert t["status"] == "DONE"
    # 非法转移被拒
    try:
        o.advance(w, 1, "DRAFTING")
        assert False, "终态不该能推进"
    except ValueError:
        pass
    # 持久化:重新取仍是 DONE
    assert o.get(w, 1)["status"] == "DONE"
    print("  ✓ test_transition_rules / test_persist_and_advance")


if __name__ == "__main__":
    test_transition_rules()
    test_persist_and_advance()
    print("\n通过。")
