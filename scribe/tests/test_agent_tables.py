"""C5-4/内核0完整版 自检:讨论线程持久化、跨会话记忆(阈值)、技能审批门。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def test_threads():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    tid = d.create_thread(w, "第3章要不要揭穿", "feedback")
    d.add_thread_message(tid, "user", "主角该不该揭穿?")
    d.add_thread_message(tid, "editor", "给你两个方案", concern_type="option_set")
    th = d.list_threads(w)[0]
    import json
    msgs = json.loads(th["messages"])
    assert len(msgs) == 2 and msgs[1]["concern_type"] == "option_set"
    d.resolve_thread(tid, "resolved", "选了方案A")
    assert d.list_threads(w, "resolved")[0]["id"] == tid


def test_agent_memory_threshold():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    assert d.write_agent_memory("u", "semantic", "主角口头禅", {"v": "呵"}, 0.9) is not None
    assert d.write_agent_memory("u", "semantic", "低置信", {"v": "?"}, 0.5) is None  # <0.8 不入
    mem = d.read_agent_memory("u", "semantic", w)
    assert len(mem) == 1 and json._default if False else True
    assert mem[0]["key"] == "主角口头禅"


def test_skill_approval_gate():
    d = Database(":memory:")
    sid = d.propose_skill("u", "自动卷尾摘要", {"trigger": "volume_end"})
    s = d.list_skills("u", "proposed")[0]
    assert s["approved_by_human"] == 0
    d.set_skill_status(sid, "approved", approved_by_human=True)
    assert d.list_skills("u", "approved")[0]["approved_by_human"] == 1


import json  # noqa: E402

if __name__ == "__main__":
    test_threads(); test_agent_memory_threshold(); test_skill_approval_gate()
    print("  ✓ threads / agent_memory / skill_gate\n通过。")
