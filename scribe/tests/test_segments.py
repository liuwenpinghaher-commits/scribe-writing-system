"""P0-2 段落化 + 规则引用 自检。"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scribe_mcp.db import Database  # noqa: E402


def _db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    return Database(tmp.name)


def test_segment_split_and_citation():
    db = _db()
    w = db.create_work("u", "书")
    db.upsert_character(w, "林越")
    db.upsert_setting(w, "item", "断魂剑")
    cid = db.save_chapter(w, 1)
    content = "林越握紧了断魂剑。\n窗外下着雨。\n他想起了断魂剑的来历。"
    n = db.save_segments(w, cid, content, created_by="ai")
    assert n == 3
    segs = db.list_segments(cid)
    assert [s["seq"] for s in segs] == [0, 1, 2]
    # 第0段引用 林越 + 断魂剑;第1段无引用;第2段引用 断魂剑
    c0 = {x["name"] for x in json.loads(segs[0]["citation_refs"])}
    c1 = json.loads(segs[1]["citation_refs"])
    c2 = {x["name"] for x in json.loads(segs[2]["citation_refs"])}
    assert c0 == {"林越", "断魂剑"}
    assert c1 == []
    assert c2 == {"断魂剑"}
    assert segs[0]["created_by"] == "ai"


def test_resegment_replaces():
    db = _db()
    w = db.create_work("u", "书"); cid = db.save_chapter(w, 1)
    db.save_segments(w, cid, "一段。\n二段。", "ai")
    db.save_segments(w, cid, "只剩一段。", "human")  # 重切应替换
    segs = db.list_segments(cid)
    assert len(segs) == 1 and segs[0]["created_by"] == "human"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ✓ {fn.__name__}")
    print(f"\n全部 {len(fns)} 项通过。")


if __name__ == "__main__":
    _run_all()
