"""C2-1/C2-4/C2-6 自检:章摄取解析、落库(记忆/状态/时间线/关系)、时间对齐查询。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402
from scribe_mcp.memory import parse_ingest, ingest_chapter  # noqa: E402


def test_parse_ingest():
    r = parse_ingest('前言。{"summary":"沈砚揭穿卧底","char_states":[{"name":"沈砚","state":"暴露身份","change_type":"status"}],"timeline":[{"description":"地下室对峙","order":1}],"relations":[{"src":"沈砚","dst":"裴姞","relation":"敌对"}]} 后记')
    assert r["summary"] == "沈砚揭穿卧底"
    assert r["char_states"][0]["name"] == "沈砚"
    assert r["timeline"][0]["order"] == 1
    assert r["relations"][0]["relation"] == "敌对"
    assert parse_ingest("乱码无json")["summary"] == ""


def test_ingest_and_time_align():
    d = Database(":memory:")
    w = d.create_work("u", "书")
    d.upsert_character(w, "沈砚")
    for s in (1, 2, 3):
        cid = d.save_chapter(w, s, f"第{s}章")
        d.save_snapshot(w, cid, f"第{s}章正文,沈砚做了事{s}。", created_by="ai")

    def fake(prompt: str) -> str:
        # 从 prompt 里读出章号,造对应摘要/状态
        import re
        seq = re.search(r"第 (\d+) 章", prompt)
        if seq:
            n = seq.group(1)
            return ('{"summary":"第%s章梗概","char_states":[{"name":"沈砚","state":"状态%s","change_type":"status"}],'
                    '"timeline":[{"description":"事件%s","order":1}],"relations":[]}') % (n, n, n)
        return "全书主线压缩。"

    for s in (1, 2, 3):
        ingest_chapter(d, fake, w, s)

    # 记忆:3 章 + global
    mems = d.list_chapter_memories(w)
    assert [m["seq"] for m in mems] == [1, 2, 3]
    assert d.get_memory(w, "global") is not None
    # C2-6 时间对齐:截至第2章只看到 ≤2 的记忆
    assert [m["seq"] for m in d.list_chapter_memories(w, upto_seq=2)] == [1, 2]
    # 角色状态时点查询:截至第2章 → 状态2
    c = d.get_character_by_name(w, "沈砚")
    assert d.get_char_state_at(c["id"], 2)["state_desc"] == "状态2"
    assert d.get_char_state_at(c["id"], 3)["state_desc"] == "状态3"
    # 时间线 ≤2
    assert len(d.list_timeline(w, upto_seq=2)) == 2
    print("  ✓ test_parse_ingest / test_ingest_and_time_align")


if __name__ == "__main__":
    test_parse_ingest()
    test_ingest_and_time_align()
    print("\n通过。")
